from typing import Any

from app.services.document_analysis import analyze_docx_source, unsupported_report
from app.services.document_security import DocumentSecurityError


def analyze_document_template(content: bytes, document_type: str) -> dict[str, Any]:
    try:
        if document_type not in {"cover_letter", "tailored_resume"}:
            return unsupported_report(
                element="documentType",
                description="Unsupported document type",
            )
        return analyze_docx_source(content, document_type).preflight_report()
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
