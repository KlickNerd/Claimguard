# ClaimGuard API

Python-Backend für die Analyse-Pipeline (Claim-Detection, Retrieval, Evaluation) und Platzhalter für Auth/Billing-Endpoints.

## Stack

- Python 3.12, FastAPI, Pydantic v2
- Anthropic SDK (Claude Sonnet 4.6 + Opus 4.7)
- Qdrant (Vektor), Supabase Postgres (Daten + FTS)
- ARQ + Redis (Async-Worker, siehe ADR-0002)
- Paketmanager: `uv`

## Setup (lokal)

```bash
# uv installieren (einmalig)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Infrastruktur hochfahren (im Repo-Root)
docker compose up -d

# Python-Abhängigkeiten installieren
uv sync

# .env anlegen
cp .env.example .env  # ANTHROPIC_API_KEY etc. eintragen

# API starten
uv run uvicorn app.main:app --reload --port 8000
```

Health-Check: `curl http://localhost:8000/health`

## Verzeichnisstruktur

```
app/
├── api/          # FastAPI-Routen (pro Feature ein Router)
├── pipelines/    # Orchestrierung Detection / Retrieval / Evaluation
├── services/     # Externe Clients (Anthropic, Qdrant, Postgres, Redis, jina)
├── schemas/      # Pydantic-Modelle
├── cache/        # Redis-Caching
├── prompts/      # Versionierte Markdown-Prompts (PROJ-7)
├── config.py     # Settings via pydantic-settings
└── main.py       # FastAPI-App-Init
scripts/          # CLI-Tools (KB-Update, Eval-Runner)
eval/datasets/    # Eval-Sets (JSONL)
tests/            # pytest
```

## Tests

```bash
uv run pytest
uv run ruff check .
uv run mypy app
```

## Worker (wenn implementiert)

```bash
uv run arq app.worker.WorkerSettings
```
