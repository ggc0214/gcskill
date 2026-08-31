# Canonical audit result

Use this reference whenever the audit will produce chat output, standard reconciliation, screenshots, or Excel. The canonical JSON is the single source of truth; do not independently rebuild conclusions for each output channel.

## Required workflow

1. Create a skeleton with `scripts/audit_result.py new --mode ...` or construct the same structure directly.
2. Record every input file and its page/image dimensions.
3. Populate coverage, report rows, all canonical standards and occurrences, claims, issues, supported claims, and limitations.
4. Run `scripts/audit_result.py normalize` so issue ordering and standard numbers are deterministic.
5. Run `scripts/audit_result.py validate`. Do not label the review final or create the final workbook when validation fails.
6. Generate both the concise problem-only text and the fixed Excel workbook from the validated JSON. Never add a conclusion in one output that is absent from the JSON.

The machine-readable schema is [audit-result.schema.json](audit-result.schema.json). `schema_version` is currently `1.0`.

## Important field contracts

- `mode`: `typo_only`, `standards_only`, or `full`.
- `report_rows[].standard_numbers`: complete canonical standard numbers extracted from that report row.
- `standards[]`: exactly one result per canonical standard in `report_rows`; no missing or extra number is allowed.
- `standards[].occurrences`: every distinct PDF/page/sample-or-part/test-item location.
- `issues[]`: the only source for chat problem items and `审核问题表` rows.
- `issues[].occurrence_key`: for an abnormal-standard issue, join `source_pdf|page|sample_part|test_item` exactly as the validator does. Create one issue per distinct abnormal occurrence.
- `issues[].screenshot_path`: absolute readable crop path. If unavailable, set `screenshot_note` and explain why.
- `supported_claims[]`: normal supported claims retained only for Excel traceability.
- `coverage.uncovered_*`: must be empty before final delivery.

## Deterministic output

Normalize issues in this order: `必须整改`, `需补证`, `人工确认`; then red, orange, yellow; then source-file/page/image-coordinate order. A confirmed typo is always orange and mandatory.

## Commands

```text
python scripts/audit_result.py new --mode full --output audit_result.json
python scripts/audit_result.py normalize --input audit_result.json --output audit_result.normalized.json
python scripts/audit_result.py validate --input audit_result.normalized.json
```

Use the normalized file for all later commands.
