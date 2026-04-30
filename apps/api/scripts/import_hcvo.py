"""CLI: import an EU food-law regulation from a saved Eur-Lex HTML page.

Usage:
    uv run python -m scripts.import_hcvo \\
        --source apps/api/data/hcvo_2014-12-13.html \\
        --regulation 1924/2006 \\
        --title "Verordnung (EG) Nr. 1924/2006 (HCVO)" \\
        --eur-lex-url https://eur-lex.europa.eu/eli/reg/2006/1924/2014-12-13

Eur-Lex blocks scripted downloads, so the user provides the file.
Save the consolidated DE version from
    https://eur-lex.europa.eu/eli/reg/2006/1924/2014-12-13
via the browser's "Save page as" → "Webpage, complete" first.

For Verordnung 432/2012 the URL is
    https://eur-lex.europa.eu/eli/reg/2012/432/2021-05-17
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from datetime import date as Date
from pathlib import Path

from app.schemas.regulation import RegulationImport
from app.services.eur_lex_parser import parse_eur_lex_html

logger = logging.getLogger("import_hcvo")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import an EU regulation from a saved Eur-Lex HTML page.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the saved HTML file.",
    )
    parser.add_argument(
        "--regulation",
        required=True,
        help="Regulation identifier, e.g. '1924/2006' or '432/2012'.",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Human-readable regulation title.",
    )
    parser.add_argument(
        "--eur-lex-url",
        required=True,
        help="Canonical Eur-Lex URL (used as deep-link in reports).",
    )
    parser.add_argument(
        "--consolidated-date",
        default=None,
        help="ISO date of the consolidated version (e.g. 2014-12-13). Optional.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: apps/api/data/regulation_<id>.json).",
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

    html_text = args.source.read_text(encoding="utf-8", errors="replace")
    chunks = parse_eur_lex_html(
        html_text,
        regulation_id=args.regulation,
        eur_lex_url=args.eur_lex_url,
    )

    if not chunks:
        logger.error(
            "No chunks parsed. The HTML may be empty or use an unexpected layout. "
            "Double-check that you saved the consolidated DE 'Document' view (not the "
            "'Notice' page).",
        )
        return 3

    by_article = dict(Counter(c.article for c in chunks if c.article is not None))

    consolidated: Date | None = None
    if args.consolidated_date:
        try:
            consolidated = Date.fromisoformat(args.consolidated_date)
        except ValueError:
            logger.warning("Could not parse --consolidated-date, ignoring.")

    payload = RegulationImport(
        kb_version=args.consolidated_date or Date.today().isoformat(),
        regulation_id=args.regulation,
        regulation_title=args.title,
        consolidated_date=consolidated,
        source_file=args.source.name,
        imported_at=Date.today(),
        total=len(chunks),
        by_article=by_article,
        chunks=chunks,
    )

    output = args.output or Path(__file__).resolve().parents[1] / "data" / (
        f"regulation_{args.regulation.replace('/', '_')}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        payload.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )

    logger.info("Wrote %d chunks → %s", payload.total, output)
    logger.info(
        "Articles covered: %d (range %d-%d)",
        len(by_article),
        min(by_article) if by_article else 0,
        max(by_article) if by_article else 0,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
