import json
import zipfile
from io import BytesIO
from typing import Any

from docx.oxml.ns import qn
from lxml import etree

from app.services.cover_letter_blocks import (
    UnsupportedCoverLetterStructureError,
    extract_cover_letter_blocks_from_docx,
)
from app.services.document_security import DocumentSecurityError, validate_docx_package
from app.services.resume_blocks import (
    UnsupportedResumeStructureError,
    extract_resume_blocks_from_docx,
    find_unsupported_word_constructions,
)


SOURCE_CONTEXT_MAX_CHARS = 10_000


def analyze_document_template(content: bytes, document_type: str) -> dict[str, Any]:
    rejected_elements: list[dict[str, str]] = []
    immutable_elements: list[dict[str, str]] = []
    editable_count = 0
    structured_elements: list[dict[str, Any]] = []

    try:
        validate_docx_package(content)
        with zipfile.ZipFile(BytesIO(content)) as archive:
            root = etree.fromstring(archive.read("word/document.xml"))
    except DocumentSecurityError as exc:
        return unsupported_report(
            element="invalidDocument",
            description=str(exc),
        )
    except Exception:
        return unsupported_report(
            element="invalidDocument",
            description="DOCX could not be read safely",
        )

    body = root.find(qn("w:body"))
    if body is None:
        return unsupported_report(
            element="documentBody",
            description="DOCX has no document body",
        )

    for issue in find_unsupported_word_constructions(body):
        rejected_elements.append(
            {"element": issue.element, "description": issue.description}
        )
    if rejected_elements:
        return {
            "supported": False,
            "editableCount": 0,
            "immutableCount": 0,
            "immutableElements": [],
            "rejectedElements": rejected_elements,
            "sourceContext": empty_source_context(),
        }

    try:
        if document_type == "tailored_resume":
            structured_elements = extract_resume_blocks_from_docx(content)
            id_key = "blockId"
            format_name = "resume-blocks-v2"
        else:
            structured_elements = extract_cover_letter_blocks_from_docx(content)
            id_key = "paragraphId"
            format_name = "cover-letter-blocks-v1"
    except (UnsupportedResumeStructureError, UnsupportedCoverLetterStructureError) as exc:
        return unsupported_report(
            element="mixedFormat",
            description=str(exc).removeprefix("Unsupported DOCX construction: "),
        )
    except Exception:
        return unsupported_report(
            element="documentStructure",
            description="Template structure could not be classified safely",
        )

    for element in structured_elements:
        element_id = str(element[id_key])
        editable_spans = [span for span in element.get("spans", []) if span.get("editable")]
        editable_count += len(editable_spans)
        if not element.get("editable"):
            immutable_elements.append(
                immutable_item(
                    element_id,
                    str(element.get("type") or "protected"),
                    str(element.get("original") or ""),
                )
            )
            continue
        for span in element.get("spans", []):
            if span.get("editable"):
                continue
            immutable_elements.append(
                immutable_item(
                    str(span.get("spanId") or element_id),
                    str(span.get("type") or "protected"),
                    str(span.get("original") or ""),
                )
            )

    if editable_count == 0:
        rejected_elements.append(
            {
                "element": "editableText",
                "description": "no safely editable text spans were found",
            }
        )

    source_context = source_context_report(
        structured_elements,
        id_key=id_key,
        format_name=format_name,
    )
    return {
        "supported": editable_count > 0 and not rejected_elements,
        "editableCount": editable_count,
        "immutableCount": len(immutable_elements),
        "immutableElements": immutable_elements[:100],
        "rejectedElements": rejected_elements,
        "sourceContext": source_context,
    }


def immutable_item(element_id: str, element_type: str, original: str) -> dict[str, str]:
    preview = " ".join(original.split())
    return {
        "id": element_id,
        "type": element_type,
        "text": preview[:180],
        "reason": "AI changes targeting this protected element will be rejected",
    }


def source_context_report(
    elements: list[dict[str, Any]],
    *,
    id_key: str,
    format_name: str,
) -> dict[str, Any]:
    base_key = "blocks" if id_key == "blockId" else "paragraphs"
    base: dict[str, Any] = {"format": format_name, base_key: []}
    total_characters = len(
        json.dumps(
            {**base, base_key: elements},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    included: list[dict[str, Any]] = []
    for element in elements:
        candidate = {**base, base_key: [*included, element]}
        if len(json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))) > SOURCE_CONTEXT_MAX_CHARS:
            break
        included.append(element)
    included_characters = len(
        json.dumps(
            {**base, base_key: included},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return {
        "totalElements": len(elements),
        "includedElements": len(included),
        "omittedElements": len(elements) - len(included),
        "estimatedCharacters": total_characters,
        "includedCharacters": included_characters,
        "truncated": len(included) < len(elements),
    }


def empty_source_context() -> dict[str, int | bool]:
    return {
        "totalElements": 0,
        "includedElements": 0,
        "omittedElements": 0,
        "estimatedCharacters": 0,
        "includedCharacters": 0,
        "truncated": False,
    }


def unsupported_report(*, element: str, description: str) -> dict[str, Any]:
    return {
        "supported": False,
        "editableCount": 0,
        "immutableCount": 0,
        "immutableElements": [],
        "rejectedElements": [{"element": element, "description": description}],
        "sourceContext": empty_source_context(),
    }
