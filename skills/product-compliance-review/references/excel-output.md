# Excel audit workbook

Use this reference when the compliance review produces its default Excel deliverable.

## Scope boundary

The request to show only problem items applies to the concise chat/text result, not to the Excel workbook. Keep the Excel workbook complete and auditable: include the issue list, supported claims, every detected standard and its status, and material/coverage notes. Do not reduce the workbook to a single problem-only sheet.

Use the workbook structure and visual conventions established by `双面萌宠翻转帽_合规预审结果.xlsx`. Do not introduce a dashboard, cover page, summary cards, or a different sheet layout unless the user explicitly requests a new template.

## Required workbook structure

Create an `.xlsx` workbook with these sheets in this order:

1. `审核问题表` — one row per distinct problem or manual-confirmation item.
2. `已支持宣传项` — supported claims and their evidence boundaries.
3. `标准状态` — one row for every canonical standard detected anywhere in the complete inspection reports, using the same status conclusions as the written audit working record.
4. `材料与说明` — input files, coverage, highest risk, review date, limitations, formula-derived coverage counts, and disclaimer.

Do not add `总览` or `检测报告明细` sheets to this template.

The `标准状态` sheet must contain:

| Column | Required content |
| --- | --- |
| 标准号 | One complete canonical prefix, number, part, and year |
| 标准状态 | Exactly the required two-line status text |
| 报告出现位置 | Every report filename, page, and item/row where the standard occurs |
| 核验来源 | Authoritative URL or the explicit lookup outcome |
| 核验结果 | Authoritative result or `官方接口超时/未命中` |
| 核验日期 | Current review date |
| 核验方式 | `联网核验`, `30天缓存`, `7天缓存`, `历史缓存回退`, or `官方接口超时/未命中` |
| 缓存核验日期 | Required for fresh or stale cache rows; blank for live/no-result rows |

The `材料与说明` sheet must show formula-derived standard coverage counts: `报告标准总数`, `标准状态行数`, `联网核验数`, `有效缓存数`, `历史缓存回退数`, `官方接口超时/未命中数`, and `漏项数`. The final workbook requires `漏项数 = 0`.

The main `审核问题表` must contain these fixed columns in order:

| Column | Required content |
| --- | --- |
| 序号 | Stable row number |
| 风险等级 | Red/orange/yellow or the review's corresponding Chinese risk label |
| 宣传图片位置 | Page/module and approximate coordinates or slice index; use `不适用（检测报告）` for report-standard problems |
| 宣传原文 | Exact transcribed source text; for a report-standard problem use `标准号｜检测项目` |
| 审核结果 | The compliance, numeric, evidence, typo, or standard-status finding |
| 报告证据位置 | Report filename, page, item, result, and relevant conditions |
| 整改建议 | Actionable replacement, deletion, supplementation, or standard-update guidance |
| 整改要求 | Exactly one of `必须整改`, `需补证`, or `人工确认`; every `确认错别字` is `必须整改` |
| 问题截图切片 | Embedded crop from the original marketing image or PDF page |
| 处理状态 | Editable status such as 待处理、已修改、保留并补证、不采用 |

Use filters, frozen headers, wrapped text, readable column widths, and risk-color formatting. Provide summary counts derived from formulas rather than manually duplicated totals.

## Abnormal standard linkage

The full `标准状态` sheet always includes normal and abnormal standards. In addition, every standard that is `废止`, `被代替`, `即将实施`, `官方接口超时/未命中`, a dated stale-cache fallback requiring confirmation, or otherwise needs action must also appear as a problem row in `审核问题表`.

For each such issue row:

- `宣传图片位置` = `不适用（检测报告）`.
- `宣传原文` = `完整标准号｜检测项目`.
- `审核结果` states the exact status, replacement standard, and relevant dates when available.
- `报告证据位置` states the complete PDF filename, page, sample/part when applicable, and exact inspection item. Never provide only a standard number without its report occurrence.
- `问题截图切片` is cropped from the original PDF page and shows both the inspection item and standard number. If they cannot fit legibly in one crop, place a clearly labeled pair of crops in the same image cell.
- Retain every distinct PDF/page/item occurrence. Deduplicate only identical occurrences.

## Required issue ordering

所有需要整改的行必须排在表格最前面。排序必须在生成工作簿时完成，不能只依赖用户手动筛选：

1. `第一排序键`：整改要求，固定顺序为 `必须整改`、`需补证`、`人工确认`。
2. `第二排序键`：风险等级，固定顺序为红色、橙色、黄色。
3. `第三排序键`：原始材料顺序，按文件、页面或图片纵向坐标、稳定序号升序，保证重复生成结果一致。

Every `确认错别字` row must use `橙色—整改后复审` and `必须整改`, so it appears before evidence-supplement and manual-confirmation rows. Do not place confirmed typos among yellow items. `字形不确定` remains `黄色—人工确认` until the original character can be confirmed.

## Fixed visual style

Keep the selected workbook's visual style consistent:

- `审核问题表` header range `A1:J1`, dark-blue fill `#1F4E78`, white bold Microsoft YaHei text;
- body Microsoft YaHei 10 pt, wrapped and top-aligned;
- freeze the first row and first two columns on `审核问题表`;
- risk fills: red `#F4CCCC`, orange `#FCE5CD`, yellow `#FFF2CC`;
- requirement fills: mandatory `#F4CCCC`, supplement `#FFF2CC`, manual confirmation `#D9EAF7`;
- issue columns equivalent to A 7, B 19, C 34, D 28, E 44, F 48, G 42, H 12, I 36, J 13;
- approximately 240 px issue-row height when an image is embedded;
- embed each issue crop in column I around 250 × 220 px without covering text;
- column J list validation: `待处理`, `已修改`, `保留并补证`, `不采用`;
- `已支持宣传项` uses the established green header style; `标准状态` and `材料与说明` retain the established blue styles.

## Screenshot crop rules

- Crop from the original highest-resolution source, not an OCR result or reconstructed text.
- Marketing issues must show the exact problematic text and enough nearby context to locate it.
- Report-standard issues must show both the inspection item and standard number.
- If several rows share one source region, embed the crop in every applicable row so filtering does not hide evidence.
- If the source characters remain unreadable at full resolution, do not fabricate a conclusion; mark the text uncertain.

## Text/workbook consistency

The concise chat/text result contains only problem items. The Excel workbook remains complete. Every chat problem must have a matching row in `审核问题表`, but the workbook may additionally contain supported claims, normal standards, and audit coverage information in their dedicated sheets. Do not copy those normal sections back into the concise chat result.

## Verification before delivery

1. Confirm every input PDF page and meaningful marketing region was reviewed.
2. Confirm every issue row has a screenshot crop or an explicit explanation that no reliable crop exists.
3. Confirm all `必须整改` rows are contiguous at the beginning of `审核问题表`, every confirmed typo is orange and mandatory, and no `需补证` or `人工确认` row precedes them.
4. Recompute the canonical standard set from all extracted report rows and compare it with the `标准状态` standard-number column by exact set equality. Confirm missing, extra, blank-outcome, and missing-location sets are all empty; do not export a final workbook otherwise.
5. Confirm every abnormal standard has both a `标准状态` row and an `审核问题表` row containing PDF filename, page, inspection item, and standard number.
6. Confirm every `历史缓存回退` row has a visible cache verification date and network-failure note, and no `官方接口超时/未命中` result was treated as reusable cache.
7. Inspect formulas for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, and `#N/A`.
8. Render or open every sheet to check clipping, wrapping, row height, column width, filters, and readability.
9. Export one final `.xlsx` and provide it together with the concise problem-only chat summary.

End the workbook's material/limitations sheet with:

`本结果用于上架前风险预审，不等于正式批准上架，也不替代法务、检测机构或认证机构结论。`

