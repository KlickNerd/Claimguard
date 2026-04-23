# PROJ-11: Text-Input-Analyse

## Status: In Progress
**Implementierungsstand:** Frontend-Mock auf `/app` fertig (Tabs Text/URL/PDF, Zeichenzähler, Kategorie-Pill, Disclaimer). Anbindung an Backend-Pipeline (PROJ-8/9/10) ausstehend. Sprach-Check clientseitig noch offen.
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-001

## Dependencies
- PROJ-1 (User Authentication)
- PROJ-2 (Plan-Management) — Credit-Check
- PROJ-8, PROJ-9, PROJ-10 (Pipeline)

## User Stories
- Als Nutzer möchte ich Text einfach in ein Feld einfügen und auf „Analysieren" klicken, damit ich keinen Umweg über Datei-Upload habe.
- Als Nutzer möchte ich während der Analyse sehen, wo die Pipeline gerade steht, damit ich weiß, dass nichts hängt.
- Als Nutzer möchte ich einen Zeichenzähler sehen, damit ich Limits einhalten kann.

## Acceptance Criteria
- [ ] Textarea auf `/analyze/new` akzeptiert bis **20.000 Zeichen**
- [ ] Zeichenzähler sichtbar, Live-Update bei Eingabe
- [ ] Warnung ab 90 % Auslastung (18.000 Zeichen): gelbe Pill „2000 Zeichen übrig"
- [ ] Bei 100 %: Eingabe wird hart abgeschnitten, rote Fehlermeldung
- [ ] Analyse-Button deaktiviert wenn: Text leer, < 50 Zeichen, User-Limit erreicht, Sprach-Check negativ
- [ ] **Sprach-Erkennung** (clientseitig: `franc` oder `cld3`) vor Submit: wenn nicht DE → Fehler „ClaimGuard unterstützt im MVP nur deutschsprachige Texte"
- [ ] Während Analyse: Fortschrittsanzeige mit Pipeline-Schritten (5 Stufen):
  1. Text normalisieren
  2. Claims erkennen (X gefunden)
  3. Rechtsquellen suchen
  4. Bewertung (X von Y fertig)
  5. Report erstellen
- [ ] Server-Sent-Events oder Polling alle 2s für Fortschritt
- [ ] Bei Abbruch (Navigation weg): Analyse läuft im Backend durch, Credit wird verbraucht, User findet Report später im Dashboard
- [ ] Nach Erfolg: Redirect auf `/analyze/{id}` mit Report

## Edge Cases
- **Text enthält nur Sonderzeichen/Emojis:** Sprach-Check schlägt fehl, Fehlermeldung
- **Text hat Mix aus DE und EN:** Wenn DE-Anteil > 70 %, läuft Analyse; sonst Ablehnung
- **Text mit versteckten Unicode-Zeichen (RTL-Overrides etc.):** Serverseitige Normalisierung vor Detection
- **Copy-Paste aus Word mit Smart-Quotes:** Normalisierung auf Standard-Anführungszeichen
- **HTML im Text (User paste Rich Text):** `<tag>` werden entfernt, Inhalt bleibt
- **User klickt 2x Analyse-Button (Double-Click):** Idempotenz-Key, zweite Request → gleiche Analyse-ID
- **Netzwerk-Abbruch während Analyse:** Backend läuft durch, Client zeigt Reconnect-State, findet Ergebnis via Polling
- **Browser-Refresh während Analyse:** Auf `/analyze/{id}` routen, Polling fortsetzen

## Technical Requirements
- Next.js Route: `/analyze/new` (Editor), `/analyze/{id}` (Report)
- Client-Side Sprach-Erkennung: `franc-min` (klein, 58 kB)
- Backend: `POST /api/analyses` (Credit-Check, neue Analyse erstellen, Job-ID zurück)
- Pipeline als Async-Task (Celery/ARQ/FastAPI BackgroundTasks — Entscheidung in /architecture)
- Fortschritts-Endpoint: `GET /api/analyses/{id}/status`
- WCAG 2.1 AA: Textarea mit Label, Button mit aria-busy während Analyse

## Open Questions
- Textarea mit Rich-Text (Markierungen, Formatierung erhalten)? → **MVP: plain text, V1.1 Rich**
- Multi-Text-Input (mehrere Varianten parallel)? → V1.2
- Auto-Save Draft? → **MVP: nein, V1.1**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
