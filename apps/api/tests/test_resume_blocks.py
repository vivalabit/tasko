import json
from io import BytesIO

import pytest
from docx import Document

from app.services.document_export import build_document_from_template
from app.services.resume_blocks import extract_resume_blocks_from_docx


def resume_template() -> bytes:
    document = Document()
    document.add_paragraph("ada@example.com · +41 44 555 12 34")
    document.add_paragraph("SUMMARY", style="Heading 1")
    document.add_paragraph("Original professional profile backed by delivery evidence.")
    document.add_paragraph("SKILLS", style="Heading 1")
    document.add_paragraph("Python, FastAPI, PostgreSQL")
    document.add_paragraph("EXPERIENCE", style="Heading 1")
    document.add_paragraph("Acme · 2024")
    document.add_paragraph("Built and operated a verified production API for customers.")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "German B2"
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_docx_is_parsed_into_stable_typed_resume_blocks() -> None:
    blocks = extract_resume_blocks_from_docx(resume_template())

    assert [block["blockId"] for block in blocks] == [
        f"block-{index:04d}" for index in range(1, 10)
    ]
    assert {block["type"] for block in blocks} == {
        "immutable",
        "summary",
        "skill",
        "achievement",
        "heading",
        "contact",
        "table cell",
    }


def test_resume_renderer_applies_partial_json_replacements_without_line_count() -> None:
    template = resume_template()
    content = json.dumps(
        {
            "replacements": [
                {
                    "blockId": "block-0003",
                    "original": "Original professional profile backed by delivery evidence.",
                    "replacement": "Backend engineer delivering verified FastAPI services.",
                    "reason": "Aligns verified delivery evidence with the vacancy",
                }
            ]
        }
    )

    rendered = build_document_from_template(
        template_content=template,
        content=content,
        document_type="tailored_resume",
    )
    document = Document(BytesIO(rendered))

    assert document.paragraphs[2].text == "Backend engineer delivering verified FastAPI services."
    assert document.paragraphs[6].text == "Acme · 2024"
    assert document.tables[0].cell(0, 0).text == "German B2"


def test_resume_renderer_rejects_immutable_and_mismatched_blocks() -> None:
    template = resume_template()
    immutable_replacement = json.dumps(
        {
            "replacements": [
                {
                    "blockId": "block-0007",
                    "original": "Acme · 2024",
                    "replacement": "Different employer · 2025",
                    "reason": "Unsafe invented change",
                }
            ]
        }
    )
    mismatched_original = json.dumps(
        {
            "replacements": [
                {
                    "blockId": "block-0003",
                    "original": "A different original",
                    "replacement": "Backend engineer",
                    "reason": "Stale model response",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="Immutable resume block cannot be changed"):
        build_document_from_template(
            template_content=template,
            content=immutable_replacement,
            document_type="tailored_resume",
        )
    with pytest.raises(ValueError, match="original does not match template"):
        build_document_from_template(
            template_content=template,
            content=mismatched_original,
            document_type="tailored_resume",
        )
