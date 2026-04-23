# PROJ-4: EU-Claim-Register-Integration

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-020

## Dependencies
- None (Wissensbasis-Fundament)

## User Stories
- Als System möchte ich alle zugelassenen und abgelehnten Health Claims der EU-Kommission strukturiert indexiert vorhalten, damit die Pipeline sie als Grundlage nutzen kann.
- Als Betreiber möchte ich das Register vierteljährlich aktualisieren können, damit neue Entscheidungen einfließen.
- Als Betreiber möchte ich Update-Fehler protokolliert bekommen, damit Datenqualität verifizierbar ist.

## Acceptance Criteria
- [ ] Parser für offiziellen XML-Export der EU-Kommission (Quelle: ec.europa.eu/food/food-feed-portal/screen/health-claims-register)
- [ ] JSON-Schema je Eintrag: `id`, `claim_de`, `claim_en`, `nutrient`, `conditions`, `status` (authorised / non-authorised / on-hold), `regulation_reference`, `entry_date`, `source_url`
- [ ] Mindestens 2.000 Einträge in DB nach Erstimport
- [ ] Vektor-Indexierung in Qdrant (Embeddings via OpenAI `text-embedding-3-large` ODER jina-v3 — finale Wahl in Architecture)
- [ ] Full-Text-Index in Postgres (`claim_de`, `claim_en`, `nutrient`, `conditions`)
- [ ] Update-Script: `python -m apps.api.scripts.update_eu_register` — idempotent, diff-basiert
- [ ] Update-Run protokolliert: Neu / Geändert / Gelöscht / Fehler als strukturiertes Log
- [ ] Wenn DE-Übersetzung in XML fehlt: Feld bleibt NULL, Retrieval fällt auf EN zurück
- [ ] Quartals-Cron (manuell triggerbar im MVP) läuft ohne Downtime der Produktions-Pipeline

## Edge Cases
- **EU-Register ändert XML-Schema:** Parser schlägt fehl, Alarm per E-Mail, alte Daten bleiben aktiv (kein Overwrite bei Parse-Error)
- **Eintrag wird von `on-hold` auf `non-authorised` geändert:** Historie bleibt in DB erhalten (`valid_from`/`valid_to`), Retrieval nutzt aktiven Stand
- **Doppelte IDs im XML:** letzte Version gewinnt, Warnung loggen
- **Partieller Download (Netzwerk-Abbruch):** Kein partielles Überschreiben, Transaktion-Rollback
- **Fehlende Pflichtfelder (`claim_de` & `claim_en` beide NULL):** Eintrag wird übersprungen, Alarm
- **Embedding-Provider-Ausfall während Update:** Postgres-Import läuft weiter, Vektor-Index-Update wird retried

## Technical Requirements
- XML-Parser: `lxml` (Python)
- Qdrant-Collection: `eu_claims`, Dim passend zu Embedding-Modell
- Postgres-Tabelle: `eu_claims` mit GIN-Index auf `to_tsvector('german', claim_de || ' ' || nutrient)`
- Batch-Embedding (100 Stück pro API-Call) für Kosten/Performance
- Versionierung der Wissensbasis: `kb_version` in Metadaten jedes Chunks

## Open Questions
- Embedding-Modell finale Wahl: OpenAI (US, bessere DE-Qualität) vs. jina-v3 (EU, Self-Host) → **Entscheidung in /architecture PROJ-9**
- EU-Register liefert EN-primär, DE-Übersetzungen teilweise lückenhaft — manuell nachpflegen? → **MVP: nein, EN-Fallback im Retrieval**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
