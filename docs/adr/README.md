# Architecture Decision Records (ADR)

Dieses Verzeichnis enthält dokumentierte Architektur-Entscheidungen im MADR-Light-Format. Jedes ADR beschreibt **Kontext, Optionen, Empfehlung und Folgen** einer Entscheidung, die über ein einzelnes Feature hinausgeht.

## Status

| ADR | Titel | Status | Betroffene Features |
|---|---|---|---|
| [0001](0001-monorepo-structure.md) | Monorepo mit Turborepo + pnpm | Accepted & Implemented | alle |
| [0002](0002-async-worker-arq.md) | ARQ + Redis als Worker-Infrastruktur | Accepted | PROJ-8/9/10, PROJ-11/12/13, PROJ-15, PROJ-17 |
| [0003](0003-embedding-model.md) | jina-embeddings-v3 self-hosted | Superseded by [0006](0006-embedding-model-e5.md) | PROJ-4/5/6, PROJ-9 |
| [0004](0004-reranker-v11.md) | Reranker erst in V1.1 | Accepted | PROJ-9 |
| [0005](0005-caching-strategy.md) | Minimaler Embedding-Cache im MVP | Accepted | PROJ-4/5/6, PROJ-9 |
| [0006](0006-embedding-model-e5.md) | `multilingual-e5-base` in-process | Accepted | PROJ-4/5/6, PROJ-9 |
| [0007](0007-evaluation-model-sonnet.md) | Sonnet 4.6 als Default-Evaluator (statt Opus 4.7) | Accepted | PROJ-10 |

## Status-Werte

- **Proposed** — Entscheidung zur Diskussion, noch nicht akzeptiert
- **Accepted** — durch Product Owner bestätigt, verbindlich
- **Deprecated** — durch ein späteres ADR ersetzt
- **Superseded by ADR-XXXX** — überholt

## Prozess

- Neue ADRs werden bei Entscheidungen mit Wirkung über ein Feature hinaus angelegt
- Nummerierung fortlaufend, nie ändern
- Änderungen eines Proposed-ADR: direkt editierbar
- Änderungen eines Accepted-ADR: neues ADR mit „Supersedes ADR-XXXX" anlegen, alt wird auf `Superseded` gesetzt
