# ADR-0003: Embedding-Modell jina-embeddings-v3 (self-hosted)

**Status:** Accepted (2026-04-24)
**Datum:** 2026-04-23
**Kontext:** PROJ-4/5/6 (Wissensbasis-Indexierung), PROJ-9 (Hybrid Retrieval)
**Verwandte Backlog-Frage:** 5.3 Punkt 2

## Kontext

Für die Vektor-Suche in Qdrant brauchen wir ein Embedding-Modell. Anthropic bietet aktuell kein dediziertes Embedding-Modell. Die Wahl beeinflusst:
- **Retrieval-Qualität** (dominanter Faktor für F-Score der Evaluation)
- **DSGVO-Konformität** (wohin fließen User-Claim-Texte zur Embedding-Berechnung?)
- **Laufende Kosten**

Drei realistische Optionen:

## Optionen

| Kriterium | OpenAI `text-embedding-3-large` | jina-embeddings-v3 (self-hosted) | voyage-2 / cohere-multilingual |
|---|---|---|---|
| DE-Qualität (MTEB-DE) | sehr gut | sehr gut (Top-3) | gut |
| EU-Hosting möglich? | **Nein (US-Cloud)** | **Ja (Docker auf VPS)** | Nein |
| DSGVO-Aufwand | AV + Art. 49 Rechtfertigung nötig | Keine Drittübermittlung | dito OpenAI |
| Kosten (Monat, ~20k Analysen) | ~ 40 € | Infra-Anteil (geschätzt 10–20 €) | ~ 50 € |
| Lizenz kommerziell | OK (bezahlt) | CC-BY-NC-4.0 für Weights, API-Nutzung OK | OK (bezahlt) |
| Dimension | 3072 | 1024 | 1024 |
| Latenz | ~ 200 ms (Netz) | ~ 50 ms (local) | ~ 200 ms |

## Empfehlung

**jina-embeddings-v3 self-hosted** via Jina-Docker-Image auf dem Hostinger-VPS.

### Gründe
1. **DSGVO:** Keine Drittland-Übermittlung, kein separater DPA, keine Diskussion mit Kunden über US-Zugriff. Bei Gesundheitsdaten-nahe Texten ist das ein harter Vorteil für Enterprise-Zielgruppe (F-300er-Roadmap).
2. **Qualität:** jina-v3 ist multilingual trainiert mit explizitem DE-Fokus, auf MTEB-German in den Top-3. Für Claim-Matching gegen Rechtstexte ausreichend.
3. **Latenz:** Lokaler Call spart ~ 150 ms pro Claim — bei 20 Claims pro Analyse merkbar.
4. **Kosten:** Embedding-Kosten fallen bei Anzahl Analysen + KB-Indexierung. Self-Host ist bei aktuellen Preisen günstiger, spätestens ab ~ 10k Analysen/Monat.
5. **Fallback-Plan:** Sollte Qualität im Eval nicht reichen (Recall < 85 % bei PROJ-9), Fallback auf OpenAI mit expliziter Kunden-Transparenz („Bei Nutzung unseres Pro-Plans werden Ihre Claim-Texte an einen EU-US-zertifizierten Anbieter übermittelt, siehe DS-Erklärung").

## Folgen

- **Positiv:** Klare DSGVO-Story, geringere laufende Kosten bei Skalierung, niedrigere Latenz.
- **Negativ:**
  - Zusätzlicher Container auf VPS (~ 2 GB RAM, ein CPU)
  - Self-Host-Verantwortung (Patches, Monitoring)
  - Erst-Indexierung der KB (~ 5.000 Chunks) dauert 5–15 Min
- **Risiko:** Wenn MTEB-Benchmarks nicht die reale Claim-Matching-Qualität widerspiegeln — deshalb **Gate in PROJ-9**: Recall gegen Eval-Set messen, bevor wir uns final binden.

## Gate-Kriterium für die Entscheidung

Vor Produktion:
- 50 Claim-Text-Eingaben gegen indexierte KB testen
- Messen: Wurden die rechtlich relevanten Quellen in Top-8 zurückgegeben?
- **Schwelle:** Recall@8 ≥ 0.85. Darunter: Switch auf OpenAI (inkl. DSGVO-Nachdokumentation).

## Open Items
- Jina-Docker-Image Lizenz-Terms noch mal gegen geschäftliche Nutzung prüfen (kommerziell via API-Plan oder ab v3 Open-Source?)
- Alternative zu prüfen: `bge-m3` self-hosted (Apache-2-Lizenz, multilingual, ebenfalls EU-konform). Falls Jina-Lizenz kommerziell problematisch wäre.
