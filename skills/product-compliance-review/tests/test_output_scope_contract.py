from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
EXCEL_RULES = (SKILL_ROOT / "references" / "excel-output.md").read_text(encoding="utf-8")


def test_chat_output_contains_only_problem_items():
    required = (
        "output only problem items",
        "do not enumerate supported claims",
        "PDF filename, page, sample/part",
        "inspection item",
    )
    for value in required:
        assert value in SKILL_TEXT


def test_excel_remains_complete_and_uses_the_established_template():
    required = (
        "applies to the concise chat/text result, not to the Excel workbook",
        "Do not reduce the workbook to a single problem-only sheet",
        "`审核问题表`",
        "`已支持宣传项`",
        "`标准状态`",
        "`材料与说明`",
        "Do not add `总览` or `检测报告明细`",
        "A1:J1",
        "#1F4E78",
    )
    for value in required:
        assert value in EXCEL_RULES


def test_abnormal_standard_rows_are_traceable_to_pdf_items():
    required = (
        "complete PDF filename",
        "exact inspection item",
        "完整标准号｜检测项目",
        "shows both the inspection item and standard number",
        "both a `标准状态` row and an `审核问题表` row",
    )
    for value in required:
        assert value in EXCEL_RULES


def test_normal_content_stays_in_excel_but_not_chat():
    assert "The Excel workbook remains complete" in EXCEL_RULES
    assert "supported claims, normal standards, and audit coverage information" in EXCEL_RULES
    assert "Do not copy those normal sections back into the concise chat result" in EXCEL_RULES

