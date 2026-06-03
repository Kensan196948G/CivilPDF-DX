"""Electronic delivery (電子納品) ZIP package generator.

Conforms to the MLIT (国土交通省) CALS/EC electronic delivery standard.
Generates a ZIP with folder structure, PDF files, and INDEX.XML metadata.
"""

import io
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from models.document import Document, DocumentType
from models.user import Project

# Maps DocumentType → (folder_name, file_prefix)
_FOLDER_MAP: dict[DocumentType, tuple[str, str]] = {
    DocumentType.DRAWING: ("DRAWINGS", "DRAW"),
    DocumentType.PHOTO: ("PHOTO", "PHOT"),
    DocumentType.INSPECTION: ("INSPECTION", "INSP"),
    DocumentType.SAFETY: ("SAFETY", "SAFE"),
    DocumentType.CONTRACT: ("CONTRACT", "CONT"),
    DocumentType.REPORT: ("REPORT", "REPO"),
    DocumentType.CORRECTION: ("CORRECTION", "CORR"),
    DocumentType.OTHER: ("OTHER", "OTHE"),
}


def _sanitize_code(code: str) -> str:
    """Convert project code to uppercase alphanumeric + underscore (max 16 chars)."""
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", code).upper()
    return sanitized[:16]


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _build_index_xml(
    project: Project,
    by_folder: dict[str, list[Document]],
    generated_at: datetime,
) -> bytes:
    """Build INDEX.XML per MLIT electronic delivery standard."""
    root = ET.Element("工事管理情報")

    basic = ET.SubElement(root, "基本情報")
    _sub(basic, "工事番号", project.code)
    _sub(basic, "工事名称", project.name)
    _sub(basic, "作成日", generated_at.strftime("%Y%m%d"))
    _sub(basic, "ソフトウェア名", "CivilPDF-DX")
    _sub(basic, "ソフトウェアバージョン", "v0.7.0")

    outcomes = ET.SubElement(root, "成果品情報")
    for folder_name, docs in sorted(by_folder.items()):
        _, prefix = _FOLDER_MAP.get(docs[0].document_type, ("OTHER", "OTHE"))
        folder_el = ET.SubElement(
            outcomes,
            "フォルダ情報",
            attrib={"フォルダ名": folder_name, "ファイル数": str(len(docs))},
        )
        for i, doc in enumerate(docs, start=1):
            file_el = ET.SubElement(folder_el, "ファイル情報")
            _sub(file_el, "ファイル名", f"{prefix}_{i:04d}.PDF")
            _sub(file_el, "タイトル", doc.title)
            _sub(file_el, "ファイルサイズ", str(doc.file_size))
            _sub(file_el, "PDF_A準拠", "1" if doc.is_pdfa else "0")

    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_body = ET.tostring(root, encoding="unicode")
    return (declaration + xml_body).encode("utf-8")


def _group_by_folder(documents: list[Document]) -> dict[str, list[Document]]:
    by_folder: dict[str, list[Document]] = defaultdict(list)
    for doc in documents:
        folder_name, _ = _FOLDER_MAP.get(doc.document_type, ("OTHER", "OTHE"))
        by_folder[folder_name].append(doc)
    return by_folder


def check_delivery_readiness(
    project: Project, documents: list[Document]
) -> dict[str, Any]:
    """Return readiness status for electronic delivery packaging."""
    pdfa_count = sum(1 for d in documents if d.is_pdfa)
    non_pdfa = [
        {"id": d.id, "title": d.title, "filename": d.filename}
        for d in documents
        if not d.is_pdfa
    ]
    warnings: list[str] = []
    if not documents:
        warnings.append("プロジェクトに文書が1件もありません")
    if non_pdfa:
        warnings.append(f"PDF/A 非準拠ファイルが {len(non_pdfa)} 件あります")

    return {
        "ready": len(documents) > 0,
        "document_count": len(documents),
        "pdfa_compliant_count": pdfa_count,
        "non_pdfa_documents": non_pdfa,
        "warnings": warnings,
    }


def generate_delivery_zip(project: Project, documents: list[Document]) -> bytes:
    """Build in-memory ZIP conforming to MLIT electronic delivery layout.

    Layout:
        {CODE}_{YYYYMMDD}/
        ├── INDEX.XML
        ├── DRAWINGS/DRAW_0001.PDF …
        ├── PHOTO/PHOT_0001.PDF …
        └── …
    """
    generated_at = datetime.now(timezone.utc)
    date_str = generated_at.strftime("%Y%m%d")
    proj_code = _sanitize_code(project.code)
    root_dir = f"{proj_code}_{date_str}"

    by_folder = _group_by_folder(documents)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        index_xml = _build_index_xml(project, by_folder, generated_at)
        zf.writestr(f"{root_dir}/INDEX.XML", index_xml)

        for folder_name, docs in sorted(by_folder.items()):
            _, prefix = _FOLDER_MAP.get(docs[0].document_type, ("OTHER", "OTHE"))
            for i, doc in enumerate(docs, start=1):
                dest_name = f"{prefix}_{i:04d}.PDF"
                dest_path = f"{root_dir}/{folder_name}/{dest_name}"
                file_bytes = _read_file(doc)
                zf.writestr(dest_path, file_bytes)

    return buf.getvalue()


def _read_file(doc: Document) -> bytes:
    """Read document bytes; return empty placeholder if file is missing."""
    if doc.file_path:
        try:
            return Path(doc.file_path).read_bytes()
        except OSError:
            pass
    return b""
