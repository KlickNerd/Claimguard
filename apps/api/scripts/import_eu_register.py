"""CLI: import the EU Register of Health Claims from an Excel export.

Usage:
    uv run python -m scripts.import_eu_register \\
        --source apps/api/data/eu_register_2026-04-19.xlsx \\
        --output apps/api/data/eu_claims.json

If --output is omitted, JSON is written to apps/api/data/eu_claims.json.

The resulting JSON file is the source of truth for PROJ-9 (Hybrid Retrieval)
- a follow-up step ("indexer") loads it into Qdrant + Postgres.

Download the Excel file from:
    https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register
    → Click "Download all" (top right of the table).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import date as Date
from pathlib import Path

from app.schemas.eu_claim import EuRegisterImport
from app.services.eu_register_parser import parse_excel

logger = logging.getLogger("import_eu_register")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import the EU Register of Health Claims from an Excel export.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the EU register Excel file (.xlsx).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "eu_claims.json",
        help="Where to write the parsed JSON (default: apps/api/data/eu_claims.json).",
    )
    parser.add_argument(
        "--kb-version",
        default=None,
        help="Optional knowledge-base version tag (default: today's date).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.source.exists():
        logger.error("Source file not found: %s", args.source)
        return 2

    logger.info("Parsing %s …", args.source)
    claims = parse_excel(args.source)

    if not claims:
        logger.error("No claims parsed - is this the correct Excel file?")
        return 3

    by_status = Counter(c.status for c in claims)
    by_type = Counter(c.claim_type for c in claims)

    payload = EuRegisterImport(
        kb_version=args.kb_version or Date.today().isoformat(),
        source_file=args.source.name,
        imported_at=Date.today(),
        total=len(claims),
        by_status=dict(by_status),
        by_type=dict(by_type),
        claims=claims,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        payload.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )

    logger.info("Wrote %d claims → %s", payload.total, args.output)
    logger.info("Status breakdown: %s", dict(by_status))
    logger.info("Type breakdown:   %s", dict(by_type))
    return 0


if __name__ == "__main__":
    sys.exit(main())
