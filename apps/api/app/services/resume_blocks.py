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
UNSUPPORTED_ELEMENTS = {
    "altChunk": "embedded alternative content",
    "customXml": "custom XML blocks",
    "del": "tracked deletions",
    "drawing": "drawings or text boxes",
    "fldChar": "Word fields",
    "fldSimple": "Word fields",
    "ins": "tracked insertions",
    "instrText": "Word fields",
    "moveFrom": "tracked moves",
    "moveTo": "tracked moves",
    "noBreakHyphen": "special hyphen runs",
    "object": "embedded objects",
    "oMath": "equations",
    "oMathPara": "equations",
    "pict": "legacy drawings",
    "ptab": "positional tabs",
    "softHyphen": "special hyphen runs",
    "smartTag": "smart tags",
    "sym": "symbol runs",
    "txbxContent": "text boxes",
}
UNSUPPORTED_CONTENT_CONTROL_PROPERTIES = {
    "checkBox": "checkbox content controls",
    "comboBox": "combo-box content controls",
    "date": "date content controls",
    "docPartObj": "document-part content controls",
    "dropDownList": "drop-down content controls",
    "picture": "picture content controls",
    "repeatingSection": "repeating-section content controls",
}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class UnsupportedResumeStructureError(ValueError):
    pass


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
    validate_supported_resume_structure(body)
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
    values: list[str] = []
    for part_type, value in paragraph_inline_parts(element):
        values.append(value.text or "" if part_type == "text" else value)
    return "".join(values)


def paragraph_inline_parts(element: Any) -> list[tuple[str, Any]]:
    parts: list[tuple[str, Any]] = []
    for node in element.iter():
        if node is element or nearest_paragraph(node) is not element:
            continue
        if node.tag == qn("w:t"):
            value = node.text or ""
            if "\t" in value or "\n" in value or "\r" in value:
                raise UnsupportedResumeStructureError(
                    "Unsupported DOCX construction: literal tabs or line breaks inside w:t"
                )
            parts.append(("text", node))
        elif node.tag == qn("w:tab"):
            parts.append(("control", "\t"))
        elif node.tag in {qn("w:br"), qn("w:cr")}:
            parts.append(("control", "\n"))
    return parts


def replace_paragraph_text_preserving_inline(element: Any, replacement: str) -> None:
    validate_supported_paragraph(element)
    parts = paragraph_inline_parts(element)
    slot_groups: list[list[Any]] = [[]]
    original_controls: list[str] = []
    for part_type, value in parts:
        if part_type == "text":
            slot_groups[-1].append(value)
        else:
            original_controls.append(value)
            slot_groups.append([])

    replacement_parts = re.split(r"([\t\n])", replacement)
    replacement_segments = replacement_parts[::2]
    replacement_controls = replacement_parts[1::2]
    if replacement_controls != original_controls:
        raise UnsupportedResumeStructureError(
            "Resume replacements must preserve the original tabs and line breaks"
        )
    if len(replacement_segments) != len(slot_groups):
        raise UnsupportedResumeStructureError(
            "Resume replacement does not match the paragraph inline structure"
        )

    for slots, segment in zip(slot_groups, replacement_segments, strict=True):
        distribute_text_across_slots(slots, segment)


def distribute_text_across_slots(slots: list[Any], replacement: str) -> None:
    if not slots:
        if replacement:
            raise UnsupportedResumeStructureError(
                "Resume replacement cannot add text where the DOCX has no text run"
            )
        return

    original_lengths = [len(slot.text or "") for slot in slots]
    active_indexes = [index for index, length in enumerate(original_lengths) if length > 0]
    if not active_indexes:
        if replacement:
            raise UnsupportedResumeStructureError(
                "Resume replacement cannot target an empty run-only segment"
            )
        allocations = [0] * len(slots)
    else:
        allocations = proportional_allocations(original_lengths, len(replacement))

    cursor = 0
    for slot, length in zip(slots, allocations, strict=True):
        value = replacement[cursor : cursor + length]
        cursor += length
        slot.text = value
        if value.startswith(" ") or value.endswith(" "):
            slot.set(XML_SPACE, "preserve")
        else:
            slot.attrib.pop(XML_SPACE, None)


def proportional_allocations(weights: list[int], target_length: int) -> list[int]:
    allocations = [0] * len(weights)
    active_indexes = [index for index, weight in enumerate(weights) if weight > 0]
    if not active_indexes or target_length <= 0:
        return allocations

    baseline = 1 if target_length >= len(active_indexes) else 0
    for index in active_indexes:
        allocations[index] = baseline
    remaining = target_length - baseline * len(active_indexes)
    total_weight = sum(weights[index] for index in active_indexes)
    cumulative_weight = 0
    assigned = 0
    for index in active_indexes:
        cumulative_weight += weights[index]
        cumulative_target = round(cumulative_weight * remaining / total_weight)
        allocations[index] += cumulative_target - assigned
        assigned = cumulative_target
    return allocations


def validate_supported_resume_structure(body: Any) -> None:
    for element in body.iter():
        local_name = etree.QName(element).localname
        unsupported = UNSUPPORTED_ELEMENTS.get(local_name)
        if unsupported:
            raise UnsupportedResumeStructureError(
                f"Unsupported DOCX construction: {unsupported} ({local_name})"
            )
        if local_name == "sdtPr":
            for property_element in element.iterchildren():
                property_name = etree.QName(property_element).localname
                unsupported_property = UNSUPPORTED_CONTENT_CONTROL_PROPERTIES.get(property_name)
                if unsupported_property:
                    raise UnsupportedResumeStructureError(
                        "Unsupported DOCX construction: "
                        f"{unsupported_property} ({property_name})"
                    )


def validate_supported_paragraph(paragraph: Any) -> None:
    for element in paragraph.iter():
        local_name = etree.QName(element).localname
        unsupported = UNSUPPORTED_ELEMENTS.get(local_name)
        if unsupported:
            raise UnsupportedResumeStructureError(
                f"Unsupported DOCX construction: {unsupported} ({local_name})"
            )
        if local_name == "sdtPr":
            for property_element in element.iterchildren():
                property_name = etree.QName(property_element).localname
                unsupported_property = UNSUPPORTED_CONTENT_CONTROL_PROPERTIES.get(property_name)
                if unsupported_property:
                    raise UnsupportedResumeStructureError(
                        "Unsupported DOCX construction: "
                        f"{unsupported_property} ({property_name})"
                    )


def nearest_paragraph(element: Any) -> Any | None:
    ancestor = element.getparent()
    while ancestor is not None:
        if ancestor.tag == qn("w:p"):
            return ancestor
        ancestor = ancestor.getparent()
    return None


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
