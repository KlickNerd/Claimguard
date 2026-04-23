# ADR-0001: Monorepo-Struktur mit Turborepo + pnpm

**Status:** Accepted & Implemented (2026-04-24)
**Datum:** 2026-04-23
**Kontext:** Alle MVP-Features
**Beteiligte Features:** alle

## Kontext

Aktueller Zustand: ClaimGuard ist als Single-Next.js-Projekt initialisiert (`src/`, `package.json` im Root). Der Backlog (Abschnitt 5.1) und die meisten MVP-Features fordern jedoch:
- `apps/web/` (Next.js 16, TypeScript) für das Frontend
- `apps/api/` (Python 3.12, FastAPI, Pydantic v2) für die Analyse-Pipeline
- Shared-Packages für z. B. Pydantic-/TypeScript-Typen (optional)

Ein Python-Backend lässt sich nicht in der Next.js-Route integrieren. Spätestens PROJ-8 (Claim-Detection) braucht eine Python-Laufzeit. Die Frage ist, ob wir den Monorepo-Umbau jetzt oder später machen.

## Optionen

### Option A: Jetzt auf Monorepo umstellen (empfohlen)
- Struktur: `apps/web`, `apps/api`, `packages/shared-types` (optional)
- Tooling: Turborepo + pnpm Workspaces
- Aufwand: 1 Tag (bestehenden Next.js-Code verschieben, Configs anpassen, README)

### Option B: Zwei getrennte Repos
- `claimguard-web` (Next.js), `claimguard-api` (Python)
- Kein Shared-Tooling, einfacher Einstieg
- Nachteil: Versions-Skew, doppelte CI, kein atomares Commit über beide Seiten

### Option C: Python-Backend als Sub-Verzeichnis ohne Monorepo-Tooling
- `/api/` neben `/src/`, kein Turborepo
- Funktioniert, ist aber unüblich und erschwert Dev-Experience (2 verschiedene Commands für Dev-Server)

## Empfehlung

**Option A — jetzt umstellen.** Der Umzug kostet 1 Tag, spätere Migration ist aufwendiger, weil dann CI/CD, Deployment, Tests schon auf der alten Struktur laufen. Monorepo mit Turborepo ist der dokumentierte Stack im Backlog.

## Folgen

- **Positiv:** Klare Trennung, einheitliche Dev-Experience (`pnpm dev` startet beide), atomische PRs über Frontend + Backend, Typing-Konsistenz via shared packages.
- **Negativ:** Bestehende `CLAUDE.md` und `.claude/`-Skills referenzieren `src/` — müssen aktualisiert werden. Initial Overhead für pnpm-Learning falls unbekannt.
- **Risiko:** Turborepo-Remote-Cache erst bei CI aktivieren (lokal ohne Auth).

## Offene Punkte

- Migrations-Task als erster Arbeitsschritt vor PROJ-1 einplanen? → **Ja, empfohlen.**
- Shared-Types-Package jetzt oder später? → **Später**, sobald das erste Modell zwischen Frontend und Backend geteilt wird (vermutlich bei PROJ-11).
