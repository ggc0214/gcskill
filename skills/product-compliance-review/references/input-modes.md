# Input modes

Select one mode only after Feishu retrieval and any required user selection of returned PDFs. Files retrieved from Feishu count exactly like files uploaded directly.

## 单张宣传文案图片：错别字审核模式

Use this mode only when the available review material is one standalone marketing-copy image and there is no inspection-report PDF.

1. Inspect every meaningful image region at readable resolution, including titles, badges, captions, tables, footnotes, specifications, and script text.
2. Transcribe the exact source wording before judging it. Apply the typo rules in `audit-rules.md`.
3. Report material coverage, each `确认错别字` with image location, exact original text, suggested correction, and reason. Every confirmed typo is `橙色—整改后复审` and `必须整改`; list all such items before `字形不确定` and wording suggestions. Keep a separate `字形不确定` list for text that cannot be confirmed from the source pixels.
4. Keep wording, punctuation, and style suggestions separate from confirmed typos.
5. 不执行宣传证据匹配，不执行检测数值或条件比对，不查询标准状态。
6. Return a concise chat result. Create an Excel workbook with issue crops only if the user explicitly requests a table or Excel output.

## 仅检测报告：标准状态核验模式

Use this mode when the available review material consists of one or more inspection-report PDFs and there is no marketing material.

1. Inspect every page of every selected report and state the page coverage.
2. Build the canonical inventory of全部标准号 from headers, test rows, method cells, applicable-basis cells, requirements, notes, continuation tables, appendices, and footnotes. Preserve the complete prefix, number, part, and year; deduplicate only exact canonical standard numbers and retain every occurrence location.
   Use `scripts/extract_standard_inventory.py` for searchable and OCR page text, then visually resolve unreadable pages and unresolved candidates.
3. Apply `standard-cache.md` and query each canonical standard at most once. Determine the exact authoritative status, including at least `现行`, `废止`, `被代替`, and `即将实施`. Preserve an authoritative source's more precise status wording when applicable. Never infer status from a related number or a replacement result.
4. Write the inventory and lookup results into the canonical audit JSON, normalize it, and run `scripts/audit_result.py validate` to enforce `精确集合一致性`. Every detected standard must have an occurrence location and one lookup outcome; missing and extra sets must both be empty before the result is final.
5. Lead with coverage and lookup counts. For every canonical standard, output exactly:
   `标准号：...；`
   `现行状态：...；`
   Include its report file/page occurrence and authoritative source link adjacent to the record when useful for traceability.
6. When no exact authoritative result is available after required retry, use `官方接口超时/未命中`; do not guess.
7. 不执行错别字审核，不执行宣传证据匹配，也不进行宣传数值或条件一致性判断。
8. Return a concise chat result. Create a standard-status Excel sheet only if the user explicitly requests a table or Excel output.

## 宣传材料和检测报告同时存在：完整合规审核模式

Use the full compliance workflow, full-mode output, and default Excel deliverable in `SKILL.md`. A standalone image combined with one or more selected Feishu PDFs also belongs to this mode.

## Unsupported or ambiguous inputs

If the supplied material does not fit any mode, state what is missing and ask one concise clarification. Do not silently expand a reduced mode into a full audit.
