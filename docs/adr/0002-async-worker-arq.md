# ADR-0002: Async-Worker-Infrastruktur mit ARQ + Redis

**Status:** Accepted (2026-04-24)
**Datum:** 2026-04-23
**Kontext:** PROJ-8/9/10 (Pipeline), PROJ-11/12/13 (Eingabe-Flows), PROJ-17 (Datenexport)
**Verwandte Backlog-Frage:** 5.3 Punkt 1

## Kontext

Die Analyse-Pipeline (PROJ-8 → PROJ-9 → PROJ-10) dauert p95 bis 60 s. HTTP-Requests so lange offen zu halten ist aus mehreren Gründen problematisch:
- Browser-Timeouts und Proxy-Reset (Caddy / Cloudflare)
- Keine Resilienz bei Prozess-Neustart (Deploy, OOM) → User verliert Analyse + Credit
- Keine Parallelisierung mehrerer LLM-Calls über Worker
- Keine Retry-Semantik bei transienten Fehlern
- PROJ-17 (DSGVO-Datenexport) und PROJ-4/5/6 (KB-Updates) brauchen ebenfalls Hintergrund-Jobs

Drei realistische Optionen für das MVP:

## Optionen

### Option A: FastAPI `BackgroundTasks`
- Eingebaut, keine Zusatz-Infra.
- **Problem:** Tasks laufen im selben Prozess, kein Persist, kein Retry, kein Timeout-Schutz. Bei Deploy/OOM verloren.
- Geeignet nur für schnelle Fire-and-Forget-Jobs (< 1 s), nicht für 60-s-Pipelines.

### Option B: ARQ (Redis-basiert, async-native) ← empfohlen
- Leichtgewichtig, async-first, baut auf Redis auf.
- Job-Persist, Retry, Timeout, Cron, alles out-of-the-box.
- Ein Worker-Container neben dem API-Container. Redis läuft eh für Session-Rate-Limits.
- Community kleiner als Celery, aber für MVP-Umfang mehr als ausreichend.
- Simple Dev-Experience: Jobs als normale async-Funktionen.

### Option C: Celery + Redis
- Industriestandard, riesige Community, viele Features.
- **Nachteile:** sync-basiert (extra Gymnastik für async SDK-Calls wie Anthropic), komplexe Konfiguration, schwerer Debugger-Setup, Overkill für Solo-Founder.
- Vorteil: Bewährt bei Millionen-Scale — aber das ist kein MVP-Thema.

## Empfehlung

**Option B — ARQ.** Gleicher Funktionsumfang wie Celery für MVP-Bedarf, halber Betriebsaufwand, async-kompatibel zur Anthropic-SDK, keine zusätzliche Komplexität gegenüber BackgroundTasks bei drastisch besserer Resilienz.

## Folgen

- **Positiv:**
  - Pipeline überlebt Prozess-Restarts
  - Credit-Refund bei gescheiterten Jobs zuverlässig
  - Horizontale Skalierung via Worker-Replikas möglich
  - Wiederverwendbar für PROJ-17 (Datenexport), PROJ-4–6 (KB-Update-Jobs), PROJ-15 (PDF-Generierung)
- **Negativ:**
  - Redis muss auf dem VPS betrieben werden (Docker-Container, minimaler Overhead)
  - Dev-Setup hat eine Komponente mehr (docker-compose erledigt das)
- **Operativ:** Redis-Backup (täglicher RDB-Dump) in das Backup-Konzept aufnehmen (redis-data zeilt im Hostinger-VPS-Backup).

## Open Items
- Max. Job-Laufzeit: 120 s (doppelt so hoch wie p95-Ziel, harter Abbruch)
- Max. gleichzeitige Worker-Prozesse: 4 (abhängig von VPS-Ressourcen, tuning-bar)
- Monitoring: ARQ-Jobs an Sentry hängen bei Exception
