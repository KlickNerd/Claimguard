# PROJ-6: Urteilsdatenbank (30 Fälle)

## Status: In Progress
**Created:** 2026-04-23
**Last Updated:** 2026-05-01
**Backlog-Referenz:** F-022

## Implementation Notes (2026-05-01)

**Was umgesetzt ist (MVP-Stand):**
- Pydantic-Schema [`schemas/case_law.py`](../apps/api/app/schemas/case_law.py)
  mit `CaseLawEntry` (id, court, case_number, decision_date, title, claim_type,
  decision, summary, legal_basis, tags, source_url) und Wrapper `CaseLawDataset`.
- JSON-Seed-Datei [`data/case_law.json`](../apps/api/data/case_law.json) mit
  **12 Landmark-Entscheidungen** als redaktionelle Paraphrasen — keine
  Volltext-Übernahme aus juris/beck-online (Urheberrecht). Inhaltsspektrum:
  Detox-Slogans (BGH/OLG Düsseldorf), Monsterbacke I+II, Vitalpilze,
  Bach-Blüten, Innova Vital (EuGH), Präbiotik/Probiotik, Immunsystem-
  Werbung (OLG Frankfurt), Schlankheits-Versprechen (OLG Hamburg),
  Arzt-Empfehlung (OLG Köln), Markenname-Therapie.
- [`scripts/index_knowledge_base.py`](../apps/api/scripts/index_knowledge_base.py)
  erweitert: dritte Qdrant-Collection `case_law` (12 Punkte) wird neben
  `eu_claims` und `regulation` indexiert. Embedding-Input = Title + Summary
  + Tags, sodass thematische Treffer auch ohne wörtliche Aktenzeichen-
  Übereinstimmung greifen.
- [`retrieval_service.py`](../apps/api/app/services/retrieval_service.py)
  durchsucht `case_law` jetzt parallel mit den anderen beiden Quellen via
  RRF.
- Smoke-Test 2026-05-01 mit Detox-/Reinigung-/Immunsystem-/Milch-Claims:
  Alle vier Claims bekommen verifizierte case_law-Hits, z. B.
  `bgh-i-zr-167-13-monsterbacke` für „So wichtig wie das tägliche Glas Milch"
  und `olg-frankfurt-6-u-184-19-immunabwehr` für „stärkt das Immunsystem".
  Opus zitiert ausschließlich aus dem Evidence-Pool — keine halluzinierten
  Aktenzeichen mehr.

**Bewusst nicht im MVP, aber als Folgetasks offen:**
- **Nur 12 Urteile statt 30** (Spec-Acceptance). Die 12 sind aber alle
  Landmark-Cases mit hoher praktischer Bedeutung. Jeder weitere Eintrag
  braucht eine handgeschriebene Paraphrase + verifiziertes Aktenzeichen,
  weshalb der „30 Fälle"-Anspruch ein redaktionelles, kein Code-Thema ist.
- **Kein Admin-CRUD-UI** (Spec-Acceptance). MVP pflegt das JSON direkt im
  Repo — sobald Dominik regelmäßig Urteile ergänzen will, kommt eine
  separate Route `/admin/cases` mit Supabase-RLS (hängt an PROJ-1 Auth).
- **Kein Audit-Log / Soft-Delete / overruled-Filter.** Die 12 Urteile sind
  alle in Kraft; Filterung kommt erst, wenn die Liste wächst.
- **Kein Postgres-FTS-Index** auf case_law (war im Spec für die hybrid-
  Retrieval-Variante in PROJ-9 vorgesehen, dort aktuell auch nicht).
- **Verifikation der Aktenzeichen.** Die Seed-Paraphrasen stammen aus
  belastbarem Trainingswissen, aber jeder Eintrag muss vor produktiver
  Nutzung gegen die `source_url` gegengeprüft werden.

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
