#!/usr/bin/env python3
"""Persistent status cache for product-compliance standard verification."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SCHEMA = """
CREATE TABLE IF NOT EXISTS standard_status_cache (
    canonical_number TEXT PRIMARY KEY,
    standard_type TEXT NOT NULL,
    status TEXT NOT NULL,
    publish_date TEXT,
    effective_date TEXT,
    abolish_or_replace_date TEXT,
    replacement_standard TEXT,
    source_url TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS standard_lookup_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_number TEXT NOT NULL,
    standard_type TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    result_summary TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_standard_lookup_attempts_number
ON standard_lookup_attempts(canonical_number, attempted_at);
"""


def default_db_path() -> Path:
    base = os.environ.get("CODEX_HOME")
    if base:
        return Path(base) / "state" / "product-compliance-review" / "standard_status.sqlite3"
    return Path.home() / ".codex" / "state" / "product-compliance-review" / "standard_status.sqlite3"


def canonicalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").upper().strip()
    text = re.sub(r"[‐‑‒–—―−]", "-", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(GB/T|GB|FZ/T|T/[A-Z0-9]+|Q/[A-Z0-9]+)\s*(?=\d)", r"\1 ", text)
    return text.strip()


def parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    return connection


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_record(connection: sqlite3.Connection, standard: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM standard_status_cache WHERE canonical_number = ?",
        (canonicalize(standard),),
    ).fetchone()


def event_refresh_reason(record: sqlite3.Row, now: datetime) -> str | None:
    checked = parse_datetime(record["checked_at"]).date()
    today = now.date()
    for field in ("effective_date", "abolish_or_replace_date"):
        event = parse_date(record[field])
        if not event:
            continue
        delta = (event - today).days
        if 0 <= delta <= 60:
            return "status_event_within_60_days"
        if checked < event <= today:
            return "status_event_passed_since_check"
    return None


def command_get(connection: sqlite3.Connection, args: argparse.Namespace) -> dict:
    canonical = canonicalize(args.standard)
    record = get_record(connection, canonical)
    if record is None:
        return {"decision": "miss", "canonical_number": canonical}

    now = parse_datetime(args.now)
    latest_failure = connection.execute(
        """SELECT attempted_at FROM standard_lookup_attempts
        WHERE canonical_number = ? AND outcome = 'official_timeout_or_miss'
        ORDER BY attempted_at DESC LIMIT 1""",
        (canonical,),
    ).fetchone()
    event_reason = event_refresh_reason(record, now)
    ttl_days = 30 if record["standard_type"] in {"national", "industry"} else 7
    age_days = (now - parse_datetime(record["checked_at"])).total_seconds() / 86400
    decision = "fresh"
    reason = "within_ttl"
    if latest_failure and parse_datetime(latest_failure["attempted_at"]) > parse_datetime(record["checked_at"]):
        decision, reason = "refresh_required", "previous_lookup_failed"
    elif event_reason:
        decision, reason = "refresh_required", event_reason
    elif age_days > ttl_days:
        decision, reason = "refresh_required", "cache_expired"

    result = row_to_dict(record)
    result.update(
        decision=decision,
        reason=reason,
        ttl_days=ttl_days,
        age_days=round(max(age_days, 0), 3),
    )
    return result


def command_put(connection: sqlite3.Connection, args: argparse.Namespace) -> dict:
    canonical = canonicalize(args.standard)
    replacement = canonicalize(args.replacement_standard) if args.replacement_standard else None
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    values = (
        canonical,
        args.standard_type,
        args.status,
        args.publish_date,
        args.effective_date,
        args.abolish_or_replace_date,
        replacement,
        args.source_url,
        args.checked_at,
        args.summary,
        now,
    )
    connection.execute(
        """
        INSERT INTO standard_status_cache (
            canonical_number, standard_type, status, publish_date, effective_date,
            abolish_or_replace_date, replacement_standard, source_url, checked_at,
            result_summary, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(canonical_number) DO UPDATE SET
            standard_type=excluded.standard_type,
            status=excluded.status,
            publish_date=excluded.publish_date,
            effective_date=excluded.effective_date,
            abolish_or_replace_date=excluded.abolish_or_replace_date,
            replacement_standard=excluded.replacement_standard,
            source_url=excluded.source_url,
            checked_at=excluded.checked_at,
            result_summary=excluded.result_summary,
            updated_at=excluded.updated_at
        """,
        values,
    )
    connection.commit()
    return {"decision": "stored", "canonical_number": canonical}


def command_record_failure(connection: sqlite3.Connection, args: argparse.Namespace) -> dict:
    canonical = canonicalize(args.standard)
    connection.execute(
        """INSERT INTO standard_lookup_attempts
        (canonical_number, standard_type, attempted_at, outcome, result_summary)
        VALUES (?, ?, ?, 'official_timeout_or_miss', ?)""",
        (canonical, args.standard_type, args.attempted_at, args.summary),
    )
    connection.commit()
    record = get_record(connection, canonical)
    if record is None:
        return {
            "decision": "no_cache_network_failure",
            "canonical_number": canonical,
            "summary": args.summary,
        }
    cached = row_to_dict(record)
    checked_date = parse_datetime(record["checked_at"]).date().isoformat()
    cached.update(
        decision="stale_fallback",
        cache_checked_at=record["checked_at"],
        network_failure_summary=args.summary,
        display_note=f"网络查询失败；使用历史缓存，缓存核验日期：{checked_date}。",
    )
    return cached


def command_prepare_run(args: argparse.Namespace) -> dict:
    values = json.loads(args.standards_json)
    if not isinstance(values, list):
        raise ValueError("standards-json must be a JSON array")
    standards = sorted({canonicalize(str(item)) for item in values if canonicalize(str(item))})
    return {"input_count": len(values), "unique_count": len(standards), "standards": standards}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=default_db_path())
    commands = parser.add_subparsers(dest="command", required=True)

    get_parser = commands.add_parser("get")
    get_parser.add_argument("--standard", required=True)
    get_parser.add_argument("--now", required=True)

    put_parser = commands.add_parser("put")
    put_parser.add_argument("--standard", required=True)
    put_parser.add_argument("--type", dest="standard_type", required=True,
                            choices=["national", "industry", "enterprise", "group", "other"])
    put_parser.add_argument("--status", required=True)
    put_parser.add_argument("--publish-date")
    put_parser.add_argument("--effective-date")
    put_parser.add_argument("--abolish-or-replace-date")
    put_parser.add_argument("--replacement-standard")
    put_parser.add_argument("--source-url", required=True)
    put_parser.add_argument("--checked-at", required=True)
    put_parser.add_argument("--summary", required=True)

    failure_parser = commands.add_parser("record-failure")
    failure_parser.add_argument("--standard", required=True)
    failure_parser.add_argument("--type", dest="standard_type", required=True,
                                choices=["national", "industry", "enterprise", "group", "other"])
    failure_parser.add_argument("--attempted-at", required=True)
    failure_parser.add_argument("--summary", required=True)

    prepare_parser = commands.add_parser("prepare-run")
    prepare_parser.add_argument("--standards-json", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "prepare-run":
            result = command_prepare_run(args)
        else:
            with connect(args.db) as connection:
                if args.command == "get":
                    result = command_get(connection, args)
                elif args.command == "put":
                    result = command_put(connection, args)
                else:
                    result = command_record_failure(connection, args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

