import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

from docx.oxml.ns import qn
from lxml import etree

from app.services.document_security import validate_docx_package
from app.services.resume_headings import (
    ACHIEVEMENT_HEADINGS,
    ALL_RESUME_HEADINGS,
    EXPERIENCE_HEADINGS,
    LANGUAGE_HEADINGS,
    PROJECT_HEADINGS,
    SKILL_HEADINGS,
    SUMMARY_HEADINGS,
    normalize_resume_heading,
)


ResumeBlockType = Literal[
    "immutable",
    "summary",
    "skill",
    "achievement",
    "heading",
    "contact",
    "table cell",
]
ResumeSpanType = Literal[
    "text",
    "hyperlink",
    "tab",
    "lineBreak",
    "drawing",
    "symbol",
    "field",
]
EDITABLE_BLOCK_TYPES = {"summary", "skill", "achievement"}

HEADING_WORDS = ALL_RESUME_HEADINGS
SUMMARY_SECTIONS = SUMMARY_HEADINGS
SKILL_SECTIONS = frozenset().union(SKILL_HEADINGS, LANGUAGE_HEADINGS)
ACHIEVEMENT_SECTIONS = frozenset().union(
    EXPERIENCE_HEADINGS,
    PROJECT_HEADINGS,
    ACHIEVEMENT_HEADINGS,
)
CONTACT_PATTERN = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|linkedin\.com|github\.com|"
    r"(?:\+?\d[\d\s()./-]{7,}\d))",
    re.IGNORECASE,
)
UNSUPPORTED_ELEMENTS = {
    "altChunk": "embedded alternative content",
    "customXml": "custom XML blocks",
    "del": "tracked deletions",
    "ins": "tracked insertions",
    "moveFrom": "tracked moves",
    "moveTo": "tracked moves",
    "noBreakHyphen": "special hyphen runs",
    "object": "embedded objects",
    "oMath": "equations",
    "oMathPara": "equations",
    "ptab": "positional tabs",
    "softHyphen": "special hyphen runs",
    "smartTag": "smart tags",
    "txbxContent": "text boxes",
}
SUPPORTED_WORD_FIELDS = {
    "AUTHOR",
    "COMMENTS",
    "CREATEDATE",
    "DATE",
    "DOCPROPERTY",
    "FILENAME",
    "FILESIZE",
    "HYPERLINK",
    "KEYWORDS",
    "LASTSAVEDBY",
    "NUMPAGES",
    "PAGE",
    "PAGEREF",
    "PRINTDATE",
    "REF",
    "REVNUM",
    "SAVEDATE",
    "SECTION",
    "SECTIONPAGES",
    "SUBJECT",
    "TIME",
    "TITLE",
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
class UnsupportedWordConstruction:
    element: str
    description: str

    @property
    def message(self) -> str:
        return f"Unsupported DOCX construction: {self.description} ({self.element})"


@dataclass(frozen=True)
class ResumeSpan:
    span_id: str
    span_type: ResumeSpanType
    original: str
    editable: bool
    text_nodes: tuple[Any, ...] = ()

    def as_context(self) -> dict[str, str | bool]:
        return {
            "spanId": self.span_id,
            "type": self.span_type,
            "original": self.original,
            "editable": self.editable,
            "evidenceId": source_span_evidence_id(self.span_id),
        }


@dataclass(frozen=True)
class ResumeBlock:
    block_id: str
    block_type: ResumeBlockType
    original: str
    editable: bool
    spans: tuple[ResumeSpan, ...]

    def as_context(self) -> dict[str, Any]:
        return {
            "blockId": self.block_id,
            "type": self.block_type,
            "original": self.original,
            "editable": self.editable,
            "spans": [span.as_context() for span in self.spans],
        }


def extract_resume_blocks_from_docx(content: bytes) -> list[dict[str, Any]]:
    validate_docx_package(content)
    with zipfile.ZipFile(BytesIO(content)) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    body = root.find(qn("w:body"))
    if body is None:
        raise ValueError("Resume template has no document body")
    return [block.as_context() for block in parse_resume_blocks(body)]


def parse_resume_blocks(body: Any) -> list[ResumeBlock]:
    validate_supported_word_structure(body)
    blocks: list[ResumeBlock] = []
    document_section = ""
    table_column_sections: dict[Any, dict[int, str]] = {}
    active_table_row: Any | None = None
    active_row_section = ""
    for paragraph in body.iter(qn("w:p")):
        original = paragraph_text(paragraph)
        text = original.strip()
        if not text:
            continue
        table_cell = nearest_ancestor(paragraph, qn("w:tc"))
        table = nearest_ancestor(table_cell, qn("w:tbl")) if table_cell is not None else None
        table_row = nearest_ancestor(table_cell, qn("w:tr")) if table_cell is not None else None
        if table_row is not active_table_row:
            active_table_row = table_row
            active_row_section = ""
        if table is not None and table_cell is not None:
            column_index = table_cell_column_index(table_cell)
            current_section = (
                active_row_section
                or table_column_sections.get(table, {}).get(column_index, "")
            )
        else:
            column_index = None
            current_section = document_section
        block_type = classify_resume_block(
            paragraph,
            text,
            current_section=current_section,
            block_index=len(blocks),
        )
        block_id = f"block-{len(blocks) + 1:04d}"
        allows_edits = block_type in EDITABLE_BLOCK_TYPES
        spans = tuple(
            build_resume_spans(
                paragraph,
                block_id=block_id,
                block_editable=allows_edits,
            )
        )
        block = ResumeBlock(
            block_id=block_id,
            block_type=block_type,
            original=original,
            editable=any(span.editable for span in spans),
            spans=spans,
        )
        blocks.append(block)
        if block_type == "heading":
            section = normalize_heading(text)
            if table is not None and column_index is not None:
                column_sections = table_column_sections.setdefault(table, {})
                for covered_column in range(
                    column_index,
                    column_index + table_cell_grid_span(table_cell),
                ):
                    column_sections[covered_column] = section
                active_row_section = section
            else:
                document_section = section
    return blocks


def classify_resume_block(
    paragraph: Any,
    text: str,
    *,
    current_section: str,
    block_index: int,
) -> ResumeBlockType:
    if is_heading(paragraph, text):
        return "heading"
    in_table_cell = has_ancestor(paragraph, qn("w:tc"))
    if CONTACT_PATTERN.search(text):
        return "table cell" if in_table_cell else "contact"
    if current_section in SUMMARY_SECTIONS:
        return "summary"
    if current_section in SKILL_SECTIONS:
        return "skill"
    if current_section in ACHIEVEMENT_SECTIONS and len(text) >= 20:
        return "achievement"
    if in_table_cell:
        return "table cell"
    if has_numbering(paragraph):
        return "achievement"
    if block_index <= 2 and len(text) >= 40 and len(text.split()) >= 6:
        return "summary"
    if len(text) <= 160 and len(re.split(r"[,|•]", text)) >= 3:
        return "skill"
    return "immutable"


def paragraph_text(element: Any) -> str:
    return "".join(token.original for token in paragraph_inline_tokens(element))


@dataclass(frozen=True)
class InlineToken:
    token_type: ResumeSpanType
    original: str
    text_node: Any | None
    hyperlink: Any | None
    formatting_signature: bytes


def paragraph_inline_tokens(element: Any) -> list[InlineToken]:
    tokens: list[InlineToken] = []
    complex_field_depth = 0
    for node in element.iter():
        if node is element or nearest_paragraph(node) is not element:
            continue
        if nearest_ancestor(node, qn("w:fldSimple")) is not None:
            continue
        if nearest_ancestor(node, qn("w:drawing")) is not None:
            continue
        if nearest_ancestor(node, qn("w:pict")) is not None:
            continue
        if node.tag == qn("w:fldSimple"):
            tokens.append(protected_inline_token("field", "[Field]", node))
            continue
        if node.tag == qn("w:fldChar"):
            field_type = node.get(qn("w:fldCharType"), "")
            if field_type == "begin":
                if complex_field_depth == 0:
                    tokens.append(protected_inline_token("field", "[Field]", node))
                complex_field_depth += 1
            elif field_type == "end":
                complex_field_depth = max(0, complex_field_depth - 1)
            continue
        if complex_field_depth:
            continue
        if node.tag in {qn("w:drawing"), qn("w:pict")}:
            tokens.append(protected_inline_token("drawing", "[Drawing]", node))
            continue
        if node.tag == qn("w:sym"):
            tokens.append(protected_inline_token("symbol", symbol_label(node), node))
            continue
        if node.tag == qn("w:t"):
            value = node.text or ""
            if "\t" in value or "\n" in value or "\r" in value:
                raise UnsupportedResumeStructureError(
                    "Unsupported DOCX construction: literal tabs or line breaks inside w:t"
                )
            tokens.append(
                InlineToken(
                    token_type="text",
                    original=value,
                    text_node=node,
                    hyperlink=nearest_ancestor(node, qn("w:hyperlink")),
                    formatting_signature=run_formatting_signature(node),
                )
            )
        elif node.tag == qn("w:tab"):
            tokens.append(
                InlineToken(
                    token_type="tab",
                    original="\t",
                    text_node=None,
                    hyperlink=nearest_ancestor(node, qn("w:hyperlink")),
                    formatting_signature=b"",
                )
            )
        elif node.tag in {qn("w:br"), qn("w:cr")}:
            tokens.append(
                InlineToken(
                    token_type="lineBreak",
                    original="\n",
                    text_node=None,
                    hyperlink=nearest_ancestor(node, qn("w:hyperlink")),
                    formatting_signature=b"",
                )
            )
    return tokens


def protected_inline_token(
    token_type: ResumeSpanType,
    original: str,
    node: Any,
) -> InlineToken:
    return InlineToken(
        token_type=token_type,
        original=original,
        text_node=None,
        hyperlink=nearest_ancestor(node, qn("w:hyperlink")),
        formatting_signature=b"",
    )


def symbol_label(node: Any) -> str:
    character = node.get(qn("w:char"), "").upper()
    return f"[Symbol {character}]" if character else "[Symbol]"


def build_resume_spans(
    paragraph: Any,
    *,
    block_id: str,
    block_editable: bool,
) -> list[ResumeSpan]:
    tokens = paragraph_inline_tokens(paragraph)
    spans: list[ResumeSpan] = []
    cursor = 0
    while cursor < len(tokens):
        token = tokens[cursor]
        if token.hyperlink is not None:
            end = cursor + 1
            while end < len(tokens) and tokens[end].hyperlink is token.hyperlink:
                end += 1
            group = tokens[cursor:end]
            append_resume_span(
                spans,
                block_id=block_id,
                span_type="hyperlink",
                tokens=group,
                editable=False,
            )
            cursor = end
            continue
        if token.token_type != "text":
            append_resume_span(
                spans,
                block_id=block_id,
                span_type=token.token_type,
                tokens=[token],
                editable=False,
            )
            cursor += 1
            continue

        end = cursor + 1
        while (
            end < len(tokens)
            and tokens[end].hyperlink is None
            and tokens[end].token_type == "text"
        ):
            end += 1
        group = tokens[cursor:end]
        signatures = {
            item.formatting_signature
            for item in group
            if item.original
        }
        if block_editable and len(signatures) > 1:
            raise UnsupportedResumeStructureError(
                "Unsupported DOCX construction: ambiguous mixed formatting in "
                f"editable resume block ({block_id})"
            )
        original = "".join(item.original for item in group)
        append_resume_span(
            spans,
            block_id=block_id,
            span_type="text",
            tokens=group,
            editable=block_editable and bool(original.strip()),
        )
        cursor = end
    return spans


def append_resume_span(
    spans: list[ResumeSpan],
    *,
    block_id: str,
    span_type: ResumeSpanType,
    tokens: list[InlineToken],
    editable: bool,
) -> None:
    original = "".join(token.original for token in tokens)
    if not original:
        return
    spans.append(
        ResumeSpan(
            span_id=f"{block_id}-span-{len(spans) + 1:04d}",
            span_type=span_type,
            original=original,
            editable=editable,
            text_nodes=tuple(
                token.text_node for token in tokens if token.text_node is not None
            ),
        )
    )


def run_formatting_signature(text_node: Any) -> bytes:
    run = nearest_ancestor(text_node, qn("w:r"))
    properties = run.find(qn("w:rPr")) if run is not None else None
    return etree.tostring(properties) if properties is not None else b""


def replace_resume_text_span(span: ResumeSpan, replacement: str) -> None:
    if not span.editable or span.span_type != "text":
        raise ValueError(f"Immutable resume span cannot be changed: {span.span_id}")
    if not replacement.strip():
        raise ValueError(f"Resume span replacement cannot be empty: {span.span_id}")
    if any(control in replacement for control in ("\t", "\n", "\r")):
        raise ValueError(
            f"Resume text span replacement cannot contain tabs or line breaks: {span.span_id}"
        )
    if not span.text_nodes:
        raise ValueError(f"Resume text span has no editable text node: {span.span_id}")
    first, *remaining = span.text_nodes
    set_text_node_value(first, replacement)
    for node in remaining:
        set_text_node_value(node, "")


def set_text_node_value(node: Any, value: str) -> None:
    node.text = value
    if value.startswith(" ") or value.endswith(" "):
        node.set(XML_SPACE, "preserve")
    else:
        node.attrib.pop(XML_SPACE, None)


def source_span_evidence_id(span_id: str) -> str:
    return f"source:{span_id}"


def validate_supported_word_structure(body: Any) -> None:
    unsupported = find_unsupported_word_constructions(body)
    if unsupported:
        raise UnsupportedResumeStructureError(unsupported[0].message)


def find_unsupported_word_constructions(body: Any) -> list[UnsupportedWordConstruction]:
    """Return every distinct Word construction that cannot be tailored safely."""
    issues: list[UnsupportedWordConstruction] = []
    seen: set[tuple[str, str]] = set()

    def append_issue(element: str, description: str) -> None:
        key = (element, description)
        if key not in seen:
            seen.add(key)
            issues.append(
                UnsupportedWordConstruction(
                    element=element,
                    description=description,
                )
            )

    field_stack: list[tuple[Any | None, list[str]]] = []
    for element in body.iter():
        local_name = etree.QName(element).localname
        unsupported = UNSUPPORTED_ELEMENTS.get(local_name)
        if unsupported:
            append_issue(local_name, unsupported)
        if local_name == "blip" and element.get(qn("r:link")):
            append_issue("drawing", "externally linked drawings")
        if local_name == "t":
            value = element.text or ""
            if "\t" in value or "\n" in value or "\r" in value:
                append_issue("t", "literal tabs or line breaks inside w:t")
        if local_name == "sdtPr":
            for property_element in element.iterchildren():
                property_name = etree.QName(property_element).localname
                unsupported_property = UNSUPPORTED_CONTENT_CONTROL_PROPERTIES.get(property_name)
                if unsupported_property:
                    append_issue(property_name, unsupported_property)
        if local_name == "fldSimple":
            append_field_issue(
                append_issue,
                element.get(qn("w:instr"), ""),
            )
        elif local_name == "fldChar":
            field_type = element.get(qn("w:fldCharType"), "")
            if field_type == "begin":
                if field_stack:
                    append_issue("field", "nested Word fields")
                field_stack.append((nearest_paragraph(element), []))
            elif field_type == "end":
                if not field_stack:
                    append_issue("field", "field end without a matching begin")
                else:
                    field_paragraph, instructions = field_stack.pop()
                    if field_paragraph is not nearest_paragraph(element):
                        append_issue("field", "Word fields spanning multiple paragraphs")
                    append_field_issue(append_issue, "".join(instructions))
            elif field_type not in {"separate"}:
                append_issue("field", f"unknown field marker {field_type or 'empty'}")
        elif local_name == "instrText":
            if not field_stack:
                append_issue("field", "field instruction without a matching begin")
            else:
                field_stack[-1][1].append(element.text or "")
    if field_stack:
        append_issue("field", "field begin without a matching end")
    return issues


def append_field_issue(
    append_issue: Any,
    instruction: str,
) -> None:
    match = re.match(r"\s*([A-Za-z][A-Za-z0-9]*)\b", instruction)
    if not match:
        append_issue("field", "Word field has no supported instruction")
        return
    field_name = match.group(1).upper()
    if field_name not in SUPPORTED_WORD_FIELDS:
        append_issue("field", f"unsupported Word field {field_name}")


def nearest_ancestor(element: Any | None, tag: str) -> Any | None:
    if element is None:
        return None
    ancestor = element.getparent()
    while ancestor is not None:
        if ancestor.tag == tag:
            return ancestor
        ancestor = ancestor.getparent()
    return None


def nearest_paragraph(element: Any) -> Any | None:
    return nearest_ancestor(element, qn("w:p"))


def has_ancestor(element: Any, tag: str) -> bool:
    return nearest_ancestor(element, tag) is not None


def table_cell_column_index(cell: Any) -> int:
    row = nearest_ancestor(cell, qn("w:tr"))
    if row is None:
        return 0
    column_index = 0
    for sibling in row.iterchildren(qn("w:tc")):
        if sibling is cell:
            return column_index
        column_index += table_cell_grid_span(sibling)
    return column_index


def table_cell_grid_span(cell: Any) -> int:
    properties = cell.find(qn("w:tcPr"))
    grid_span = properties.find(qn("w:gridSpan")) if properties is not None else None
    try:
        return max(1, int(grid_span.get(qn("w:val"), "1"))) if grid_span is not None else 1
    except ValueError:
        return 1


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
    return normalize_resume_heading(text)
