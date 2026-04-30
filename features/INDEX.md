# Feature Index

> Central tracking for all features. Updated by skills automatically.

## Status Legend
- **Planned** - `/requirements` done, spec written, architecture not yet designed
- **Architected** - `/architecture` done, tech design approved, ready to build
- **In Progress** - `/frontend` or `/backend` active or completed, not yet in QA
- **In Review** - `/qa` active, testing in progress
- **Approved** - `/qa` passed, no critical/high bugs, ready to deploy
- **Deployed** - `/deploy` done, live in production

## Features

| ID | Feature | Status | Spec | Created |
|----|---------|--------|------|---------|
| PROJ-1 | User Authentication | Planned | [PROJ-1](PROJ-1-user-authentication.md) | 2026-04-23 |
| PROJ-2 | Plan- & Nutzungs-Verwaltung | Planned | [PROJ-2](PROJ-2-plan-usage-management.md) | 2026-04-23 |
| PROJ-3 | Stripe-Integration (Subscription) | Planned | [PROJ-3](PROJ-3-stripe-subscription.md) | 2026-04-23 |
| PROJ-4 | EU-Claim-Register-Integration | In Progress | [PROJ-4](PROJ-4-eu-claim-register.md) | 2026-04-23 |
| PROJ-5 | HCVO-Verordnungstext-Integration | Planned | [PROJ-5](PROJ-5-hcvo-regulation.md) | 2026-04-23 |
| PROJ-6 | Urteilsdatenbank (30 Fälle) | Planned | [PROJ-6](PROJ-6-case-law-database.md) | 2026-04-23 |
| PROJ-7 | Prompt-Management | In Progress | [PROJ-7](PROJ-7-prompt-management.md) | 2026-04-23 |
| PROJ-8 | Claim-Detection | In Progress | [PROJ-8](PROJ-8-claim-detection.md) | 2026-04-23 |
| PROJ-9 | Hybrid Retrieval | Architected | [PROJ-9](PROJ-9-hybrid-retrieval.md) | 2026-04-23 |
| PROJ-10 | Claim-Evaluation | Architected | [PROJ-10](PROJ-10-claim-evaluation.md) | 2026-04-23 |
| PROJ-11 | Text-Input-Analyse | In Progress | [PROJ-11](PROJ-11-text-input-analysis.md) | 2026-04-23 |
| PROJ-12 | PDF-Upload | Planned | [PROJ-12](PROJ-12-pdf-upload.md) | 2026-04-23 |
| PROJ-13 | URL-Analyse (Text-only) | Planned | [PROJ-13](PROJ-13-url-analysis.md) | 2026-04-23 |
| PROJ-14 | Analyse-Report-Darstellung | In Progress | [PROJ-14](PROJ-14-report-visualization.md) | 2026-04-23 |
| PROJ-15 | PDF-Export des Reports | Planned | [PROJ-15](PROJ-15-pdf-export.md) | 2026-04-23 |
| PROJ-16 | Dashboard | In Progress | [PROJ-16](PROJ-16-dashboard.md) | 2026-04-23 |
| PROJ-17 | DSGVO-Konformität | Planned | [PROJ-17](PROJ-17-dsgvo-compliance.md) | 2026-04-23 |
| PROJ-18 | Marketing Landing Page + Beta-Waitlist | In Progress | [PROJ-18](PROJ-18-marketing-landing.md) | 2026-04-24 |

<!-- Add features above this line -->

## Next Available ID: PROJ-19

## Recommended Build Order

Aufgeteilt in vier Wellen mit klaren Dependencies:

**Welle 1 — Fundament (parallelisierbar, Woche 1):**
- PROJ-1 User Authentication
- PROJ-7 Prompt-Management (Infrastruktur)
- PROJ-17 DSGVO-Querschnitt (Rechtstexte vorbereiten)

**Welle 2 — Wissensbasis (parallel, Woche 1–2):**
- PROJ-4 EU-Claim-Register
- PROJ-5 HCVO-Verordnungstext
- PROJ-6 Urteilsdatenbank

**Welle 3 — Pipeline (Woche 2–3):** ← Architektur-Fokus
- PROJ-8 Claim-Detection
- PROJ-9 Hybrid Retrieval
- PROJ-10 Claim-Evaluation

**Welle 4 — User-Facing (Woche 3–4):**
- PROJ-11 Text-Input
- PROJ-12 PDF-Upload
- PROJ-13 URL-Analyse
- PROJ-14 Report-Darstellung
- PROJ-15 PDF-Export
- PROJ-16 Dashboard
- PROJ-2 Plan & Usage
- PROJ-3 Stripe
