import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
AUDIT_RULES = (SKILL_ROOT / "references" / "audit-rules.md").read_text(encoding="utf-8")
EXCEL_RULES = (SKILL_ROOT / "references" / "excel-output.md").read_text(encoding="utf-8")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "confirmed_typo_requires_rectification.json"


def test_confirmed_typo_fixture_is_a_mandatory_rectification():
    case = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert case["source_text"] == "易刺饶炸毛"
    assert case["confirmed_character_change"] == "饶→挠"
    assert case["expected_risk"] == "橙色—整改后复审"
    assert case["expected_rectification"] == "必须整改"
    assert case["expected_sort_group"] == 0


def test_audit_rules_classify_every_confirmed_typo_as_major_and_rectifiable():
    required = (
        "确认错别字属于重大错误",
        "橙色—整改后复审",
        "必须整改",
        "字形不确定",
        "黄色—人工确认",
    )
    for value in required:
        assert value in AUDIT_RULES
    assert "Typo results do not change the compliance risk level by themselves" not in AUDIT_RULES


def test_excel_places_all_mandatory_rectifications_first():
    required = (
        "整改要求",
        "必须整改",
        "所有需要整改的行必须排在表格最前面",
        "需补证",
        "人工确认",
        "确认错别字",
    )
    for value in required:
        assert value in EXCEL_RULES


def test_sorting_contract_is_deterministic():
    assert "第一排序键" in EXCEL_RULES
    assert "第二排序键" in EXCEL_RULES
    assert "第三排序键" in EXCEL_RULES

