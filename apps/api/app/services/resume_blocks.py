import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

from docx.oxml.ns import qn
from lxml import etree


ResumeBlockType = Literal[
    "immutable",
    "summary",
    "skill",
    "achievement",
    "heading",
    "contact",
    "table cell",
]

HEADING_WORDS = {
    "about",
    "achievements",
    "certifications",
    "education",
    "experience",
    "languages",
    "profile",
    "projects",
    "skills",
    "summary",
    "technical skills",
    "work experience",
}
SUMMARY_SECTIONS = {"about", "objective", "profile", "professional profile", "summary"}
SKILL_SECTIONS = {"competencies", "skills", "technical skills", "technologies", "tools"}
ACHIEVEMENT_SECTIONS = {
    "achievements",
    "experience",
    "projects",
    "professional experience",
    "work experience",
}
CONTACT_PATTERN = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|linkedin\.com|github\.com|"
    r"(?:\+?\d[\d\s()./-]{7,}\d))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResumeBlock:
    block_id: str
    block_type: ResumeBlockType
    original: str
    element: Any

    def as_context(self) -> dict[str, str]:
        return {
            "blockId": self.block_id,
            "type": self.block_type,
            "original": self.original,
        }


def extract_resume_blocks_from_docx(content: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    body = root.find(qn("w:body"))
    if body is None:
        raise ValueError("Resume template has no document body")
    return [block.as_context() for block in parse_resume_blocks(body)]


def parse_resume_blocks(body: Any) -> list[ResumeBlock]:
    blocks: list[ResumeBlock] = []
    current_section = ""
    for paragraph in body.iter(qn("w:p")):
        original = paragraph_text(paragraph)
        text = original.strip()
        if not text:
            continue
        block_type = classify_resume_block(
            paragraph,
            text,
            current_section=current_section,
            block_index=len(blocks),
        )
        block = ResumeBlock(
            block_id=f"block-{len(blocks) + 1:04d}",
            block_type=block_type,
            original=original,
            element=paragraph,
        )
        blocks.append(block)
        if block_type == "heading":
            current_section = normalize_heading(text)
    return blocks


def classify_resume_block(
    paragraph: Any,
    text: str,
    *,
    current_section: str,
    block_index: int,
) -> ResumeBlockType:
    if has_ancestor(paragraph, qn("w:tc")):
        return "table cell"
    if is_heading(paragraph, text):
        return "heading"
    if CONTACT_PATTERN.search(text):
        return "contact"
    if current_section in SUMMARY_SECTIONS:
        return "summary"
    if current_section in SKILL_SECTIONS:
        return "skill"
    if current_section in ACHIEVEMENT_SECTIONS and len(text) >= 20:
        return "achievement"
    if has_numbering(paragraph):
        return "achievement"
    if block_index <= 2 and len(text) >= 40 and len(text.split()) >= 6:
        return "summary"
    if len(text) <= 160 and len(re.split(r"[,|•]", text)) >= 3:
        return "skill"
    return "immutable"


def paragraph_text(element: Any) -> str:
    return "".join(node.text or "" for node in paragraph_text_nodes(element))


def paragraph_text_nodes(element: Any) -> list[Any]:
    nodes: list[Any] = []
    for node in element.iter(qn("w:t")):
        ancestor = node.getparent()
        while ancestor is not None and ancestor.tag != qn("w:p"):
            ancestor = ancestor.getparent()
        if ancestor is element:
            nodes.append(node)
    return nodes


def has_ancestor(element: Any, tag: str) -> bool:
    ancestor = element.getparent()
    while ancestor is not None:
        if ancestor.tag == tag:
            return True
        ancestor = ancestor.getparent()
    return False


def has_numbering(paragraph: Any) -> bool:
    properties = paragraph.find(qn("w:pPr"))
    return properties is not None and properties.find(qn("w:numPr")) is not None


def is_heading(paragraph: Any, text: str) -> bool:
    properties = paragraph.find(qn("w:pPr"))
    style = properties.find(qn("w:pStyle")) if properties is not None else None
    style_name = style.get(qn("w:val"), "").lower() if style is not None else ""
    normalized = normalize_heading(text)
    return (
        style_name.startswith("heading")
        or normalized in HEADING_WORDS
        or (len(text) <= 48 and text.isupper() and any(character.isalpha() for character in text))
    )


def normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip(":"))
