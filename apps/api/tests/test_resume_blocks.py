import json
import zipfile
from io import BytesIO

import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from lxml import etree

from app.services.document_export import build_document_from_template
from app.services.resume_blocks import extract_resume_blocks_from_docx, paragraph_text


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


def add_hyperlink(paragraph, text: str, url: str) -> str:
    relationship_id = paragraph.part.relate_to(
        url,
        RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.extend((color, underline))
    node = OxmlElement("w:t")
    node.text = text
    run.extend((properties, node))
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return relationship_id


def add_plain_content_control(document: Document, text: str) -> None:
    control = OxmlElement("w:sdt")
    properties = OxmlElement("w:sdtPr")
    tag = OxmlElement("w:tag")
    tag.set(qn("w:val"), "tasko-editable")
    plain_text = OxmlElement("w:text")
    properties.extend((tag, plain_text))
    content = OxmlElement("w:sdtContent")
    paragraph = OxmlElement("w:p")
    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")
    italic = OxmlElement("w:i")
    run_properties.append(italic)
    node = OxmlElement("w:t")
    node.text = text
    run.extend((run_properties, node))
    paragraph.append(run)
    content.append(paragraph)
    control.extend((properties, content))
    document._body._element.insert(-1, control)


def complex_resume_template() -> tuple[bytes, str]:
    document = Document()
    document.add_paragraph("SUMMARY", style="Heading 1")
    paragraph = document.add_paragraph()
    first = paragraph.add_run("Original ")
    first.bold = True
    second = paragraph.add_run("profile")
    second.italic = True
    relationship_id = add_hyperlink(paragraph, " site", "https://example.com/profile")
    final = paragraph.add_run()
    final.add_tab()
    final.add_text("Remote")
    final.add_break()
    final.add_text("Delivery")
    table = document.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Original table achievement"
    add_plain_content_control(document, "Original controlled summary")
    output = BytesIO()
    document.save(output)
    return output.getvalue(), relationship_id


def document_root(content: bytes):
    with zipfile.ZipFile(BytesIO(content)) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def test_complex_docx_preserves_runs_hyperlinks_controls_tabs_and_breaks() -> None:
    template, relationship_id = complex_resume_template()
    template_root = document_root(template)
    template_paragraph = template_root.findall(".//" + qn("w:p"))[1]
    original_run_properties = [
        etree.tostring(properties)
        for properties in template_paragraph.findall(".//" + qn("w:rPr"))
    ]
    content = json.dumps(
        {
            "replacements": [
                {
                    "blockId": "block-0002",
                    "original": "Original profile site\tRemote\nDelivery",
                    "replacement": "Targeted summary link\tHybrid\nDelivery proof",
                    "reason": "Tailors the summary while retaining inline structure",
                },
                {
                    "blockId": "block-0003",
                    "original": "Original table achievement",
                    "replacement": "Verified table achievement",
                    "reason": "Uses verified evidence in the existing table cell",
                },
                {
                    "blockId": "block-0004",
                    "original": "Original controlled summary",
                    "replacement": "Verified controlled summary",
                    "reason": "Updates a supported plain-text content control",
                },
            ]
        }
    )

    rendered = build_document_from_template(
        template_content=template,
        content=content,
        document_type="tailored_resume",
    )
    rendered_root = document_root(rendered)
    rendered_paragraph = rendered_root.findall(".//" + qn("w:p"))[1]
    rendered_run_properties = [
        etree.tostring(properties)
        for properties in rendered_paragraph.findall(".//" + qn("w:rPr"))
    ]
    text_nodes = rendered_paragraph.findall(".//" + qn("w:t"))
    hyperlink = rendered_paragraph.find(".//" + qn("w:hyperlink"))
    controlled_text = rendered_root.find(
        ".//" + qn("w:sdt") + "/" + qn("w:sdtContent") + "//" + qn("w:t")
    )
    controlled_italic = rendered_root.find(
        ".//" + qn("w:sdt") + "/" + qn("w:sdtContent") + "//" + qn("w:rPr") + "/" + qn("w:i")
    )

    assert paragraph_text(rendered_paragraph) == "Targeted summary link\tHybrid\nDelivery proof"
    assert original_run_properties == rendered_run_properties
    assert hyperlink is not None
    assert hyperlink.get(qn("r:id")) == relationship_id
    assert len([node for node in text_nodes if node.text]) >= 3
    assert len(rendered_paragraph.findall(".//" + qn("w:tab"))) == 1
    assert len(rendered_paragraph.findall(".//" + qn("w:br"))) == 1
    assert controlled_text is not None and controlled_text.text == "Verified controlled summary"
    assert controlled_italic is not None
    rendered_document = Document(BytesIO(rendered))
    assert rendered_document.part.rels[relationship_id].target_ref == "https://example.com/profile"
    assert rendered_document.tables[0].style.name == "Table Grid"
    assert rendered_document.tables[0].cell(0, 0).text == "Verified table achievement"


def test_complex_docx_rejects_changed_inline_controls_and_word_fields() -> None:
    template, _ = complex_resume_template()
    changed_controls = json.dumps(
        {
            "replacements": [
                {
                    "blockId": "block-0002",
                    "original": "Original profile site\tRemote\nDelivery",
                    "replacement": "Targeted summary without controls",
                    "reason": "Invalid structural change",
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="preserve the original tabs and line breaks"):
        build_document_from_template(
            template_content=template,
            content=changed_controls,
            document_type="tailored_resume",
        )

    unsupported = Document()
    paragraph = unsupported.add_paragraph("Total ")
    field_run = paragraph.add_run()._r
    field_begin = OxmlElement("w:fldChar")
    field_begin.set(qn("w:fldCharType"), "begin")
    field_run.append(field_begin)
    output = BytesIO()
    unsupported.save(output)

    with pytest.raises(ValueError, match=r"Unsupported DOCX construction: Word fields"):
        extract_resume_blocks_from_docx(output.getvalue())
