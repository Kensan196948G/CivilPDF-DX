"""PDF/A validation service.

Primary: subprocess call to veraPDF (if installed) for full ISO 14289 conformance.
Fallback: pypdf XMP metadata inspection for basic PDF/A marker detection.
"""

import json
import logging
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

VERA_PDF_CMD = shutil.which("verapdf")  # None if not on PATH


def _xmp_pdfa_version(reader: PdfReader) -> Optional[str]:
    """Extract PDF/A version string from XMP metadata, or None."""
    try:
        xmp = reader.xmp_metadata
        if xmp is None:
            return None
        # XMP pdfaid:conformance and pdfaid:part indicate PDF/A level
        conformance = xmp.get_element(
            "", "http://www.aiim.org/pdfa/ns/id/", "conformance"
        )
        part = xmp.get_element("", "http://www.aiim.org/pdfa/ns/id/", "part")
        if part is not None and conformance is not None:
            return f"PDF/A-{part.text}{conformance.text.lower()}"
    except Exception:
        pass
    return None


def _validate_with_pypdf(content: bytes) -> dict:
    """Lightweight PDF/A detection using pypdf XMP metadata."""
    result: dict = {
        "validator": "pypdf",
        "is_pdfa": False,
        "pdfa_version": None,
        "conformant": False,
        "warnings": [],
        "errors": [],
    }
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        version = _xmp_pdfa_version(reader)
        if version:
            result["is_pdfa"] = True
            result["pdfa_version"] = version
            result["conformant"] = True
        else:
            result["warnings"].append(
                "No PDF/A XMP metadata found. Document may not be PDF/A compliant."
            )
    except PdfReadError as exc:
        result["errors"].append(f"PDF parse error: {exc}")
    return result


def _validate_with_verapdf(file_path: str) -> dict:
    """Full PDF/A validation via veraPDF CLI (must be on PATH)."""
    result: dict = {
        "validator": "veraPDF",
        "is_pdfa": False,
        "pdfa_version": None,
        "conformant": False,
        "warnings": [],
        "errors": [],
        "raw": None,
    }
    try:
        proc = subprocess.run(  # noqa: S603
            [VERA_PDF_CMD, "--format", "json", "--flavour", "0", file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        raw = json.loads(proc.stdout)
        result["raw"] = raw

        # Navigate veraPDF JSON report structure
        reports = raw.get("report", {}).get("jobs", [])
        if reports:
            job = reports[0]
            validation = job.get("validationResult", {})
            result["conformant"] = validation.get("compliant", False)
            result["is_pdfa"] = result["conformant"]
            profile = validation.get("profileName", "")
            if profile:
                result["pdfa_version"] = profile
            failed = validation.get("assertions", {}).get("failedChecks", 0)
            if failed:
                result["warnings"].append(f"{failed} failed assertion(s)")
    except subprocess.TimeoutExpired:
        result["errors"].append("veraPDF validation timed out (>60s)")
    except (json.JSONDecodeError, KeyError) as exc:
        result["errors"].append(f"veraPDF output parse error: {exc}")
    except Exception as exc:
        result["errors"].append(f"veraPDF error: {exc}")
    return result


def validate_pdfa(content: bytes, file_path: Optional[str] = None) -> dict:
    """Validate PDF/A compliance.

    Uses veraPDF if available, otherwise falls back to pypdf XMP inspection.

    Returns dict with keys: is_pdfa, pdfa_version, conformant, validator, warnings, errors.
    """
    if VERA_PDF_CMD and file_path and Path(file_path).exists():
        logger.debug("Running veraPDF on %s", file_path)
        result = _validate_with_verapdf(file_path)
    else:
        if VERA_PDF_CMD is None:
            logger.debug("veraPDF not found; using pypdf fallback")
        result = _validate_with_pypdf(content)

    logger.info(
        "PDF/A validation: is_pdfa=%s version=%s validator=%s",
        result["is_pdfa"],
        result.get("pdfa_version"),
        result["validator"],
    )
    return result
