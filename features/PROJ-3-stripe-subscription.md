# PROJ-3: Stripe-Integration (Subscription)

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-042

## Dependencies
- PROJ-1 (User Authentication)
- PROJ-2 (Plan- & Nutzungs-Verwaltung) — Plan-Tabelle existiert

## User Stories
- Als Free-Nutzer möchte ich mit 2 Klicks auf Pro upgraden, damit ich sofort mehr Analysen bekomme.
- Als zahlender Kunde möchte ich meine Rechnungen herunterladen können, damit ich Buchhaltung machen kann.
- Als Kunde möchte ich meinen Plan jederzeit kündigen können, damit ich keine Abo-Falle fürchte.
- Als Kunde möchte ich mein Zahlungsmittel wechseln können, damit ich nicht durch abgelaufene Karte Service verliere.

## Acceptance Criteria
- [ ] Stripe Checkout für Erst-Abo (monatlich + jährlich mit 20 % Rabatt)
- [ ] Drei Produkte in Stripe: `pro_monthly`, `pro_yearly`, `agency_monthly`, `agency_yearly`
- [ ] Enterprise: „Kontakt aufnehmen"-Flow, kein Self-Service-Checkout
- [ ] Webhook-Handler für: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.paid`
- [ ] Webhook-Signatur wird via Stripe-Signing-Secret verifiziert, ungültige Requests werden abgelehnt
- [ ] Idempotenz: gleiche `event.id` wird nicht doppelt verarbeitet
- [ ] Customer Portal verlinkt (Zahlungsmittel, Rechnungen, Kündigung, Plan-Wechsel)
- [ ] Bei `invoice.payment_failed`: 3-stufiger Retry durch Stripe, bei finalem Fail: Plan auf `free` degradieren + E-Mail
- [ ] DSGVO: AV-Vertrag mit Stripe dokumentiert, Datenweitergabe in Datenschutzerklärung erwähnt
- [ ] Testmode: separate Keys für `dev`/`staging`, Webhook-Endpunkte getrennt

## Edge Cases
- **Nutzer schließt Browser während Checkout:** Stripe zeigt Session als abgebrochen, kein Plan-Wechsel
- **Webhook-Delivery-Verzögerung:** UI zeigt Plan-Wechsel erst nach Webhook-Verarbeitung, Polling auf Erfolgsseite max. 30 s
- **Zahlung erfolgreich, Webhook-Ausfall:** Reconciliation-Job (täglich) gleicht Stripe-Abos mit DB ab
- **User kündigt und registriert sich neu:** neuer Stripe-Customer, alter gespeichert für Audit
- **Plan-Wechsel von jährlich auf monatlich:** Pro-rata-Credit durch Stripe verwaltet
- **Testkarte im Production-Mode:** Stripe lehnt automatisch ab
- **Mehrere aktive Subscriptions für gleichen Customer:** Sollte nicht vorkommen, Hard-Check im Webhook, Alarm bei Mismatch

## Technical Requirements
- Stripe Node/Python SDK (Python im FastAPI-Backend für Webhook-Handling)
- Webhook-Endpunkt: `/api/webhooks/stripe` — raw body für Signatur-Check
- Webhook-Events in Dead-Letter-Queue bei Fehler (Retry 3x, dann Alarm)
- Reconciliation-Cron: täglich 3:00 UTC
- Stripe Restricted Key für Server-Code (kein Secret-Key im Frontend)

## Open Questions
- MwSt.-Handling: Stripe Tax aktivieren? → **Entscheidung: ja, EU-weite VAT-Compliance**
- Trial-Periode (14 Tage Pro kostenlos)? → **MVP: nein, Free-Plan dient als Trial**
- Metered Billing für Enterprise (pay-per-analysis)? → V1.2

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
