# ADR-0005: Caching-Strategie — minimaler Embedding-Cache im MVP

**Status:** Accepted (2026-04-24)
**Datum:** 2026-04-23
**Kontext:** PROJ-4/5/6 (KB-Indexierung), PROJ-9 (Retrieval)
**Verwandte Backlog-Frage:** 5.3 Punkt 5

## Kontext

Mögliche Cache-Ebenen:
1. **Analysis-Cache:** identische User-Inputs → gleiche Ergebnisse liefern
2. **Embedding-Cache:** identische Texte (Claims + KB-Chunks) nicht doppelt einbetten
3. **Retrieval-Cache:** gleiche Claim-Query gegen gleiche KB-Version → gleiche Top-K

Redis ist wegen ADR-0002 bereits verfügbar — eine Cache-Infrastruktur kostet also nichts Neues.

## Analyse pro Ebene

### Analysis-Cache
- User-Inputs sind nahezu nie identisch (ein Komma, ein Wortwechsel → anderer Hash)
- Selbst wenn gleich: User erwartet eigenes Credit-Handling, eigenen Zeitstempel
- **Nutzen: nahe null.** NICHT IM MVP.

### Embedding-Cache
- Während KB-Indexierung: viele ähnliche Chunks (z. B. Paraphrasen aus Urteilen)
- Bei Claim-Embedding während Retrieval: einige Claim-Texte wiederholen sich aus Vorlagen
- Spart direkt Embedding-Kosten und Latenz
- **Nutzen: messbar, einfach implementierbar.** MVP.

### Retrieval-Cache
- Braucht KB-Version als Teil des Cache-Keys
- Cache-Invalidierung bei KB-Update komplex
- Nutzen erst ab hohen Volumina
- **Nutzen: gering im MVP.** V1.1.

## Empfehlung

**Nur Embedding-Cache im MVP.** Key = `sha256(text + model_version)`, Value = Vektor als float32-Array (gepackt). TTL 30 Tage. Kapazität im Redis begrenzen (LRU, max. 500 MB).

Alle anderen Cache-Ebenen werden in V1.1 evaluiert, wenn echte Production-Metriken vorliegen.

## Folgen

- **Positiv:**
  - Spürbare Kosten- und Latenz-Einsparung bei KB-Updates und Re-Indexierung
  - Einfach implementiert, geringe Fehlerfläche
- **Negativ:** Zusätzliche Redis-Speichernutzung (LRU begrenzt)
- **Risiko:** Vergessener Cache-Bust bei Embedding-Modell-Wechsel → Modell-Version ist Teil des Cache-Keys, damit das nicht passiert.
