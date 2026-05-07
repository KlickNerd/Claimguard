"""Postgres-FTS over the curated knowledge base (PROJ-9, hybrid retrieval).

This is the keyword half of the hybrid retrieval. The vector half lives in
``retrieval_service``; both run in parallel and get fused via RRF. We
deliberately keep one ``kb_chunks`` table covering all source types so
the FTS query can rank across regulation snippets, EU-claim entries and
case-law paraphrases at once - that's exactly what the spec wants.

Schema (created by ``ensure_schema``):

    kb_chunks (
        chunk_id      text primary key,
        source_type   text not null,        -- eu_claim | regulation | case_law
        reference     text not null,
        snippet       text not null,
        url           text,
        metadata      jsonb,
        tsv           tsvector generated always as (
                          setweight(to_tsvector('german', coalesce(reference,'')), 'A') ||
                          setweight(to_tsvector('german', coalesce(snippet,'')),   'B')
                      ) stored,
        gin_idx       on tsv (gin)
    )

We use ``websearch_to_tsquery`` with the ``german`` configuration so the
built-in snowball stemmer reduces ``Apotheker`` and ``Apothekers`` to the
same lexeme - which is exactly the recall problem we observed in the
PROJ-19 smoke test.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Json

from app.config import settings

logger = logging.getLogger(__name__)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS kb_chunks (
    chunk_id    text PRIMARY KEY,
    source_type text NOT NULL,
    reference   text NOT NULL,
    snippet     text NOT NULL,
    url         text,
    metadata    jsonb,
    tsv         tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('german', coalesce(reference, '')), 'A') ||
                    setweight(to_tsvector('german', coalesce(snippet,   '')), 'B')
                ) STORED
);
CREATE INDEX IF NOT EXISTS kb_chunks_tsv_idx ON kb_chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS kb_chunks_source_idx ON kb_chunks (source_type);
"""


@dataclass(slots=True)
class FtsHit:
    chunk_id: str
    source_type: str
    reference: str
    snippet: str
    url: str
    metadata: dict
    rank: float


def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.kb_db_url)


@contextmanager
def _cursor() -> Iterator[psycopg.Cursor]:
    with _connect() as conn, conn.cursor() as cur:
        yield cur
        conn.commit()


def ensure_schema() -> None:
    """Idempotent schema bootstrap - safe to call on every indexer run."""
    with _cursor() as cur:
        cur.execute(_SCHEMA_SQL)


def upsert_chunks(items: list[dict]) -> int:
    """Insert or update chunks. Returns number of rows written.

    Each item must carry ``chunk_id``, ``source_type``, ``reference``,
    ``snippet``; ``url`` and ``metadata`` are optional.
    """
    if not items:
        return 0
    rows = [
        (
            item["chunk_id"],
            item["source_type"],
            item.get("reference", ""),
            item.get("snippet", ""),
            item.get("url") or None,
            Json(item.get("metadata") or {}),
        )
        for item in items
    ]
    with _cursor() as cur:
        cur.executemany(
            """
            INSERT INTO kb_chunks (chunk_id, source_type, reference, snippet, url, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                reference   = EXCLUDED.reference,
                snippet     = EXCLUDED.snippet,
                url         = EXCLUDED.url,
                metadata    = EXCLUDED.metadata
            """,
            rows,
        )
    return len(rows)


def reset_for_source(source_type: str) -> None:
    """Drop existing rows for a single source so the indexer can reseed it
    cleanly. We keep this granular instead of a TRUNCATE so re-indexing
    one source (e.g. only case_law) doesn't wipe the others."""
    with _cursor() as cur:
        cur.execute("DELETE FROM kb_chunks WHERE source_type = %s", (source_type,))


def count() -> int:
    with _cursor() as cur:
        cur.execute("SELECT count(*) FROM kb_chunks")
        row = cur.fetchone()
        return int(row[0]) if row else 0


_WORD_RE = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = {
    "der", "die", "das", "und", "oder", "ein", "eine", "eines", "einer",
    "im", "in", "an", "auf", "bei", "zu", "mit", "von", "fuer", "für",
    "ist", "sind", "war", "wird", "werden", "ihre", "ihr", "ihrem",
    "wenn", "dann", "auch", "dass", "nicht", "kein", "keine",
}


def _tokenize_query(query: str) -> list[str]:
    """Pull non-trivial words out of a free-text query for FTS.

    The German-snowball stemmer doesn't bridge across all derivations
    (``Empfehlung`` vs ``empfohlen`` reduce to different lexemes), so we
    feed the cleaned tokens into Postgres as an OR-query - any one match
    is enough for the keyword half. Stopwords are dropped so we don't
    chew through the whole table on a single ``"die"``.
    """
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in _WORD_RE.findall(query.lower()):
        if len(raw) < 3:
            continue
        if raw in _STOPWORDS:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        tokens.append(raw)
    return tokens


def search(query: str, *, limit: int = 8) -> list[FtsHit]:
    """German-FTS search; returns hits sorted by ts_rank descending.

    Empty / whitespace-only queries return an empty list - no FTS, no row.
    """
    if not query or not query.strip():
        return []
    tokens = _tokenize_query(query)
    if not tokens:
        return []

    # Build an OR-query: plainto_tsquery('german', tok1) || plainto_tsquery('german', tok2) || …
    # Each plainto_tsquery applies the German stemmer to one token. The
    # ``||`` operator in tsquery-land is OR, which is what we want for the
    # keyword half of hybrid retrieval (any matching token counts).
    expr = " || ".join(["plainto_tsquery('german', %s)"] * len(tokens))
    sql = f"""
        WITH q AS (SELECT ({expr}) AS query)
        SELECT chunk_id, source_type, reference, snippet, url, metadata,
               ts_rank_cd(tsv, q.query) AS rank
        FROM   kb_chunks, q
        WHERE  tsv @@ q.query
        ORDER  BY rank DESC
        LIMIT  %s
    """
    with _cursor() as cur:
        cur.execute(sql, (*tokens, limit))
        rows = cur.fetchall()
    hits: list[FtsHit] = []
    for row in rows:
        chunk_id, source_type, reference, snippet, url, metadata, rank = row
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        hits.append(
            FtsHit(
                chunk_id=str(chunk_id),
                source_type=str(source_type),
                reference=str(reference),
                snippet=str(snippet),
                url=str(url or ""),
                metadata=dict(metadata or {}),
                rank=float(rank),
            ),
        )
    return hits
