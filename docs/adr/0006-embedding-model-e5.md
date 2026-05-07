# ADR-0006: Embedding-Modell `intfloat/multilingual-e5-base` (in-process)

**Status:** Accepted (2026-05-01)
**Datum:** 2026-05-01
**Supersedes:** [ADR-0003](0003-embedding-model.md)
**Kontext:** PROJ-4/5/6 (Wissensbasis-Indexierung), PROJ-9 (Hybrid Retrieval)

## Kontext

ADR-0003 hatte `jina-embeddings-v3` als separat per Docker gehostetes
Embedding-Modell festgelegt. Beim Beginn der PROJ-9-Implementierung haben
sich zwei Punkte als problematischer herausgestellt als gedacht:

1. **`trust_remote_code` ist Pflicht** für jina-v3 in der `transformers`-
   Pipeline. Das ist ein expliziter Code-Execution-Trust, der bei jedem
   Modell-Update neu zu prüfen wäre — operationaler und reviewtechnischer
   Overhead, den wir im Solo-Setup nicht tragen wollen.
2. **Separater Container** kostet uns einen weiteren langlebigen Service
   auf dem VPS (~ 2 GB RAM), inklusive Health-Check, Restart-Policy,
   Caddy-Routing für Embedding-HTTP. Für ~ 400 KB-Chunks und ein paar
   Dutzend Queries pro Analyse ist der zusätzliche Hop reine Komplexität.

Während des Bauens war außerdem klar, dass die KB im MVP unter 5.000
Einträgen bleibt — Embedding-Throughput ist kein Engpass.

## Entscheidung

**`intfloat/multilingual-e5-base` direkt im FastAPI-Prozess**, geladen
über `sentence-transformers` als Lazy-Singleton.

### Gründe

| Kriterium | E5-Base | jina-v3 |
|---|---|---|
| Lizenz | Apache-2.0 (frei kommerziell) | CC-BY-NC-4.0 für Weights |
| `trust_remote_code` | nein | **ja** |
| Größe | ~ 440 MB | ~ 1.1 GB |
| Embedding-Dim | 768 | 1024 |
| MTEB-DE | Top-Tier (multilingual) | Top-3 |
| Deployment | In-process, kein extra Container | Eigener Docker-Container |
| Latenz | < 30 ms (lokal, kein HTTP) | ~ 50 ms (HTTP-Hop) |
| ARM64 | nativ | nativ |

E5 erwartet Instruction-Prefixes (`query: ` / `passage: `). Das ist im
Wrapper [embedding_service.py](../../apps/api/app/services/embedding_service.py)
kapselt, sodass Aufrufer es nicht wissen müssen.

## Folgen

- **Positiv:**
  - Apache-2.0 — null Lizenz-Risiko bei kommerzieller Nutzung
  - Ein Service weniger auf dem VPS (kein Embedding-Container, kein
    Caddy-Routing, kein Health-Check)
  - Kein `trust_remote_code` — sauberer Audit-Pfad
  - Kleinere Vektoren (768 vs. 1024) reduzieren Qdrant-Speicher um ~ 25 %
- **Negativ:**
  - FastAPI-Prozess hält ~ 500 MB RAM für das Modell. Bei mehreren
    Worker-Replicas multipliziert sich das. → akzeptabel auf dem VPS,
    bei Bedarf in V1.1 auf einen dedizierten Worker mit ARQ verlagern.
  - Erst-Boot lädt das Modell (~ 5–10 s). Nicht kritisch, weil per
    Lazy-Singleton hinter dem ersten Embed-Call.
- **Nicht negativ:** EU-Hosting bleibt erhalten — wir laden Weights von
  Huggingface und cachen sie auf dem VPS. Keine Drittland-Übermittlung
  von User-Daten.

## Gate-Kriterium (übernommen aus ADR-0003)

Vor Produktion gegen das PROJ-9-Eval-Set messen:

- 50 Claim-Eingaben, manuell annotierte Gold-Quellen
- **Recall@8 ≥ 0.85**: relevante KB-Quelle landet in Top-8

Unterhalb der Schwelle: Eskalation in dieser Reihenfolge:
1. Auf `multilingual-e5-large` upgraden (~ 1.1 GB, gleiches API)
2. Reranker (BGE-Reranker-v2) gemäß ADR-0004 vorziehen
3. Erst dann: kommerzieller Anbieter mit DSGVO-Klärung

## Operative Hinweise

- Modell-Cache: `~/.cache/huggingface` auf dem VPS persistieren
  (Volume-Mount), damit Container-Restart nicht erneut 440 MB zieht.
- Modellname per Env-Var `EMBEDDING_MODEL` überschreibbar — falls wir
  ohne Code-Deploy auf E5-Large wechseln müssen.
- Embedding-Dimension ist auf 768 hardcodiert in
  [embedding_service.py](../../apps/api/app/services/embedding_service.py).
  Bei Modell-Wechsel: Konstante anpassen + Qdrant-Collections neu
  aufsetzen (Index-Skript ist idempotent).
