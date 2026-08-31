from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
REFERENCE_PATH = SKILL_ROOT / "references" / "feishu-report-retrieval.md"


def test_skill_routes_feishu_base_retrieval_to_dedicated_reference():
    assert "references/feishu-report-retrieval.md" in SKILL_TEXT
    assert REFERENCE_PATH.exists()


def test_feishu_reference_fixes_the_source_and_attachment_fields():
    text = REFERENCE_PATH.read_text(encoding="utf-8")
    required_values = (
        "HCldb55rWaHzsds71L4cHNzWnDH",
        "tbla8mt0SxmYmdSK",
        "文案进度跟踪表",
        "产品名称",
        "检测报告",
        "检测报告（面料）-自动同步测试",
    )
    for value in required_values:
        assert value in text
    assert "不要读取 `检测报告（面料）`" in text


def test_feishu_reference_requires_content_dedup_selection_and_recovery():
    text = REFERENCE_PATH.read_text(encoding="utf-8")
    required_behaviors = (
        "SHA-256",
        "多份",
        "等待用户选择",
        "授权",
        "3 次",
        "手动上传",
        "不得开始审核",
    )
    for behavior in required_behaviors:
        assert behavior in text


