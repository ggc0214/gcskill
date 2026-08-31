#!/usr/bin/env python3
"""Create, normalize, and validate the canonical compliance-audit result JSON."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from standard_cache import canonicalize


SCHEMA_VERSION = "1.0"
REQUIREMENT_ORDER = {"必须整改": 0, "需补证": 1, "人工确认": 2}
RISK_ORDER = {"红色": 0, "橙色": 1, "黄色": 2}
ABNORMAL_STATUSES = {
    "废止",
    "被代替",
    "即将实施",
    "官方接口超时/未命中",
    "历史缓存回退",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("audit result must be a JSON object")
    return value


def dump_json(value: dict[str, Any], path: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def new_result(mode: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_id": "",
        "review_date": date.today().isoformat(),
        "mode": mode,
        "inputs": {"marketing_images": [], "reports": []},
        "coverage": {
            "marketing_regions": [],
            "report_pages": [],
            "uncovered_marketing_regions": [],
            "uncovered_report_pages": [],
        },
        "report_rows": [],
        "standards": [],
        "claims": [],
        "issues": [],
        "supported_claims": [],
        "materials": {},
    }


def text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def requirement_rank(value: Any) -> int:
    return REQUIREMENT_ORDER.get(text(value), 99)


def risk_rank(value: Any) -> int:
    value_text = text(value)
    for key, rank in RISK_ORDER.items():
        if key in value_text:
            return rank
    return 99


def issue_sort_key(issue: dict[str, Any]) -> tuple[Any, ...]:
    source_order = issue.get("source_order", 999999)
    if isinstance(source_order, list):
        source_order = tuple(source_order)
    else:
        source_order = (source_order,)
    return (
        requirement_rank(issue.get("requirement")),
        risk_rank(issue.get("risk_level")),
        source_order,
        text(issue.get("id")),
    )


def normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    value.setdefault("schema_version", SCHEMA_VERSION)
    value.setdefault("review_date", date.today().isoformat())
    value.setdefault("inputs", {"marketing_images": [], "reports": []})
    value.setdefault("coverage", {})
    for key in (
        "marketing_regions",
        "report_pages",
        "uncovered_marketing_regions",
        "uncovered_report_pages",
    ):
        value["coverage"].setdefault(key, [])
    for key in ("report_rows", "standards", "claims", "issues", "supported_claims"):
        value.setdefault(key, [])
    value.setdefault("materials", {})

    for row in value["report_rows"]:
        row["standard_numbers"] = sorted(
            {canonicalize(item) for item in row.get("standard_numbers", []) if canonicalize(item)}
        )
    for standard in value["standards"]:
        standard["standard_number"] = canonicalize(standard.get("standard_number", ""))
        standard.setdefault("occurrences", [])
        standard.setdefault("lookup_result", "")
        standard.setdefault("lookup_method", "")
    value["standards"].sort(key=lambda item: item["standard_number"])
    value["issues"].sort(key=issue_sort_key)
    return value


def standard_inventory_from_rows(value: dict[str, Any]) -> set[str]:
    return {
        canonicalize(number)
        for row in value.get("report_rows", [])
        for number in row.get("standard_numbers", [])
        if canonicalize(number)
    }


def standard_inventory_from_results(value: dict[str, Any]) -> set[str]:
    return {
        canonicalize(item.get("standard_number", ""))
        for item in value.get("standards", [])
        if canonicalize(item.get("standard_number", ""))
    }


def validate(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_top = {
        "schema_version",
        "audit_id",
        "review_date",
        "mode",
        "inputs",
        "coverage",
        "report_rows",
        "standards",
        "issues",
        "supported_claims",
        "materials",
    }
    missing_top = sorted(required_top - set(value))
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(missing_top)}")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if value.get("mode") not in {"typo_only", "standards_only", "full"}:
        errors.append("mode must be typo_only, standards_only, or full")

    coverage = value.get("coverage", {})
    for key in ("uncovered_marketing_regions", "uncovered_report_pages"):
        if coverage.get(key):
            errors.append(f"coverage is incomplete: {key} is not empty")

    inventory = standard_inventory_from_rows(value)
    result_set = standard_inventory_from_results(value)
    missing = sorted(inventory - result_set)
    extra = sorted(result_set - inventory)
    if missing:
        errors.append("standards missing from status results: " + ", ".join(missing))
    if extra:
        errors.append("status results not found in report rows: " + ", ".join(extra))

    standards_by_number: dict[str, dict[str, Any]] = {}
    for item in value.get("standards", []):
        number = canonicalize(item.get("standard_number", ""))
        if not number:
            errors.append("standard result contains a blank standard_number")
            continue
        if number in standards_by_number:
            errors.append(f"duplicate standard result: {number}")
        standards_by_number[number] = item
        if not item.get("occurrences"):
            errors.append(f"standard has no occurrence location: {number}")
        if not text(item.get("lookup_result")):
            errors.append(f"standard has no lookup_result: {number}")

    issues = value.get("issues", [])
    if issues != sorted(issues, key=issue_sort_key):
        errors.append("issues are not in deterministic mandatory/risk/source order")
    issue_ids: set[str] = set()
    for issue in issues:
        issue_id = text(issue.get("id"))
        if not issue_id:
            errors.append("issue contains a blank id")
        elif issue_id in issue_ids:
            errors.append(f"duplicate issue id: {issue_id}")
        issue_ids.add(issue_id)
        if issue.get("category") == "确认错别字":
            if issue.get("requirement") != "必须整改" or "橙色" not in text(issue.get("risk_level")):
                errors.append(f"confirmed typo must be orange and mandatory: {issue_id}")
        if issue.get("requirement") not in REQUIREMENT_ORDER:
            errors.append(f"invalid issue requirement: {issue_id}")

    for number, item in standards_by_number.items():
        status = text(item.get("status"))
        method = text(item.get("lookup_method"))
        abnormal = status in ABNORMAL_STATUSES or method == "历史缓存回退"
        if not abnormal:
            continue
        linked = [
            issue
            for issue in issues
            if number in {canonicalize(v) for v in issue.get("standard_numbers", [])}
        ]
        if not linked:
            errors.append(f"abnormal standard is not linked to an issue: {number}")
        for occurrence in item.get("occurrences", []):
            occurrence_key = "|".join(
                text(occurrence.get(key))
                for key in ("source_pdf", "page", "sample_part", "test_item")
            )
            if occurrence_key and not any(
                occurrence_key == text(link.get("occurrence_key")) for link in linked
            ):
                errors.append(
                    f"abnormal standard occurrence is not linked to an issue: {number} @ {occurrence_key}"
                )

    report_inputs = value.get("inputs", {}).get("reports", [])
    expected_pages = {
        (text(report.get("path")), page)
        for report in report_inputs
        for page in range(1, int(report.get("page_count") or 0) + 1)
    }
    covered_pages = {
        (text(item.get("source_pdf")), int(item.get("page") or 0))
        for item in coverage.get("report_pages", [])
    }
    page_gaps = sorted(expected_pages - covered_pages)
    if page_gaps:
        errors.append(
            "report page coverage missing: "
            + ", ".join(f"{path}#p{page}" for path, page in page_gaps)
        )

    if not value.get("audit_id"):
        warnings.append("audit_id is blank")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "report_standard_count": len(inventory),
        "status_standard_count": len(result_set),
        "issue_count": len(issues),
        "missing_standards": missing,
        "extra_standards": extra,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="write a canonical result skeleton")
    new.add_argument("--mode", required=True, choices=["typo_only", "standards_only", "full"])
    new.add_argument("--output", type=Path)
    normalize = sub.add_parser("normalize", help="normalize and deterministically sort a result")
    normalize.add_argument("--input", type=Path, required=True)
    normalize.add_argument("--output", type=Path)
    check = sub.add_parser("validate", help="validate coverage, ordering, and standard reconciliation")
    check.add_argument("--input", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "new":
            dump_json(new_result(args.mode), args.output)
            return 0
        value = normalize_result(load_json(args.input))
        if args.command == "normalize":
            dump_json(value, args.output)
            return 0
        result = validate(value)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
