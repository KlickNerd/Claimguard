# PROJ-2: Plan- & Nutzungs-Verwaltung

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-041

## Dependencies
- PROJ-1 (User Authentication) — User muss eingeloggt sein
- PROJ-3 (Stripe-Integration) — für Upgrade-Flow, aber Plan-Tabelle existiert vorher

## User Stories
- Als Free-Nutzer möchte ich sehen, wie viele Analysen ich diesen Monat noch habe, damit ich planen kann.
- Als Pro-Nutzer möchte ich bei 90 % Auslastung gewarnt werden, damit ich rechtzeitig upgraden kann.
- Als Nutzer bei 100 % Limit möchte ich klar verstehen, wie ich upgraden kann, damit ich sofort weiterarbeiten kann.
- Als Admin möchte ich Usage-Daten pro Nutzer einsehen, damit ich Missbrauch erkenne.

## Acceptance Criteria
- [ ] Plan-Tabelle in Supabase: `free` (5/Monat), `pro` (100/Monat), `agency` (500/Monat), `enterprise` (unlimitiert)
- [ ] `monthly_usage_reset_at` pro User, reset am Abrechnungstag (Free: 1. des Monats)
- [ ] Counter wird atomar inkrementiert beim Start einer Analyse (nicht bei Abschluss), fehlgeschlagene Analysen werden zurückgebucht
- [ ] Bei 90 % Auslastung: persistenter Banner im Dashboard mit Upgrade-CTA
- [ ] Bei 100 %: Analyse-Button deaktiviert, Modal mit Upgrade-Optionen
- [ ] Usage-Historie der letzten 12 Monate pro User in der Datenbank (für Abrechnungs-Disputes)
- [ ] Admin-View (separate Route mit Role-Check) zeigt Usage pro User, sortierbar
- [ ] API-Endpunkt `/api/usage/current` gibt zurück: `{used, limit, reset_at, plan}`

## Edge Cases
- **Analyse läuft bei Monatswechsel:** Credit wird im Monat der Analyse-Erstellung abgerechnet, nicht bei Abschluss
- **Plan-Upgrade mitten im Monat:** Neues Limit sofort aktiv, kein Pro-rata-Rollback
- **Plan-Downgrade:** Wirksam am nächsten Abrechnungstag (vermeidet Credit-Verlust)
- **Fehlgeschlagene Analyse (z.B. LLM-Outage):** Credit wird automatisch zurückgebucht, Logeintrag
- **Nutzer erreicht Limit während laufender Analyse:** Aktuelle Analyse läuft zu Ende, nächste blockiert
- **Race-Condition bei paralleler Analyse am Limit:** Atomare DB-Operation (`UPDATE ... WHERE used < limit RETURNING`), zweite Analyse wird abgelehnt
- **Enterprise-Plan ohne Limit:** `limit` = NULL, UI zeigt „unlimitiert"

## Technical Requirements
- Supabase: `user_plans` Tabelle + Row-Level-Security
- `usage_events` Tabelle mit `event_type` (siehe Datenmodell im Backlog)
- Atomare Counter via Postgres-Funktion oder `UPDATE ... RETURNING`
- Banner/Modal-Komponente in Next.js, via React Context global verfügbar

## Open Questions
- Soll Free-Plan befristet sein (14 Tage Trial) oder permanent limitiert? → **Default: permanent limitiert, 5/Monat**
- Credit-Rollover bei ungenutzten Credits? → **Default: nein, reset hart**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
