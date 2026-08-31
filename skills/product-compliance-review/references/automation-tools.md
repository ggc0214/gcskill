# Deterministic audit tools

Use these tools when their input type is present. They preserve coverage and output consistency; they do not replace human or model judgment.

## Long-image tiling

Run the slicer for any marketing image that is not readable at full resolution. It supports both vertical and horizontal subdivision and always writes exact source coordinates:

```text
python scripts/slice_long_image.py --input marketing.jpg --output-dir work/image_tiles
```

Read every tile in `coverage_manifest.json`. Do not finalize unless `coverage_ok` is true and `uncovered_rectangles` is empty. Copy reviewed tile records into `coverage.marketing_regions`; retain the original coordinates for problem locations and screenshot crops.

Defaults are 1800 × 2200 pixels with 180/220-pixel overlap. Override dimensions only when text remains unreadable or the source is unusually narrow. Never use zero-overlap ad-hoc slices.

## Complete standard inventory

For searchable PDFs:

```text
python scripts/extract_standard_inventory.py --pdf report1.pdf --pdf report2.pdf --output standard_inventory.json
```

For scanned pages, first obtain page-level OCR text and provide a JSON list of `{source_pdf, page, text}` records:

```text
python scripts/extract_standard_inventory.py --text-json ocr_pages.json --output standard_inventory.json
```

Merge searchable and OCR inputs in one call when necessary. Treat `unreadable_pages` and `unresolved_candidates` as blocking coverage items; inspect those pages at high resolution and resolve them before final reconciliation. Do not silently drop a standard-like fragment merely because the regex cannot confirm its year.

The inventory is a discovery aid. Compare it with visual page inspection so image-only tables, rotated text, footnotes, and OCR mistakes are not missed.

## Fixed Excel generation

The generator consumes only a validated normalized audit JSON:

```text
node scripts/build_audit_workbook.mjs --input audit_result.normalized.json --output compliance_review.xlsx --preview-dir work/previews
```

Use the bundled spreadsheet runtime. Before executing, follow the spreadsheet Skill requirement to make its provided `node_modules` available from the working directory. The generator rejects incomplete coverage or unequal standard sets, creates exactly the four required sheets, sorts issues deterministically, embeds available screenshot crops, scans formula errors, and renders every sheet into the preview directory. Inspect all four previews before delivery.
