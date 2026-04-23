# PROJ-5: HCVO-Verordnungstext-Integration

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-021

## Dependencies
- None (Wissensbasis-Fundament)

## User Stories
- Als System möchte ich den vollständigen Verordnungstext der HCVO (VO 1924/2006) und VO 432/2012 strukturiert abrufen können, damit die Pipeline rechtliche Grundlagen zitieren kann.
- Als Nutzer möchte ich im Report den exakten Artikel + Absatz sehen, damit ich die Bewertung nachvollziehen kann.

## Acceptance Criteria
- [ ] Chunking nach Artikel und Absatz (nicht nach Tokenzahl) — semantische Einheiten bleiben erhalten
- [ ] Metadaten je Chunk: `regulation_id` (`1924/2006` oder `432/2012`), `article`, `paragraph`, `subparagraph` (optional), `language` (DE), `eur_lex_url`
- [ ] Quelle: Eur-Lex XML- oder HTML-Export, offizielle DE-Fassung
- [ ] Vektor-Index in Qdrant (`regulation_chunks`)
- [ ] Full-Text-Index in Postgres
- [ ] Deep-Link auf Eur-Lex pro Chunk (Artikel-Anker)
- [ ] Fußnoten und Querverweise werden als eigenes Metadatenfeld `cross_references` gespeichert
- [ ] Update manuell triggerbar, historisch konsolidierte Fassung bevorzugt (nicht Originalfassung 2006)

## Edge Cases
- **Eur-Lex ändert URL-Struktur:** Parser-Konfiguration zentral, Alarm bei Parse-Error
- **Konsolidierte Fassung wird aktualisiert:** Versions-Timestamp in Metadaten, alte Version deprecated aber in DB gehalten für Reproduzierbarkeit alter Reports
- **Artikel mit Anhang (z.B. Anhang zu VO 432/2012 mit Claim-Liste):** Anhang als eigene Chunks mit `is_annex: true`
- **Mischsprache in Quelle (Verweise auf EN-Dokumente):** nicht im MVP, nur DE-Text indexieren
- **Leere Absätze oder Streichungen:** skippen, Lücke in `paragraph`-Nummerierung zulässig

## Technical Requirements
- Parser: `lxml` oder `BeautifulSoup4` je nach Eur-Lex-Format
- Chunk-Size variabel (kann 50–1500 Zeichen sein, semantisch)
- Embedding + Postgres analog zu PROJ-4
- Konsolidierte Fassung: z.B. `eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:02006R1924-20141213`

## Open Questions
- Sollen deutsche Ausführungsgesetze (z.B. LFGB) mit rein? → **MVP: nein, nur EU-Verordnungen. LFGB ggf. V1.1 bei Nachfrage**
- BfR-Leitlinien zu Botanicals einbinden? → **MVP: nein**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
