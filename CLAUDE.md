# ClaimGuard

> SaaS zur automatisierten Prüfung gesundheitsbezogener Werbeaussagen (Health Claims) nach EU-Verordnung 1924/2006 (HCVO) und deutscher Rechtsprechung. Zielmarkt: DACH.

## Tech Stack

- **Monorepo:** Turborepo + pnpm
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Zod + react-hook-form
- **Backend:** Python 3.12, FastAPI, Pydantic v2, uv (Paketmanager)
- **Async-Worker:** ARQ + Redis (siehe [ADR-0002](docs/adr/0002-async-worker-arq.md))
- **Datenbanken:** Supabase Postgres (EU), Qdrant self-hosted
- **Embeddings:** jina-embeddings-v3 self-hosted (EU, siehe [ADR-0003](docs/adr/0003-embedding-model.md))
- **LLM:** Claude Sonnet 4.6 (Detection), Claude Opus 4.7 (Evaluation) mit Zero-Data-Retention
- **Payments:** Stripe
- **Hosting:** Hostinger VPS Frankfurt (EU-Souveränität, kein US-Vendor-Lock-in)
- **Reverse Proxy:** Caddy (TLS automatisch)

## Project Structure

```
apps/
  web/              Next.js Frontend
    src/
      app/          Pages (App Router)
      components/
        ui/         shadcn/ui (NIE neu erstellen, nur ergänzen)
      hooks/        Custom React Hooks
      lib/          Supabase-Client, Utils
    tests/          Playwright E2E
  api/              Python FastAPI Backend
    app/
      api/          FastAPI Routes
      pipelines/    Orchestrierung: Detection → Retrieval → Evaluation
      services/     Clients: Anthropic, Qdrant, Postgres, Redis, jina
      schemas/      Pydantic-Modelle
      cache/        Redis-Cache
      prompts/      Versionierte Markdown-Prompts (PROJ-7)
    scripts/        CLI: KB-Update, Eval-Runner
    eval/datasets/  Eval-Sets (JSONL)
    tests/          pytest
docs/
  PRD.md            Produkt-Anforderungen
  adr/              Architecture Decision Records (0001–0005 Accepted)
features/
  INDEX.md          Feature-Status-Übersicht
  PROJ-*.md         Feature-Spezifikationen
docker-compose.yml  Lokale Services: Redis, Qdrant, jina-embeddings
```

## Development Workflow

1. `/requirements` - Feature-Spec schreiben
2. `/architecture` - Tech-Design entwerfen (PM-freundlich, kein Code)
3. `/frontend` - UI-Komponenten bauen (shadcn/ui zuerst prüfen)
4. `/backend` - API-Routen, Python-Pipeline-Code, Supabase-Migrationen
5. `/qa` - Akzeptanzkriterien + Security-Audit
6. `/deploy` - Produktions-Deployment auf Hostinger-VPS

## Feature Tracking

Alle Features in `features/INDEX.md`. Jede Skill liest ihn beim Start und aktualisiert ihn beim Abschluss. Specs liegen in `features/PROJ-X-name.md`.

## Key Conventions

- **Feature-IDs:** PROJ-1, PROJ-2, ... (sequenziell)
- **Commits:** `type(PROJ-X): Beschreibung` — types: feat, fix, refactor, test, docs, deploy, chore
- **Single Responsibility:** eine Feature pro Spec-Datei
- **shadcn/ui first:** installierte shadcn-Komponenten NIE neu erstellen
- **Human-in-the-loop:** Genehmigung des Nutzers an jedem Skill-Handoff
- **Sprache des Produkts:** Deutsch (MVP), i18n-ready (next-intl vorgesehen)
- **DSGVO-Pflicht:** Daten bleiben in EU, Zero-Data-Retention bei Anthropic
- **Tests:** Unit co-located (`useHook.test.ts` neben `useHook.ts`), E2E unter `apps/web/tests/`, Python-Tests unter `apps/api/tests/`
- **Umgangssprache:** Dominik nutzt Deutsch, antworte ebenfalls auf Deutsch

## Build & Test Commands

```bash
# Infrastruktur (Redis, Qdrant, jina-embeddings)
pnpm services:up        # docker compose up -d
pnpm services:down
pnpm services:logs

# Frontend + Backend parallel
pnpm dev                # turbo run dev --parallel
pnpm dev:web            # nur Next.js (Port 3000)
pnpm dev:api            # nur FastAPI (Port 8000)

# Build
pnpm build

# Tests
pnpm test               # Unit (Vitest + pytest via turbo)
pnpm test:e2e           # Playwright
pnpm test:all
```

### Backend separat (apps/api)

```bash
cd apps/api
uv sync                              # Python-Deps installieren
uv run uvicorn app.main:app --reload # Dev-Server
uv run pytest                        # Tests
uv run ruff check .                  # Linter
uv run mypy app                      # Type-Check
```

## Produkt-Kontext

@docs/PRD.md

## Feature-Übersicht

@features/INDEX.md

## Architektur-Entscheidungen (ADRs)

@docs/adr/README.md
