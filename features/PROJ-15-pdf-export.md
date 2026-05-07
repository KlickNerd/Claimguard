# PROJ-15: PDF-Export des Reports

## Status: In Progress
**Created:** 2026-04-23
**Last Updated:** 2026-05-01
**Backlog-Referenz:** F-014

## Implementation Notes (2026-05-01)

**Was umgesetzt ist (MVP-Stand):**
- Client-side Print-Pipeline statt server-Playwright. Begründung unten.
- Globale Print-Styles in [`globals.css`](../apps/web/src/app/globals.css)
  (`@media print`): A4 mit 18 mm × 14 mm Margin, Hide aller `nav`/`aside`/
  `button`/`[data-print="hide"]`, Force-Block für `[data-print="report"]`,
  `break-inside: avoid` pro Claim-Card, Disclaimer-Block prominent oberhalb
  der Cards, Anchor-URLs werden nach dem Linktext mit ausgegeben.
- Der Report-Container im DoneState ([`apps/web/src/app/app/page.tsx`](../apps/web/src/app/app/page.tsx))
  trägt `data-print="report"`; ein extra Disclaimer-Block mit
  `data-print="disclaimer"` ist im Screen-Mode versteckt und nur im
  Print-Mode sichtbar.
- Im Report-Header sitzt jetzt ein „Als PDF speichern"-Button. Klick setzt
  temporär `document.title` auf `ClaimGuard-Report-{id8}-{YYYY-MM-DD}` (das
  ist in Chrome/Safari/Firefox der Default-Filename im Print-Dialog) und
  ruft `window.print()` auf.
- Header trägt ID, Erstellungsdatum (lokalisiert) und `source_reference` der
  Analyse — entspricht den Deckblatt-Anforderungen aus der Spec.

**Bewusst nicht im MVP (Abweichungen vom Spec):**
- **Kein server-side Playwright/WeasyPrint.** Spec sieht Playwright vor,
  aber die client-Print-Pipeline reicht für den 1-User-pro-Browser-MVP
  und spart einen weiteren Long-Running-Service auf dem VPS. Server-Side
  wird in V1.1 nötig, wenn wir Reports per E-Mail / API-Call versenden
  oder White-Label-Branding einbauen. Bis dahin ist der Browser-PDF
  konsistent (gleicher Renderer wie die Web-View) und kostet nichts.
- Kein S3-PDF-Cache (24 h) — kommt mit V1.1 server-side.
- Keine Rate-Limit-Logik im Frontend (MVP-Standard: Browser limitiert sich
  selbst, weil der User im Print-Dialog steht).
- Kein dediziertes Deckblatt mit Logo — ergibt sich aus dem Header-Block
  und dem Print-Disclaimer; Logo-Embedding folgt mit Print-Branding-Polish
  in PROJ-18-Update.
- Kein Truncation auf 100 Claims — wir verlassen uns auf
  `break-inside: avoid` und das Browser-Pagination, bis Reports tatsächlich
  > 50 Seiten produzieren.

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
