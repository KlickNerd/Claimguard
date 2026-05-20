# PROJ-20: KI-Chat-Assistent (Analyse-Context)

## Status: Planned
**Created:** 2026-05-11
**Last Updated:** 2026-05-11

## Dependencies
- Requires: PROJ-1 (User Authentication) — Chat-Verlauf gehört einem User, RLS-gesichert
- Requires: PROJ-8 (Claim-Detection) — Chat braucht die erkannten Claims als Kontext
- Requires: PROJ-9 (Hybrid Retrieval) — Chat braucht die abgerufenen Rechtsquellen als Kontext
- Requires: PROJ-10 (Claim-Evaluation) — Chat braucht die Urteile (Status, Confidence, Reasoning) als Kontext
- Requires: PROJ-14 (Analyse-Report-Darstellung) — Chat-Button lebt in der Report-UI
- Soft: PROJ-2 (Plan- & Nutzungs-Verwaltung) — Chat-Token-Verbrauch zählt in Plan-Limits
- Soft: PROJ-16 (Dashboard / History) — Wiederöffnen einer Analyse muss den Verlauf wiederherstellen

## User Stories
- Als Marketing-Manager möchte ich „warum ist Claim 3 borderline?" fragen können, damit ich die juristische Begründung verstehe, ohne den ganzen Report zu lesen.
- Als Content-Lead möchte ich einen Satz im Editor markieren und „mach das weniger werblich" schreiben können, damit ich einen rechtskonformen Vorschlag bekomme, ohne den Editor zu verlassen.
- Als Nutzer einer alten Analyse aus der History möchte ich meinen bisherigen Chat wiedersehen, damit ich an der Stelle weitermachen kann, an der ich zuletzt war.
- Als Texter möchte ich, dass die KI im Gespräch konkrete Textänderungen vorschlägt („ersetze 'heilt' durch 'unterstützt'") und ich sie mit einem Klick übernehmen kann, damit ich nicht kopieren-einfügen muss.
- Als unsicherer Nutzer einer Rechtsquellen-Zitierung möchte ich fragen können „welche Quelle nutzt ihr für diese Einschätzung?" und die Chunk-ID + URL zurückbekommen, damit ich die Original-Quelle prüfen kann.
- Als Marketing-Manager möchte ich, dass der Chat Token-für-Token streamt (wie ChatGPT/Claude), damit es sich responsiv anfühlt und ich frühe Antworten lesen kann, während der Rest noch generiert wird.

## Acceptance Criteria

### Einstieg & UI
- [ ] Auf der Analyse-Report-Seite (PROJ-14) gibt es einen sichtbaren Button („KI fragen" oder ähnlich), der ein Drawer / Sheet von rechts öffnet.
- [ ] Der Drawer enthält den vollständigen bisherigen Chat-Verlauf der aktuellen Analyse plus ein Eingabefeld unten.
- [ ] Beim Schließen des Drawers bleibt der Zustand erhalten — beim Wiederöffnen ist der Verlauf direkt wieder da.
- [ ] Der Drawer ist auf Mobile responsiv (Vollbild oder >90 % Breite, da die Analyse-UI selbst auf Mobile kompakt ist).

### Streaming & Antwortverhalten
- [ ] KI-Antworten streamen Token-für-Token; das erste Token erscheint < 1,5 s nach Send (Time-to-first-Token).
- [ ] Während des Streamings ist das Eingabefeld disabled; eine „Abbrechen"-Aktion ist möglich.
- [ ] Bricht der Stream ab (Netzwerk / Server), wird die Nachricht als „abgebrochen" markiert und es gibt einen Retry-Button.

### KI-Kontext (Prompt-Engineering)
- [ ] Der Anthropic-Call erhält als Kontext: vollständiger Input-Text der Analyse, alle erkannten Claims (claim_text, claim_type, position_start/end, nutrient, substance), alle Bewertungen (status, confidence, risk_level, reasoning, rewrite_suggestion, legal_hints), alle Retrieval-Hits (chunk_id, source_type, reference, snippet, url, score).
- [ ] Der Kontext-Block ist mit Prompt-Caching markiert (`cache_control: ephemeral`), so dass Folgenachrichten in derselben Konversation den teuren Context billig wiederverwenden.
- [ ] Modell: Claude Sonnet 4.6 (`anthropic_model_evaluation`-Setting wiederverwenden oder eigene Env-Var `anthropic_model_chat`).

### Textänderungen via KI

**Variante a — Cursor-Style (Selection → Prompt → Diff):**
- [ ] Wenn der User Text im Editor markiert, erscheint ein „Mit KI ändern"-Button (Floating-Toolbar oder Bubble-Menu).
- [ ] Klick öffnet einen kleinen Prompt-Input (Inline oder im Drawer).
- [ ] Die KI-Antwort kommt als strukturierter Vorschlag zurück (alter Text / neuer Text / kurze Begründung).
- [ ] Der User sieht einen Diff-View (links: alt, rechts: neu, farblich hervorgehoben) und kann „Übernehmen" oder „Verwerfen" klicken.
- [ ] „Übernehmen" ersetzt den markierten Bereich im Editor; „Verwerfen" tut nichts.

**Variante b — Chat-Vorschlag-Apply:**
- [ ] Wenn die KI im normalen Chat-Verlauf eine konkrete Textänderung vorschlägt, ruft sie ein Anthropic-Tool `propose_text_change(old_text, new_text, rationale)` auf.
- [ ] Der Tool-Aufruf rendert im Chat einen Vorschlags-Block mit Diff-Anzeige + „Übernehmen"-Button.
- [ ] Klick auf „Übernehmen" sucht `old_text` im Editor (exakter Match) und ersetzt durch `new_text`.
- [ ] Findet `old_text` nicht (User hat zwischenzeitlich editiert), zeigt der Button eine Fehlermeldung „Textstelle nicht mehr gefunden — bitte manuell anwenden".
- [ ] Mehrere Vorschläge in derselben Antwort werden jeweils mit eigenem Apply-Button gerendert.

### Persistierung
- [ ] Jede Nachricht (User + KI) wird in einer Supabase-Tabelle `chat_messages` gespeichert mit Feldern: `id`, `analysis_id`, `role` (user/assistant/tool), `content`, `tool_calls` (jsonb), `input_tokens`, `output_tokens`, `created_at`.
- [ ] RLS-Policy: nur der Owner der zugehörigen Analyse darf lesen/schreiben.
- [ ] Beim Öffnen einer Analyse aus der History (PROJ-16) werden die Chat-Nachrichten zur Analyse aus der DB nachgeladen.

### DSGVO & Token-Tracking
- [ ] Anthropic-Calls nutzen Zero-Data-Retention (wie bei den anderen Endpoints — keine Trainingsdaten, keine Server-Logs jenseits 30 Tage).
- [ ] `input_tokens` + `output_tokens` werden pro Nachricht erfasst und an die Nutzungstabelle (PROJ-2) gemeldet, so dass Plan-Limits greifen können.
- [ ] Wenn der User sein Plan-Limit überschritten hat, ist das Chat-Input-Feld disabled mit Hinweis „Limit erreicht — Upgrade nötig".

## Edge Cases
- **0 Claims erkannt** — Chat funktioniert trotzdem, KI bekommt nur den Input-Text als Kontext (kein leerer Claims-Block, der Token kostet).
- **Analyse-Owner ≠ aktueller User** — der Endpoint antwortet mit 403; im Frontend ist der Button gar nicht sichtbar, falls die Analyse nicht dem User gehört.
- **Sehr langer Chat-Verlauf** — nur die letzten N Nachrichten (z. B. 20) werden an Anthropic geschickt; ältere bleiben in DB und UI sichtbar, sind aber nicht mehr im Modell-Kontext.
- **KI schlägt Änderung vor, die nicht mehr im Editor steht** — Apply-Button zeigt Fehlermeldung; Vorschlag bleibt sichtbar zum manuellen Übernehmen.
- **Anthropic-API down** — Fehlermeldung im Chat-UI mit Retry-Button, kein App-Crash; der bisherige Verlauf bleibt sichtbar.
- **Streaming bricht mittendrin ab** — Nachricht als „abgebrochen" markieren, Retry-Button neben der Nachricht.
- **Plan-Limit während laufender Antwort erreicht** — der gerade laufende Stream wird zuendegeführt, das Input-Feld wird danach disabled.
- **Selection-Edit mit leerer Selection** — Button „Mit KI ändern" wird nicht angezeigt.
- **Selection-Edit über mehrere Absätze** — erlaubt; der Diff zeigt mehrere Hunks oder den gesamten Block.
- **Tool-Call mit unsinnigen Werten** (KI halluziniert `old_text` der nie im Editor stand) — Apply-Button schlägt fehl wie oben; in Logs als „hallucinated text change" markieren, kein Crash.
- **Mehrere Vorschläge in einer Antwort** — jeder bekommt eigenen Apply-Button und eigenen Diff-View; Reihenfolge der Anwendung ist beliebig.

## Non-Goals (MVP für PROJ-20)
- Sprachassistent / Voice-Input (kein Sprach-zu-Text, keine Audioausgabe — explizit ausgeschlossen, vermutlich nie).
- **Globaler Dashboard-Chat** ohne Analyse-Context — separates Feature, sollte als eigene Spec angelegt werden (z. B. PROJ-21).
- **Rechtsquellen-Browser-Chat** (auf der Sources-Seite) — separates Feature mit anderem Kontext (Rechtsquellen-DB), sollte als eigene Spec angelegt werden (z. B. PROJ-22).
- Mehrere parallele Konversationen pro Analyse — eine lineare Konversation reicht im MVP.
- Multi-User-Chats / kollaborative Konversation — Team-Feature, V1.1.
- Export des Chat-Verlaufs in den PDF-Report (PROJ-15) — V1.1.
- Inline-Suggestions à la GitHub Copilot beim Tippen (Ghost-Text) — Chat-getrieben ist das Pattern für MVP.
- Hochladen von Dateien in den Chat (Bilder, PDFs) — V1.1.

## Technical Requirements
- **Performance:** Time-to-first-Token ≤ 1,5 s p95; vollständige Antwort ≤ 30 s für typische Fragen.
- **Modell:** Claude Sonnet 4.6 (Opus 4.7 als optionales Premium nutzbar, gesteuert über User-Plan).
- **Prompt-Caching:** Cache-Control `ephemeral` auf System-Prompt + Analyse-Context-Block. Folgenachrichten in derselben Konversation lesen den Cache (90 % günstiger pro Input-Token).
- **DSGVO:** Anthropic Zero-Data-Retention (`x-anthropic-data-retention: 0d`-Header oder Setting); Daten bleiben in EU (Hostinger VPS Frankfurt + Supabase EU).
- **Sprache:** Deutsch (UI und KI-Antworten).
- **Backend:** Neuer FastAPI-Endpoint `POST /api/analyses/{analysis_id}/chat` mit Server-Sent-Events (SSE)-Streaming-Response. Anthropic-SDK kann nativ streamen.
- **Frontend:** Neues Drawer/Sheet-Komponent (shadcn/ui `Sheet`); Streaming-State via `EventSource` oder `ReadableStream`; Tool-Call-Rendering als spezielle Message-Variante.
- **Editor-Integration:** TipTap (siehe `apps/web/src/components/app/markdown-editor.tsx`) muss eine Methode bekommen, einen markierten Range durch Text zu ersetzen, und eine Methode, einen Range per Text-Suche zu finden + zu ersetzen.
- **Datenbank:** Supabase-Tabelle `chat_messages` (Migration via Supabase MCP / SQL); FK auf `analyses(id)`; RLS-Policy.
- **Tool-Definition:** Ein Anthropic-Tool `propose_text_change` mit JSON-Schema `{ old_text: string, new_text: string, rationale: string }`. System-Prompt instruiert die KI, das Tool zu nutzen, wenn sie konkrete Textänderungen vorschlägt.
- **Rate-Limit:** Pro User max. X Nachrichten pro Tag (Plan-abhängig, in PROJ-2 spezifiziert).

## Offene Fragen (für /architecture)
- Konkrete Implementierung des Diff-Views: eigene Komponente oder `react-diff-viewer-continued`?
- SSE vs. fetch-with-ReadableStream — beide funktionieren mit FastAPI, aber SSE hat besseres Reconnect-Verhalten.
- Wo lebt die Anthropic-Tool-Definition? Inline im Endpoint oder als versionierter Prompt (PROJ-7)?
- Soll der System-Prompt für den Chat als eigene Datei in `apps/api/app/prompts/chat_system_v1.md` versioniert werden (analog zu detection/evaluation)?

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)

### Großer Bogen

Der Chat sitzt **rechts neben der Analyse als Schiebepanel** (Drawer/Sheet) und teilt sich den Editor mit dem bestehenden Report. Beim ersten Öffnen fragt das Frontend die gespeicherten Chat-Nachrichten dieser Analyse aus Supabase ab. Eingaben gehen an einen neuen Streaming-Endpoint im Backend, der den vollen Analyse-Context (Eingabetext + Claims + Bewertungen + Rechtsquellen) als zwischengespeicherten Block an Sonnet 4.6 schickt und die Antwort Token für Token zurückstreamt. Schlägt die KI eine Textänderung vor, kommt sie nicht als Fließtext sondern als strukturierter Tool-Aufruf zurück, den die UI als Diff-Block mit „Übernehmen"-Button rendert.

### Komponentenstruktur (Frontend)

```
Report-Seite (PROJ-14, bestehend)
├── MarkdownEditor (bestehend, bekommt eine Methode "Range ersetzen")
├── Claims-Spalte (bestehend)
├── Chat-Button (neu) — schwebt unten rechts oder Header-Icon
│   └── öffnet:
└── ChatSheet (neu, baut auf shadcn Sheet)
    ├── Header: Analyse-Titel + Schließen-Button
    ├── Verlauf (scrollbar, zeigt alte + Live-Nachrichten)
    │   ├── UserMessage (rechts ausgerichtet, einfacher Text)
    │   ├── AssistantMessage (links, mit blinkendem Cursor während des Streamings)
    │   └── ProposeChangeCard (neu) — Spezial-Variante für Tool-Aufrufe
    │       ├── Diff-Anzeige (alt rot durchgestrichen / neu grün)
    │       ├── Begründungs-Text der KI
    │       └── "Übernehmen" / "Verwerfen" Buttons
    ├── Selection-Edit-Banner (neu) — nur sichtbar, wenn der User Text markiert hat
    │   └── zeigt "Du hast X Zeichen markiert — was soll geändert werden?" + Quick-Prompt-Input
    └── Eingabefeld + Senden-Button (+ Abbrechen, während Streaming läuft)
```

### Datenmodell (in Worten)

**Neue Tabelle: `chat_messages`** (Supabase Postgres, EU)

Jede Nachricht trägt:
- eine eindeutige ID,
- eine Zuordnung zur Analyse (Foreign Key auf die bestehende `analyses`-Tabelle),
- eine Rolle (`user`, `assistant`, oder `tool` für Tool-Aufrufe der KI),
- den Inhalt — entweder als Klartext oder als strukturiertes JSON (für Tool-Aufrufe mit `old_text` / `new_text` / `rationale`),
- Token-Verbrauch (Input + Output, damit PROJ-2 Plan-Limits zählen kann),
- einen Zeitstempel.

**Row-Level-Security:** Nur der Owner der zugehörigen Analyse (über die bereits vorhandene `user_id` auf der Analyse) darf Nachrichten lesen oder schreiben.

**Bewusst NICHT mitgespeichert:** Der Analyse-Context (Claims, Bewertungen, Rechtsquellen). Der lebt bereits in der `analyses`-Tabelle und wird bei jeder Chat-Anfrage frisch zusammengestellt — so spiegeln sich Editor-Änderungen zwischen zwei Chat-Nachrichten sofort im Kontext der KI.

### Backend (FastAPI)

**Neuer Endpoint:** `POST /api/analyses/{analysis_id}/chat`
- nimmt die neue Nachricht des Users entgegen,
- lädt aus Supabase Analyse-Snapshot + die letzten ~20 Chat-Nachrichten,
- baut den Anthropic-Prompt aus: System-Prompt (versioniert) + Analyse-Context (mit Cache-Marker) + Chat-Historie + neue Nachricht,
- streamt die Sonnet-Antwort als Server-Sent-Events zurück,
- persistiert die User-Nachricht sofort, die Assistant-Nachricht nach Ende des Streams.

**Neuer Service:** `ChatService` (analog zur Struktur von `RewriteService` / `ClaimEvaluator`)
- baut Prompts, ruft Anthropic auf, definiert das `propose_text_change`-Tool,
- nutzt den bereits gehärteten `anthropic_client` (Timeouts, Retries — Fixes der letzten Iteration),
- lädt seinen versionierten System-Prompt aus `apps/api/app/prompts/chat_system_v1.0.0.md`.

**Tool-Definition für die KI:** `propose_text_change(old_text, new_text, rationale)`. Der System-Prompt instruiert die KI, dieses Tool zu nutzen, sobald sie eine konkrete Textänderung vorschlägt — statt das nur in Fließtext zu schreiben. So weiß das Frontend immer eindeutig, wann ein Apply-Button gerendert werden muss.

### Tech-Entscheidungen (das Warum)

1. **Server-Sent-Events statt WebSocket** — Streaming ist einseitig (Server → Client). SSE läuft über normales HTTPS, ist hinter Caddy ohne Sonderkonfiguration unterstützt, hat automatisches Reconnect, und das Anthropic-SDK liefert nativ einen Stream-Iterator, den der Endpoint nur durchschleifen muss.

2. **Tool-Use für Textänderungen statt Markdown-Parsing** — Würde die KI im Fließtext „ich würde X durch Y ersetzen" schreiben, müssten wir mit Regex erraten, was gemeint ist. Mit einem strukturierten Tool-Aufruf bekommen wir das maschinenlesbar zurück und sparen uns fragiles Parsen.

3. **Sliding Window für die Chat-Historie (~20 Nachrichten)** — Bei längeren Verläufen würde der gesamte Chat den Anthropic-Prompt aufblähen und teuer machen. Die UI zeigt weiterhin alle Nachrichten, aber Anthropic sieht nur das relevante Ende. Ältere Nachrichten bleiben in Supabase liegen.

4. **Prompt-Caching auf System-Prompt + Analyse-Context** — Der Context (kompletter Input + Claims + Bewertungen + Rechtsquellen) ist groß, oft 10–20k Tokens. Mit dem Cache-Marker liest Anthropic den gleichen Block in den nächsten ~5 Minuten zu 10 % des Preises wieder ein — bei mehreren aufeinanderfolgenden Fragen zur selben Analyse spart das deutlich.

5. **Versionierter Prompt-File analog zu Detection / Evaluation** — Das Prompt-Engineering wird sich entwickeln (was darf die KI sagen, wann soll sie Tools nutzen, wie zitiert sie Quellen). Versionierung erlaubt A/B-Tests und sauberen Rollback wie bei den anderen Prompts.

6. **Diff-Anzeige als eigene Komponente, keine externe Lib** — Wir zeigen genau zwei Blöcke: alt (rot durchgestrichen) und neu (grün hervorgehoben). Eine externe Diff-Lib wäre Overkill und 30+ KB im Frontend-Bundle. Eine kleine eigene Komponente reicht.

7. **Frontend-Apply via Text-Suche, nicht via Position** — Die KI liefert `old_text` als String, und das Frontend sucht den exakt im aktuellen Editor-Inhalt und ersetzt das erste Vorkommen. Vorteil: robust gegen User-Edits zwischen KI-Vorschlag und Klick auf „Übernehmen" — solange der Text noch da ist, klappt es; wenn nicht, kommt eine klare Fehlermeldung.

### Dependencies

**Neu zu installieren:** keine. Sheet ist installiert, Streaming geht mit der nativen `fetch`-API plus `ReadableStream`, Markdown-Rendering existiert bereits. Backend-seitig ist das Anthropic-SDK schon eingebunden, FastAPI kann SSE nativ, und Supabase-Postgres ist gehookt.

**Bereits vorhanden, neu genutzt:**
- shadcn `Sheet` als Drawer
- TipTap-Editor-API für das Ersetzen markierter Stellen
- `anthropic_client` aus den letzten Pipeline-Fixes
- `prompt_loader` zum Laden des versionierten Chat-Prompts

### Migration / Datenbank

Eine neue Supabase-Migration legt die `chat_messages`-Tabelle an, samt Index auf `analysis_id` und RLS-Policy. Alle bestehenden Daten bleiben unangetastet — es ist eine reine Erweiterung, kein Schema-Change am Bestand.

### Risiken & Mitigationen

- **Latenz bis zum ersten Token** — bei großem Context und kaltem Cache 2–3 s. Mitigation: Skeleton-/Pulsanimation während der Wartezeit; optionales Cache-Vorwärmen beim Öffnen des Drawers (V1.1).
- **KI halluziniert `old_text`** — Apply-Button schlägt fehl, Vorschlag bleibt aber sichtbar zum manuellen Übernehmen. Akzeptabel im MVP.
- **Token-Kostenexplosion bei langer Konversation** — Sliding Window plus PROJ-2 Plan-Limits begrenzen den Schaden.
- **Race-Condition: User editiert, während KI antwortet** — Apply auf den veränderten Editor schlägt sauber fehl wie oben.

### Offene Fragen aus der Spec — beantwortet

- **Diff-View-Lib:** eigene minimale Komponente, keine Dep.
- **SSE vs. fetch-streaming:** SSE (siehe Begründung 1).
- **Tool-Definition Ort:** inline im `ChatService` fürs MVP. Wenn PROJ-7 Tool-Definitionen versioniert, später dorthin.
- **Chat-System-Prompt als versionierte Datei:** ja, `apps/api/app/prompts/chat_system_v1.0.0.md`.

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
