from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
MODE_REFERENCE = SKILL_ROOT / "references" / "input-modes.md"


def test_skill_routes_by_available_input_types():
    assert "references/input-modes.md" in SKILL_TEXT
    assert MODE_REFERENCE.exists()


def test_single_marketing_image_is_typo_only():
    text = MODE_REFERENCE.read_text(encoding="utf-8")
    required = (
        "单张宣传文案图片",
        "错别字审核模式",
        "不执行宣传证据匹配",
        "不查询标准状态",
        "确认错别字",
        "字形不确定",
    )
    for value in required:
        assert value in text


def test_report_only_mode_verifies_every_standard_status():
    text = MODE_REFERENCE.read_text(encoding="utf-8")
    required = (
        "仅检测报告",
        "标准状态核验模式",
        "全部标准号",
        "现行",
        "废止",
        "被代替",
        "即将实施",
        "精确集合一致性",
        "不执行错别字审核",
    )
    for value in required:
        assert value in text


def test_combined_inputs_keep_full_compliance_review():
    text = MODE_REFERENCE.read_text(encoding="utf-8")
    assert "宣传材料和检测报告同时存在" in text
    assert "完整合规审核模式" in text


