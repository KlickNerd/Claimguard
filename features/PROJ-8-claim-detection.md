# PROJ-8: Claim-Detection

## Status: Architected
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-010

## Dependencies
- PROJ-7 (Prompt-Management) — nutzt versionierten Detection-Prompt

## User Stories
- Als Nutzer möchte ich, dass das System alle gesundheitsbezogenen Aussagen in meinem Text findet, auch wenn ich sie implizit formuliere, damit ich nichts übersehe.
- Als Nutzer möchte ich pro Claim wissen, wo genau er im Text steht, damit ich ihn direkt finde.
- Als Betreiber möchte ich die Detection-Qualität messen können, damit ich Regressionen erkenne.

## Acceptance Criteria
- [ ] Erkennung **expliziter** Claims (z.B. „stärkt das Immunsystem", „reduziert Müdigkeit")
- [ ] Erkennung **impliziter** Claims (z.B. „für einen energiegeladenen Tag", „wie von der Natur gedacht")
- [ ] Output als strukturierte JSON-Liste (Pydantic-Schema):
  - `claim_id` (UUID)
  - `claim_text` (string, Original-Wortlaut)
  - `position_start`, `position_end` (Zeichen-Index im Originaltext)
  - `claim_type` (enum: `nutrient_based`, `health_based`, `reduction_based`, `wellbeing_based`, `disease_based`)
  - `nutrient` (string, nullable — z.B. „Vitamin C")
  - `substance` (string, nullable — z.B. „Ashwagandha")
  - `implicitness` (enum: `explicit`, `implicit`)
- [ ] Modell: Claude Sonnet 4.6 (Update gegenüber Backlog-V0.1: Sonnet 4.5)
- [ ] Prompt versioniert (siehe PROJ-7), initiale Version `claim_detection_v1.0.0`
- [ ] Eval-Set: 30+ annotierte Texte, Precision ≥ 90 %, Recall ≥ 85 %
- [ ] Konsistente Position-Indexe (keine Off-by-one zwischen Char/Byte)
- [ ] Logging: Input-Länge, Anzahl gefundener Claims, Latenz, Tokens

## Edge Cases
- **Kein Claim im Text:** Leere Liste, kein Fehler, Analyse läuft durch zu Report „Keine gesundheitsbezogenen Aussagen gefunden"
- **Text unter 50 Zeichen:** Eingabe wird akzeptiert, Warnung im UI „Sehr kurzer Text, Ergebnis eingeschränkt"
- **Nicht-deutscher Input:** Wird vor Detection abgefangen durch Sprach-Check (PROJ-11) — Detection läuft nie auf EN
- **Text mit HTML-Resten (aus URL-Extraktion):** Normalisierung vor Detection entfernt Tags, `position_*` referenzieren normalisierten Text
- **Überlappende Claims (verschachtelte Aussagen):** Beide werden zurückgegeben mit überlappenden Positionen
- **LLM halluziniert Claim, der nicht im Text steht:** Post-Check validiert `claim_text` via `text.find()`, bei Mismatch → Claim verworfen + Alarm
- **Claude-API-Outage:** 3x Retry mit exponentiellem Backoff (1s, 3s, 9s), dann Error mit Hinweis auf Status-Page, Credit zurückbuchen
- **Input > 20.000 Zeichen:** Abgefangen in PROJ-11, kommt hier nicht an
- **Token-Limit des Modells erreicht:** Text chunken (semantisch), Ergebnisse mergen, Positions-Offsets korrekt

## Technical Requirements
- Anthropic SDK (Python), `claude-sonnet-4-6` Model-ID
- Zero-Data-Retention-Header: `anthropic-beta: zdr-2024-06-01`
- Pydantic v2 Schema `DetectedClaim`
- Strukturiertes Output via Tool-Use oder JSON-Mode
- Retry-Library: `tenacity`
- Max Input Tokens: 20k Zeichen ≈ 8k Tokens (gut im Limit)
- Latenz-Ziel: p95 ≤ 15 s für 5.000-Zeichen-Text

## Open Questions
- Fallback auf Opus bei niedrigem Self-Confidence des Sonnet? → **Entscheidung in /architecture**
- Post-Validation durch zweites LLM (Consistency-Check)? → **MVP: nein, nur Post-Check auf `claim_text in input`**
- Multimodale Erweiterung (Bild-Claims)? → V1.1

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)

### Zielbild & Einordnung
PROJ-8 ist **Stufe 1 der Analyse-Pipeline**. Es nimmt Rohtext entgegen und liefert eine strukturierte Liste erkannter Health-Claims. Die Ergebnisse fließen in PROJ-9 (Retrieval) und PROJ-10 (Evaluation). PROJ-8 ist damit der Qualitäts-Flaschenhals für das gesamte Produkt: Was hier nicht erkannt wird, kann auch nicht bewertet werden.

### Pipeline-Flow (Übersicht)

```
[ Eingabetext (DE, bis 20k Zeichen) ]
          │
          ▼
┌─────────────────────────────────────┐
│  1. Vorverarbeitung                 │
│     - Normalisierung (HTML raus,    │
│       Smart-Quotes, Unicode)        │
│     - Sprach-Check (franc)          │
│     - Chunking bei > 8.000 Zeichen  │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  2. Prompt-Assembly                 │
│     - Prompt-Loader lädt versioned  │
│       Template (siehe PROJ-7)       │
│     - Jinja2 füllt Variablen        │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  3. LLM-Call                        │
│     - Claude Sonnet 4.6             │
│     - Structured Output (Tool-Use)  │
│     - Zero-Data-Retention-Header    │
│     - Retry 3x mit Backoff          │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  4. Post-Validation                 │
│     - Schema-Check (Pydantic)       │
│     - „claim_text in input?"        │
│       (Halluzinations-Filter)       │
│     - Position-Offsets korrigieren  │
│       (bei Chunking)                │
└─────────────────────────────────────┘
          │
          ▼
[ Liste von DetectedClaim-Objekten → PROJ-9 ]
```

### Komponenten-Struktur (Backend)

```
apps/api/app/
├── pipelines/
│   └── claim_detection.py         # Orchestrator (Schritte 1-4)
├── services/
│   ├── text_normalizer.py         # HTML raus, Unicode, Quotes
│   ├── language_detector.py       # franc-min Wrapper
│   ├── anthropic_client.py        # Wrapper mit Retry + ZDR-Header
│   └── claim_validator.py         # Post-Validation
├── schemas/
│   └── claim.py                   # Pydantic: DetectedClaim, DetectionResult
└── prompts/
    └── claim_detection_v1.0.0.md  # aus PROJ-7
```

### Datenmodell (Plain Language)

**DetectedClaim** (wird an PROJ-9 weitergereicht, nicht permanent gespeichert als isolierte Entität):
- Eindeutige ID (UUID)
- Wörtlicher Claim-Text aus dem Input
- Start- und End-Position im Originaltext (Zeichen-Index)
- Claim-Typ: einer von „nährstoffbezogen", „gesundheitsbezogen", „reduktionsbezogen", „wohlbefinden", „krankheitsbezogen"
- Optional: erkannter Nährstoff (z. B. „Vitamin C") oder Substanz (z. B. „Ashwagandha")
- Implizitheits-Flag: explizit oder implizit

**DetectionResult** (wird in der Analyse-Tabelle gespeichert):
- Referenz auf die Analyse
- Liste der DetectedClaims
- Verwendete Prompt-Version (für Nachvollziehbarkeit)
- Modell-Version (z. B. `claude-sonnet-4-6-20261015`)
- Latenz, verbrauchte Input/Output-Tokens
- Ob Chunking verwendet wurde

Gespeichert wird das Ergebnis in der `claims`-Tabelle (Supabase Postgres), das Modell-/Prompt-Metadaten-Set in `analyses` (siehe Datenmodell in Backlog 6).

### Tech-Entscheidungen mit Begründung

| Entscheidung | Wahl | Warum |
|---|---|---|
| LLM-Modell | Claude Sonnet 4.6 | Balance aus Kosten und DE-Qualität; Haiku zu schwach für implizite Claims, Opus reserviert für Evaluation |
| Structured Output | **Tool-Use** statt JSON-Mode | Härtere Schema-Einhaltung; Anthropic bestätigt 99%+ valide Outputs |
| Retry-Library | tenacity | Standard in Python, einfache Backoff-Policies, kompatibel mit async |
| Sprach-Erkennung | franc-min (Client) + langdetect (Server) | Doppelte Prüfung: Client für UX, Server für Security (kann nicht umgangen werden) |
| Text-Normalisierung | bleach (HTML) + ftfy (Unicode) | Bewährte Libraries, behandeln Edge-Cases automatisch |
| Chunking-Strategie | Semantisch nach Absätzen, Max 8.000 Zeichen | Verhindert Claim-Split mitten im Satz; Context-Window-sicher |
| Halluzinations-Check | `claim_text` per `str.find()` im Input | Billig, deterministisch, fängt 90%+ der Halluzinationen |
| Anthropic ZDR | Beta-Header `anthropic-beta: zdr-2024-06-01` | DSGVO-Pflicht, kein Training mit Kundendaten |

### Dependencies (Backend-Seite, neu zu installieren)

- `anthropic` — offizielles SDK mit async-Support
- `pydantic` v2 — Schema-Validation für Claims
- `tenacity` — Retry mit exponentiellem Backoff
- `langdetect` — Server-seitige Sprach-Erkennung
- `bleach` — HTML-Sanitizer
- `ftfy` — Unicode-Reparatur (Mojibake etc.)
- `jinja2` — Prompt-Templating (aus PROJ-7)
- `python-frontmatter` — Prompt-Metadaten (aus PROJ-7)

### Verknüpfte Architektur-Entscheidungen (siehe docs/adr/)
- [ADR-0001](../docs/adr/0001-monorepo-structure.md) Monorepo-Migration
- [ADR-0002](../docs/adr/0002-async-worker-arq.md) Async-Worker-Infrastruktur
- [ADR-0003](../docs/adr/0003-embedding-model.md) Embedding-Modell (betrifft PROJ-9, aber jetzt zu entscheiden)
- [ADR-0004](../docs/adr/0004-reranker-v11.md) Reranker erst in V1.1
- [ADR-0005](../docs/adr/0005-caching-strategy.md) Caching-Strategie

### Risiken & Mitigation (PROJ-8-spezifisch)

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| Precision < 90% im Eval-Set | Mittel | Iteratives Prompt-Tuning, größeres Eval-Set (50+), ggf. Few-Shot-Beispiele |
| Off-by-one bei Chunking-Offsets | Niedrig | Unit-Tests mit Grenzfällen, Positions-Test bei jedem Integration-Test |
| Anthropic-Quota-Limits bei Peaks | Niedrig (MVP) | Rate-Limit eigenerseits (5 parallele Anthropic-Calls pro User), Warteschlange via ARQ |
| Token-Kosten-Explosion bei langen Texten | Mittel | Hard-Cap 20k Zeichen im Input, Token-Budget pro Analyse getrackt, Alarm bei > 50k Tokens |
| Implizite Claims werden übersehen (Recall-Lücke) | Hoch | Eval-Set MUSS implizite Claims abdecken, Recall ≥ 85% als Gate |

### Explizit NICHT im Design enthalten (bewusst ausgeklammert)

- Kein Self-Consistency (mehrfache Evaluation) → V1.1 wenn Eval-F1 < Ziel
- Kein Fine-Tuning → zu früh, nicht kosteneffizient bei Sonnet
- Kein Fallback-LLM bei Anthropic-Outage für Detection → Status-Page + Retry reicht, Credit-Refund
- Keine Multi-Modal-Erkennung (Bild-Claims) → V1.1

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
