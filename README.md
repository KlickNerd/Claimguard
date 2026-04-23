# ClaimGuard

SaaS zur automatisierten Prüfung gesundheitsbezogener Werbeaussagen (Health Claims) auf rechtliche Zulässigkeit nach EU-Verordnung 1924/2006 (HCVO) und deutscher Rechtsprechung. Zielmarkt: DACH.

## Monorepo-Struktur

```
apps/
  web/    Next.js 16 Frontend (TypeScript, shadcn/ui)
  api/    Python 3.12 / FastAPI Backend (Analyse-Pipeline)
docs/
  PRD.md  Produkt-Anforderungen
  adr/    Architecture Decision Records (0001–0005)
features/ Feature-Specs (PROJ-1 bis PROJ-17, MVP)
```

Details: siehe [CLAUDE.md](CLAUDE.md)

## Quick Start

```bash
# Voraussetzungen: Node 20+, pnpm 9+, Python 3.12+, uv, Docker

# Dependencies
pnpm install                         # Frontend (Monorepo)
cd apps/api && uv sync && cd ../..   # Backend

# Lokale Services hoch (Redis, Qdrant, jina-embeddings)
pnpm services:up

# Dev-Server (beides parallel)
pnpm dev

# Einzeln
pnpm dev:web    # http://localhost:3000
pnpm dev:api    # http://localhost:8000/health
```

## Entwicklungs-Workflow

Alle Schritte laufen über Claude-Code-Skills:

1. `/requirements` – Feature-Spec
2. `/architecture` – Tech-Design + ggf. ADR
3. `/frontend` – UI bauen (shadcn/ui first)
4. `/backend` – APIs bauen (FastAPI + Supabase)
5. `/qa` – Test + Security-Review
6. `/deploy` – Produktion

Aktueller Stand: siehe [features/INDEX.md](features/INDEX.md).

## Architektur auf einen Blick

- **LLM-Pipeline:** Claude Sonnet 4.6 (Claim-Detection) → Hybrid Retrieval (Qdrant + Postgres FTS, RRF-Fusion) → Claude Opus 4.7 (Evaluation)
- **Wissensbasis:** EU-Claim-Register + HCVO-Verordnungstext + Urteilsdatenbank
- **Worker:** ARQ + Redis (async, persistent, Credit-Refund-fest)
- **Embeddings:** jina-embeddings-v3 self-hosted (EU, DSGVO)
- **Hosting:** Hostinger VPS Frankfurt (EU-Souveränität)

Entscheidungen dokumentiert in [docs/adr/](docs/adr/).

## Lizenz

Proprietär, © KlickNerds 2026.
