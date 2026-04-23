# PROJ-17: DSGVO-Konformität

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-060

## Dependencies
- Querschnittsfeature — impliziert bei allen anderen Features, aber eigenständig testbar über Rechtstexte, Cookie-Banner, Export/Delete-Flows

## User Stories
- Als EU-Nutzer möchte ich sehen, welche Daten über mich gespeichert werden, damit ich DSGVO-Rechte wahrnehmen kann.
- Als EU-Nutzer möchte ich meinen Account mit allen Daten löschen können, damit ich das Recht auf Vergessen nutzen kann.
- Als EU-Nutzer möchte ich meine Daten exportieren können, damit ich sie zu einem anderen Dienst mitnehmen kann (Art. 20).
- Als Seitenbesucher möchte ich Cookies granular steuern, damit ich nur notwendige zulasse.
- Als Betreiber möchte ich AV-Verträge mit allen Subunternehmern dokumentiert haben, damit ich auditfest bin.

## Acceptance Criteria
- [ ] **Datenschutzerklärung** (`/datenschutz`): anwaltlich geprüft, listet alle Subunternehmer (Supabase EU, Stripe, Anthropic, Hostinger) mit Zweck und Rechtsgrundlage
- [ ] **AGB** (`/agb`): anwaltlich geprüft, enthält Haftungsausschluss „keine Rechtsberatung"
- [ ] **Impressum** (`/impressum`): vollständig nach §5 TMG
- [ ] **Cookie-Banner** (via `cookiebot` / `klaro` / Eigenbau):
  - Granular: Funktional (immer on), Analytics (opt-in), Marketing (opt-in)
  - Ablehnung gleich einfach wie Zustimmung (TTDSG konform)
  - Consent-Log serverseitig mit Timestamp + IP-Hash
- [ ] **Datenexport** (`/settings/data`): User lädt JSON mit allen personenbezogenen Daten + Analysen herunter
  - Enthält: Profil, Analysen (Input-Text + Output), Usage-Events, Billing-Metadaten
  - Generierung asynchron (bei großem Volume), E-Mail-Benachrichtigung wenn fertig
- [ ] **Account-Löschung** (`/settings/delete`): 2-stufig (Bestätigung + E-Mail-Link)
  - Soft-Delete sofort (Login gesperrt)
  - Hard-Delete nach 30 Tagen (alle personenbezogenen Daten + Analysen + Stripe-Beziehung)
  - Ausnahme: Rechnungen bleiben gemäß §147 AO (10 Jahre), pseudonymisiert
- [ ] **Zero-Data-Retention** bei Anthropic: Header `anthropic-beta: zdr-2024-06-01` auf allen Pipeline-Calls
- [ ] **Alle Server + DBs in EU:** Supabase-Projekt in EU-Region (Frankfurt), Hostinger-VPS Frankfurt, Qdrant auf VPS, kein CDN für personenbezogene Inhalte außerhalb EU
- [ ] **AV-Verträge** dokumentiert in `docs/compliance/` (nicht öffentlich):
  - Supabase DPA unterzeichnet
  - Stripe DPA unterzeichnet
  - Anthropic DPA unterzeichnet
  - OpenAI / jina DPA je nach Embedding-Entscheidung (PROJ-4)
- [ ] **TOMs** (technisch-organisatorische Maßnahmen) als eigenes Dokument verfasst
- [ ] **Datenpannen-Prozess** dokumentiert: Meldung an BfDI innerhalb 72h
- [ ] **Aufbewahrungsfristen** je Datentyp in Datenschutzerklärung aufgeführt

## Edge Cases
- **User fragt Export an, Analysen noch `running`:** Export enthält Analyse-Liste mit Status, Input-Text, aber noch kein Output — Erklärung im Export-JSON
- **Account-Löschung während laufender Analyse:** Analyse wird abgebrochen, Credit zurückgebucht, Soft-Delete greift
- **User hat aktives Abo bei Löschung:** Stripe-Subscription wird gekündigt, Rest-Zahlung abgerechnet
- **Export zu groß (> 100 MB):** ZIP-Streaming, Download-Link gültig 7 Tage
- **Subunternehmer-Wechsel:** Datenschutzerklärung wird aktualisiert, Änderungs-Benachrichtigung per E-Mail + UI-Banner
- **Rechtswidrige Daten im Input (User paste Dritt-Daten):** Nutzer hat Verantwortung (in AGB), ClaimGuard speichert nicht mehr als nötig, Analysen können vom User sofort gelöscht werden
- **Minderjährige (< 16):** Registrierung verboten, Altersabfrage bei Signup, AGB-Hinweis
- **Datenexport im „Portabilitäts-Format":** JSON + menschenlesbares PDF-Summary
- **Consent-Widerruf nach Analyse:** Cookies werden entfernt, bestehende Analysen bleiben (nicht vom Consent abhängig)

## Technical Requirements
- Rechtstexte in Next.js als MDX-Seiten unter `src/app/(legal)/`
- Cookie-Banner-Library: `klaro` (self-hostbar, DSGVO-konform) oder Eigenbau mit `js-cookie`
- Consent-Log-Endpunkt: `POST /api/consent`, Log in Supabase
- Datenexport-Queue (asynchron, gleicher Worker wie Analyse-Pipeline)
- Delete-Job: scheduled 2:00 UTC täglich, löscht alle Accounts mit `deleted_at < NOW() - 30 days`
- RLS-Policies auf allen Tabellen: User sieht nur eigene Daten
- Audit-Log für admin-initiierte Datenoperationen

## Open Questions
- **Datenschutzbeauftragter (DSB) nötig?** Abhängig von Mitarbeiteranzahl und Datenverarbeitungs-Umfang. → Solo-Founder: aktuell nein, aber bei > 20 MA oder Verarbeitung besonderer Daten (Gesundheitsdaten!): Prüfung durch Anwalt
- **Ist die LLM-Eingabe von User-Texten „Datenverarbeitung im Auftrag"?** → Ja, mit Anthropic als AV. Zero-Data-Retention notwendig
- **Eval-Set aus echten User-Texten trainieren?** → **Nein**, nur synthetische / konsentierte Daten, keine PII
- **Recht auf Auskunft (Art. 15) Self-Service oder per E-Mail?** → **MVP: per E-Mail an `datenschutz@claimguard.de`, V1.1 Self-Service**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
