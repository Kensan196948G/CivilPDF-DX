#!/usr/bin/env python3
"""Scheduled retention / GDPR deletion pass for CivilPDF-DX.

Before this script existed, retention enforcement only happened when an admin
called ``POST /api/v1/privacy/admin/run-deletion-job`` by hand — the policy code
was implemented and tested but nothing ran it, so retention expiry and the
GDPR Art.17 cooling-off period were never actually applied. This is the
entry point the ``civilpdf-retention.timer`` systemd unit invokes.

What one pass does (see ``services/retention_service.run_retention_cycle``):
  1. seed the default RetentionPolicy rows if the table is empty (idempotent)
  2. archive documents whose ``retention_expires_at`` has passed
  3. physically delete files whose deletion a user requested more than
     ``--grace-days`` ago (the DB record skeleton and the tamper-evident audit
     chain are retained for legal evidence)

Safety:
  * ``--apply`` is required to change anything. Without it the pass is a
    dry-run that only reports the counts, so a misconfigured timer cannot
    delete production documents.
  * ``--grace-days`` keeps the cooling-off period between a user's deletion
    request and the irreversible file removal.

Usage:
    DATABASE_URL=postgresql://... \\
    PYTHONPATH=src/console/backend \\
    python scripts/retention-job.py --dry-run
    python scripts/retention-job.py --apply --grace-days 30

Exit codes: 0 = pass completed (dry-run or apply), 1 = unexpected error.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "src",
        "console",
        "backend",
    ),
)

from config import settings  # noqa: E402
from database import SessionLocal  # noqa: E402
from services.retention_service import run_retention_cycle  # noqa: E402

logger = logging.getLogger("retention-job")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one retention pass: archive expired documents and physically "
            "delete documents whose deletion request is past the grace period."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually modify data. Without this flag the pass is a dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly request a dry-run (the default when --apply is absent).",
    )
    parser.add_argument(
        "--grace-days",
        type=int,
        default=30,
        help="Cooling-off days after a deletion request before physical deletion "
        "(default: 30).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the summary as a single JSON object (for log ingestion).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only log warnings and errors.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.grace_days < 1:
        print("ERROR: --grace-days must be >= 1", file=sys.stderr)
        return 2

    # --apply wins over --dry-run; the default (neither flag) is a dry-run.
    apply_changes = args.apply and not args.dry_run
    if args.apply and args.dry_run:
        logger.warning("--apply and --dry-run both given; taking --dry-run")

    db = SessionLocal()
    try:
        summary = run_retention_cycle(
            db, grace_days=args.grace_days, dry_run=not apply_changes
        )
    except Exception as exc:  # noqa: BLE001 — surface a non-zero exit for the timer
        logger.error("Retention pass failed: %s", exc, exc_info=True)
        print(f"ERROR: retention pass failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    summary["mode"] = "apply" if apply_changes else "dry-run"
    summary["database"] = settings.database_url.split("://", 1)[0]
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "retention pass ({mode}): expired_documents={expired_documents} "
            "deletion_processed={deletion_processed} "
            "deletion_deleted_files={deletion_deleted_files} "
            "deletion_errors={deletion_errors} seeded_policies={seeded_policies}"
            .format(**summary)
        )
        if not apply_changes:
            print("(dry-run: nothing was changed; re-run with --apply to enforce)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
