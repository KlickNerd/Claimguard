# PROJ-6: Urteilsdatenbank (30 Fälle)

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-022

## Dependencies
- None (Wissensbasis-Fundament)

## User Stories
- Als System möchte ich relevante deutsche Gerichtsentscheidungen zu Health Claims strukturiert abrufen, damit die Pipeline Präzedenzfälle berücksichtigt.
- Als Betreiber möchte ich Urteile einfach pflegen können, damit die Wissensbasis aktuell bleibt.
- Als Nutzer möchte ich die Quelle eines Urteils im Report sehen, damit ich sie selbst nachlesen kann.

## Acceptance Criteria
- [ ] JSON-Schema je Urteil: `id`, `court` (z.B. „OLG Hamburg"), `case_number`, `date` (ISO), `claim_type` (enum), `decision` (allowed/forbidden/borderline), `reasoning_paraphrased` (DE, eigene Formulierung), `source_url`, `tags` (Liste), `created_by`, `created_at`
- [ ] Mindestens 30 Urteile beim MVP-Launch
- [ ] **Rechtliche Anforderung: nur Paraphrasen, keine Volltext-Übernahme** aus juris / beck-online (Urheberrecht)
- [ ] Admin-UI (separate Route `/admin/cases`, RBAC: `role = 'admin'`) mit CRUD-Funktionen
- [ ] Admin-UI ist nicht öffentlich zugänglich (robots.txt blockiert, keine Links von Public-UI)
- [ ] Vektor-Index in Qdrant (`case_law`)
- [ ] Full-Text-Index in Postgres
- [ ] Audit-Log aller Änderungen (wer, wann, was)
- [ ] Preview-Funktion: Admin sieht vor Publish, wie das Urteil im Retrieval-Output aussieht
- [ ] Export als JSON-Backup (manuell triggerbar)

## Edge Cases
- **Urteil wird in Revision aufgehoben:** Eintrag wird auf `status: overruled` gesetzt, bleibt in DB, Retrieval filtert es aus
- **Doppelter Eintrag (gleiches Aktenzeichen):** UI verhindert Speichern, Update-Flow stattdessen
- **Quelle wird offline (404):** Urteil bleibt in DB, Admin wird per Weekly-Job gewarnt
- **Paraphrase zu nah am Original (Plagiat-Risiko):** Redaktionelle Regel: keine wörtlichen Zitate > 10 Wörter
- **Urteil-Datum unvollständig (nur Jahr bekannt):** Erlaubt, Sortierung nach Jahr
- **Admin löscht aus Versehen Urteil:** Soft-Delete (`deleted_at`), Wiederherstellung in 30 Tagen möglich

## Technical Requirements
- Admin-UI als Next.js Route mit Role-Check (Supabase RLS + Middleware)
- Tabelle `case_law` in Supabase Postgres
- Rich-Text-Editor für `reasoning_paraphrased` (Tiptap oder Markdown-Editor)
- Tag-Input mit Autocomplete (vorhandene Tags + neue erlaubt)
- Vektor-Indexierung getriggert bei Publish, nicht bei Draft

## Open Questions
- Welche Gerichte priorisieren? → **MVP: BGH, OLG-Ebene, relevante LG. Kein AG außer Landmark-Fälle**
- Externe Autoren (Anwälte) sollen pflegen können? → V1.1, MVP nur Dominik als Admin
- Lizenzmodell für Inhalte später (CC-BY-NC)? → V1.1

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
