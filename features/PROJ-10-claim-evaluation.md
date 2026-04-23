# PROJ-10: Claim-Evaluation

## Status: Architected
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-012

## Dependencies
- PROJ-7 (Prompt-Management)
- PROJ-8 (Claim-Detection)
- PROJ-9 (Hybrid Retrieval)

## User Stories
- Als Nutzer möchte ich pro Claim eine klare Bewertung (erlaubt / verboten / grenzwertig / unklar) sehen, damit ich handeln kann.
- Als Nutzer möchte ich die juristische Begründung in verständlicher Sprache lesen, damit ich auch ohne Rechtskenntnisse entscheiden kann.
- Als Nutzer möchte ich einen konkreten Reformulierungsvorschlag erhalten, damit ich nicht bei Null anfangen muss.
- Als Nutzer möchte ich bei unsicheren Fällen einen klaren „unclear"-Hinweis bekommen, damit ich keine falsche Sicherheit habe.

## Acceptance Criteria
- [ ] Modell: Claude Opus 4.7
- [ ] Strukturiertes JSON-Output via Pydantic-Schema `ClaimEvaluation`:
  - `claim_id` (UUID, referenziert Detection-Output)
  - `status` (enum: `allowed`, `forbidden`, `borderline`, `unclear`)
  - `confidence` (float 0–1)
  - `legal_basis` (Liste von `{source_type, reference, snippet, url}`)
  - `reasoning` (string, DE, 2–5 Sätze, für Laien verständlich)
  - `rewrite_suggestion` (string, DE, nullable — nur bei `forbidden`/`borderline`)
  - `risk_level` (enum: `low`, `medium`, `high`)
- [ ] `status = unclear` wenn `confidence < 0.6`, begleitet von Hinweis „Manuelle Prüfung empfohlen"
- [ ] `rewrite_suggestion` enthält mindestens 1 Alternativ-Formulierung, bei Bedarf bis zu 3
- [ ] Input für LLM: Claim + Top-8 Retrieval-Treffer (PROJ-9) + System-Prompt mit HCVO-Grundprinzipien
- [ ] Prompt versioniert (PROJ-7), initiale Version `claim_evaluation_v1.0.0`
- [ ] Max Output Tokens: 2000 pro Claim
- [ ] Latenz p95 ≤ 20 s pro Claim

## Edge Cases
- **Retrieval liefert 0 Treffer:** LLM bekommt Hinweis „keine Fundstellen", muss `unclear` zurückgeben
- **Widersprüchliche Fundstellen (z.B. EU-Register erlaubt, OLG-Urteil verbietet):** LLM muss Widerspruch im `reasoning` adressieren, `status = borderline`, `risk_level = medium/high`
- **Claim bezieht sich auf Substanz ohne EU-Eintrag (z.B. Botanicals on-hold):** `status = borderline`, Hinweis auf On-Hold-Liste
- **Krankheitsbezogener Claim (disease_based):** Immer `forbidden` (Art. 7 HWG), `risk_level = high`
- **LLM verweigert Antwort (z.B. bei heiklen Themen):** Status `unclear`, Log-Alarm
- **LLM liefert ungültiges JSON:** 1x Retry mit verschärftem Prompt, dann `unclear` + Alarm
- **Legal Basis referenziert nicht-existente Quelle:** Post-Validation prüft `chunk_id` gegen DB, ungültige Refs werden entfernt
- **Claude-Opus-Outage:** 3x Retry, dann Fallback: Sonnet 4.6 mit Warning im Report „Bewertung mit Reserve-Modell"
- **Confidence 0.99 aber Reasoning leer:** Schema-Validation fängt das, `unclear`

## Technical Requirements
- Anthropic SDK, `claude-opus-4-7` Model-ID
- Zero-Data-Retention-Header
- Pydantic v2 Strict-Mode für Output-Schema
- Strukturiertes Output via Tool-Use (nicht nur JSON-Mode)
- Parallel-Evaluation aller Claims einer Analyse (max. 5 gleichzeitig pro User, Rate-Limit gegen Anthropic-Quota)
- Token-Budget pro Analyse tracken, Alarm bei > 100k Tokens

## Open Questions
- Self-Consistency: Claim 3x evaluieren und Mehrheit nehmen? → **MVP: nein (Kosten), V1.1 bei niedrigem F1**
- Separate Prompts pro `claim_type` (disease/nutrient/wellbeing)? → **MVP: ein Prompt mit Branching, V1.1 ggf. splitten**
- Caching bei identischem (Claim + Retrieval)-Hash? → **V1.1**
- Legal-Review-Loop: bei `high risk` menschlicher Review? → V2 Enterprise-Feature

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)

### Zielbild & Einordnung
PROJ-10 ist **Stufe 3 (final) der Analyse-Pipeline**. Input: DetectedClaim (aus PROJ-8) + Retrieval-Treffer (aus PROJ-9). Output: `ClaimEvaluation` mit Status, Confidence, Begründung, Rechtsgrundlagen, Reformulierung. Das ist das Feature, das dem Nutzer Wert liefert — alles vorher war Vorbereitung.

### Evaluation-Flow pro Claim

```
[ DetectedClaim + RetrievalResult ]
          │
          ▼
┌─────────────────────────────────────┐
│  1. Prompt-Assembly                 │
│     - System: HCVO-Grundprinzipien  │
│       + Claim-Typ-Regeln            │
│     - User: Claim + Top-8 Snippets  │
│     - Tool-Schema: ClaimEvaluation  │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  2. LLM-Call                        │
│     - Claude Opus 4.7               │
│     - Tool-Use (structured output)  │
│     - ZDR-Header                    │
│     - Retry 3x mit Backoff          │
│     - Fallback: Sonnet 4.6          │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  3. Post-Validation                 │
│     - Schema (Pydantic strict)      │
│     - legal_basis.chunk_id in KB?   │
│     - confidence < 0.6 → unclear    │
│     - Halluzinations-Check Rewrite  │
└─────────────────────────────────────┘
          │
          ▼
[ ClaimEvaluation ] → persistiert in Postgres
```

Alle Claims einer Analyse werden parallel evaluiert (mit Semaphore-Limit), nicht seriell.

### Komponenten-Struktur

```
apps/api/app/
├── pipelines/
│   └── evaluation.py             # Orchestrator, parallel über Claims
├── services/
│   ├── anthropic_client.py       # Shared mit PROJ-8, Modell als Argument
│   └── evaluation_validator.py   # Post-Validation
├── schemas/
│   └── evaluation.py             # ClaimEvaluation Pydantic-Schema
└── prompts/
    ├── claim_evaluation_v1.0.0.md      # Haupt-Prompt
    └── claim_evaluation_system_v1.0.0.md  # System-Prompt mit HCVO-Regeln
```

### Datenmodell (Plain Language, aus Backlog 6)

**ClaimEvaluation**:
- Referenz auf den zugehörigen DetectedClaim
- Status: `allowed`, `forbidden`, `borderline`, `unclear`
- Confidence-Score (0–1). Unter 0.6 wird Status auf `unclear` überschrieben.
- Legal Basis: Liste von {Quelltyp, Referenz, Snippet, URL} — MUSS auf echte Chunks aus PROJ-9 zeigen
- Reasoning: 2–5 Sätze Begründung auf Deutsch, Laien-verständlich
- Rewrite-Vorschlag: 1–3 Alternativ-Formulierungen (nur bei `forbidden`/`borderline`)
- Risiko-Level: `low`, `medium`, `high`
- Modell-Version und Prompt-Version zur Nachvollziehbarkeit

Gespeichert in der `claims`-Tabelle (Supabase), verknüpft mit der Analyse.

### Tech-Entscheidungen mit Begründung

| Entscheidung | Wahl | Warum |
|---|---|---|
| LLM-Modell | Claude Opus 4.7 | Höchste Reasoning-Qualität bei juristischen Nuancen; Sonnet reicht nicht für Abwägungsfragen (z. B. widersprüchliche Fundstellen) |
| Fallback-Modell | Sonnet 4.6 | Nur bei Opus-Outage, mit sichtbarer Warnung im Report |
| Structured Output | Anthropic Tool-Use | Härtere Schema-Durchsetzung als JSON-Mode |
| Parallel-Strategie | `asyncio.gather` mit `asyncio.Semaphore(5)` pro User | Schont Anthropic-Rate-Limit, bleibt schnell |
| Prompt-Split | System (HCVO-Regeln) + User (Claim+Snippets) | System-Prompt cacheable (Anthropic Prompt-Caching reduziert Kosten ~ 50 %) |
| Confidence-Threshold | 0.6 | Unter dieser Schwelle verliert die Empfehlung Aussagekraft — „unclear" schützt Nutzer |
| Halluzinations-Check | `legal_basis.chunk_id` gegen KB prüfen | Einfach, fängt Erfindungen zuverlässig |
| Max Output Tokens | 2.000 pro Claim | Reicht für Reasoning + 3 Rewrites, deckelt Kosten |
| Disease-Claim-Shortcut | Regelbasierte Post-Check: `claim_type = disease` → erzwingt `forbidden` | HWG ist eindeutig, LLM-Unsicherheit unnötig |

### Dependencies

- `anthropic` (bereits aus PROJ-8)
- `pydantic` v2 (bereits)
- `tenacity` (bereits)

### Prompt-Caching-Strategie (Anthropic-Feature)

Opus 4.7 unterstützt Prompt-Caching. Wir strukturieren so:
- System-Prompt (lang, ändert sich pro Prompt-Version) → cache-able
- User-Input (kurz, pro Claim unterschiedlich) → nicht cache-able

Erwartete Kostenreduktion: ~ 40–60 % bei typischer Analyse mit 5–15 Claims. Der erste Claim einer Analyse „heizt" den Cache, die restlichen profitieren.

### Verknüpfte ADRs
- [ADR-0002](../docs/adr/0002-async-worker-arq.md) Worker für Pipeline
- [ADR-0005](../docs/adr/0005-caching-strategy.md) Anthropic Prompt-Caching (nicht im Caching-ADR explizit, aber im Einklang mit „nur was wirklich spart")

### Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| Opus liefert ungültiges JSON | Niedrig | Tool-Use statt JSON-Mode, 1× Retry mit Schärfungs-Prompt, dann `unclear` |
| Fehlerhafte Legal-Basis-References (Halluzination) | Mittel | Post-Validation entfernt ungültige Refs; Minimum 1 gültige Ref sonst `unclear` |
| Widersprüchliche Fundstellen führen zu `unclear` statt Bewertung | Mittel | System-Prompt instruiert explizit: Widersprüche im `reasoning` adressieren, `borderline` mit `medium`/`high` Risk |
| Opus-Kosten-Explosion bei Traffic-Peaks | Mittel | Token-Budget pro Analyse getrackt; Hard-Abort bei > 100k Tokens; Sonnet-Fallback wenn Opus rate-limited |
| Opus-Outage parallel zu Sonnet-Outage | Sehr niedrig | Credit-Refund, Status-Page, User-Mail bei Wiederverfügbarkeit |
| Rewrite-Vorschlag verletzt selbst die HCVO | Mittel | Prompt-Instruktion „Rewrite darf selbst kein `forbidden` Claim sein"; Eval-Set erfasst das |

### Explizit nicht im Design
- Kein Self-Consistency (3× evaluieren, Mehrheit nehmen) — V1.1 wenn F1 < Ziel
- Kein Legal-Review-Loop (Mensch im Hot-Path) — V2 Enterprise-Feature
- Kein Streaming der Teilergebnisse an den Client — Analyse erscheint komplett am Ende
- Kein Feedback-Loop (User-Daumen-runter trainiert Modell) — DSGVO-heikel, V2

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
