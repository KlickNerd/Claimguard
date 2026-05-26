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

### Großer Bogen

Eine neue `analyses`-Tabelle in Supabase verankert jedes Ergebnis dauerhaft. Wenn der bestehende `POST /api/analyses` durchgelaufen ist, schreibt das Backend die Ergebnis-Zeile in einem letzten Pipeline-Schritt — der User bekommt sein Ergebnis sofort UND eine `analysis_id` mitgeliefert. Vier neue Endpoints fürs Lesen, Listen, Löschen und Wiederherstellen runden das aus. Die History-Seite zieht ihre Liste über den neuen List-Endpoint und ersetzt die `MOCK_ANALYSES` ohne sonstige UI-Umbau. Soft-Delete läuft über eine `deleted_at`-Spalte; ein täglicher pg_cron-Job räumt Zeilen, die länger als 30 Tage gelöscht sind, physisch weg. RLS auf der Tabelle stellt sicher, dass nur der Owner liest und schreibt.

### Komponentenstruktur (Backend)

```
apps/api/app/
├── api/
│   └── analyses.py            (bestehend → bekommt GET single, GET list, DELETE, POST restore)
├── services/
│   ├── analysis_storage.py    (neu — Supabase-Client-Wrapper für die analyses-Tabelle)
│   └── (bestehende Pipeline-Services bleiben unverändert)
├── schemas/
│   └── analysis.py            (bestehend → neue Variante "StoredAnalysis" mit id/user_id/created_at/deleted_at)
└── core/auth.py                (kommt aus PROJ-1 — wird hier genutzt für Owner-Check)
```

### Komponentenstruktur (Frontend)

```
apps/web/src/
├── app/app/history/page.tsx   (bestehend → MOCK_ANALYSES raus, echte API-Calls rein)
├── components/app/
│   └── analysis-row.tsx       (neu, optional — extrahiert die History-Zeile mit Lösch-Toast-Logik)
└── lib/api-client.ts          (bestehend → 4 neue Funktionen: listAnalyses, getAnalysis, deleteAnalysis, restoreAnalysis)
```

### Datenmodell (in Worten)

**Neue Tabelle: `analyses`** (Public-Schema, Supabase Postgres EU)

Pro Zeile gespeichert:
- **ID** (UUID, Primary Key, vom Server vergeben)
- **user_id** (Foreign Key auf `auth.users`, CASCADE bei Account-Löschung)
- **source_type** (`text` | `url` | `pdf`) + **source_reference** (optional, z. B. URL oder Dateiname)
- **input_text** (langes Text-Feld, bis 50k Zeichen)
- **detected_claims** (JSONB — Snapshot aller erkannten Claims mit Position, Typ, Nutrient/Substance)
- **evaluated_claims** (JSONB — Snapshot aller Bewertungen inkl. Status, Confidence, Reasoning, Legal-Hints, Retrieval-Evidence)
- **warnings** (JSONB-Array — Pipeline-Warnungen wie „Retrieval eingeschränkt")
- **Metadaten zur Berechnung**: `prompt_version`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `latency_ms`
- **created_at** (Zeitstempel mit UTC-Zeitzone, gesetzt von DB)
- **deleted_at** (Zeitstempel, nullbar — gesetzt beim Soft-Delete)

**Indexe:**
- Schlüssel-Index: `(user_id, created_at DESC) WHERE deleted_at IS NULL` — der wichtigste, beschleunigt die History-Liste.
- Sekundär-Index auf `deleted_at` — beschleunigt den Purge-Job.

**Row-Level-Security:**
- SELECT, INSERT, UPDATE, DELETE: nur erlaubt, wenn `auth.uid() = user_id`.
- Backend nutzt Service-Role-Key (umgeht RLS), prüft Owner zusätzlich im Code als Defense-in-Depth.

**JSONB statt separate Tabellen für Claims/Evaluations:** Wir speichern die kompletten Claim-Listen als JSONB-Snapshot. Das passt zum Spec-Snapshot-Verhalten (Analysen sind unveränderlich) und spart eine 3-Tabellen-JOIN-Kaskade beim Lesen. JSONB komprimiert automatisch (Postgres TOAST), spart auch Storage bei den 40+ Claim-Bewertungen.

**Beibehaltung der zwei Spalten** (`detected_claims` + `evaluated_claims` separat statt ein gemeinsames `result`):
- entspricht der `AnalysisResponse`-Schema-Struktur (Konsistenz mit Pydantic-Modellen),
- erlaubt JSONB-Indexierung gezielt auf eines der beiden Felder,
- macht spätere Migrationen einfacher (z. B. wenn `evaluated_claims` mal in eine relationale Tabelle umzieht).

### Endpoints im Überblick

| Methode | Pfad | Wozu |
|---|---|---|
| POST | `/api/analyses` | bestehend; bekommt jetzt nur ein zusätzliches Feld `analysis_id` im Response |
| GET | `/api/analyses/{id}` | einzelne Analyse laden (Owner-Check, 404 wenn soft-deleted) |
| GET | `/api/analyses` | paginierte eigene Liste (Default 20, max 100, sortiert created_at desc) |
| DELETE | `/api/analyses/{id}` | Soft-Delete (setzt `deleted_at`) |
| POST | `/api/analyses/{id}/restore` | Soft-Delete rückgängig machen, nur innerhalb 30 Tagen |

### Soft-Delete + Auto-Purge

- **Soft-Delete** via `deleted_at`-Spalte (DB-Trigger ist nicht nötig — der DELETE-Endpoint setzt das Feld einfach).
- **Auto-Purge** via **pg_cron** (Postgres-Extension, in Supabase aktivierbar mit einem Klick): ein täglicher Job löscht physisch alle Zeilen mit `deleted_at < now() - 30 days`. Der Job ist 1 SQL-Statement, kein extra Container, keine Worker-Wartung.
- **Cascade auf Account-Löschung:** `ON DELETE CASCADE` auf `user_id` sorgt dafür, dass beim Account-Wegfall alle Analysen sofort physisch wegfliegen — ohne Soft-Delete-Window, DSGVO-konform.
- **Cascade auf abhängige Datensätze:** wird beim Anlegen der `chat_messages`-Tabelle (PROJ-20) als `ON DELETE CASCADE` auf `analysis_id` definiert. Heißt: Hard-Delete einer Analyse (auch durch den Purge-Job) nimmt deren Chat-Verlauf mit.

### Tech-Entscheidungen (das Warum)

1. **pg_cron statt ARQ-Worker für Auto-Purge** — ARQ ist in ADR-0002 als Standard-Worker-Infrastruktur vorgesehen, aber aktuell nicht implementiert. Für einen täglichen 1-SQL-Cleanup-Job ist ein vollständiger Worker-Stack massiv überdimensioniert. pg_cron ist als Supabase-Extension mit einem Klick aktivierbar, läuft direkt in der DB, und kostet null zusätzliche Infrastruktur. ARQ kann später für andere Use-Cases (z. B. async Pipeline-Worker) kommen.

2. **Zwei separate JSONB-Spalten für `detected_claims` + `evaluated_claims`** — konsistent zum bestehenden `AnalysisResponse`-Pydantic-Schema (kein Zusatz-Mapping nötig); erlaubt gezielten JSONB-Index, falls später nach Status/Risk gefiltert werden soll; ermöglicht spätere Migration von `evaluated_claims` in eine relationale Tabelle ohne Schema-Bruch.

3. **UTC timestamptz für `created_at`** — Postgres-Standard, vermeidet jede Art von Timezone-Bug. Das Frontend formatiert in Europe/Berlin beim Rendern.

4. **JSONB statt separate `claim_evaluations`-Tabelle** — eine Analyse ist ein unveränderlicher Snapshot (per Spec). Es gibt keine Use-Cases, in denen einzelne Claim-Bewertungen ohne ihre Analyse abgefragt werden. JSONB im Snapshot spart Joins und matched das Snapshot-Semantik 1:1.

5. **Persistierung als letzter Pipeline-Schritt im selben Request** — der Pipeline-Code hat das Result bereits im Speicher; ein DB-Insert direkt vor dem Response ist atomar und braucht keinen extra Worker. Falls Insert fehlschlägt: User bekommt sein Ergebnis trotzdem (Acceptance Criterion 5 oben), nur die `analysis_id` ist null.

6. **Service-Role-Key im Backend + Owner-Check im Code** — der Backend-Container nutzt den Service-Role-Key, um RLS zu umgehen (sonst müssten wir bei jedem Insert das User-JWT durchschleifen). Sicherheit kommt aus zwei Schichten: der `user_id` im Insert wird aus dem authentifizierten JWT (`get_current_user`-Dependency, PROJ-1) genommen, und beim Lesen/Löschen prüft der Code zusätzlich `user_id == current_user.id`. Defense-in-Depth.

7. **Soft-Delete mit 30-Tage-Window** — User-Erwartung: „aus Versehen geklickt → schnell rückgängig". Ohne Soft-Delete wäre jede Lösch-Aktion endgültig, was teure UI-Confirmation-Dialoge nötig macht. Mit 30 Tagen Toleranz reicht ein einfacher Toast mit „Rückgängig", und DSGVO ist trotzdem gewahrt, weil der Purge-Job nach Frist physisch löscht.

8. **Pagination via `limit`/`offset` statt Cursor** — Cursor-basierte Pagination ist robuster bei vielen Inserts während des Blätterns, aber das passiert hier praktisch nie (Solo-User, History-Liste). `limit`/`offset` ist trivial zu implementieren und für die erwartete History-Größe (< 1.000 Analysen pro User im ersten Jahr) absolut performant.

### Dependencies

**Neu zu installieren:** keine. Die `supabase`-Python-Lib kommt bereits mit PROJ-1 dazu; pg_cron ist eine Postgres-Extension, kein npm- oder pip-Paket.

**Bereits vorhanden, neu genutzt:**
- `get_current_user`-Dependency aus PROJ-1 (für Owner-Auflösung)
- Supabase Postgres (für Tabelle + RLS + pg_cron)

### Migration / Datenbank-Änderungen

Drei Schritte in einer Supabase-Migration:
1. **Tabelle `analyses` anlegen** mit allen Feldern + Indexen.
2. **RLS-Policy** für SELECT/INSERT/UPDATE/DELETE (jeweils `auth.uid() = user_id`).
3. **pg_cron-Extension aktivieren** + täglichen Purge-Job registrieren.

Die Migration kann gleichzeitig mit der PROJ-1-Migration (profiles + Trigger) gefahren werden — beide hängen an `auth.users`, kein Konflikt.

### Risiken & Mitigationen

- **DB-Insert schlägt fehl, Anthropic-Call lief schon durch** — User bekommt Ergebnis mit `analysis_id = null` + Warning. Kein Pipeline-Rollback nötig.
- **pg_cron in Supabase nicht aktiviert** — Bei Setup einmalig im Supabase-Dashboard anschalten. Falls vergessen: Auto-Purge läuft nicht, Soft-Delete-Zeilen sammeln sich an. Monitoring: einfache Query „wie viele Zeilen mit deleted_at?" in einer Health-Page.
- **JSONB-Felder werden sehr groß** (40+ Claims, je mit langem Reasoning) — TOAST komprimiert ab ~2 kB automatisch; im Worst Case landet eine Zeile bei ~50 kB im Storage, kein Performance-Problem.
- **Concurrent Delete + Restore** — Postgres-Transaktionen serialisieren das. Letzter Schreibvorgang gewinnt; in der Praxis nie ein Issue, weil beide Aktionen vom selben User kommen.
- **Migration in Produktion mit bereits laufenden Analysen** — Aktuell läuft die API stateless, es gibt keine bestehenden Analysen, die migriert werden müssten. Greenfield.

### Offene Fragen aus der Spec — beantwortet

- **ARQ vs. pg_cron?** → **pg_cron**, weil 1-SQL-Job, kein Worker-Stack nötig.
- **Zwei JSONB-Spalten vs. ein `result`-Feld?** → **zwei Spalten**, weil konsistent zum Pydantic-Schema und besser für gezielte Indexe.
- **Timezone?** → **UTC** in der DB, Frontend rendert lokal.

### Erweiterung durch PROJ-22 (Multi-Projekt-Workspaces)

Dieses Design bleibt vollständig in Kraft. PROJ-22 fügt einen einzigen Zusatz hinzu:

- Spalte **`project_id`** auf `analyses` (FK auf neue Tabelle `projects`, `NOT NULL` nach Migration). Eine Analyse gehört damit zu genau einem Projekt; der bestehende `user_id`-Foreign-Key bleibt für Audit/Author-Tracking erhalten.
- Der Index `(user_id, created_at DESC) WHERE deleted_at IS NULL` wird ersetzt durch `(project_id, created_at DESC) WHERE deleted_at IS NULL` — die History-Liste filtert primär nach Projekt, nicht nach User.
- Die RLS-Policy erweitert sich: SELECT erlaubt, wenn der User Mitglied des `project_id` ist (vorher: wenn er der `user_id` ist). Schreibrechte abhängig von der Rolle (Editor oder Owner). PROJ-22 dokumentiert die exakten Policies.

**Wichtig:** Die zwei Migrations-Sequenzen (PROJ-21 + PROJ-22) werden zu **einer** zusammengeführt. Es entsteht kein Zwischenzustand, in dem `analyses.project_id` `NULL` ist. Siehe PROJ-22 → „Migration / Datenbank-Änderungen" für die finale neun-stufige Reihenfolge.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
