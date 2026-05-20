# PROJ-21: Analyses-Persistierung

## Status: Planned
**Created:** 2026-05-11
**Last Updated:** 2026-05-11

## Dependencies
- Requires: PROJ-1 (User Authentication) — `analyses.user_id` braucht `auth.uid()` für RLS und Ownership
- Soft: PROJ-11 / PROJ-12 / PROJ-13 (Text / PDF / URL Input) — rufen aktuell `/api/analyses` auf, der erweitert wird
- Soft: PROJ-14 (Report-Darstellung) — kann auf echte gespeicherte Analyse zurückgreifen
- Soft: PROJ-16 (Dashboard / History) — wird von Mock-Daten auf echte DB umgestellt
- Soft: PROJ-20 (KI-Chat) — `chat_messages.analysis_id` referenziert die hier angelegte Tabelle

## User Stories
- Als eingeloggter Nutzer möchte ich, dass jede meiner Analysen automatisch gespeichert wird, damit ich sie später wiederfinde — ohne extra „Speichern"-Klick.
- Als eingeloggter Nutzer möchte ich auf der History-Seite eine Liste meiner letzten Analysen sehen, damit ich schnell zu früheren Prüfungen zurückkehren kann.
- Als eingeloggter Nutzer möchte ich eine alte Analyse anklicken und das vollständige Ergebnis (Original-Text, Claims, Bewertungen, Rechtsquellen) wieder vor mir haben, damit ich keine Arbeit doppelt machen muss.
- Als eingeloggter Nutzer möchte ich eine Analyse aus der Liste löschen können — mit 30 Tagen Rückholbarkeit, falls ich mich vertippt habe.
- Als eingeloggter Nutzer möchte ich beim Löschen meines Accounts, dass alle meine Analysen mit verschwinden (DSGVO), damit keine personenbezogenen Daten zurückbleiben.

## Acceptance Criteria

### Persistierung
- [ ] Erfolgreich abgeschlossene Analysen werden nach Berechnung in einer neuen `analyses`-Tabelle gespeichert.
- [ ] Eine Analyse wird mit dem aktuell eingeloggten User verknüpft (`user_id`, FK auf `auth.users`).
- [ ] Fehlgeschlagene Analysen werden NICHT in die History persistiert (nur erfolgreich abgeschlossene).
- [ ] Demo-Analysen via Landing-Widget werden NICHT persistiert (kein eingeloggter User → kein Persist).
- [ ] Folgende Felder werden gespeichert: `id`, `user_id`, `source_type`, `source_reference`, `input_text`, `detected_claims` (JSONB), `evaluated_claims` (JSONB), `warnings` (JSONB), `prompt_version`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `latency_ms`, `created_at`, `deleted_at`.

### Snapshot-Verhalten
- [ ] Die gespeicherte Analyse ist ein unveränderlicher Snapshot des Original-Ergebnisses.
- [ ] Editor-Änderungen oder angewendete Rewrites NACH der Analyse modifizieren die gespeicherte Zeile NICHT.
- [ ] Klickt der User „Neu prüfen" mit verändertem Text, entsteht eine NEUE Analyse-Zeile; die alte bleibt erhalten.

### API-Endpoints
- [ ] `POST /api/analyses` (existiert) gibt jetzt zusätzlich zur Analyse die `analysis_id` (UUID) zurück.
- [ ] `GET /api/analyses/{analysis_id}` lädt eine einzelne Analyse zurück (nur Owner, sonst 403, soft-deleted → 404).
- [ ] `GET /api/analyses?limit=N&offset=M` liefert die paginierte Liste der eigenen Analysen, sortiert nach `created_at` absteigend; Default `limit=20`, max `limit=100`.
- [ ] `DELETE /api/analyses/{analysis_id}` setzt `deleted_at = now()` (Soft-Delete), antwortet 200; nur Owner.
- [ ] `POST /api/analyses/{analysis_id}/restore` setzt `deleted_at = NULL` (funktioniert nur innerhalb 30 Tage seit Löschung); nur Owner.

### History-Page (PROJ-16)
- [ ] Die History-Seite ruft die echten Analysen aus `GET /api/analyses` ab statt `MOCK_ANALYSES` zu zeigen.
- [ ] Anzeige pro Zeile: Source-Type-Icon (Text/PDF/URL), erste ~100 Zeichen Input-Text als Titel, Ampel-Score, Datum.
- [ ] Klick auf eine Zeile lädt die volle Analyse via `GET /api/analyses/{id}` und navigiert zur Report-Seite.
- [ ] Lösch-Icon pro Zeile mit Bestätigungs-Dialog; nach `DELETE` Toast mit „Rückgängig" (5 s Cooldown → ruft Restore).
- [ ] Soft-deleted Analysen sind in der Liste unsichtbar (Server filtert `deleted_at IS NULL`).

### Soft-Delete + Auto-Purge
- [ ] Soft-deleted Analysen bleiben 30 Tage mit `deleted_at`-Timestamp in der DB.
- [ ] Ein Background-Job (täglich) löscht physisch alle Analysen mit `deleted_at < now() - 30 days`.
- [ ] Cascade: Hard-Delete einer Analyse löscht alle abhängigen Datensätze mit (vorbereitet für PROJ-20 Chat-Messages).
- [ ] Account-Löschung (User löscht sich selbst, PROJ-17) → CASCADE löscht alle Analysen + abhängige Daten **sofort**, kein Soft-Delete-Window.

### RLS + Sicherheit
- [ ] RLS-Policy auf `analyses`: nur `auth.uid() = user_id` darf SELECT, INSERT, UPDATE, DELETE.
- [ ] Server-side Backend-Calls (mit Service-Role-Key) umgehen RLS, prüfen aber Owner zusätzlich im Code (Defense-in-Depth).
- [ ] Alle Daten bleiben in der EU (Supabase EU Region wie der Rest des Stacks).

## Edge Cases
- **User nicht eingeloggt** ruft `POST /api/analyses`: Backend antwortet 401 (kommt aus PROJ-1). Demo bleibt im Demo-Widget, ungespeichert.
- **User-Quota erreicht** (PROJ-2): `POST /api/analyses` antwortet 402; Frontend zeigt „Upgrade nötig", keine Persistierung.
- **DB-Insert schlägt fehl, Anthropic-Call lief aber durch**: Analyse-Result wird trotzdem zurückgegeben, mit Warning „Konnte nicht in History gespeichert werden" und `analysis_id = null`. Kein Workflow-Block für den User.
- **User lädt alte Analyse, deren `prompt_version` nicht mehr existiert**: Anzeige funktioniert (Snapshot enthält alle Daten), kleine Info „Mit alter Prompt-Version analysiert".
- **Sehr lange Input-Texte** (bis 50k Zeichen): Postgres-`text`-Spalte ist unbegrenzt; TOAST-Storage komprimiert automatisch.
- **Race-Condition: User löscht Analyse während Chat-Call darauf läuft**: Chat-Endpoint prüft Existenz + Owner; bei Soft-Delete kommt 404, Frontend zeigt „Analyse nicht mehr verfügbar".
- **Restore einer Analyse, deren Cascade-Children (z. B. Chat-Messages) schon physisch weg sind**: Restore klappt für die Analyse selbst, Chat-Verlauf bleibt leer. Akzeptabel im MVP.
- **User klickt versehentlich Lösch-Icon**: Bestätigungs-Dialog + Toast mit „Rückgängig"-Link nach Soft-Delete.
- **Pagination-Grenzen**: Default `limit=20`, max `limit=100`; Server cappt automatisch, falls Client mehr fordert.
- **`evaluated_claims` JSON wird groß** (40+ Claims mit Reasoning): JSONB-Spalte, TOAST-Komprimierung; keine Größenprobleme zu erwarten.
- **History-Liste wird sehr lang** (>1.000 Analysen): Pagination greift; Filter (Datum / Source-Type) sind in PROJ-16 ohnehin vorgesehen.

## Non-Goals (MVP)
- **Multi-User-Sharing** („Analyse mit Kollegen teilen") — V1.1.
- **Team-Workspaces** — V1.1.
- **Versionierung** (mehrere „Drafts" pro Input) — V1.2.
- **Re-Run mit aktualisierter KB** („Was sagt der heutige Stand zu meiner alten Analyse?") — V1.2.
- **Volltextsuche in alten Analysen** — V1.2.
- **Plan-abhängige Retention** (Free 30 Tage, Pro unbegrenzt) — abhängig von PROJ-2, kommt später.
- **Export der gesamten History** (CSV/JSON-Dump) — V1.1, gehört zu PROJ-17 DSGVO.

## Technical Requirements
- **Datenbank:** Supabase Postgres (EU), neue Tabelle `analyses` im `public`-Schema.
- **API:** Bestehender `POST /api/analyses` bleibt rückwärtskompatibel — gibt dasselbe JSON zurück, plus `analysis_id`. Neue Endpoints für Get/List/Delete/Restore.
- **Backend-DB-Zugriff:** Server-side Supabase-Client mit Service-Role-Key (umgeht RLS, prüft Owner im Code).
- **Soft-Delete-Purge:** Hintergrund-Job — ARQ (siehe ADR-0002) oder pg_cron, Entscheidung in der Architektur-Phase.
- **Performance:** History-List-Query muss bei 1.000 Analysen pro User < 300 ms zurückkommen (Index auf `(user_id, created_at DESC) WHERE deleted_at IS NULL`).
- **Sicherheit:** RLS aktiv auf allen CRUD-Operationen; zusätzlicher Owner-Check im Code als Defense-in-Depth.
- **DSGVO:** Account-Löschung kaskadiert sofort auf alle Analysen (kein Soft-Delete-Window bei Account-Wegfall).

## Offene Fragen (für /architecture)
- ARQ-Worker oder pg_cron für Auto-Purge?
- `detected_claims` + `evaluated_claims` als zwei Spalten oder ein einziger `result`-JSONB? (Performance vs. Lesbarkeit)
- Timezone für `created_at` — UTC (Standard) und im Frontend rendern?

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
