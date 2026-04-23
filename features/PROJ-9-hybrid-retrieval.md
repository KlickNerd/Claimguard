# PROJ-9: Hybrid Retrieval

## Status: Architected
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-011

## Dependencies
- PROJ-4 (EU-Claim-Register) — Datenquelle
- PROJ-5 (HCVO-Verordnungstext) — Datenquelle
- PROJ-6 (Urteilsdatenbank) — Datenquelle
- PROJ-8 (Claim-Detection) — liefert Claims als Query-Input

## User Stories
- Als System möchte ich für jeden erkannten Claim die relevantesten Rechtsquellen finden, damit die Evaluation fundiert bewerten kann.
- Als Nutzer möchte ich im Report die 3–5 wichtigsten Fundstellen pro Claim sehen, damit ich die Bewertung nachvollziehe.

## Acceptance Criteria
- [ ] Für jeden Claim: parallele Suche in Qdrant (Vektor) + Postgres (Keyword)
- [ ] Suchraum: Union aus `eu_claims`, `regulation_chunks`, `case_law`
- [ ] Fusion via Reciprocal Rank Fusion (RRF, Konstante k=60)
- [ ] Top-K konfigurierbar, Default 8, Enterprise-Plan erlaubt bis 20
- [ ] Retrieval-Latenz p95 ≤ 500 ms pro Claim (ohne LLM)
- [ ] Jeder Treffer mit Metadaten: `source_type` (eu_claim / regulation / case_law), `score`, `chunk_id`, `snippet`
- [ ] Query-Erweiterung: Claim-Text + erkannte `nutrient`/`substance` werden kombiniert gesucht
- [ ] Keyword-Suche nutzt Deutsch-Analyzer (`to_tsvector('german', ...)`)
- [ ] Deduplication: gleicher `chunk_id` erscheint nur einmal, auch wenn in beiden Suchen getroffen

## Edge Cases
- **Claim hat keine matching Einträge:** Leere Trefferliste, Evaluation erhält `unclear`-Signal
- **Sehr generischer Claim (z.B. „gesund"):** Viele schwache Treffer — Score-Threshold (Default 0.5) filtert
- **Qdrant-Ausfall:** Fallback auf Postgres-only (FTS), UI-Hinweis „eingeschränkte Retrieval-Qualität"
- **Postgres-Timeout bei FTS:** Fallback auf Qdrant-only
- **Claim in Nicht-DE-Sprache:** kommt nicht vor (Sprach-Check in PROJ-11)
- **Knowledge-Base während Query geupdated:** Transaction-Isolation, alte Version zu Ende lesen
- **Sehr langer Claim-Text (> 500 Zeichen):** Query gekürzt, Warnung loggen

## Technical Requirements
- Qdrant Python Client (async)
- Embedding-Modell identisch zu Index (siehe PROJ-4, Entscheidung in /architecture)
- `asyncio.gather` für parallele Qdrant + Postgres Queries
- RRF-Implementierung: `score = sum(1 / (k + rank_i))` über alle Quellen
- Score-Threshold konfigurierbar per Config

## Open Questions
- Reranker (Cohere Rerank / BGE-Reranker self-hosted) im MVP oder V1.1? → **Offene Architektur-Frage aus Backlog 5.3 Punkt 3**
- Per-Source-Gewichtung (z.B. Urteile > Register > Verordnung)? → **MVP: gleich gewichtet, V1.1 tunen**
- Query-Caching bei identischem Claim-Text (Hash-basiert)? → **V1.1, MVP kein Cache**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)

### Zielbild & Einordnung
PROJ-9 ist **Stufe 2 der Analyse-Pipeline**. Es bekommt eine Liste `DetectedClaim` aus PROJ-8 und liefert pro Claim die rechtlich relevantesten Wissens-Chunks aus drei Quellen (EU-Register, HCVO, Urteilsdatenbank) zurück. Die Qualität hier entscheidet, auf welcher Faktenbasis PROJ-10 urteilt — „Garbage in, garbage out".

### Retrieval-Flow pro Claim

```
[ DetectedClaim aus PROJ-8 ]
          │
          ▼
┌─────────────────────────────────────┐
│  1. Query-Erweiterung               │
│     query = claim_text              │
│             + nutrient              │
│             + substance             │
└─────────────────────────────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐  ┌─────────────┐
│ Qdrant  │  │ Postgres    │
│ Vektor- │  │ Full-Text-  │
│ Suche   │  │ Suche (DE)  │
│ Top-K   │  │ Top-K       │
└─────────┘  └─────────────┘
    │           │
    └─────┬─────┘
          ▼
┌─────────────────────────────────────┐
│  2. RRF-Fusion (k=60)               │
│     score = Σ 1 / (k + rank_i)      │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  3. Dedup + Threshold-Filter        │
│     score ≥ 0.5                     │
│     max 8 pro Claim                 │
└─────────────────────────────────────┘
          │
          ▼
[ RetrievalResult → PROJ-10 ]
```

### Komponenten-Struktur

```
apps/api/app/
├── pipelines/
│   └── retrieval.py              # Orchestrator
├── services/
│   ├── embedding_client.py       # jina-v3 local HTTP (ADR-0003)
│   ├── qdrant_client.py          # Qdrant-Wrapper, async
│   ├── postgres_fts.py           # Postgres Full-Text-Search
│   └── fusion.py                 # RRF-Algorithmus
├── schemas/
│   └── retrieval.py              # RetrievalHit, RetrievalResult
└── cache/
    └── embedding_cache.py        # Redis-Cache (ADR-0005)
```

Drei Qdrant-Collections werden parallel durchsucht: `eu_claims`, `regulation_chunks`, `case_law` (Union-Suche, gleicher Score-Raum).

### Datenmodell (Plain Language)

**RetrievalHit**:
- Chunk-ID (UUID aus KB)
- Quelle: `eu_claim`, `regulation`, oder `case_law`
- Score nach RRF (0–1)
- Snippet (gekürzter Text für Report-Anzeige, max. 300 Zeichen)
- Vollständige Metadaten je Quelltyp (Artikel+Absatz, Aktenzeichen, Registereintrag-Status)
- Deep-Link auf Originalquelle (Eur-Lex, BGH-Urteil, EU-Register)

**RetrievalResult** (pro Claim):
- Referenz auf DetectedClaim
- Liste von RetrievalHits (max. 8, nach Score sortiert)
- Metadaten: Suchlatenz, Anzahl Kandidaten vor Dedup, KB-Version

### Tech-Entscheidungen mit Begründung

| Entscheidung | Wahl | Warum |
|---|---|---|
| Embedding-Modell | jina-embeddings-v3 self-hosted | ADR-0003; EU, DSGVO, niedrige Latenz |
| Fusion | Reciprocal Rank Fusion (k=60) | Literatur-Standard (Cormack et al.), parameterarm, robust gegen Score-Skew zwischen Vektor- und Keyword-Suche |
| Per-Source-Gewichtung | Gleich gewichtet (V1.0) | MVP: Daten fehlen für informed-Tuning. V1.1: Urteile ggf. boosten basierend auf Eval |
| Parallelisierung | `asyncio.gather(qdrant, postgres)` | Beide I/O-bound, Latenz-Gewinn ~ 40 % gegenüber sequentiell |
| FTS-Sprache | `to_tsvector('german', …)` | Native Stemming für DE (Foo→Fuß, Kinder→Kind etc.) |
| Score-Threshold | 0.5 | Filtert offensichtliche False-Positives, überschaubar im Prompt |
| Top-K | 8 (Default), bis 20 (Enterprise) | Balance Prompt-Länge/Kosten und Kontext-Qualität |
| Reranker | Kein (siehe ADR-0004) | RRF reicht für MVP-KB-Größe |
| Query-Erweiterung | Claim + Nutrient + Substance konkateniert | Simple, wirksam, keine zusätzliche LLM-Call-Latenz |
| Fallback bei Qdrant-Ausfall | Postgres-only mit UI-Warning | Graceful Degradation statt Hard-Fail |

### Dependencies (neu)

- `qdrant-client` (mit async-Extra)
- `asyncpg` (schneller Postgres-Driver)
- `httpx` (für jina-v3 lokalen HTTP-Call)
- `redis` (asyncio) für Embedding-Cache (aus ADR-0005)

### Verknüpfte ADRs
- [ADR-0002](../docs/adr/0002-async-worker-arq.md) Redis verfügbar → Embedding-Cache möglich
- [ADR-0003](../docs/adr/0003-embedding-model.md) jina-v3 self-hosted
- [ADR-0004](../docs/adr/0004-reranker-v11.md) kein Reranker im MVP
- [ADR-0005](../docs/adr/0005-caching-strategy.md) Embedding-Cache aktiv

### Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| Recall@8 < 0.85 (relevante Chunks landen nicht in Top-8) | Mittel | Eval-Set in PROJ-9, Gate-Kriterium ADR-0003, Reranker V1.1 als Plan B |
| Qdrant + Postgres out-of-sync (KB-Update teilweise) | Niedrig | KB-Update in DB-Transaction; Qdrant-Upsert erst nach DB-Commit |
| Score-Inflation bei sehr kurzen Claims | Mittel | Score-Threshold 0.5, zusätzliche Prüfung auf Mindestsnippet-Länge |
| Latenz > 500 ms pro Claim | Niedrig | Embedding-Cache in ADR-0005, async-Parallel, Indexe vorhanden |
| Claim in anderer Sprache als KB | Niedrig (DE-only MVP) | Ausgeschlossen durch Sprach-Check PROJ-11 |

### Explizit nicht im Design
- Kein HyDE (hypothetical document embeddings) — zu früh
- Keine Query-Rewriting-LLM-Calls — Latenz/Kosten
- Kein semantisches Chunking zur Query-Zeit — Chunks sind bereits beim Indexieren optimiert (PROJ-4/5/6)

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
