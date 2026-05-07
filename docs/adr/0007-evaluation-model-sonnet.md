# ADR-0007: Sonnet 4.6 als Default-Evaluator (statt Opus 4.7)

**Status:** Accepted (2026-05-04)
**Datum:** 2026-05-04
**Kontext:** PROJ-10 (Claim-Evaluation), Cost Optimization

## Kontext

PROJ-10 hatte ursprünglich **Claude Opus 4.7** als Evaluator-Modell
festgelegt - mit der Begründung, juristische Nuancen brauchen das
stärkste Reasoning. Im Inhouse-Betrieb hat sich gezeigt:

- 5–6 Prüfungen verbrennen ~ $10 Anthropic-Credit, der Großteil davon
  Opus-Kosten ($15/M Input, $75/M Output).
- Der HCVO-System-Prompt (~ 2 kTok) wird pro Claim erneut bezahlt -
  mit Prompt Caching (ADR/Implementation seit 2026-05-04) sinkt das
  zwar deutlich, aber Sonnet ist trotzdem 5× günstiger pro Token.
- Die juristische Substanz lebt mittlerweile in der KB
  (1.961 Chunks: 221 EU-Register + 188 Verordnungstext + 12 Urteile +
  1.540 Botanicals + LFGB/LMIV/HWG/UWG-Auszüge) und im Hybrid-Retrieval
  (Qdrant-Vektor + Postgres-FTS + BGE-Reranker). Der LLM klassifiziert
  + verbalisiert, das schwere Reasoning macht das Retrieval.
- Sonnet 4.6 hat in Smoke-Tests dieselben Klassifikationen geliefert
  wie Opus, mit denselben verifizierten chunk_ids als Belegen.

## Entscheidung

**Sonnet 4.6 ist ab sofort Default-Modell für die Evaluation.**

Opus 4.7 bleibt als Konfigurations-Fallback verfügbar
(``ANTHROPIC_MODEL_EVALUATION=claude-opus-4-7``) und wird in V1.1 als
optionale Premium-Stufe für Pro-Tier-Kunden angeboten.

## Folgen

- **Positiv:**
  - **5× geringere Token-Kosten** auf dem teuersten Pipeline-Schritt
  - 2–3× schnellere Latenz pro Claim → spürbar im UI
  - In Kombination mit Prompt Caching (System-Prompt cache_control)
    realistisch **70–85 % Cost-Reduktion** gegenüber dem alten
    Opus-ohne-Cache-Setup
- **Risiko:** Bei sehr widersprüchlichen Quellen (z. B. EU-Register
  erlaubt + BGH engt ein) liefert Sonnet marginal weniger elegante
  Begründungen. Mitigation:
  1. Eval-Set-Gate aus PROJ-9 misst Qualität - bei Drop unter Schwelle
     reaktivieren wir Opus per Env-Var
  2. Frontend-Confidence-Threshold (0.6) fängt schwache Verdicts als
     `unclear` ab, unabhängig vom Modell
- **Neutral:** ADR-0007 dokumentiert die Entscheidung, PROJ-10-Spec ist
  entsprechend aktualisiert.

## Gate-Kriterium für Rückkehr zu Opus

Falls das PROJ-9 Eval-Set einen Precision-Drop > 5 pp gegenüber dem
Opus-Baseline zeigt, schalten wir auf Opus zurück oder bauen einen
Hybrid (Sonnet-Default + Opus-Eskalation bei `confidence < 0.7`).

## Verknüpfte ADRs

- [ADR-0002](0002-async-worker-arq.md) - Anthropic-Pipeline-Setup
- [ADR-0005](0005-caching-strategy.md) - Caching-Strategie (Prompt Cache)
