# Product Requirements Document – ClaimGuard

## Vision
ClaimGuard ist eine SaaS-Plattform zur automatisierten Prüfung gesundheitsbezogener Werbeaussagen (Health Claims) auf rechtliche Zulässigkeit nach EU-Verordnung 1924/2006 (HCVO) und aktueller deutscher Rechtsprechung. Die Plattform liefert in unter 60 Sekunden eine strukturierte Risikobewertung mit Rechtsgrundlage und Reformulierungsvorschlägen — als Pre-Check-Instanz vor Publikation, nicht als Rechtsberatung. Zielmarkt: DACH-Raum.

## Target Users

**Primary – Marketing-Manager Supplement-Brand** (5–50 MA): Erstellt regelmäßig Produkttexte, Landing Pages, Newsletter. Hat erlebte oder gefürchtete Abmahnung (Wettbewerbszentrale, IDO-Verband). Kein juristischer Background. Braucht schnelle, verständliche Prüfung vor Publikation.

**Primary – Agentur-Inhaber / Content-Lead** (SEO/Content/Performance, 5–30 Kunden): Muss Content für mehrere Brands parallel liefern. Braucht Multi-Workspace, PDF-Export, White-Label-Report als Argumentationshilfe gegenüber Kunden.

**Secondary – Produktmanager Functional Food**: Arbeitet cross-funktional mit Marketing und Regulatory Affairs. Prüft Claims gegen interne Guidelines und Wettbewerb. Braucht URL-Input für Konkurrenzanalyse und strukturierten Export.

**Tertiary – Freier Texter / Copywriter**: Schreibt für Supplement-/Food-Kunden. Braucht Absicherung der eigenen Lieferung, günstigen Pro-Plan, einfache UI.

## Core Features (Roadmap)

| Priority | ID | Feature | Status |
|----------|----|---------|--------|
| P0 (MVP) | PROJ-1 | User Authentication | Planned |
| P0 (MVP) | PROJ-2 | Plan- & Nutzungs-Verwaltung | Planned |
| P0 (MVP) | PROJ-3 | Stripe-Integration (Subscription) | Planned |
| P0 (MVP) | PROJ-4 | EU-Claim-Register-Integration | Planned |
| P0 (MVP) | PROJ-5 | HCVO-Verordnungstext-Integration | Planned |
| P0 (MVP) | PROJ-6 | Urteilsdatenbank (30 Fälle) | Planned |
| P0 (MVP) | PROJ-7 | Prompt-Management | Planned |
| P0 (MVP) | PROJ-8 | Claim-Detection | Planned |
| P0 (MVP) | PROJ-9 | Hybrid Retrieval | Planned |
| P0 (MVP) | PROJ-10 | Claim-Evaluation | Planned |
| P0 (MVP) | PROJ-11 | Text-Input-Analyse | Planned |
| P0 (MVP) | PROJ-12 | PDF-Upload | Planned |
| P0 (MVP) | PROJ-13 | URL-Analyse (Text-only) | Planned |
| P0 (MVP) | PROJ-14 | Analyse-Report-Darstellung | Planned |
| P0 (MVP) | PROJ-15 | PDF-Export des Reports | Planned |
| P0 (MVP) | PROJ-16 | Dashboard | Planned |
| P0 (MVP) | PROJ-17 | DSGVO-Konformität | Planned |
| P1 | – | URL-Crawling mit Bild-OCR (F-101) | Planned |
| P1 | – | DOCX-Upload (F-102) | Planned |
| P1 | – | Nährstoff-Mengen-Check (F-103) | Planned |
| P1 | – | Team-Features / Multi-Workspace (F-104) | Planned |
| P1 | – | Web-Recherche nach neuen Urteilen (F-105) | Planned |
| P2 | – | Öffentliche API (F-201) | Planned |
| P2 | – | Batch-Analyse (F-202) | Planned |
| P2 | – | White-Label-Reports (F-203) | Planned |
| V2 | – | Kosmetikverordnung, HWG, Mehrsprachigkeit, Plugins, Custom-Rules | Planned |

## Success Metrics

**Geschäftsziele:**
- 3 Monate post-MVP: 15 zahlende Kunden
- 6 Monate: 2.500 € MRR
- 12 Monate: 10.000 € MRR

**Qualitäts-KPIs:**
- Claim-Detection Precision ≥ 90 % im kuratierten Eval-Set (min. 30 Texte)
- Analyse-Durchlaufzeit p95 ≤ 60 s bei Texten bis 5.000 Zeichen
- Uptime ≥ 99,5 %
- Dashboard-Ladezeit p95 ≤ 1,5 s

## Constraints

- **Team:** Solo-Founder (Dominik / KlickNerds), begrenzte Kapazität
- **Zeitrahmen MVP:** Release Woche 4 ab Start
- **Hosting:** Hostinger VPS Frankfurt (bestehend, EU-Standort) — Backend & DBs dürfen EU nicht verlassen
- **DSGVO:** Volle Konformität inkl. Zero-Data-Retention bei Anthropic-API, AV-Verträge mit allen Subunternehmern
- **Sprache MVP:** ausschließlich Deutsch (i18n-ready vorbereiten)
- **Kein Vendor-Lock-in auf US-Cloud** (kein Pinecone, kein Vercel-Backend)
- **Haftungslimit:** ClaimGuard liefert keine Rechtsberatung — sichtbarer Disclaimer auf allen Reports, AGB durch Anwalt zu prüfen

## Non-Goals (MVP)

- Keine OCR für gescannte PDFs (V1.1)
- Keine Bild-Analyse bei URL-Crawling (V1.1)
- Kein DOCX-Upload (V1.1)
- Keine Mehrsprachigkeit — nicht-deutscher Input wird abgelehnt
- Keine automatische Rechtsauskunft / anwaltlicher Ersatz
- Keine Team-Features / Multi-User pro Workspace (V1.1)
- Keine öffentliche API (V1.2)
- Keine Abdeckung von Kosmetikverordnung, HWG, Medizinprodukten (V2)
- Keine automatische Übernahme von Web-Suchergebnissen in die Hauptwissensbasis

---

Use `/architecture` to design the technical approach for the first feature. Empfehlung für Start: **PROJ-8 (Claim-Detection)** — Herzstück mit höchstem technischen Risiko.
