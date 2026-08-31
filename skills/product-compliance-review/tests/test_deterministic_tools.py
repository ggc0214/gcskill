import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def load_module(name: str, filename: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


def valid_audit_result() -> dict:
    occurrence = {
        "source_pdf": "report.pdf",
        "page": 1,
        "sample_part": "面料",
        "test_item": "甲醛含量",
    }
    return {
        "schema_version": "1.0",
        "audit_id": "fixture-001",
        "review_date": "2026-08-31",
        "mode": "full",
        "inputs": {
            "marketing_images": [{"path": "marketing.jpg", "width": 800, "height": 2400}],
            "reports": [{"path": "report.pdf", "page_count": 1}],
        },
        "coverage": {
            "marketing_regions": [{"source_path": "marketing.jpg", "region_id": "tile-1"}],
            "report_pages": [{"source_pdf": "report.pdf", "page": 1}],
            "uncovered_marketing_regions": [],
            "uncovered_report_pages": [],
        },
        "report_rows": [{
            "id": "row-1",
            "source_pdf": "report.pdf",
            "page": 1,
            "sample_part": "面料",
            "test_item": "甲醛含量",
            "method_or_standard": "GB 31701-2015",
            "requirement": "≤20",
            "measured_result": "未检出",
            "conclusion": "合格",
            "uncertainty": "",
            "standard_numbers": ["GB 31701-2015"],
        }],
        "standards": [{
            "standard_number": "GB 31701-2015",
            "status": "现行",
            "status_text": "标准号：GB 31701-2015；\n现行状态：现行；",
            "occurrences": [occurrence],
            "source_url": "https://std.samr.gov.cn/",
            "lookup_result": "现行",
            "verified_at": "2026-08-31",
            "lookup_method": "联网核验",
            "cache_verified_at": "",
        }],
        "claims": [],
        "issues": [
            {
                "id": "issue-typo",
                "category": "确认错别字",
                "risk_level": "橙色—整改后复审",
                "requirement": "必须整改",
                "marketing_location": "marketing.jpg / tile-1 / y=100",
                "source_text": "易刺饶炸毛",
                "finding": "‘饶’为错别字",
                "evidence_location": "不适用",
                "recommendation": "改为‘易刺挠炸毛’",
                "source_order": [0, 100],
                "screenshot_note": "测试样本不附图",
                "handling_status": "待处理",
                "standard_numbers": [],
            },
            {
                "id": "issue-manual",
                "category": "字形不确定",
                "risk_level": "黄色—人工确认",
                "requirement": "人工确认",
                "marketing_location": "marketing.jpg / tile-1 / y=200",
                "source_text": "模糊文字",
                "finding": "原图像素不足",
                "evidence_location": "不适用",
                "recommendation": "核对源文件",
                "source_order": [0, 200],
                "screenshot_note": "测试样本不附图",
                "handling_status": "待处理",
                "standard_numbers": [],
            },
        ],
        "supported_claims": [{
            "source_text": "未检出甲醛",
            "marketing_location": "marketing.jpg / tile-1",
            "evidence": "甲醛含量未检出",
            "evidence_location": "report.pdf / 第1页 / 甲醛含量",
            "boundary": "仅限送检样品",
        }],
        "materials": {"highest_risk": "橙色—整改后复审", "limitations": "测试样本"},
    }


def test_audit_result_normalization_and_validation_are_semantic():
    module = load_module("audit_result_tool", "audit_result.py")
    value = valid_audit_result()
    value["issues"].reverse()
    normalized = module.normalize_result(value)
    assert [item["id"] for item in normalized["issues"]] == ["issue-typo", "issue-manual"]
    result = module.validate(normalized)
    assert result["valid"] is True
    assert result["report_standard_count"] == result["status_standard_count"] == 1


def test_audit_result_blocks_missing_standard_and_uncovered_page():
    module = load_module("audit_result_tool_invalid", "audit_result.py")
    value = valid_audit_result()
    value["standards"] = []
    value["coverage"]["uncovered_report_pages"] = [{"source_pdf": "report.pdf", "page": 1}]
    result = module.validate(module.normalize_result(value))
    assert result["valid"] is False
    assert result["missing_standards"] == ["GB 31701-2015"]
    assert any("coverage is incomplete" in error for error in result["errors"])


def test_long_image_slicer_has_overlap_and_zero_gaps(tmp_path):
    module = load_module("slice_long_image_tool", "slice_long_image.py")
    source = tmp_path / "long.png"
    Image.new("RGB", (2100, 5100), "white").save(source)
    manifest = module.split_image(source, tmp_path / "tiles", 1200, 1800, 120, 180)
    assert manifest["coverage_ok"] is True
    assert manifest["uncovered_rectangles"] == []
    assert manifest["tile_count"] > 3
    assert any(item["x"] > 0 for item in manifest["tiles"])
    assert any(item["y"] > 0 for item in manifest["tiles"])
    assert (tmp_path / "tiles" / "coverage_manifest.json").exists()


def test_standard_inventory_preserves_prefix_part_year_and_locations():
    module = load_module("standard_inventory_tool", "extract_standard_inventory.py")
    pages = [{
        "source_pdf": "report.pdf",
        "page": 5,
        "text": "纤维含量 FZ/T 01057.1-2007；水洗尺寸变化率 GB/T 8628-2013；企标 Q/KQZN 011-2025。",
    }]
    inventory = module.build_inventory(pages, [])
    assert inventory["coverage_ok"] is True
    assert [item["standard_number"] for item in inventory["standards"]] == [
        "FZ/T 01057.1-2007",
        "GB/T 8628-2013",
        "Q/KQZN 011-2025",
    ]
    assert all(item["occurrences"][0]["page"] == 5 for item in inventory["standards"])


def test_schema_file_is_valid_json_and_requires_single_source_fields():
    schema = json.loads((SKILL_ROOT / "references" / "audit-result.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert {"report_rows", "standards", "issues", "coverage"}.issubset(schema["required"])


def test_fixed_workbook_generator_creates_exact_four_sheets(tmp_path):
    node = os.environ.get("CODEX_NODE_EXE")
    artifact_package = SKILL_ROOT / "node_modules" / "@oai" / "artifact-tool"
    if not node or not artifact_package.exists():
        pytest.skip("bundled Node/artifact-tool link is not configured")
    source = tmp_path / "audit.json"
    output = tmp_path / "result.xlsx"
    previews = tmp_path / "previews"
    source.write_text(json.dumps(valid_audit_result(), ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(
        [node, str(SCRIPTS / "build_audit_workbook.mjs"), "--input", str(source), "--output", str(output), "--preview-dir", str(previews)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert output.exists()
    with zipfile.ZipFile(output) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
    names = ["审核问题表", "已支持宣传项", "标准状态", "材料与说明"]
    assert all(f'name="{name}"' in workbook_xml for name in names)
    assert workbook_xml.count("<x:sheet ") == 4
    assert all((previews / f"{name}.png").exists() for name in names)
