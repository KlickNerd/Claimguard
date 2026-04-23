# PROJ-13: URL-Analyse (Text-only)

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-003

## Dependencies
- PROJ-11 (Text-Input-Analyse) — gemeinsame Pipeline

## User Stories
- Als Nutzer möchte ich eine URL eingeben und den Seiteninhalt prüfen lassen, damit ich Wettbewerber / eigene Landingpages schnell checken kann.
- Als Nutzer möchte ich vor der Analyse den extrahierten Text sehen, damit ich manipulierte Extraktion erkenne.
- Als Nutzer möchte ich eine klare Meldung sehen, wenn ich Bilder-Claims im MVP noch nicht abdecke, damit ich nicht enttäuscht bin.

## Acceptance Criteria
- [ ] URL-Eingabefeld auf `/analyze/new` (Tab „URL")
- [ ] Validierung: nur `http(s)://` URLs, keine IPs, keine localhost-Adressen
- [ ] Backend rendert Seite via **Playwright** (headless Chromium) mit JS-Ausführung
- [ ] Timeout 30 Sekunden, danach Fehlermeldung
- [ ] `robots.txt` wird respektiert: bei `Disallow` für User-Agent `ClaimGuardBot` → Fehlermeldung „Diese Seite erlaubt kein Crawlen"
- [ ] User-Agent: `ClaimGuardBot/1.0 (+https://claimguard.de/bot)`
- [ ] Extraktion: `readability-lxml` für Haupttext + Meta-Description + strukturierte Daten (JSON-LD)
- [ ] Extrahierter Text wird vor Analyse in Textarea angezeigt, **editierbar**
- [ ] UI-Hinweis: „Bilder und Grafiken werden im MVP nicht analysiert (ab V1.1 mit OCR)"
- [ ] Original-URL wird als `source_reference` gespeichert
- [ ] Ergebnis-Link im Report führt zur Original-URL

## Edge Cases
- **URL hinter Login / Paywall:** Extraktion läuft, aber auf Content-Marketing-Text statt hinter Paywall — Nutzer sieht Text und kann erkennen, dass es falsch ist
- **URL mit JS-Redirect:** Playwright folgt Redirects (max. 5), nutzt Final-URL
- **URL mit Endless-Scroll / Infinite Load:** nur Initial-Viewport gerendert, 2s Wait nach `domcontentloaded`
- **URL lieferte 404 / 5xx:** Klare Fehlermeldung mit Status-Code
- **URL in Cloudflare-Challenge:** Erkennung, Fehlermeldung „Seite durch Bot-Schutz blockiert"
- **Sehr große Seite (> 5 MB HTML):** Abbruch, Fehlermeldung „Seite zu groß"
- **Private IPs (10.x, 192.168.x, 127.0.0.1):** SSRF-Schutz, harte Ablehnung
- **URL mit User-Credentials (`https://user:pass@...`):** Ablehnen
- **URL mit Query-Params / Anker:** beibehalten, da Inhalt oft davon abhängt
- **Extrahierter Text < 50 Zeichen:** Warnung, User kann trotzdem manuell Text hinzufügen
- **Nicht-DE-Sprache:** Sprach-Check (wie PROJ-11) → Ablehnung vor Analyse
- **Seite mit iFrame:** iFrame-Inhalt wird nicht extrahiert, Warnung
- **Cookie-Consent-Banner verdeckt Text:** Pre-Action: Auto-Accept-Cookies-Script (Standard-Selektoren), Fallback Hinweis

## Technical Requirements
- Library: Playwright (Python), Browser im Docker vorinstalliert
- Ressourcen-Limits: max 512 MB RAM pro Playwright-Instance, max 5 parallel
- Extraktions-Pipeline: `goose3` oder `readability-lxml` + `lxml` für strukturierte Daten
- SSRF-Protection: DNS-Resolution vor Fetch, private IP-Ranges blocken
- User-Agent-Dokumentation unter `https://claimguard.de/bot`

## Open Questions
- Screenshots der Seite als PDF-Anhang im Report? → V1.1
- Crawl-Rate-Limit pro Domain (um Abuse zu verhindern)? → **MVP: 5 req/min pro User pro Domain**
- Wettbewerber-URLs mit Robots-Disallow trotzdem crawlen (Legal-Risiko)? → **Nein, strikt respektieren**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
