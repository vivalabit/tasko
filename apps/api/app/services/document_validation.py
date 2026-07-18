import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml.ns import qn
from lxml import etree
from pypdf import PdfReader

from app.services.document_export import parse_resume_replacements
from app.services.resume_blocks import extract_resume_blocks_from_docx


TECHNOLOGIES = {
    "angular",
    "aws",
    "azure",
    "c#",
    "c++",
    "css",
    "django",
    "docker",
    "excel",
    "fastapi",
    "figma",
    "flask",
    "gcp",
    "git",
    "go",
    "graphql",
    "html",
    "java",
    "javascript",
    "kotlin",
    "kubernetes",
    "mongodb",
    "mysql",
    "next.js",
    "node.js",
    "postgresql",
    "power bi",
    "python",
    "react",
    "redis",
    "rest",
    "rust",
    "salesforce",
    "sap",
    "sketch",
    "sql",
    "swift",
    "tableau",
    "terraform",
    "typescript",
    "vue",
}
CLAIM_VERBS = {
    "achieved",
    "architected",
    "automated",
    "baute",
    "built",
    "created",
    "delivered",
    "designed",
    "developed",
    "drove",
    "entwickelte",
    "generated",
    "grew",
    "implemented",
    "implementierte",
    "improved",
    "increased",
    "launched",
    "led",
    "leitete",
    "lieferte",
    "managed",
    "mentored",
    "optimized",
    "optimierte",
    "owned",
    "reduced",
    "reduzierte",
    "saved",
    "scaled",
    "skalierte",
    "spearheaded",
    "steigerte",
    "transformed",
}
STOP_WORDS = {
    "about",
    "across",
    "and",
    "for",
    "from",
    "für",
    "into",
    "mit",
    "und",
    "that",
    "the",
    "their",
    "through",
    "using",
    "with",
}
DATE_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?|januar|februar|märz|mai|juni|juli|oktober|"
    r"dezember)\s+(?:19|20)\d{2}\b|\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(
    r"(?<![\w-])(?:[$€£]\s*)?\d+(?:[.,]\d+)?(?:\s*(?:%|x|k|m|million|billion|users?|"
    r"clients?|projects?|people|members?|months?|years?))?(?![\w-])",
    re.IGNORECASE,
)
COMPANY_PATTERN = re.compile(
    r"(?:\b(?:at|with|bei)\s+|\b(?:worked|working|consulted|employed|arbeitete)\s+"
    r"(?:for|für)\s+)([A-ZÄÖÜ][\w&.-]+"
    r"(?:\s+[A-ZÄÖÜ][\w&.-]+){0,3})",
)
TITLE_PATTERN = re.compile(
    r"\b(?:as|als)\s+(?:an?\s+)?((?:[A-ZÄÖÜ][\w/-]*\s+){0,4}"
    r"(?:Engineer|Designer|Manager|Director|Lead|Consultant|Developer|Architect|Analyst|"
    r"Entwickler|Ingenieur|Berater|Leiter))\b|"
    r"\b((?:Senior|Lead|Principal|Staff|Junior)\s+(?:Software\s+)?"
    r"(?:Engineer|Designer|Manager|Director|Consultant|Developer|Architect|Analyst))"
    r"\s+(?:at|bei)\b",
)
RENDER_TIMEOUT_SECONDS = 90


class DocumentValidationError(ValueError):
    pass


def validate_generated_document(
    *,
    template_content: bytes,
    rendered_content: bytes,
    generated_content: str,
    document_type: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    source_text = extract_docx_text(template_content)
    evidence_text = "\n".join(flatten_evidence(evidence))
    allowed_text = f"{source_text}\n{evidence_text}"
    diff = build_document_diff(
        template_content,
        generated_content,
        document_type,
        rendered_content=rendered_content,
    )
    factual_issues = validate_factual_changes(diff, allowed_text)
    visual_report, visual_issues = validate_visual_output(template_content, rendered_content)
    issues = [*factual_issues, *visual_issues]
    if issues:
        raise DocumentValidationError("Document validation failed: " + "; ".join(issues[:8]))
    return {
        "factual": {
            "status": "passed",
            "checkedChanges": len(diff),
            "checkedEvidenceCharacters": len(allowed_text),
        },
        "visual": visual_report,
        "diff": diff,
    }


def build_document_diff(
    template_content: bytes,
    generated_content: str,
    document_type: str,
    *,
    rendered_content: bytes | None = None,
) -> list[dict[str, str]]:
    if document_type == "tailored_resume":
        blocks = {
            block["blockId"]: block
            for block in extract_resume_blocks_from_docx(template_content)
        }
        return [
            {
                "blockId": replacement["blockId"],
                "spanId": replacement["spanId"],
                "type": blocks.get(replacement["blockId"], {}).get("type", "block"),
                "original": replacement["original"],
                "replacement": replacement["replacement"],
                "reason": replacement["reason"],
            }
            for replacement in parse_resume_replacements(generated_content)
            if replacement["replacement"] != replacement["original"]
        ]

    original_paragraphs = extract_docx_paragraphs(template_content)
    if rendered_content is not None:
        generated_paragraphs = extract_docx_paragraphs(rendered_content)
    else:
        generated_paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", generated_content.strip())
            if paragraph.strip()
        ]
    matcher = SequenceMatcher(a=original_paragraphs, b=generated_paragraphs, autojunk=False)
    diff: list[dict[str, str]] = []
    for change_index, (operation, left_start, left_end, right_start, right_end) in enumerate(
        matcher.get_opcodes(),
        start=1,
    ):
        if operation == "equal":
            continue
        diff.append(
            {
                "blockId": f"paragraph-change-{change_index:04d}",
                "type": "paragraph",
                "original": "\n\n".join(original_paragraphs[left_start:left_end]),
                "replacement": "\n\n".join(generated_paragraphs[right_start:right_end]),
                "reason": "Generated cover-letter paragraph update",
            }
        )
    return diff


def validate_factual_changes(diff: list[dict[str, str]], allowed_text: str) -> list[str]:
    issues: list[str] = []
    allowed_normalized = normalize_fact(allowed_text)
    allowed_tokens = significant_tokens(allowed_text)
    for change in diff:
        original = change["original"]
        replacement = change["replacement"]
        for label, extractor in (
            ("date", extract_dates),
            ("number", extract_numbers),
            ("technology", extract_technologies),
            ("company", extract_companies),
            ("job title", extract_titles),
        ):
            original_values = {normalize_fact(value) for value in extractor(original)}
            for value in extractor(replacement):
                normalized = normalize_fact(value)
                if normalized not in original_values and not contains_normalized_fact(
                    allowed_normalized,
                    normalized,
                ):
                    issues.append(
                        f'{change["blockId"]} adds unsupported {label} "{value}"'
                    )

        for sentence in split_sentences(replacement):
            sentence_tokens = significant_tokens(sentence) - CLAIM_VERBS
            if not (significant_tokens(sentence) & CLAIM_VERBS) or not sentence_tokens:
                continue
            supported = sentence_tokens & allowed_tokens
            if len(supported) / len(sentence_tokens) < 0.5:
                issues.append(
                    f'{change["blockId"]} adds an unsupported claim "{sentence[:100]}"'
                )
    return issues


def validate_visual_output(
    template_content: bytes,
    rendered_content: bytes,
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    source_links = Counter(extract_hyperlink_targets(template_content))
    rendered_links = Counter(extract_hyperlink_targets(rendered_content))
    links_preserved = all(
        rendered_links[target] >= count for target, count in source_links.items()
    )
    if not links_preserved:
        issues.append("hyperlinks changed or were removed")

    table_issues = detect_table_overflow(template_content, rendered_content)
    issues.extend(table_issues)
    source_pages, rendered_pages = render_and_count_pages(template_content, rendered_content)
    if rendered_pages > source_pages:
        issues.append(
            f"page count increased from {source_pages} to {rendered_pages}"
        )
    return (
        {
            "status": "passed" if not issues else "failed",
            "sourcePageCount": source_pages,
            "renderedPageCount": rendered_pages,
            "linksPreserved": links_preserved,
            "sourceLinkCount": sum(source_links.values()),
            "renderedLinkCount": sum(rendered_links.values()),
            "tableOverflow": bool(table_issues),
        },
        issues,
    )


def render_and_count_pages(source: bytes, rendered: bytes) -> tuple[int, int]:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        raise DocumentValidationError(
            "Document validation failed: LibreOffice is required for page validation"
        )
    stable_tmp = "/private/tmp" if Path("/private/tmp").is_dir() else None
    with tempfile.TemporaryDirectory(
        prefix="tasko-docx-validation-",
        dir=stable_tmp,
    ) as directory:
        workdir = Path(directory)
        source_path = workdir / "source.docx"
        rendered_path = workdir / "rendered.docx"
        source_path.write_bytes(source)
        rendered_path.write_bytes(rendered)
        runtime_home = workdir / "home"
        runtime_home.mkdir()
        runtime_tmp = Path("/private/tmp")
        if not runtime_tmp.is_dir():
            runtime_tmp = workdir / "tmp"
            runtime_tmp.mkdir()
        environment = {
            **os.environ,
            "HOME": str(runtime_home),
            "TMPDIR": str(runtime_tmp),
            "TEMP": str(runtime_tmp),
            "TMP": str(runtime_tmp),
            "XDG_CONFIG_HOME": str(runtime_home / "xdg-config"),
            "XDG_CACHE_HOME": str(runtime_home / "xdg-cache"),
        }
        Path(environment["XDG_CONFIG_HOME"]).mkdir()
        Path(environment["XDG_CACHE_HOME"]).mkdir()
        for input_path in (source_path, rendered_path):
            profile = workdir / f"libreoffice-profile-{input_path.stem}"
            profile.mkdir()
            try:
                result = subprocess.run(
                    [
                        executable,
                        "--invisible",
                        "--headless",
                        "--norestore",
                        "--nofirststartwizard",
                        f"-env:UserInstallation={profile.as_uri()}",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(workdir),
                        str(input_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=RENDER_TIMEOUT_SECONDS,
                    check=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                raise DocumentValidationError(
                    "Document validation failed: DOCX rendering timed out"
                ) from exc
            output_path = workdir / f"{input_path.stem}.pdf"
            if result.returncode != 0 or not output_path.exists():
                detail = (result.stderr or result.stdout or "unknown conversion error").strip()
                raise DocumentValidationError(
                    f"Document validation failed: DOCX rendering failed ({detail[:240]})"
                )
        source_pdf = workdir / "source.pdf"
        rendered_pdf = workdir / "rendered.pdf"
        try:
            source_pages = len(PdfReader(source_pdf).pages)
            rendered_pages = len(PdfReader(rendered_pdf).pages)
        except Exception as exc:
            raise DocumentValidationError(
                "Document validation failed: rendered PDF could not be inspected"
            ) from exc
        rasterizer = shutil.which("pdftoppm")
        if not rasterizer:
            raise DocumentValidationError(
                "Document validation failed: pdftoppm is required for visual validation"
            )
        try:
            raster_result = subprocess.run(
                [rasterizer, "-png", "-r", "96", str(rendered_pdf), str(workdir / "page")],
                capture_output=True,
                text=True,
                timeout=RENDER_TIMEOUT_SECONDS,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise DocumentValidationError(
                "Document validation failed: rendered page inspection timed out"
            ) from exc
        rendered_images = sorted(workdir.glob("page-*.png"))
        if (
            raster_result.returncode != 0
            or len(rendered_images) != rendered_pages
            or any(image.stat().st_size == 0 for image in rendered_images)
        ):
            detail = (
                raster_result.stderr or raster_result.stdout or "incomplete page rasterization"
            ).strip()
            raise DocumentValidationError(
                f"Document validation failed: rendered page inspection failed ({detail[:240]})"
            )
        return source_pages, rendered_pages


def detect_table_overflow(source: bytes, rendered: bytes) -> list[str]:
    source_document = Document(BytesIO(source))
    rendered_document = Document(BytesIO(rendered))
    issues: list[str] = []
    if len(source_document.tables) != len(rendered_document.tables):
        return ["table count changed"]
    for table_index, (source_table, rendered_table) in enumerate(
        zip(source_document.tables, rendered_document.tables, strict=True),
        start=1,
    ):
        rendered_width = table_width_twips(rendered_table)
        available_width = max(
            section_available_width_twips(section)
            for section in rendered_document.sections
        )
        if rendered_width and rendered_width > available_width + 20:
            issues.append(f"table {table_index} exceeds the available page width")
        if len(source_table.rows) != len(rendered_table.rows):
            issues.append(f"row count changed in table {table_index}")
            continue
        for row_index, (source_row, rendered_row) in enumerate(
            zip(source_table.rows, rendered_table.rows, strict=True),
            start=1,
        ):
            if len(source_row.cells) != len(rendered_row.cells):
                issues.append(f"cell count changed in table {table_index}, row {row_index}")
                continue
            for cell_index, (source_cell, rendered_cell) in enumerate(
                zip(source_row.cells, rendered_row.cells, strict=True),
                start=1,
            ):
                exact_height = rendered_row.height_rule == WD_ROW_HEIGHT_RULE.EXACTLY
                content_expanded_excessively = len(rendered_cell.text.strip()) > max(
                    180,
                    len(source_cell.text.strip()) * 3,
                )
                fixed_row_would_clip = exact_height and row_text_exceeds_exact_height(
                    source_cell.text,
                    rendered_cell.text,
                    rendered_cell,
                    rendered_row,
                )
                if content_expanded_excessively or fixed_row_would_clip:
                    issues.append(
                        f"possible table overflow at table {table_index}, row {row_index}, "
                        f"cell {cell_index}"
                    )
    return issues


def table_width_twips(table: Any) -> int:
    grid = table._tbl.tblGrid
    if grid is None:
        return 0
    return sum(
        int(column.get(qn("w:w"), "0"))
        for column in grid.gridCol_lst
    )


def section_available_width_twips(section: Any) -> int:
    width = int(section.page_width or 0)
    left = int(section.left_margin or 0)
    right = int(section.right_margin or 0)
    return max(0, (width - left - right) // 635)


def row_text_exceeds_exact_height(
    source_text: str,
    rendered_text: str,
    rendered_cell: Any,
    rendered_row: Any,
) -> bool:
    height = int(rendered_row.height or 0) // 635
    width_element = rendered_cell._tc.tcPr.tcW
    width = int(width_element.get(qn("w:w"), "0")) if width_element is not None else 0
    if height <= 0 or width <= 0:
        return len(rendered_text.strip()) > max(80, len(source_text.strip()) * 1.4)
    characters_per_line = max(8, width // 110)
    line_capacity = max(1, height // 240)
    source_lines = estimated_wrapped_lines(source_text, characters_per_line)
    rendered_lines = estimated_wrapped_lines(rendered_text, characters_per_line)
    return rendered_lines > max(source_lines, line_capacity)


def estimated_wrapped_lines(text: str, characters_per_line: int) -> int:
    lines = text.splitlines() or [""]
    return sum(
        max(1, (len(line) + characters_per_line - 1) // characters_per_line)
        for line in lines
    )


def extract_hyperlink_targets(content: bytes) -> list[str]:
    targets: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        archive_names = archive.namelist()
        for name in archive_names:
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            part_root = etree.fromstring(archive.read(name))
            directory, file_name = name.rsplit("/", 1)
            relationships_name = f"{directory}/_rels/{file_name}.rels"
            relationships: dict[str, str] = {}
            if relationships_name in archive_names:
                relationships_root = etree.fromstring(archive.read(relationships_name))
                relationships = {
                    relationship.get("Id", ""): relationship.get("Target", "")
                    for relationship in relationships_root
                    if relationship.get("Type", "").endswith("/hyperlink")
                }
            for hyperlink in part_root.iter(qn("w:hyperlink")):
                relationship_id = hyperlink.get(qn("r:id"), "")
                anchor = hyperlink.get(qn("w:anchor"), "")
                if relationship_id in relationships:
                    targets.append(f"external:{relationships[relationship_id]}")
                elif anchor:
                    targets.append(f"internal:{anchor}")
            for instruction in part_root.iter(qn("w:instrText")):
                field_match = re.search(
                    r'\bHYPERLINK\s+(?:"([^"]+)"|(\S+))',
                    instruction.text or "",
                    flags=re.IGNORECASE,
                )
                if field_match:
                    targets.append(f"field:{field_match.group(1) or field_match.group(2)}")
    return sorted(targets)


def extract_docx_text(content: bytes) -> str:
    return "\n".join(extract_docx_paragraphs(content))


def extract_docx_paragraphs(content: bytes) -> list[str]:
    document = Document(BytesIO(content))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            paragraphs.extend(cell.text.strip() for cell in row.cells)
    return [paragraph for paragraph in paragraphs if paragraph]


def flatten_evidence(value: Any) -> list[str]:
    if isinstance(value, str):
        if value.startswith("data:"):
            return []
        return [value]
    if isinstance(value, dict):
        return [text for nested in value.values() for text in flatten_evidence(nested)]
    if isinstance(value, list):
        return [text for nested in value for text in flatten_evidence(nested)]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    return []


def extract_dates(text: str) -> list[str]:
    return [match.group(0) for match in DATE_PATTERN.finditer(text)]


def extract_numbers(text: str) -> list[str]:
    return [match.group(0) for match in NUMBER_PATTERN.finditer(text)]


def extract_technologies(text: str) -> list[str]:
    normalized = text.casefold()
    return [
        technology
        for technology in TECHNOLOGIES
        if re.search(rf"(?<![\w]){re.escape(technology)}(?![\w])", normalized)
    ]


def extract_companies(text: str) -> list[str]:
    return [match.group(1) for match in COMPANY_PATTERN.finditer(text)]


def extract_titles(text: str) -> list[str]:
    return [match.group(1) or match.group(2) for match in TITLE_PATTERN.finditer(text)]


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    ]


def significant_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[^\W\d_][\w+#.-]{2,}", text.casefold())
        if token not in STOP_WORDS
    }


def normalize_fact(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace(",", ".")).strip()


def contains_normalized_fact(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(
        rf"(?<![\w]){re.escape(needle)}(?![\w])",
        haystack,
        flags=re.IGNORECASE,
    ) is not None
