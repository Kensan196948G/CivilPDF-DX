"""Shared helpers for CSV exports (Excel-safe, UTF-8 BOM, RBAC applied by caller)."""

from __future__ import annotations

import csv
import io
import re
from typing import Iterable

from fastapi.responses import StreamingResponse

# Cells beginning with these characters can be interpreted as formulas by
# spreadsheet applications (CSV / formula injection). Prefix with a single
# quote so exported field values are always treated as text.
_FORMULA_PREFIX = re.compile(r"^[=+\-@\t\r]")


def sanitize_cell(value: object) -> str:
    """Convert a value to a CSV cell string, neutralising formula injection."""
    if value is None:
        return ""
    text = str(value)
    if _FORMULA_PREFIX.match(text):
        return "'" + text
    return text


def csv_stream_response(
    headers: list[str],
    rows: Iterable[Iterable[object]],
    filename: str,
) -> StreamingResponse:
    """Return a StreamingResponse carrying a UTF-8 (BOM) CSV attachment."""
    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM so Excel detects UTF-8
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([sanitize_cell(cell) for cell in row])
    content = buffer.getvalue()
    safe_name = re.sub(r'["\r\n]', "_", filename)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
