"""CLI: convert EFSA's questions-on-hold-botanical-claims.xlsx into our
``botanicals_efsa.json`` JSON-shape.

Usage:
    cd apps/api
    uv run python -m scripts.import_efsa_botanicals \\
        --source data/questions-on-hold-botanical-claims.xlsx \\
        --output data/botanicals_efsa.json

The output file is then picked up by ``scripts.index_knowledge_base``.

We intentionally do **not** merge with the curated ``data/botanicals.json`` -
the curated list has hand-written German risk notes that we want to keep
separate from the auto-imported English EFSA rows. The indexer reads both
files and dedups by chunk_id.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.services.efsa_botanicals_parser import (
    parse_efsa_botanicals,
    to_botanical_entry,
)

logger = logging.getLogger("import_efsa_botanicals")

_DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "questions-on-hold-botanical-claims.xlsx"
)
_DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1] / "data" / "botanicals_efsa.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert the EFSA on-hold botanical-claims XLSX to ClaimGuard JSON.",
    )
    parser.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.source.exists():
        logger.error("Source XLSX not found: %s", args.source)
        return 2

    rows = parse_efsa_botanicals(args.source)
    entries = [to_botanical_entry(r) for r in rows]

    payload = {
        "version": datetime.now(UTC).date().isoformat(),
        "note": (
            "Auto-imported from the EFSA 'questions-on-hold-botanical-claims' "
            "spreadsheet. Each entry carries Status=on_hold and the original "
            "English wording. Use alongside data/botanicals.json (curated)."
        ),
        "source": str(args.source.name),
        "entries": entries,
    }

    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %d entries to %s", len(entries), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
