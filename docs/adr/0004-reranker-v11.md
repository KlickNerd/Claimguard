# ADR-0004: Reranker erst in V1.1 einführen

**Status:** Revisited 2026-05-04 — Reranker doch im MVP, BGE-Reranker-v2-m3 in-process
**Datum:** 2026-04-23
**Kontext:** PROJ-9 (Hybrid Retrieval)
**Verwandte Backlog-Frage:** 5.3 Punkt 3

> **Update 2026-05-04:** In der ersten Inhouse-Nutzung zeigte sich, dass
> die multilingualen Cosine-Scores für deutsche Claims fast immer im
> Band 0.78–0.86 landen — die RRF-Reihenfolge fügte deshalb regelmäßig
> thematisch fragwürdige Treffer (z. B. „Phosphor"-EU-Eintrag bei einer
> Vitalpilze-Werbung) in die Top-3-Anzeige ein. Wir haben **BGE-Reranker-v2-m3
> in-process** (Apache-2.0, ~ 568 MB) hinter die RRF-Fusion gesetzt und die
> Originalentscheidung damit revidiert. Der Reranker läuft im selben
> FastAPI-Prozess wie das E5-Embedding (kein extra Container), siehe
> [`app/services/reranker.py`](../../apps/api/app/services/reranker.py).
> Latenz +50–100 ms pro Claim, Top-3-Qualität deutlich verbessert.

## Kontext

Ein Reranker ordnet nach der ersten Hybrid-Suche (Vektor + Keyword) die Top-K-Treffer semantisch neu. Das hebt in der Regel Recall@Top-3 um 10–20 %. Für die Claim-Evaluation (PROJ-10) zählt aber **die Qualität der Top-8 Treffer insgesamt**, nicht nur der erste Platz — die RRF-Fusion im MVP liefert dort bereits gute Ergebnisse.

## Optionen

### Option A: Cohere Rerank 3.5
- Kommerziell, API-basiert, sehr gute multilinguale Qualität
- **US-Cloud** → DSGVO-Problem analog zu OpenAI
- Kosten: ~ 1 $ pro 1.000 Queries

### Option B: BGE-Reranker-v2-m3 self-hosted
- Apache-2-Lizenz, CPU-fähig, multilingual
- Zusätzlicher Container auf VPS (~ 1 GB RAM)
- Qualität gut, aber merklich unter Cohere

### Option C: Kein Reranker im MVP (empfohlen)
- Nur RRF-Fusion aus Vektor + Keyword
- Einfacher, schneller, kein Drittanbieter
- Eval-Set entscheidet, ob es reicht

## Empfehlung

**Option C — kein Reranker im MVP.** RRF-Fusion mit vernünftiger Per-Source-Balance reicht in der Regel für Knowledge-Bases in der Größenordnung (wenige 1000 Chunks). Ein Reranker fügt Komplexität, Latenz und Kosten hinzu, ohne dass der Business-Case vorher validiert ist.

### Trigger für V1.1-Upgrade
- Wenn das Eval-Set in PROJ-9 zeigt: Recall@8 < 85 %, obwohl relevante Chunks in der KB sind → BGE-Reranker self-hosted nachschieben (nicht Cohere wegen DSGVO).

## Folgen

- **Positiv:** Ein Moving Part weniger im MVP, niedrigere Latenz (~ 100 ms Ersparnis pro Claim)
- **Negativ:** Kleinere Risk-Window bei suboptimalem Retrieval — deshalb Eval-Gate scharf setzen.
