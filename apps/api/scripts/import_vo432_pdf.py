"""CLI: import the authorised-claims annex of VO 432/2012 from its PDF.

Usage:
    uv run python -m scripts.import_vo432_pdf \\
        --source apps/api/data/CELEX_32012R0432_DE_TXT.pdf \\
        --output apps/api/data/vo432_authorised_claims.json

This is the smaller, simpler counterpart to the full EU Health Claims
Register (which is unreachable as a single download right now). VO 432/2012
covers ~222 authorised Article 13(1) claims, which is the highest-signal
subset for compliance checking.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from datetime import date as Date
from pathlib import Path

from app.schemas.eu_claim import EuRegisterImport
from app.services.vo432_pdf_parser import parse_vo432_pdf

logger = logging.getLogger("import_vo432_pdf")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import authorised Art. 13(1) claims from the VO 432/2012 PDF.",
    )
    parser.add_argument("--source", type=Path, required=True, help="VO 432/2012 PDF path")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "vo432_authorised_claims.json",
    )
    parser.add_argument("--kb-version", default=None)
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
    claims = parse_vo432_pdf(args.source)

    if not claims:
        logger.error("No claims parsed - PDF layout may have changed.")
        return 3

    payload = EuRegisterImport(
        kb_version=args.kb_version or Date.today().isoformat(),
        source_file=args.source.name,
        imported_at=Date.today(),
        total=len(claims),
        by_status=dict(Counter(c.status for c in claims)),
        by_type=dict(Counter(c.claim_type for c in claims)),
        claims=claims,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        payload.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )

    logger.info("Wrote %d authorised claims → %s", payload.total, args.output)
    nutrients = Counter(c.nutrient for c in claims if c.nutrient)
    logger.info(
        "Top 10 nutrients: %s",
        ", ".join(f"{n} ({k})" for n, k in nutrients.most_common(10)),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
