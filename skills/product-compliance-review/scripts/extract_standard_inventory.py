#!/usr/bin/env python3
"""Extract complete standard numbers and their report-page occurrences."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from standard_cache import canonicalize


PREFIX = r"(?:GB(?:/T|/Z)?|FZ/T|QB/T|HG/T|YY/T|SN/T|T/[A-Z0-9]{2,12}|Q/[A-Z0-9]{2,12}|ISO|IEC|EN)"
COMPLETE_STANDARD_RE = re.compile(
    rf"(?<![A-Z0-9/])({PREFIX})\s*([0-9]{{2,6}}(?:\.[0-9]+)*\s*-\s*[0-9]{{4}})(?![0-9])",
    re.IGNORECASE,
)
POSSIBLE_FRAGMENT_RE = re.compile(
    rf"(?<![A-Z0-9/])({PREFIX})\s*([0-9]{{2,6}}(?:\.[0-9]+)*(?:\s*-\s*[0-9]{{0,3}})?)(?![0-9])",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[‐‑‒–—―−]", "-", value)
    return value


def extract_page(source_pdf: str, page: int, page_text: str) -> tuple[list[dict], list[dict]]:
    normalized = normalize_text(page_text)
    complete: list[dict] = []
    complete_spans: list[tuple[int, int]] = []
    for match in COMPLETE_STANDARD_RE.finditer(normalized):
        number = canonicalize(f"{match.group(1)} {match.group(2)}")
        line_start = normalized.rfind("\n", 0, match.start()) + 1
        line_end = normalized.find("\n", match.end())
        if line_end < 0:
            line_end = len(normalized)
        context = re.sub(r"\s+", " ", normalized[line_start:line_end]).strip()
        complete.append(
            {
                "standard_number": number,
                "source_pdf": source_pdf,
                "page": page,
                "context": context,
                "character_start": match.start(),
                "character_end": match.end(),
            }
        )
        complete_spans.append(match.span())

    fragments: list[dict] = []
    for match in POSSIBLE_FRAGMENT_RE.finditer(normalized):
        if any(start <= match.start() and match.end() <= end for start, end in complete_spans):
            continue
        raw = re.sub(r"\s+", " ", match.group(0)).strip()
        fragments.append(
            {
                "raw_text": raw,
                "source_pdf": source_pdf,
                "page": page,
                "reason": "标准号疑似缺少年份或被OCR截断",
            }
        )
    return complete, fragments


def pages_from_pdf(paths: Iterable[Path]) -> tuple[list[dict], list[dict]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to extract searchable PDF text") from exc
    pages: list[dict] = []
    unreadable: list[dict] = []
    for path in paths:
        reader = PdfReader(str(path))
        for index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append({"source_pdf": str(path.resolve()), "page": index, "text": page_text})
            if not page_text.strip():
                unreadable.append(
                    {"source_pdf": str(path.resolve()), "page": index, "reason": "无可搜索文本，需OCR"}
                )
    return pages, unreadable


def pages_from_json(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8"))
    pages = value.get("pages") if isinstance(value, dict) else value
    if not isinstance(pages, list):
        raise ValueError("text JSON must be a list or an object containing a pages list")
    return pages


def build_inventory(pages: list[dict], unreadable: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    fragments: list[dict] = []
    page_manifest: list[dict] = []
    for page in pages:
        source_pdf = str(page.get("source_pdf") or page.get("path") or "")
        page_number = int(page.get("page") or 0)
        text = str(page.get("text") or "")
        page_manifest.append(
            {
                "source_pdf": source_pdf,
                "page": page_number,
                "has_text": bool(text.strip()),
            }
        )
        complete, page_fragments = extract_page(source_pdf, page_number, text)
        fragments.extend(page_fragments)
        for occurrence in complete:
            number = occurrence.pop("standard_number")
            key = json.dumps(occurrence, ensure_ascii=False, sort_keys=True)
            existing = {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in grouped[number]}
            if key not in existing:
                grouped[number].append(occurrence)

    standards = [
        {"standard_number": number, "occurrences": occurrences}
        for number, occurrences in sorted(grouped.items())
    ]
    return {
        "inventory_version": "1.0",
        "page_count": len(page_manifest),
        "standard_count": len(standards),
        "coverage_ok": not unreadable,
        "pages": page_manifest,
        "unreadable_pages": unreadable,
        "unresolved_candidates": fragments,
        "standards": standards,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, action="append", default=[])
    parser.add_argument("--text-json", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.pdf and not args.text_json:
        print(json.dumps({"error": "provide --pdf or --text-json"}, ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        pages: list[dict] = []
        unreadable: list[dict] = []
        pdf_pages, pdf_unreadable = pages_from_pdf(args.pdf)
        pages.extend(pdf_pages)
        unreadable.extend(pdf_unreadable)
        for path in args.text_json:
            pages.extend(pages_from_json(path))
        inventory = build_inventory(pages, unreadable)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "output": str(args.output.resolve()),
            "standard_count": inventory["standard_count"],
            "coverage_ok": inventory["coverage_ok"],
            "unresolved_candidate_count": len(inventory["unresolved_candidates"]),
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
