# PROJ-15: PDF-Export des Reports

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-014

## Dependencies
- PROJ-14 (Report-Darstellung) — Quelle der Daten

## User Stories
- Als Nutzer möchte ich meinen Report als PDF exportieren, damit ich ihn per E-Mail an Kollegen / Anwälte weitergeben kann.
- Als Agentur möchte ich den Report im ClaimGuard-Design exportieren, damit er professionell aussieht.
- Als Nutzer möchte ich, dass der Disclaimer im PDF prominent zu sehen ist, damit Empfänger Erwartungen richtig einordnen.

## Acceptance Criteria
- [ ] Export-Button im Report (`/analyze/{id}`) generiert PDF-Download
- [ ] Generierung serverseitig via **Playwright** (HTML → PDF, konsistent mit UI)
- [ ] PDF-Inhalt:
  - Deckblatt: Titel, Analyse-ID, Datum, Quelle (Filename/URL)
  - Zusammenfassung: Compliance-Score, Verteilung nach Status
  - Originaltext mit Markierungen (farbig + Icon)
  - Claim-Liste mit Details (Status, Rechtsgrundlage, Begründung, Reformulierung)
  - **Haftungs-Disclaimer** auf Deckblatt UND Footer
  - Footer: Seitenzahl, ClaimGuard-Logo, Datum
- [ ] Layout im ClaimGuard-Design (Corporate Identity aus Figma/Lovable)
- [ ] Generierung < 5 Sekunden für typischen Report
- [ ] Dateiname: `ClaimGuard-Report-{analysis_id_short}-{YYYY-MM-DD}.pdf`
- [ ] DIN A4, Druck-optimiert (bw-freundliche Icons, ausreichender Kontrast)
- [ ] Strg+F im PDF findet Text (echter Text, kein Bild)

## Edge Cases
- **Sehr langer Report (100+ Claims):** Tabellarische Darstellung statt einzelner Cards, max 50 Seiten, bei Überlauf Meldung „Report gekürzt auf die 100 wichtigsten Claims"
- **Report in `running`-Status:** Export-Button disabled
- **Report failed:** Export-Button disabled
- **Emoji / Unicode im Text:** Font-Embedding korrekt (Inter oder System-Font)
- **Markierung an Seitenumbruch:** CSS `break-inside: avoid` pro Claim-Card
- **Playwright-Prozess hängt:** Timeout 30 s, Fehlermeldung
- **User exportiert mehrfach kurz hintereinander:** Rate-Limit 10 Exporte / Minute pro User
- **PDF wird via CLI generiert (Storybook):** dito, nur Dev-Use

## Technical Requirements
- Playwright (Python) mit Chromium
- Print-Stylesheet `@media print` in Next.js
- Render-URL: Backend ruft `/analyze/{id}/print-view` (ohne Nav, mit Auth-Token)
- Temporäre PDF-Datei in RAM, kein Disk-Persist
- S3-kompatibler Bucket (optional): generierte PDFs können 24h gecached werden (kostensparend bei Wiederholungs-Download)

## Open Questions
- Alternative: `WeasyPrint` (leichter, Python-nativ, aber weniger CSS-Support). → **Entscheidung in /architecture** (Empfehlung: Playwright wegen Konsistenz mit UI)
- White-Label (Agency-Kundenlogo)? → V1.2 (F-203)
- Digitale Signatur (PAdES) für Rechtssicherheit? → V2
- DOCX-Export zusätzlich? → V2

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
