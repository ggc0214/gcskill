# Feishu inspection-report retrieval

Use this workflow only when the user provides the configured Feishu Base link and a product name. Retrieval is read-only and prepares the audit inputs; it does not authorize editing the Base.

## Fixed source contract

- Base URL: `https://kocotree.feishu.cn/base/HCldb55rWaHzsds71L4cHNzWnDH?table=tbla8mt0SxmYmdSK&view=vewQTZtX7z`
- Base token from the URL: `HCldb55rWaHzsds71L4cHNzWnDH`
- Table ID from the URL: `tbla8mt0SxmYmdSK`
- Expected table name: `文案进度跟踪表`
- Product lookup field: `产品名称`
- Allowed attachment fields:
  - `检测报告`
  - `检测报告（面料）-自动同步测试`
- Do not read or use similarly named attachment fields. In particular, **不要读取 `检测报告（面料）`**.

Resolve the URL with `lark-base` as the current user and use the returned real Base/table identifiers. Confirm that the resolved table ID and actual table name match this contract before reading records. If they do not match, stop and report the mismatch rather than guessing another table.

## Record lookup

1. Query `文案进度跟踪表` with complete pagination and compare the input against `产品名称` after trimming leading/trailing whitespace. Require an exact remaining string match; do not silently select a fuzzy match.
2. If no exact record exists, report that no matching product was found and ask the user to verify the product name.
3. If more than one exact record exists, combine attachments from all exact records and retain each record ID and source field for traceability. Do not assume duplicate records contain duplicate files.
4. Read attachments only from the two allowed fields. Ignore non-PDF attachments and report their names separately.

## Authorization recovery（授权恢复）

Use user identity for the Base. When the response reports missing user scopes, expired login, `permission_violations`, or an authorization hint, follow `lark-shared` split-flow authorization:

1. request only the required scope or the smallest applicable docs/drive domain;
2. show the returned authorization URL and QR code to the user;
3. stop and wait for the user to confirm authorization;
4. complete the pending device-code authorization yourself;
5. retry the failed read operation once.

Do not package, copy, print, or reuse another person's token, cookie, device code, or application secret. A resource-level access failure such as `91403` cannot be fixed by repeated login: ask the Base owner to grant the current user access. If access still cannot be obtained, ask the user to upload the PDFs manually.

## Download, validation, and retry

Download every candidate PDF into an isolated working directory before auditing. For each attachment:

1. attempt the download up to **3 次** in total;
2. retry only transient network, timeout, server, or incomplete-transfer failures, using a short increasing delay;
3. after each download, require a non-empty file with a PDF signature and compute its SHA-256 digest;
4. do not retry authorization or permanent not-found errors as ordinary network failures; route them to the recovery rules above.

If an attachment still fails after 3 attempts, report its record ID, source field, filename, and failure reason, then require the user to **手动上传** that PDF. Do not claim complete report coverage while any selected attachment is missing.

## Content deduplication and user selection

- Deduplicate only byte-identical downloads with the same SHA-256 digest. Filename, file token, size, or column alone is not sufficient.
- When identical content occurs under multiple filenames, records, or allowed fields, retain one local PDF and preserve all source occurrences in the retrieval summary.
- When the same filename has different SHA-256 digests, keep every distinct file and disambiguate the displayed names; never discard one by filename.
- Hashing and PDF-signature validation are preparation steps, not report inspection.

After content deduplication:

- zero usable PDFs: ask the user to upload the reports manually;
- one usable PDF: report the selected source and continue only if all other required audit inputs are present;
- **多份** usable PDFs: display a numbered list with filename and source field, then stop and **等待用户选择**. Until the user selects numbers or explicitly says to use all files, **不得开始审核**, inspect report contents, extract evidence, query standards, or generate audit output.

The selection applies only to the current retrieval. A later Base query requires a new selection when it again returns multiple unique PDFs.

