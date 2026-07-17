import shutil
from io import BytesIO

import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE

from app.services.document_validation import (
    build_document_diff,
    detect_table_overflow,
    render_and_count_pages,
    validate_factual_changes,
    validate_visual_output,
)


def document_bytes(document: Document) -> bytes:
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def add_hyperlink(document: Document, target: str) -> None:
    paragraph = document.add_paragraph("Portfolio: ")
    relationship_id = paragraph.part.relate_to(
        target,
        RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "profile"
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def test_factual_validation_checks_entities_technologies_and_claims() -> None:
    allowed = (
        "Built a Python service at Acme in 2023 for 12 clients. "
        "Profile evidence confirms FastAPI delivery and API migrations."
    )
    supported = [{
        "blockId": "block-0002",
        "original": "Built a Python service at Acme in 2023 for 12 clients.",
        "replacement": "Built a FastAPI service at Acme in 2023 for 12 clients.",
    }]
    unsupported = [{
        "blockId": "block-0002",
        "original": "Built a Python service at Acme in 2023 for 12 clients.",
        "replacement": "Led a Kubernetes migration at Globex in 2025 for 900 clients.",
    }]

    assert validate_factual_changes(supported, allowed) == []
    issues = validate_factual_changes(unsupported, allowed)
    assert any("unsupported date" in issue and "2025" in issue for issue in issues)
    assert any("unsupported number" in issue and "900" in issue for issue in issues)
    assert any("unsupported technology" in issue and "kubernetes" in issue for issue in issues)
    assert any("unsupported company" in issue and "Globex" in issue for issue in issues)
    assert any("unsupported claim" in issue for issue in issues)


def test_factual_validation_uses_fact_boundaries_and_checks_job_titles() -> None:
    allowed = "Worked as a Senior Software Engineer at Acme for 120 clients."
    changes = [{
        "blockId": "block-0003",
        "original": "Software Engineer at Acme",
        "replacement": "Principal Software Engineer at Acme for 12 clients.",
    }]

    issues = validate_factual_changes(changes, allowed)

    assert any("unsupported number" in issue and '"12 clients"' in issue for issue in issues)
    assert any(
        "unsupported job title" in issue and "Principal Software Engineer" in issue
        for issue in issues
    )


def test_cover_letter_diff_compares_the_rendered_docx() -> None:
    source = Document()
    source.add_paragraph("Dear Hiring Team,")
    source.add_paragraph("Original body.")
    source.add_paragraph("Kind regards,")
    source.add_table(rows=1, cols=1).cell(0, 0).text = "Preserved table text"
    rendered = Document(BytesIO(document_bytes(source)))
    rendered.paragraphs[1].text = "Validated replacement body."

    diff = build_document_diff(
        document_bytes(source),
        "This raw assistant text is not the comparison authority.",
        "cover_letter",
        rendered_content=document_bytes(rendered),
    )

    assert len(diff) == 1
    assert diff[0]["original"] == "Original body."
    assert diff[0]["replacement"] == "Validated replacement body."


def test_visual_validation_preserves_links_and_detects_table_overflow(monkeypatch) -> None:
    source = Document()
    add_hyperlink(source, "https://example.com/profile")
    source_table = source.add_table(rows=1, cols=1)
    source_table.cell(0, 0).text = "Python"
    rendered = Document(BytesIO(document_bytes(source)))
    rendered.tables[0].cell(0, 0).text = "Python"

    monkeypatch.setattr(
        "app.services.document_validation.render_and_count_pages",
        lambda _source, _rendered: (1, 1),
    )
    report, issues = validate_visual_output(document_bytes(source), document_bytes(rendered))

    assert issues == []
    assert report == {
        "status": "passed",
        "sourcePageCount": 1,
        "renderedPageCount": 1,
        "linksPreserved": True,
        "sourceLinkCount": 1,
        "renderedLinkCount": 1,
        "tableOverflow": False,
    }

    rendered.tables[0].cell(0, 0).text = "X" * 220
    overflow = detect_table_overflow(document_bytes(source), document_bytes(rendered))
    assert "possible table overflow" in overflow[0]

    removed_link = Document(BytesIO(document_bytes(source)))
    hyperlink = removed_link.paragraphs[0]._p.find(qn("w:hyperlink"))
    removed_link.paragraphs[0]._p.remove(hyperlink)
    _, removed_link_issues = validate_visual_output(
        document_bytes(source),
        document_bytes(removed_link),
    )
    assert "hyperlinks changed or were removed" in removed_link_issues

    changed_links = Document()
    add_hyperlink(changed_links, "https://example.com/different")
    changed_links.add_table(rows=1, cols=1).cell(0, 0).text = "Python"
    _, link_issues = validate_visual_output(
        document_bytes(source),
        document_bytes(changed_links),
    )
    assert "hyperlinks changed or were removed" in link_issues


def test_visual_validation_allows_new_links_and_rejects_extra_pages(monkeypatch) -> None:
    source = Document()
    add_hyperlink(source, "https://example.com/original")
    rendered = Document(BytesIO(document_bytes(source)))
    add_hyperlink(rendered, "https://example.com/new")
    monkeypatch.setattr(
        "app.services.document_validation.render_and_count_pages",
        lambda _source, _rendered: (1, 2),
    )

    report, issues = validate_visual_output(document_bytes(source), document_bytes(rendered))

    assert report["linksPreserved"] is True
    assert report["sourceLinkCount"] == 1
    assert report["renderedLinkCount"] == 2
    assert "page count increased from 1 to 2" in issues


@pytest.mark.skipif(
    not (shutil.which("soffice") or shutil.which("libreoffice")),
    reason="LibreOffice is not installed",
)
def test_docx_is_really_rendered_to_count_pages() -> None:
    source = Document()
    source.add_paragraph("One-page validation fixture")
    source_content = document_bytes(source)
    rendered = Document(BytesIO(source_content))
    rendered.add_page_break()
    rendered.add_paragraph("Second rendered page")

    assert render_and_count_pages(source_content, document_bytes(rendered)) == (1, 2)
