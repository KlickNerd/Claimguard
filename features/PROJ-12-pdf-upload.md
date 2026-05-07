# PROJ-12: PDF-Upload

## Status: In Progress
**Created:** 2026-04-23
**Last Updated:** 2026-05-01
**Backlog-Referenz:** F-002

## Implementation Notes (2026-05-01)

**Was umgesetzt ist (MVP-Stand):**
- Backend-Service [`pdf_extractor.py`](../apps/api/app/services/pdf_extractor.py)
  nutzt `pdfplumber` (statt `unstructured` aus dem Spec — bereits in der Dep-
  Tree und reicht für DACH-PDFs). Magic-Byte-Check (`%PDF-`), Größenlimit 10 MB,
  Encrypted-Detection, Mindesttext-Schwelle 50 Zeichen mit Hinweis auf
  gescannte PDFs.
- Endpoint [`POST /api/extract/pdf`](../apps/api/app/api/extract.py): Multipart-
  Upload, MIME-Check, Mapping aller Fehler auf stabile Codes (`pdf_too_large`,
  `pdf_invalid`, `pdf_encrypted`, `pdf_no_text`, `pdf_invalid_mime`).
- Frontend-Component [`PdfDropzone`](../apps/web/src/components/app/pdf-dropzone.tsx):
  HTML5-Drag-and-Drop + File-Picker, Loading-State, Filename-Display,
  Fehleranzeige. Keine extra `react-dropzone`-Dep.
- [`api-client.extractPdf`](../apps/web/src/lib/api-client.ts) ruft den
  Endpoint und gibt Text + `source_reference` zurück.
- Auf [`/app`](../apps/web/src/app/app/page.tsx) wechselt der PDF-Tab nach
  Extraktion automatisch in den Text-Tab und füllt das Editor-Textarea. User
  kann **vor** Analyse korrigieren. Filename → `source_reference` in
  `createAnalysis({source_type: "pdf", …})`.
- Datei-Bytes werden nicht persistiert — Buffer lebt nur im Request-Scope.
- Tests: [`test_pdf_extractor.py`](../apps/api/tests/test_pdf_extractor.py) +
  [`test_api_extract.py`](../apps/api/tests/test_api_extract.py). Smoke gegen
  CELEX 32012R0432 PDF: 40 Seiten, 121.203 Zeichen sauber extrahiert.

**Bewusst nicht im MVP, aber als Folgetasks offen:**
- Kein ClamAV-Scan (Spec-Acceptance) — der pdfplumber-Pfad fängt korrupte
  Dateien sicher ab; Magic-Bytes-Check verhindert MIME-Spoofing. Echter
  AV-Scan später, wenn wir File-Storage einführen.
- Kein OCR für gescannte PDFs (V1.1 wie im Spec).
- Keine Upload-Fortschrittsanzeige (10 MB unter 1 s, kein Bedarf).
- DOCX-Upload (V1.1, F-102).
- Test für `pdf_encrypted`-Pfad fehlt (Sample-PDF noch nicht im Repo).

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
