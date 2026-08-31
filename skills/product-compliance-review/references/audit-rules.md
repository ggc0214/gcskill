# Audit rules

## 1. Coverage and extraction

- Inspect every PDF page, including continuation tables, appendices, signatures, and tables whose headers appear on earlier pages.
- Inspect the complete meaningful height and width of long marketing images. Record page or image region for every extracted item.
- A report containing one legitimate test item can be complete. Never use “fewer than 10 rows” or another fixed count as an incompleteness rule.
- Determine incompleteness only from page coverage, broken table continuity, missing report identity, unreadable regions, contradictory OCR, or explicit page totals.
- Preserve rows even when requirement, result, or conclusion is `-`; do not invent missing cells.

## 2. Evidence matching

Evidence support requires all relevant dimensions to align:

1. test-item meaning;
2. product/sample and tested part;
3. method or applicable standard;
4. requirement and measured result;
5. conditions such as temperature, time, washing, direction, material layer, organism, or test population;
6. a reliable source location.

Use the keyword groups only to find candidates. Also use conservative semantic matching for wording not in the list. Do not require the marketing wording to repeat the report's exact project name, but do not collapse broader claims into narrower evidence.

Examples:

- “没有静电打扰” can be a candidate for “抗静电性能”, but must still pass the evidence checks above.
- “无重金属” can match “重金属含量” or “特定元素迁移” only as a candidate. An exemption is not the same as a measured non-detect result.
- “无甲醛” may use a “甲醛含量—未检出” row; a missing row is no evidence.
- “无荧光剂” requires a relevant fluorescent-agent item; unrelated safety tests do not support it.

## 3. Numeric consistency

- Normalize harmless notation variants such as `10^4`, `10⁴`, and `1.0×10^4`, while preserving magnitude and unit.
- Compare temperature, time, initial temperature, washing state, direction, sample part, and range bounds—not just the headline result.
- Do not treat values with `<`, `>`, `≤`, `≥`, `未检出`, or detection limits as exact numbers.
- OCR conflicts, missing units, fragments, and ambiguous table bindings are yellow manual-confirmation items, not deterministic mismatches.
- A confirmed page/report numeric or condition mismatch is orange and requires revision.

## 4. Standard verification

- Build the standard inventory from every page before lookup. Inspect headers, report bases, item names, method cells, applicable-basis cells, requirement cells, notes, continuation tables, appendices, and footnotes. Do not build it from marketing claims or selected evidence rows.
- Canonicalize harmless spacing and punctuation while preserving the complete prefix, number, part, and year. Treat different parts or years as different standards. Keep every report file, page, and row where each standard occurs.
- Browse current authoritative sources; prefer the National Public Service Platform for Standards Information (`std.samr.gov.cn`) for national and industry standards.
- Use the enterprise-standard public platform (`qybz.org.cn`) for enterprise standards when applicable, and an authoritative issuer/filing platform for group standards.
- Match the complete standard prefix, number, part, and year. Search results for a future replacement do not change the current status of the exact older version before its implementation date.
- If an exact result says current, obsolete, replaced, or soon-to-be-implemented, report that exact status.
- If the official interface times out or no exact result is found, use `官方接口超时/未命中` and retain manual verification.
- Display only the two requested lines for each standard; supporting links may be cited beside the surrounding explanation, not appended inside the status text.

### SQLite cache policy

- Use the Skill-owned cache workflow in [standard-cache.md](standard-cache.md) only after the complete report standard inventory is built. Cache hits never narrow the inventory.
- Normalize and deduplicate once per audit, so each canonical standard is resolved at most once and the result is shared by every report occurrence.
- Fresh authoritative cache TTL is 30 days for national/industry standards and 7 days for enterprise/group standards.
- Force online refresh when an effective, abolishment, or replacement date is within 60 days, or when such an event passed after the cached verification date.
- Cache expiry requires online refresh. `官方接口超时/未命中` is not reusable and must be queried again in the next audit.
- After a live network failure, an older authoritative record may be shown only with `网络查询失败；使用历史缓存，缓存核验日期：YYYY-MM-DD。`; without old authoritative cache, report `官方接口超时/未命中`.
- A successful exact online result must update status, dates, replacement standard, official link, verification time, and summary in SQLite.

### Mandatory reconciliation gate

Before final output, compare the canonical inventory and status-result table as sets, not only as counts:

1. every inventory standard has exactly one status row;
2. every status row maps to an inventory standard;
3. every row has at least one report occurrence location;
4. every row has an authoritative live/fresh-cache result, a dated stale-cache fallback, or the explicit outcome `官方接口超时/未命中`;
5. no lookup is omitted because the standard is unrelated to a marketing claim or appears only in a note, method, appendix, or continuation row.

The final-output gate passes only when the missing set, extra set, blank-outcome set, and missing-location set are all empty. If it fails, continue extraction or lookup and do not describe the audit as complete.

## 5. Risk mapping

- **红色—阻断上架**: reliable official rules and complete evidence show noncompliance, or a report marked qualified conflicts with a reliable official-limit recalculation.
- **橙色—整改后复审**: confirmed marketing/report numeric or condition mismatch; an unsupported definite high-impact claim; wrong, obsolete, or replaced standard; method or product applicability mismatch; any `确认错别字`.
- **黄色—人工确认**: incomplete or conflicting OCR, missing reliable location, ambiguous evidence relation, unknown applicability, official timeout/no exact hit, missing unit, or incomplete authorized standard text.
- **绿色—暂未发现明显风险**: coverage and evidence are complete, relevant claims are supported, numeric/condition comparisons agree, and no standard/version issue is found.

The highest applicable risk controls the overall result. Green never means formal approval.

## 6. Typo checking

- Perform typo checking as a dedicated second pass, independently of claim extraction and evidence matching. Review every meaningful marketing region, including titles, captions, badges, comparison cards, tables, footnotes, image annotations, and text filtered out of compliance matching.
- For each suspected issue, follow this order: locate the original region; transcribe the exact source text; confirm the character from the original-resolution image; then judge whether it is a typo. OCR output is only a reading candidate and never overrides the visible source.
- If a character is blurry or has multiple plausible readings, inspect the original image at higher resolution or a tighter crop. If it remains unclear, report `字形不确定，需核对源文件`; never silently choose one reading or explain a guessed phrase as if it were certain.
- Report confirmed character substitutions, homophone/shape errors, and contextually certain missing or extra characters. For every confirmed typo provide: marketing location, exact original text, corrected text, and the reason for correction.
- `确认错别字属于重大错误`。每一项确认错别字一律标记为 `橙色—整改后复审` 和 `必须整改`，并进入需要整改的问题清单；不得降为黄色人工确认，也不得只作为措辞建议。
- Keep three categories separate: `确认错别字`, `字形不确定`, and `措辞/标点优化`. Do not present wording polish or punctuation preference as a confirmed typo.
- `字形不确定` 仍属于 `黄色—人工确认`，只有在原图中确认具体字符错误后才能升级为确认错别字和必须整改。
- Do not grade brand names, model numbers, units, professional terms, dialectal wording, or grammar/style preference as typos unless the exact character-level error is independently established.
- Example regression rule: when the legible source is `易刺饶炸毛`, the confirmed character error is `饶` → `挠`; adding punctuation or rewriting it as `易扎肤、易起毛` is a separate wording suggestion, not the typo itself.
- Before finalizing, verify that the typo section covers the full marketing-image region inventory rather than only compliance-risk claims.
- A confirmed typo changes the item risk and rectification requirement as defined above. The highest applicable item still controls the overall result.

