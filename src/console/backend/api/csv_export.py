"""Shared helpers for CSV exports (Excel-safe, UTF-8 BOM, RBAC applied by caller)."""

from __future__ import annotations

import csv
import io
import re
from typing import Iterable, Iterator

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

# Cells beginning with these characters can be interpreted as formulas by
# spreadsheet applications (CSV / formula injection). Prefix with a single
# quote so exported field values are always treated as text.
_FORMULA_PREFIX = re.compile(r"^[=+\-@\t\r]")

# Rows are serialised into the response in bounded batches, so peak memory is
# governed by this constant instead of by the size of the result set. The
# previous implementation built the entire CSV in a single StringIO and handed
# the finished string to StreamingResponse, which was not streaming at all.
DEFAULT_CHUNK_ROWS = 500

# Hard ceiling for a single export. audit_logs grows for the whole retention
# period (電子帳簿保存法: 7年), so an unbounded export is both a memory and a
# request-duration hazard. Exceeding the ceiling is reported as an error rather
# than silently truncating: a truncated compliance export would look complete
# while missing records, which is worse than an explicit failure.
MAX_EXPORT_ROWS = 100_000


def sanitize_cell(value: object) -> str:
    """Convert a value to a CSV cell string, neutralising formula injection."""
    if value is None:
        return ""
    text = str(value)
    if _FORMULA_PREFIX.match(text):
        return "'" + text
    return text


def ensure_export_within_limit(row_count: int, *, label: str = "レコード") -> None:
    """Reject an export whose result set exceeds ``MAX_EXPORT_ROWS``.

    Callers obtain ``row_count`` from a COUNT query so the ceiling is enforced
    before any row is serialised.
    """
    if row_count > MAX_EXPORT_ROWS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"エクスポート対象が上限を超えています（{label} {row_count:,}件 / "
                f"上限 {MAX_EXPORT_ROWS:,}件）。"
                "期間や絞り込み条件を指定して再実行してください。"
            ),
        )


def _iter_csv_chunks(
    headers: list[str],
    rows: Iterable[Iterable[object]],
    chunk_rows: int,
) -> Iterator[bytes]:
    """Yield UTF-8 (BOM) CSV bytes in bounded batches."""
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be >= 1")

    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM so Excel detects UTF-8
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)

    pending = 0
    for row in rows:
        writer.writerow([sanitize_cell(cell) for cell in row])
        pending += 1
        if pending >= chunk_rows:
            yield buffer.getvalue().encode("utf-8")
            buffer.seek(0)
            buffer.truncate(0)
            pending = 0

    # Emits the header row for an empty export, and the final partial batch
    # otherwise. Empty when the last batch ended exactly on chunk_rows.
    if buffer.tell():
        yield buffer.getvalue().encode("utf-8")


def csv_stream_response(
    headers: list[str],
    rows: Iterable[Iterable[object]],
    filename: str,
    *,
    chunk_rows: int = DEFAULT_CHUNK_ROWS,
) -> StreamingResponse:
    """Return a StreamingResponse carrying a UTF-8 (BOM) CSV attachment.

    ``rows`` is consumed lazily, so callers should pass a streaming query
    result (e.g. ``Query.yield_per()``) rather than a materialised list.
    """
    safe_name = re.sub(r'["\r\n]', "_", filename)
    return StreamingResponse(
        _iter_csv_chunks(headers, rows, chunk_rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
