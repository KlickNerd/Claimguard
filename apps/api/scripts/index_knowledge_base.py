"""CLI: embed the parsed knowledge-base JSONs and upsert into Qdrant (PROJ-9).

Reads:
    apps/api/data/vo432_authorised_claims.json   (PROJ-4 PDF importer output)
    apps/api/data/regulation_1924_2006.json      (PROJ-5 HCVO importer output)

Writes two Qdrant collections:
    eu_claims       (one point per EU register / VO 432 entry)
    regulation      (one point per HCVO article+paragraph chunk)

Usage:
    cd apps/api
    uv run python -m scripts.index_knowledge_base

Idempotent - running again recreates collections from scratch. The model
download (~440 MB for multilingual-e5-base) happens on first invocation
and is cached under ~/.cache/huggingface.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.services import postgres_fts
from app.services.embedding_service import EMBEDDING_DIM, embed

logger = logging.getLogger("index_knowledge_base")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EU_CLAIMS_FILE = "vo432_authorised_claims.json"
HCVO_FILE = "regulation_1924_2006.json"
EXTRA_REG_FILE = "regulatory_excerpts.json"
CASE_LAW_FILE = "case_law.json"
BOTANICALS_FILE = "botanicals.json"
BOTANICALS_EFSA_FILE = "botanicals_efsa.json"

EU_CLAIMS_COLLECTION = "eu_claims"
REGULATION_COLLECTION = "regulation"
CASE_LAW_COLLECTION = "case_law"
BOTANICALS_COLLECTION = "botanicals"

BATCH_SIZE = 32
SNIPPET_MAX = 600


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        logger.warning("Skipping missing source: %s", path.name)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_collection(client: QdrantClient, name: str) -> None:
    """Drop + recreate so re-indexing always reflects the current JSON."""
    with contextlib.suppress(Exception):
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def _batched(items: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _eu_claim_text(claim: dict[str, Any]) -> str:
    """Build the embedding input from claim wording + nutrient + conditions."""
    parts = [
        claim.get("nutrient") or "",
        claim.get("claim_de") or claim.get("claim_en") or "",
        claim.get("conditions") or "",
    ]
    return " — ".join(p.strip() for p in parts if p)


def _eu_claim_payload(claim: dict[str, Any]) -> dict[str, Any]:
    nutrient = claim.get("nutrient")
    base_ref = claim.get("regulation_reference") or "EU-Register"
    reference = f"{base_ref} · {nutrient}" if nutrient else base_ref
    return {
        "chunk_id": claim["id"],
        "source_type": "eu_claim",
        "snippet": (claim.get("claim_de") or claim.get("claim_en") or "")[:SNIPPET_MAX],
        "reference": reference,
        "url": claim.get("source_url")
        or "https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register",
        "nutrient": claim.get("nutrient"),
        "claim_de": claim.get("claim_de"),
        "claim_en": claim.get("claim_en"),
        "conditions": claim.get("conditions"),
        "status": claim.get("status"),
        "claim_type": claim.get("claim_type"),
        "regulation_reference": claim.get("regulation_reference"),
    }


def _hcvo_chunk_text(chunk: dict[str, Any]) -> str:
    parts = []
    if chunk.get("article_title"):
        parts.append(chunk["article_title"])
    if chunk.get("text"):
        parts.append(chunk["text"])
    return " — ".join(parts)


def _hcvo_chunk_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    paragraph = chunk.get("paragraph")
    abs_part = f" Abs. {paragraph}" if paragraph else ""
    reference = f"VO {chunk['regulation_id']}, Art. {chunk['article']}{abs_part}"
    return {
        "chunk_id": chunk["chunk_id"],
        "source_type": "regulation",
        "snippet": (chunk.get("text") or "")[:SNIPPET_MAX],
        "reference": reference,
        "url": chunk.get("eur_lex_url", ""),
        "regulation_id": chunk.get("regulation_id"),
        "article": chunk.get("article"),
        "article_title": chunk.get("article_title"),
        "paragraph": chunk.get("paragraph"),
        "section": chunk.get("section"),
        "is_annex": chunk.get("is_annex", False),
    }


def _case_law_text(case: dict[str, Any]) -> str:
    """Embed the title + summary + tags so retrieval can match on themes."""
    parts = [case.get("title") or "", case.get("summary") or ""]
    tags = case.get("tags") or []
    if tags:
        parts.append(" ".join(tags))
    return " — ".join(p.strip() for p in parts if p)


def _case_law_payload(case: dict[str, Any]) -> dict[str, Any]:
    reference = f"{case['court']} {case['case_number']} ({case['decision_date']})"
    return {
        "chunk_id": case["id"],
        "source_type": "case_law",
        "snippet": (case.get("summary") or "")[:SNIPPET_MAX],
        "reference": reference,
        "url": _resolve_case_url(case),
        "court": case.get("court"),
        "case_number": case.get("case_number"),
        "decision_date": case.get("decision_date"),
        "decision": case.get("decision"),
        "claim_type": case.get("claim_type"),
        "title": case.get("title"),
        "tags": ",".join(case.get("tags") or []),
        "legal_basis": ",".join(case.get("legal_basis") or []),
    }


def _resolve_case_url(case: dict[str, Any]) -> str:
    """Stable lookup URL for a court ruling.

    The BGH itself only keeps Termin-URLs alive while a hearing is pending
    (303 → 400 once the ruling is published), and the German Länder
    justice portals reshuffle their URLs every couple of years. Both
    failure modes were visible in production: 'Quelle öffnen' landed on
    a 404. We instead route every entry through dejure.org's case-number
    resolver, which has stable URLs and finds the ruling on dejure /
    openjur / juris with a single hop.
    """
    from urllib.parse import quote
    az = case.get("case_number", "")
    if not az:
        return case.get("source_url") or ""
    return (
        "https://dejure.org/dienste/vernetzung/rechtsprechung?"
        + f"Aktenzeichen={quote(az)}"
    )


def _botanical_text(entry: dict[str, Any]) -> str:
    """Embed scientific + common names + summary so retrieval matches whether
    the claim mentions ``Curcuma`` or ``Kurkuma`` or ``Curcumin``."""
    parts = [
        entry.get("scientific_name") or "",
        entry.get("common_name_de") or "",
        " ".join(entry.get("common_names") or []),
        entry.get("health_relationship") or "",
        entry.get("summary") or "",
    ]
    return " — ".join(p.strip() for p in parts if p)


_BOTANICAL_STATUS_LABEL = {
    "on_hold": "EFSA on-hold",
    "non_authorised": "EFSA negativ bewertet",
    "authorised": "zugelassen",
}


def _botanical_payload(entry: dict[str, Any]) -> dict[str, Any]:
    label = _BOTANICAL_STATUS_LABEL.get(entry.get("status", ""), entry.get("status", ""))
    reference = (
        f"EFSA-Botanical · {entry['common_name_de']} ({entry['scientific_name']}) · {label}"
    )
    return {
        "chunk_id": entry["id"],
        "source_type": "botanical",
        "snippet": (entry.get("summary") or "")[:SNIPPET_MAX],
        "reference": reference,
        "url": entry.get("source_url", ""),
        "scientific_name": entry.get("scientific_name"),
        "common_name_de": entry.get("common_name_de"),
        "common_names": ",".join(entry.get("common_names") or []),
        "status": entry.get("status"),
        "health_relationship": entry.get("health_relationship"),
        "pending_claim_de": entry.get("pending_claim_de"),
        "risk_notes": ",".join(entry.get("risk_notes") or []),
    }


_FTS_FLAT_KEYS = {"chunk_id", "source_type", "reference", "snippet", "url"}


def _payload_to_fts_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull the FTS-relevant fields out of a Qdrant payload and stash the
    rest into ``metadata`` so we don't lose source-specific context."""
    metadata = {k: v for k, v in payload.items() if k not in _FTS_FLAT_KEYS}
    return {
        "chunk_id": payload.get("chunk_id"),
        "source_type": payload.get("source_type"),
        "reference": payload.get("reference") or "",
        "snippet": payload.get("snippet") or "",
        "url": payload.get("url") or "",
        "metadata": metadata,
    }


def _index(
    client: QdrantClient,
    collection: str,
    items: list[dict[str, Any]],
    text_fn,
    payload_fn,
    *,
    label: str,
    ensure_collection: bool = True,
    start_id: int = 0,
    fts_source_type: str | None = None,
) -> int:
    if not items:
        return 0
    if ensure_collection:
        _ensure_collection(client, collection)

    # FTS rows for this source live alongside the others in ``kb_chunks``;
    # wipe just this source so re-indexing is idempotent without touching
    # the others.
    if fts_source_type:
        postgres_fts.reset_for_source(fts_source_type)

    inserted = 0
    point_id = start_id
    for batch in _batched(items, BATCH_SIZE):
        texts = [text_fn(item) for item in batch]
        vectors = embed(texts, kind="passage")
        payloads = [payload_fn(item) for item in batch]
        points = [
            PointStruct(
                id=point_id + i + 1,
                vector=vectors[i],
                payload=payloads[i],
            )
            for i in range(len(batch))
        ]
        client.upsert(collection_name=collection, points=points, wait=True)
        if fts_source_type:
            postgres_fts.upsert_chunks([_payload_to_fts_row(p) for p in payloads])
        inserted += len(points)
        point_id += len(points)
        logger.info("[%s] %d/%d indexed", label, inserted, len(items))
    return inserted


def _excerpt_text(excerpt: dict[str, Any]) -> str:
    parts = [excerpt.get("title") or "", excerpt.get("snippet") or ""]
    tags = excerpt.get("tags") or []
    if tags:
        parts.append(" ".join(tags))
    return " — ".join(p.strip() for p in parts if p)


def _excerpt_payload(excerpt: dict[str, Any]) -> dict[str, Any]:
    paragraph = excerpt.get("paragraph")
    abs_part = f" Abs. {paragraph}" if paragraph else ""
    reference = f"{excerpt['regulation_id']} § {excerpt['article']}{abs_part}"
    return {
        "chunk_id": excerpt["chunk_id"],
        "source_type": "regulation",
        "snippet": (excerpt.get("snippet") or "")[:SNIPPET_MAX],
        "reference": reference,
        "url": excerpt.get("source_url", ""),
        "regulation_id": excerpt.get("regulation_id"),
        "article": excerpt.get("article"),
        "paragraph": excerpt.get("paragraph"),
        "title": excerpt.get("title"),
        "tags": ",".join(excerpt.get("tags") or []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index ClaimGuard knowledge base into Qdrant.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--qdrant-url",
        default=settings.qdrant_url,
        help="Qdrant base URL (default from app.config: %(default)s).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    client = QdrantClient(url=args.qdrant_url)
    postgres_fts.ensure_schema()

    eu_data = _read_json(args.data_dir / EU_CLAIMS_FILE)
    hcvo_data = _read_json(args.data_dir / HCVO_FILE)
    extra_reg_data = _read_json(args.data_dir / EXTRA_REG_FILE)
    case_law_data = _read_json(args.data_dir / CASE_LAW_FILE)
    botanicals_data = _read_json(args.data_dir / BOTANICALS_FILE)
    botanicals_efsa_data = _read_json(args.data_dir / BOTANICALS_EFSA_FILE)

    eu_count = 0
    hcvo_count = 0
    extra_reg_count = 0
    case_law_count = 0
    botanicals_count = 0

    if eu_data:
        logger.info("Indexing EU claims …")
        eu_count = _index(
            client,
            EU_CLAIMS_COLLECTION,
            eu_data.get("claims", []),
            _eu_claim_text,
            _eu_claim_payload,
            label="eu_claims",
            fts_source_type="eu_claim",
        )

    # Reset the regulation FTS bucket once before re-seeding; the two
    # indexer passes below append to the same kb_chunks.source_type.
    postgres_fts.reset_for_source("regulation")

    if hcvo_data:
        logger.info("Indexing HCVO chunks …")
        hcvo_count = _index(
            client,
            REGULATION_COLLECTION,
            hcvo_data.get("chunks", []),
            _hcvo_chunk_text,
            _hcvo_chunk_payload,
            label="regulation",
            fts_source_type=None,
        )
        # We managed the reset above; just write the rows here.
        postgres_fts.upsert_chunks(
            [_payload_to_fts_row(_hcvo_chunk_payload(c)) for c in hcvo_data.get("chunks", [])],
        )

    if extra_reg_data:
        logger.info("Indexing extended regulatory excerpts (LFGB/LMIV/HWG/UWG) …")
        extra_reg_count = _index(
            client,
            REGULATION_COLLECTION,
            extra_reg_data.get("excerpts", []),
            _excerpt_text,
            _excerpt_payload,
            label="reg_excerpts",
            ensure_collection=False,
            start_id=hcvo_count,
            fts_source_type=None,
        )
        postgres_fts.upsert_chunks(
            [
                _payload_to_fts_row(_excerpt_payload(e))
                for e in extra_reg_data.get("excerpts", [])
            ],
        )

    if case_law_data:
        logger.info("Indexing case law …")
        case_law_count = _index(
            client,
            CASE_LAW_COLLECTION,
            case_law_data.get("cases", []),
            _case_law_text,
            _case_law_payload,
            label="case_law",
            fts_source_type="case_law",
        )

    # Merge curated and EFSA-imported botanicals; dedup on chunk_id so the
    # curated entry wins (it has hand-written German risk notes).
    combined_botanicals: list[dict[str, Any]] = []
    seen_botanical_ids: set[str] = set()
    for source in (botanicals_data, botanicals_efsa_data):
        if not source:
            continue
        for entry in source.get("entries", []):
            entry_id = entry.get("id")
            if not entry_id or entry_id in seen_botanical_ids:
                continue
            seen_botanical_ids.add(entry_id)
            combined_botanicals.append(entry)

    if combined_botanicals:
        logger.info("Indexing botanicals (%d entries) …", len(combined_botanicals))
        botanicals_count = _index(
            client,
            BOTANICALS_COLLECTION,
            combined_botanicals,
            _botanical_text,
            _botanical_payload,
            label="botanicals",
            fts_source_type="botanical",
        )

    logger.info(
        "Done. eu_claims=%d hcvo_chunks=%d extra_reg=%d case_law=%d botanicals=%d (Qdrant: %s)",
        eu_count,
        hcvo_count,
        extra_reg_count,
        case_law_count,
        botanicals_count,
        args.qdrant_url,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
