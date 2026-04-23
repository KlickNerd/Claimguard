# PROJ-18: Marketing Landing Page + Beta-Waitlist

## Status: In Progress
**Created:** 2026-04-24
**Last Updated:** 2026-04-24
**Backlog-Referenz:** nachträglich hinzugefügt (nicht im ursprünglichen Backlog v0.1; aus Lovable-Design-Vorlage übernommen)

## Dependencies
- None auf technischer Seite (die Landing-Implementierung steht, ist Next.js-only)
- Backend-Teil (Waitlist-Persistierung) hängt bei Launch von Supabase ab, aber nicht von PROJ-1 (Auth)

## User Stories
- Als Besucher möchte ich in unter 10 Sekunden verstehen, was ClaimGuard macht und ob es für meinen Use-Case relevant ist.
- Als skeptischer Marketing-Manager möchte ich eine Live-Demo sehen, ohne mich registrieren zu müssen.
- Als Interessent möchte ich mich auf die Beta-Warteliste setzen lassen, damit ich informiert werde, wenn der Zugang freigeschaltet wird.
- Als Betreiber möchte ich Warteliste-Einträge erfassen, damit ich beim Launch zielgerichtet einladen kann.
- Als Content-Verantwortlicher möchte ich rechtssichere Formulierungen auf der Seite haben (kein Over-Promising, Disclaimer sichtbar).

## Acceptance Criteria

### Landing (implementiert)
- [x] Sticky Header mit Logo, Nav (Funktionen, So funktioniert's, Rechtsquellen, Preise), Login-Link, Beta-CTA
- [x] Hero: Pill mit Rechtsquellen, Headline, Sub-Copy, zwei CTAs („Beta anfragen" + „Live-Demo ansehen"), Trust-Row (EU-Hosting, Zero-Retention, kein Rechtsberatungs-Ersatz)
- [x] Live-Demo-Widget direkt im Hero: Tab-Switcher Text/URL/PDF, statischer Beispieltext, 3 Demo-Claims rendered mit korrekten Status-Pills
- [x] Feature-Grid (6 Cards): Implizite Claims, Primärrecht, Reformulierungen, Aktuelle Rechtslage, EU-Hosting/Zero-Retention, Multi-Input
- [x] 3-Step Prozess-Section
- [x] Rechtsquellen-Section mit Beispiel-Eintrag
- [x] Pricing: Starter 29€ / Studio 99€ (highlighted) / Enterprise Custom — V1.1/V1.2-Features sind als solche gekennzeichnet
- [x] Waitlist-CTA mit E-Mail-Input, Success-State
- [x] Footer: Logo, Disclaimer, Produkt-Links, Rechtslinks, Copyright, Regulatorik
- [x] DE-Sprache überall, SEO-Metadaten gesetzt (title-Template, description, OG)
- [x] Responsive ab 360 px Breite

### Design-System-Foundation (implementiert)
- [x] Fonts: Fraunces (serif, Display), Inter (sans, Body), JetBrains Mono (Code-Referenzen)
- [x] Farb-Tokens: Teal-Primary, warmes Off-White, 4 Status-Farben (allowed/borderline/forbidden/unclear)
- [x] Wiederverwendbare Komponenten für Report (PROJ-14): `StatusPill`, `ClaimCard`

### Waitlist-Persistierung (offen)
- [ ] Supabase-Tabelle `waitlist_entries` mit E-Mail, Zeitstempel, Consent-Flag, Quelle-Tag (utm)
- [ ] API-Route `POST /api/waitlist` mit Rate-Limit (3 pro IP pro Tag)
- [ ] Double-Opt-In-E-Mail-Flow
- [ ] DSGVO: Daten-Export und -Löschung aus Waitlist identisch zu User-Daten (siehe PROJ-17)

### Content / Copy (offen bis Anwalt-Review)
- [ ] Statistik-Claims („5.000 € Abmahnkosten" etc.) bestückt mit Quelle
- [ ] Datenschutzerklärung und AGB verlinken (stehen vor Public-Launch)
- [ ] Cookie-Banner (aus PROJ-17)

## Edge Cases
- **Besucher mit JS deaktiviert:** Hero + Content rendern (Server-Components), Demo-Widget zeigt statischen Zustand
- **E-Mail-Adresse bereits eingetragen:** freundliche Bestätigung, keine User-Enumeration
- **Bot-Submissions:** Honeypot-Feld oder Turnstile/hCaptcha vor Launch
- **Mobile, sehr kleine Viewports (< 360 px):** zweispaltige Demo stackt, Tabellen horizontal scrollbar
- **SEO-Bots:** saubere HTML-Struktur, meta-robots default allow, sitemap.xml (später)

## Technical Requirements
- Next.js 16 App Router, Server Components wo möglich, Client Components nur für Demo-Tabs und Waitlist-Form
- Komponenten unter `apps/web/src/components/site/`
- Design-Tokens in `apps/web/src/app/globals.css`, Tailwind-Config erweitert um `font-*` und `status-*` Farben
- Wiederverwendbarkeit: `StatusPill` und `ClaimCard` werden später von PROJ-14 (Report) importiert
- Barrierefrei: semantische Landmarks (`header`/`main`/`footer`/`nav`), `aria-hidden` für dekorative Icons, Fokus-Ringe erhalten

## Abweichungen gegenüber Lovable-Design-Vorlage
- **4 Status-Farben** statt 3 (ergänzt: Unclear-Grau) — deckungsgleich mit PROJ-10 Evaluation-Scope
- **Kein Kategorie-Selector** im Demo-Widget — MVP deckt nur Supplement/Food ab, Naturkosmetik/HWG sind V2
- **Team-Features** im Pricing als „V1.1" markiert, nicht als MVP-Versprechen
- **Launch-Datum** auf Q3 2026 angepasst (Lovable-Vorlage hatte Q2 2025)
- **Lifelong-Rabatt** durch „50 % im ersten Jahr" ersetzt (rechtlich sauberer)

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_Technisch leichtgewichtig, kein eigener Architektur-Entwurf nötig. Frontend-Pattern folgt den etablierten Marketing-Landing-Konventionen, Waitlist-Persistierung kommt mit PROJ-1/PROJ-17-Infrastruktur._

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
