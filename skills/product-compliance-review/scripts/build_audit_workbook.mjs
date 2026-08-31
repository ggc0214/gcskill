#!/usr/bin/env node
/** Build the fixed four-sheet compliance workbook from the canonical audit JSON. */

import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const REQUIRED_SHEETS = ["审核问题表", "已支持宣传项", "标准状态", "材料与说明"];
const REQUIREMENT_ORDER = new Map([["必须整改", 0], ["需补证", 1], ["人工确认", 2]]);
const RISK_ORDER = new Map([["红色", 0], ["橙色", 1], ["黄色", 2]]);

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) continue;
    result[key.slice(2)] = argv[index + 1];
    index += 1;
  }
  if (!result.input || !result.output) {
    throw new Error("usage: build_audit_workbook.mjs --input audit_result.json --output result.xlsx [--preview-dir dir]");
  }
  return result;
}

function canonical(value) {
  return String(value ?? "")
    .normalize("NFKC")
    .toUpperCase()
    .trim()
    .replace(/[‐‑‒–—―−]/g, "-")
    .replace(/\s*\/\s*/g, "/")
    .replace(/\s*-\s*/g, "-")
    .replace(/\s+/g, " ")
    .replace(/^(GB\/T|GB|FZ\/T|T\/[A-Z0-9]+|Q\/[A-Z0-9]+)\s*(?=\d)/, "$1 ");
}

function sourceOrder(value) {
  if (Array.isArray(value)) return value;
  return [Number.isFinite(Number(value)) ? Number(value) : 999999];
}

function riskRank(value) {
  const text = String(value ?? "");
  for (const [key, rank] of RISK_ORDER.entries()) if (text.includes(key)) return rank;
  return 99;
}

function compareIssues(a, b) {
  const requirement = (REQUIREMENT_ORDER.get(a.requirement) ?? 99) - (REQUIREMENT_ORDER.get(b.requirement) ?? 99);
  if (requirement) return requirement;
  const risk = riskRank(a.risk_level) - riskRank(b.risk_level);
  if (risk) return risk;
  const left = JSON.stringify(sourceOrder(a.source_order));
  const right = JSON.stringify(sourceOrder(b.source_order));
  return left.localeCompare(right, "zh-CN") || String(a.id ?? "").localeCompare(String(b.id ?? ""), "zh-CN");
}

function inventoryFromRows(audit) {
  return new Set((audit.report_rows ?? []).flatMap((row) => row.standard_numbers ?? []).map(canonical).filter(Boolean));
}

function validateAudit(audit) {
  const errors = [];
  if (audit.schema_version !== "1.0") errors.push("schema_version must be 1.0");
  const coverage = audit.coverage ?? {};
  if ((coverage.uncovered_marketing_regions ?? []).length) errors.push("uncovered marketing regions remain");
  if ((coverage.uncovered_report_pages ?? []).length) errors.push("uncovered report pages remain");
  const inventory = inventoryFromRows(audit);
  const statuses = new Set((audit.standards ?? []).map((item) => canonical(item.standard_number)).filter(Boolean));
  const missing = [...inventory].filter((item) => !statuses.has(item));
  const extra = [...statuses].filter((item) => !inventory.has(item));
  if (missing.length) errors.push(`standards missing from status results: ${missing.join(", ")}`);
  if (extra.length) errors.push(`status results not found in report rows: ${extra.join(", ")}`);
  for (const item of audit.standards ?? []) {
    if (!(item.occurrences ?? []).length) errors.push(`standard has no occurrence: ${item.standard_number}`);
    if (!String(item.lookup_result ?? "").trim()) errors.push(`standard has no lookup result: ${item.standard_number}`);
  }
  const issues = audit.issues ?? [];
  if (JSON.stringify(issues) !== JSON.stringify([...issues].sort(compareIssues))) {
    errors.push("issues are not deterministically ordered");
  }
  if (errors.length) throw new Error(`audit_result validation failed:\n- ${errors.join("\n- ")}`);
  return { inventory, statuses };
}

function applyHeader(range, fill) {
  range.format = {
    fill,
    font: { bold: true, color: "#FFFFFF", name: "Microsoft YaHei", size: 10 },
    verticalAlignment: "center",
    horizontalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#B4C6E7" },
  };
}

function applyBody(range) {
  range.format = {
    font: { color: "#1F2937", name: "Microsoft YaHei", size: 10 },
    verticalAlignment: "top",
    horizontalAlignment: "left",
    wrapText: true,
    borders: {
      insideHorizontal: { style: "thin", color: "#D9E2F3" },
      bottom: { style: "thin", color: "#D9E2F3" },
    },
  };
}

function riskFill(value) {
  const text = String(value ?? "");
  if (text.includes("红色")) return "#F4CCCC";
  if (text.includes("橙色")) return "#FCE5CD";
  return "#FFF2CC";
}

function requirementFill(value) {
  if (value === "必须整改") return "#F4CCCC";
  if (value === "需补证") return "#FFF2CC";
  return "#D9EAF7";
}

function occurrenceText(occurrences) {
  return (occurrences ?? []).map((item) => [
    item.source_pdf,
    item.page ? `第${item.page}页` : "",
    item.sample_part,
    item.test_item,
  ].filter(Boolean).join(" / ")).join("；\n");
}

function statusText(item) {
  if (item.status_text) return item.status_text;
  return `标准号：${item.standard_number}；\n现行状态：${item.status || item.lookup_result}；`;
}

function mimeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  return "image/png";
}

async function dataUrl(filePath) {
  const bytes = await fs.readFile(filePath);
  return `data:${mimeFor(filePath)};base64,${bytes.toString("base64")}`;
}

function addTableIfRows(sheet, range, name) {
  if (range) {
    const table = sheet.tables.add(range, true, name);
    table.showFilterButton = true;
    table.showBandedRows = false;
  }
}

async function buildIssuesSheet(workbook, audit) {
  const sheet = workbook.worksheets.add("审核问题表");
  sheet.showGridLines = false;
  const headers = [["序号", "风险等级", "宣传图片位置", "宣传原文", "审核结果", "报告证据位置", "整改建议", "整改要求", "问题截图切片", "处理状态"]];
  const issues = audit.issues ?? [];
  const rows = issues.map((issue, index) => [
    index + 1,
    issue.risk_level ?? "",
    issue.marketing_location ?? "",
    issue.source_text ?? "",
    issue.finding ?? "",
    issue.evidence_location ?? "",
    issue.recommendation ?? "",
    issue.requirement ?? "",
    issue.screenshot_path ? "见嵌入截图" : (issue.screenshot_note ?? "无可靠截图"),
    issue.handling_status ?? "待处理",
  ]);
  sheet.getRange("A1:J1").values = headers;
  applyHeader(sheet.getRange("A1:J1"), "#1F4E78");
  sheet.getRange("A1:J1").format.rowHeightPx = 34;
  if (rows.length) {
    const body = sheet.getRangeByIndexes(1, 0, rows.length, 10);
    body.values = rows;
    applyBody(body);
    for (let index = 0; index < rows.length; index += 1) {
      const excelRow = index + 2;
      sheet.getRange(`A${excelRow}:J${excelRow}`).format.rowHeightPx = 240;
      sheet.getRange(`B${excelRow}`).format.fill = riskFill(issues[index].risk_level);
      sheet.getRange(`H${excelRow}`).format.fill = requirementFill(issues[index].requirement);
      const screenshot = issues[index].screenshot_path;
      if (screenshot) {
        try {
          sheet.images.add({
            dataUrl: await dataUrl(screenshot),
            anchor: { from: { row: index + 1, col: 8 }, extent: { widthPx: 250, heightPx: 220 } },
          });
        } catch (error) {
          sheet.getRange(`I${excelRow}`).values = [[`截图读取失败：${error.message}`]];
        }
      }
    }
    sheet.getRange(`J2:J${rows.length + 1}`).dataValidation = {
      rule: { type: "list", values: ["待处理", "已修改", "保留并补证", "不采用"] },
    };
    addTableIfRows(sheet, `A1:J${rows.length + 1}`, "AuditIssuesTable");
  }
  const widths = [7, 19, 34, 28, 44, 48, 42, 12, 36, 13];
  widths.forEach((width, index) => { sheet.getRangeByIndexes(0, index, Math.max(rows.length + 1, 1), 1).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);
  return sheet;
}

function buildSupportedSheet(workbook, audit) {
  const sheet = workbook.worksheets.add("已支持宣传项");
  sheet.showGridLines = false;
  const headers = [["序号", "宣传原文", "宣传位置", "报告证据", "报告证据位置", "支持边界"]];
  const items = audit.supported_claims ?? [];
  const rows = items.map((item, index) => [
    index + 1, item.source_text ?? "", item.marketing_location ?? "", item.evidence ?? "",
    item.evidence_location ?? "", item.boundary ?? "",
  ]);
  sheet.getRange("A1:F1").values = headers;
  applyHeader(sheet.getRange("A1:F1"), "#548235");
  if (rows.length) {
    const body = sheet.getRangeByIndexes(1, 0, rows.length, 6);
    body.values = rows;
    applyBody(body);
    addTableIfRows(sheet, `A1:F${rows.length + 1}`, "SupportedClaimsTable");
  }
  [7, 35, 32, 44, 48, 38].forEach((width, index) => { sheet.getRangeByIndexes(0, index, Math.max(rows.length + 1, 1), 1).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(1);
  return sheet;
}

function buildStandardsSheet(workbook, audit) {
  const sheet = workbook.worksheets.add("标准状态");
  sheet.showGridLines = false;
  const headers = [["标准号", "标准状态", "报告出现位置", "核验来源", "核验结果", "核验日期", "核验方式", "缓存核验日期"]];
  const items = audit.standards ?? [];
  const rows = items.map((item) => [
    item.standard_number ?? "", statusText(item), occurrenceText(item.occurrences), item.source_url ?? "",
    item.lookup_result ?? "", item.verified_at ?? audit.review_date ?? "", item.lookup_method ?? "", item.cache_verified_at ?? "",
  ]);
  sheet.getRange("A1:H1").values = headers;
  applyHeader(sheet.getRange("A1:H1"), "#1F4E78");
  if (rows.length) {
    const body = sheet.getRangeByIndexes(1, 0, rows.length, 8);
    body.values = rows;
    applyBody(body);
    body.format.rowHeightPx = 84;
    addTableIfRows(sheet, `A1:H${rows.length + 1}`, "StandardStatusTable");
  }
  [22, 30, 52, 44, 28, 15, 22, 18].forEach((width, index) => { sheet.getRangeByIndexes(0, index, Math.max(rows.length + 1, 1), 1).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(1);
  return sheet;
}

function buildMaterialsSheet(workbook, audit, inventory) {
  const sheet = workbook.worksheets.add("材料与说明");
  sheet.showGridLines = false;
  sheet.getRange("A1:B1").values = [["审核信息", "内容"]];
  applyHeader(sheet.getRange("A1:B1"), "#1F4E78");
  const standardsEnd = Math.max((audit.standards ?? []).length + 1, 2);
  const inventoryEnd = Math.max(inventory.size + 1, 2);
  const auditRows = [
    ["审核编号", audit.audit_id ?? ""],
    ["审核日期", audit.review_date ?? ""],
    ["审核模式", audit.mode ?? ""],
    ["最高风险", audit.materials?.highest_risk ?? ""],
    ["报告标准总数", null],
    ["标准状态行数", null],
    ["联网核验数", null],
    ["有效缓存数", null],
    ["历史缓存回退数", null],
    ["官方接口超时/未命中数", null],
    ["漏项数", null],
    ["局限与说明", audit.materials?.limitations ?? ""],
    ["免责声明", "本结果用于上架前风险预审，不等于正式批准上架，也不替代法务、检测机构或认证机构结论。"],
  ];
  sheet.getRangeByIndexes(1, 0, auditRows.length, 2).values = auditRows;
  applyBody(sheet.getRangeByIndexes(1, 0, auditRows.length, 2));
  sheet.getRange("B6").formulas = [[`=COUNTA(G2:G${inventoryEnd})`]];
  sheet.getRange("B7").formulas = [[`=COUNTA('标准状态'!$A$2:$A$${standardsEnd})`]];
  sheet.getRange("B8").formulas = [[`=COUNTIF('标准状态'!$G$2:$G$${standardsEnd},"联网核验")`]];
  sheet.getRange("B9").formulas = [[`=COUNTIF('标准状态'!$G$2:$G$${standardsEnd},"30天缓存")+COUNTIF('标准状态'!$G$2:$G$${standardsEnd},"7天缓存")`]];
  sheet.getRange("B10").formulas = [[`=COUNTIF('标准状态'!$G$2:$G$${standardsEnd},"历史缓存回退")`]];
  sheet.getRange("B11").formulas = [[`=COUNTIF('标准状态'!$G$2:$G$${standardsEnd},"官方接口超时/未命中")`]];
  sheet.getRange("B12").formulas = [["=ABS(B6-B7)"]];

  sheet.getRange("D1:E1").values = [["输入材料", "类型"]];
  applyHeader(sheet.getRange("D1:E1"), "#4472C4");
  const inputRows = [
    ...(audit.inputs?.marketing_images ?? []).map((item) => [item.path ?? "", "宣传图片"]),
    ...(audit.inputs?.reports ?? []).map((item) => [item.path ?? "", "检测报告"]),
  ];
  if (inputRows.length) {
    sheet.getRangeByIndexes(1, 3, inputRows.length, 2).values = inputRows;
    applyBody(sheet.getRangeByIndexes(1, 3, inputRows.length, 2));
  }

  sheet.getRange("G1").values = [["报告标准号清单（强制对账）"]];
  applyHeader(sheet.getRange("G1"), "#4472C4");
  const inventoryRows = [...inventory].sort((a, b) => a.localeCompare(b, "zh-CN")).map((item) => [item]);
  if (inventoryRows.length) {
    sheet.getRangeByIndexes(1, 6, inventoryRows.length, 1).values = inventoryRows;
    applyBody(sheet.getRangeByIndexes(1, 6, inventoryRows.length, 1));
  }
  sheet.getRange("A1:G14").format.wrapText = true;
  [22, 68, 3, 58, 16, 3, 32].forEach((width, index) => { sheet.getRangeByIndexes(0, index, Math.max(auditRows.length + 1, inputRows.length + 1, inventoryRows.length + 1), 1).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(1);
  return sheet;
}

async function verifyWorkbook(workbook, previewDir) {
  const sheetSummary = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 4000 });
  const summaryText = sheetSummary.ndjson ?? String(sheetSummary);
  for (const name of REQUIRED_SHEETS) {
    if (!summaryText.includes(name)) throw new Error(`missing worksheet: ${name}`);
  }
  const formulaErrors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  const errorText = formulaErrors.ndjson ?? String(formulaErrors);
  if (/#[A-Z/0!?]+/.test(errorText) && !/"count":0/.test(errorText)) {
    throw new Error(`formula error scan returned matches: ${errorText.slice(0, 500)}`);
  }
  await fs.mkdir(previewDir, { recursive: true });
  for (const name of REQUIRED_SHEETS) {
    const blob = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
    const output = path.join(previewDir, `${name}.png`);
    await fs.writeFile(output, new Uint8Array(await blob.arrayBuffer()));
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(args.input);
  const outputPath = path.resolve(args.output);
  const previewDir = path.resolve(args["preview-dir"] ?? path.join(path.dirname(outputPath), ".audit-workbook-previews"));
  const audit = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const { inventory } = validateAudit(audit);
  const workbook = Workbook.create();
  await buildIssuesSheet(workbook, audit);
  buildSupportedSheet(workbook, audit);
  buildStandardsSheet(workbook, audit);
  buildMaterialsSheet(workbook, audit, inventory);
  await verifyWorkbook(workbook, previewDir);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(JSON.stringify({ output: outputPath, sheets: REQUIRED_SHEETS, preview_dir: previewDir }, null, 2));
}

main().catch((error) => {
  console.error(JSON.stringify({ error: error.stack || error.message }, null, 2));
  process.exitCode = 2;
});
