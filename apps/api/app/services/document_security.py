from __future__ import annotations

import stat
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree


MAX_ZIP_ENTRIES = 2_000
MAX_UNCOMPRESSED_ZIP_BYTES = 50_000_000
MAX_XML_PART_BYTES = 10_000_000
MAX_TOTAL_XML_BYTES = 20_000_000
MAX_XML_ELEMENTS = 250_000

REQUIRED_DOCX_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
}


class DocumentSecurityError(ValueError):
    def __init__(self, message: str, *, limit_exceeded: bool = False) -> None:
        super().__init__(message)
        self.limit_exceeded = limit_exceeded


def validate_docx_package(content: bytes) -> None:
    """Validate a DOCX ZIP before any XML is handed to python-docx or lxml."""
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ZIP_ENTRIES:
                raise limit_error(f"DOCX contains more than {MAX_ZIP_ENTRIES} ZIP entries")

            names = {entry.filename for entry in entries}
            if REQUIRED_DOCX_PARTS - names:
                raise DocumentSecurityError("DOCX is missing required package parts")

            declared_size = 0
            for entry in entries:
                validate_zip_entry(entry)
                declared_size += entry.file_size
                if declared_size > MAX_UNCOMPRESSED_ZIP_BYTES:
                    raise limit_error(
                        f"DOCX uncompressed size exceeds {MAX_UNCOMPRESSED_ZIP_BYTES} bytes"
                    )
                if is_xml_part(entry.filename) and entry.file_size > MAX_XML_PART_BYTES:
                    raise limit_error(
                        f"DOCX XML part exceeds {MAX_XML_PART_BYTES} bytes"
                    )

            read_size = 0
            xml_size = 0
            element_count = 0
            for entry in entries:
                part = read_bounded_part(archive, entry)
                read_size += len(part)
                if read_size > MAX_UNCOMPRESSED_ZIP_BYTES:
                    raise limit_error(
                        f"DOCX uncompressed size exceeds {MAX_UNCOMPRESSED_ZIP_BYTES} bytes"
                    )
                if not is_xml_part(entry.filename):
                    continue
                xml_size += len(part)
                if xml_size > MAX_TOTAL_XML_BYTES:
                    raise limit_error(
                        f"DOCX XML content exceeds {MAX_TOTAL_XML_BYTES} bytes"
                    )
                element_count += count_xml_elements(part)
                if element_count > MAX_XML_ELEMENTS:
                    raise limit_error(
                        f"DOCX XML element count exceeds {MAX_XML_ELEMENTS}"
                    )
    except DocumentSecurityError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise DocumentSecurityError("Template is not a valid DOCX ZIP package") from exc


def validate_zip_entry(entry: zipfile.ZipInfo) -> None:
    path = PurePosixPath(entry.filename)
    if (
        not entry.filename
        or "\x00" in entry.filename
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in entry.filename
    ):
        raise DocumentSecurityError("DOCX contains an unsafe ZIP entry path")
    if entry.flag_bits & 0x1:
        raise DocumentSecurityError("Encrypted DOCX ZIP entries are not supported")
    unix_mode = entry.external_attr >> 16
    if unix_mode and stat.S_ISLNK(unix_mode):
        raise DocumentSecurityError("DOCX ZIP symlinks are not supported")


def read_bounded_part(archive: zipfile.ZipFile, entry: zipfile.ZipInfo) -> bytes:
    part_limit = MAX_XML_PART_BYTES if is_xml_part(entry.filename) else MAX_UNCOMPRESSED_ZIP_BYTES
    with archive.open(entry) as source:
        part = source.read(part_limit + 1)
    if len(part) > part_limit:
        if is_xml_part(entry.filename):
            raise limit_error(f"DOCX XML part exceeds {MAX_XML_PART_BYTES} bytes")
        raise limit_error(
            f"DOCX uncompressed size exceeds {MAX_UNCOMPRESSED_ZIP_BYTES} bytes"
        )
    return part


def count_xml_elements(content: bytes) -> int:
    lowered = content.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise DocumentSecurityError("DOCX XML DTDs and entities are not allowed")
    try:
        count = 0
        for _, element in ElementTree.iterparse(BytesIO(content), events=("end",)):
            count += 1
            element.clear()
            if count > MAX_XML_ELEMENTS:
                return count
        return count
    except ElementTree.ParseError as exc:
        raise DocumentSecurityError("DOCX contains malformed XML") from exc


def is_xml_part(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(".xml") or lowered.endswith(".rels")


def limit_error(message: str) -> DocumentSecurityError:
    return DocumentSecurityError(message, limit_exceeded=True)
