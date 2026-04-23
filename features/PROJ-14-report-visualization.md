# PROJ-14: Analyse-Report-Darstellung

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-013

## Dependencies
- PROJ-10 (Claim-Evaluation) — liefert Bewertungsdaten
- PROJ-11 (Text-Input) — Analyse-Objekt existiert

## User Stories
- Als Nutzer möchte ich auf einen Blick sehen, wie compliant mein Text ist, damit ich schnell einschätzen kann.
- Als Nutzer möchte ich einen problematischen Claim direkt im Originaltext finden, damit ich Kontext habe.
- Als Nutzer möchte ich eine detaillierte Begründung mit Quellen lesen können, damit ich die Bewertung verstehe.
- Als Nutzer möchte ich eine Reformulierung mit einem Klick übernehmen können, damit ich schnell handeln kann.
- Als Nutzer möchte ich an jedem Report erinnert werden, dass ClaimGuard keine Rechtsberatung ist, damit ich Erwartungen richtig kalibriere.

## Acceptance Criteria
- [ ] Route `/analyze/{id}` zeigt kompletten Report
- [ ] **Zwei-Spalten-Layout:** links Originaltext mit farbigen Inline-Markierungen pro Claim, rechts Detail-Panel
- [ ] Ampel-Farbcodierung:
  - Grün (`allowed`), Gelb (`borderline`), Rot (`forbidden`), Grau (`unclear`)
- [ ] Zusammenfassung oben (Sticky): **Compliance-Score** (0–100), Anzahl pro Status, Risiko-Score
- [ ] Compliance-Score-Formel dokumentiert: `100 - (forbidden * 20 + borderline * 10 + unclear * 5)`, floor bei 0
- [ ] Klick auf Claim-Markierung → Detail-Panel öffnet mit:
  - Claim-Text (kopierbar)
  - Status-Pill + Risiko-Pill
  - Rechtsgrundlagen (ein-/ausklappbar, mit Deep-Link zur Quelle)
  - Begründung (2–5 Sätze, DE)
  - Reformulierungsvorschlag mit „Kopieren"-Button
  - Confidence-Anzeige als Balken
- [ ] **Haftungs-Disclaimer** sichtbar am Anfang und Ende des Reports: „Diese Analyse ist kein Ersatz für Rechtsberatung. ClaimGuard haftet nicht für geschäftliche Entscheidungen auf Basis dieser Auswertung."
- [ ] Export-Button (PDF, siehe PROJ-15) oben rechts
- [ ] Share-Link (read-only, tokenisiert, optional mit Ablauf 7 Tage) — **V1.1, nicht MVP**
- [ ] Mobile-responsive: Single-Column auf < 768px, Detail-Panel als Modal
- [ ] Barrierefrei: Tastaturnavigation, Screenreader-Labels für Farben („Status verboten" statt nur rot)

## Edge Cases
- **Analyse mit 0 Claims:** Report zeigt Text ohne Markierungen, Meldung „Keine gesundheitsbezogenen Aussagen gefunden", Score 100
- **Analyse mit > 50 Claims:** Virtualisierte Liste im Detail-Panel, Performance-Check < 500ms Rendering
- **Analyse noch `status = running`:** Route zeigt Progress-View (siehe PROJ-11), kein Report
- **Analyse `status = failed`:** Fehler-View mit Meldung + „Credit wurde zurückerstattet"
- **Claim-Position inkorrekt (Text wurde nach Analyse editiert — nicht möglich im MVP):** Fallback: Claim unmarkiert gelistet
- **Überlappende Claim-Markierungen:** nested Spans, hover zeigt äußerste; Klick öffnet Panel für geklickte
- **Sehr langer Text (> 10.000 Zeichen):** Sektion-Navigation (Sprungmarken zu den Claims)
- **Rewrite-Vorschlag fehlt (z.B. bei `allowed`):** Sektion ausgeblendet
- **User ruft Report eines anderen Users auf:** 403 (Supabase RLS)

## Technical Requirements
- Komponente in Next.js (shadcn/ui: Card, Badge, Collapsible, Separator, ScrollArea)
- Inline-Markierung via `<mark>` mit Data-Attributen, Highlight-Logik clientseitig
- Compliance-Score als visuelle Komponente (Ring oder Balken)
- Print-Stylesheet für Browser-Print (basic PDF-Fallback ohne PROJ-15)
- WCAG 2.1 AA: Kontrast min. 4.5:1, Markierungen nicht nur durch Farbe unterscheidbar (Icon + Farbe)

## Open Questions
- Animierte Intro-Tour beim ersten Report? → V1.1
- Diff-View zwischen zwei Analysen (alt / neu)? → V1.2
- Kommentare / Annotationen pro Claim (für Team)? → V1.1 (Multi-User)

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
