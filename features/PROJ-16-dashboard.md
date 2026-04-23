# PROJ-16: Dashboard

## Status: In Progress
**Implementierungsstand:** App-Shell (`AppSidebar` mit Workspace-Card + Plan-Widget, `AppHeader` mit Search/Notifications/Avatar) und Neue-Prüfung-Screen mit KPI-Strip live unter `/app`. Verlauf-Tabelle unter `/app/history` mit AmpelBar. Team-Screen als V1.1-Placeholder, Settings als Stub. Backend-Anbindung folgt nach PROJ-1/PROJ-2.
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-050

## Dependencies
- PROJ-1 (User Authentication)
- PROJ-2 (Plan & Usage)
- PROJ-14 (Report) — für letzte Analysen
- PROJ-6 (Urteilsdatenbank) — für Urteils-Timeline

## User Stories
- Als Nutzer möchte ich nach Login einen schnellen Überblick über meine Nutzung haben, damit ich den Kontext wiederfinde.
- Als Nutzer möchte ich mit einem Klick eine neue Analyse starten, damit Häufigkeits-Use-Cases schnell gehen.
- Als Nutzer möchte ich aktuelle Urteile sehen, damit ich über Rechtsprechung informiert bleibe (Content-Marketing-Effekt).
- Als Nutzer möchte ich meine letzten Analysen sehen und weiterbearbeiten können, damit ich nichts verliere.

## Acceptance Criteria
- [ ] Route `/dashboard` ist Standard-Redirect nach Login
- [ ] **KPI-Strip oben** (4 Cards):
  - Analysen diesen Monat (x / Limit)
  - Durchschnittlicher Compliance-Score (letzte 30 Tage)
  - Offene „borderline"/„unclear" Items (rot-markiert, clickable)
  - Verbleibende Credits (mit Upgrade-CTA wenn < 20 %)
- [ ] **Quick-Action-Panel**: 3 Buttons (Text analysieren / PDF hochladen / URL prüfen) → öffnet `/analyze/new` mit passendem Tab
- [ ] **Letzte-Analysen-Tabelle** (10 Zeilen): Titel/Quelle, Datum, Score, Status, Action „Öffnen"/„Löschen"
- [ ] **Urteils-Timeline** (rechts, sticky oder unten auf Mobile): letzte 5 aktualisierte Urteile aus PROJ-6, jeweils Gericht + Datum + Tags, Link zum Detail
- [ ] **Workspace-Row** (noch nicht funktional im MVP, nur Platzhalter „Ein Workspace" — Multi-Workspace ist V1.1/F-104)
- [ ] Ladezeit p95 ≤ 1,5 s (initial, ohne Bilder)
- [ ] Responsive: Single-Column auf < 768px, Stack-Reihenfolge: KPIs → Quick-Actions → Analysen → Urteile
- [ ] Empty State für Neu-Nutzer: „Starte deine erste Analyse" mit hervorgehobenem CTA

## Edge Cases
- **Noch keine Analysen:** Empty-State mit Beispiel-Input („Probiere ‚Vitamin C stärkt das Immunsystem'") — optionale geführte Sample-Analyse
- **Free-User ohne Credits:** KPI „Analysen" zeigt 0 / 5, Upgrade-Banner persistent
- **Mehr als 100 Analysen:** Paginierung in Tabelle, nur letzte 10 auf Dashboard, „Alle anzeigen" → eigene Route `/analyses`
- **Urteils-Timeline leer (KB noch nicht gefüllt):** Platzhalter „Urteils-DB wird gerade aufgebaut"
- **User mit abgelaufenem Abo (payment_failed):** Banner „Zahlung fehlgeschlagen — bitte aktualisieren"
- **Analyse gerade laufend:** Zeile mit Spinner, Polling, klickbar zu Progress-View

## Technical Requirements
- Server-Components in Next.js für KPI-Aggregation
- Caching: KPIs 60 s (via `revalidate`), Tabelle live
- Urteils-Timeline als separate Query (lightweight, kein RAG)
- Lovable-Design-Spec als Ausgangspunkt (siehe Backlog F-050)

## Open Questions
- Analytics-Widget (Chart.js) mit Score-Verlauf? → **MVP: nein, V1.1**
- Notifications-Center (Klingel-Icon) für Limits/Payments? → **MVP: nein, V1.1**
- Onboarding-Checklist („Verifiziere E-Mail", „Starte erste Analyse", „Lade Team ein")? → V1.1

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
