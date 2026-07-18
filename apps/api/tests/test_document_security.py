from io import BytesIO
import zipfile

import pytest

from app.services import document_security
from app.services.document_security import DocumentSecurityError, validate_docx_package


DOCUMENT_XML = (
    b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    b"<w:body><w:p><w:r><w:t>CV</w:t></w:r></w:p></w:body></w:document>"
)


def docx_package(*, extra_entries: dict[str, bytes] | None = None) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", b"<Types />")
        archive.writestr("_rels/.rels", b"<Relationships />")
        archive.writestr("word/document.xml", DOCUMENT_XML)
        for name, content in (extra_entries or {}).items():
            archive.writestr(name, content)
    return output.getvalue()


def test_docx_security_accepts_a_bounded_package() -> None:
    validate_docx_package(docx_package())


def test_docx_security_limits_entries_and_uncompressed_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = docx_package(extra_entries={"word/media/image.bin": b"x" * 128})
    monkeypatch.setattr(document_security, "MAX_ZIP_ENTRIES", 3)
    with pytest.raises(DocumentSecurityError, match="ZIP entries") as entries_error:
        validate_docx_package(content)
    assert entries_error.value.limit_exceeded is True

    monkeypatch.setattr(document_security, "MAX_ZIP_ENTRIES", 10)
    monkeypatch.setattr(document_security, "MAX_UNCOMPRESSED_ZIP_BYTES", 64)
    with pytest.raises(DocumentSecurityError, match="uncompressed size") as size_error:
        validate_docx_package(content)
    assert size_error.value.limit_exceeded is True


def test_docx_security_limits_xml_size_and_element_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = docx_package()
    monkeypatch.setattr(document_security, "MAX_XML_PART_BYTES", 32)
    with pytest.raises(DocumentSecurityError, match="XML part") as xml_error:
        validate_docx_package(content)
    assert xml_error.value.limit_exceeded is True

    monkeypatch.setattr(document_security, "MAX_XML_PART_BYTES", 10_000)
    monkeypatch.setattr(document_security, "MAX_XML_ELEMENTS", 3)
    with pytest.raises(DocumentSecurityError, match="XML element count") as element_error:
        validate_docx_package(content)
    assert element_error.value.limit_exceeded is True


def test_docx_security_rejects_unsafe_paths_and_xml_entities() -> None:
    with pytest.raises(DocumentSecurityError, match="unsafe ZIP entry path"):
        validate_docx_package(docx_package(extra_entries={"../secret.xml": b"<secret />"}))

    entity_xml = b'<!DOCTYPE x [<!ENTITY a "secret">]><w:document />'
    with pytest.raises(DocumentSecurityError, match="entities"):
        validate_docx_package(docx_package(extra_entries={"word/header1.xml": entity_xml}))

    delayed_entity_xml = b" " * 1_500 + entity_xml
    with pytest.raises(DocumentSecurityError, match="entities"):
        validate_docx_package(
            docx_package(extra_entries={"word/header2.xml": delayed_entity_xml})
        )
