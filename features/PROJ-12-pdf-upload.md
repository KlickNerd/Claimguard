# PROJ-12: PDF-Upload

## Status: Planned
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-002

## Dependencies
- PROJ-11 (Text-Input-Analyse) — wiederverwendet Pipeline + UI nach Extraktion

## User Stories
- Als Nutzer möchte ich eine PDF hochladen und daraus extrahierten Text prüfen lassen, damit ich keine manuelle Textvorbereitung brauche.
- Als Nutzer möchte ich vor der Analyse sehen, was extrahiert wurde, damit ich Extraktionsfehler korrigieren kann.
- Als Nutzer möchte ich eine klare Meldung bekommen, wenn mein PDF gescannt ist (nicht textbasiert), damit ich nicht rätsel.

## Acceptance Criteria
- [ ] Drag-and-drop und klassischer Datei-Picker auf `/analyze/new` (Tab „PDF")
- [ ] Max. Dateigröße **10 MB**, größer → Fehler mit Hinweis
- [ ] Nur MIME `application/pdf` akzeptiert, Prüfung client- UND serverseitig
- [ ] Textextraktion via `unstructured.io` (Python), fallback-robust (auch mehrspaltig)
- [ ] Extrahierter Text wird dem User **vor** Analyse angezeigt in Textarea (siehe PROJ-11), **editierbar**
- [ ] Bei gescannten PDFs (kein Text extrahierbar oder < 50 Zeichen): Meldung „Dieses PDF scheint gescannt zu sein. OCR wird im MVP nicht unterstützt — bitte Text manuell einfügen oder Word/Docx verwenden (ab V1.1)"
- [ ] Original-Filename wird als `source_reference` gespeichert
- [ ] PDF-Datei wird **nicht** dauerhaft gespeichert (nur Text), Upload-Buffer nach Extraktion gelöscht
- [ ] Upload-Fortschrittsanzeige bei großen Dateien

## Edge Cases
- **Passwort-geschütztes PDF:** Fehler „PDF ist verschlüsselt, bitte entschlüsseln und erneut hochladen"
- **Korrupte PDF:** Fehler „Datei kann nicht gelesen werden"
- **PDF mit nur Bildern (Packshots):** Gleich wie gescannt → Hinweis auf V1.1
- **Sehr große Text-PDF (> 20.000 Zeichen extrahiert):** User sieht Warnung, kann kürzen in Textarea
- **PDF mit Formularfeldern:** Werte werden extrahiert, Layout verloren — akzeptabel
- **Mehrseitige PDF mit Header/Footer-Wiederholung:** `unstructured.io` deduplicates
- **PDF mit Tabellen:** Text extrahiert, Struktur verloren — akzeptabel für MVP
- **Upload-Abbruch (Netzwerk):** keine Partial-Speicherung, User muss neu starten
- **Mime-Type-Spoofing (.exe umbenannt in .pdf):** Server-Magic-Byte-Check lehnt ab
- **Virus im PDF:** ClamAV-Scan im Backend, Block bei Fund

## Technical Requirements
- Next.js: `react-dropzone` für Upload-UI
- Backend: `POST /api/extract/pdf`, Multipart-Upload
- Library: `unstructured[pdf]`
- Antivirus: ClamAV (oder Cloud-Service — Entscheidung in /architecture)
- Upload-Limit via FastAPI-Middleware + Caddy-Config

## Open Questions
- OCR-Integration (Tesseract) im MVP? → **Nein, V1.1** (bestätigt in Backlog)
- Erhalt von Formatierung (Bold/Italic) für spätere Rich-Analyse? → V1.1
- Mehrere PDFs als Batch? → V1.2 (F-202)

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
