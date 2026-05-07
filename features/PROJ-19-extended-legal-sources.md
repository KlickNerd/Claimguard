# PROJ-19: Erweiterte Rechtsquellen (LFGB / LMIV / HWG / UWG)

## Status: In Progress
**Created:** 2026-05-01
**Last Updated:** 2026-05-01
**Backlog-Referenz:** ergibt sich aus PROJ-10-System-Prompt-Anforderungen + Nutzer-Feedback

## Dependencies
- PROJ-9 (Hybrid Retrieval) — gemeinsame Qdrant-Collection `regulation`
- PROJ-10 (Claim-Evaluation) — System-Prompt verweist bereits auf diese Normen, hatte sie aber noch nicht in der KB

## User Stories
- Als System möchte ich neben der HCVO auch LMIV / LFGB / HWG / UWG-Auszüge
  verifiziert zitieren können, damit Opus für jede Norm-Klasse einen echten
  chunk_id hat statt aus Trainingswissen zu zitieren.
- Als Nutzer möchte ich, dass Krankheitsbezugs-Verbote und Heilmittelwerbung
  nicht nur als „KI-Schätzung" auftauchen, sondern mit verifiziertem
  Quelltext-Snippet hinterlegt sind.

## Acceptance Criteria
- [x] LMIV Art. 7 (Abs. 1 a–d, Abs. 3) als eigene Chunks indexiert
- [x] LFGB § 11 (Vorschriften zum Schutz vor Täuschung) indexiert
- [x] LFGB § 12 (Verbot krankheitsbezogener Werbung) indexiert
- [x] HWG § 3 (Irreführende Werbung) indexiert
- [x] HWG § 11 (Werbung außerhalb von Fachkreisen, Auszug) indexiert
- [x] UWG § 5 (Irreführende geschäftliche Handlungen, Auszug) indexiert
- [x] System-Prompt von PROJ-10 listet HWG (das tat er vorher nicht)
- [x] EFSA-Botanical-/On-Hold-Kurzliste (67 Einträge) als eigener
      Source-Type `botanical` indexiert (Stand 2026-05-02)
- [x] EFSA On-Hold-Vollliste (1.473 Einträge aus
      `questions-on-hold-botanical-claims.xlsx`) automatisch importiert
      via [`scripts/import_efsa_botanicals.py`](../apps/api/scripts/import_efsa_botanicals.py)
      (Stand 2026-05-02). Insgesamt **1.540 indexierte Botanicals**.
- [ ] BVL-Stellungnahmen (V1.1)

## Implementation Notes (2026-05-01)

**Was umgesetzt ist:**
- Neues Daten-File [`data/regulatory_excerpts.json`](../apps/api/data/regulatory_excerpts.json)
  mit redaktionellen Paraphrasen der wichtigsten Norm-Stellen — mit
  expliziten Quellen-URLs auf `gesetze-im-internet.de` bzw. Eur-Lex zur
  Verifikation. Volltexte stehen explizit nicht im JSON, weil amtliche
  Norm-Texte zwar gemeinfrei sind (§ 5 UrhG), aber wir lieber kuratierte
  Auszüge mit konsistenter Snippet-Länge fahren.
- Indexer [`scripts/index_knowledge_base.py`](../apps/api/scripts/index_knowledge_base.py)
  hängt diese Einträge an die bestehende `regulation`-Collection als
  zusätzliche Punkte an. Damit sie nicht beim nächsten Re-Index der reinen
  HCVO-Chunks gelöscht werden, läuft die Erweiterung im selben Indexer-
  Schritt mit derselben Quellen-Liste.
- System-Prompt [`claim_evaluation_system_v1.0.0.md`](../apps/api/app/prompts/claim_evaluation_system_v1.0.0.md)
  ist um HWG (§§ 3, 11) als eigenen Punkt im Geltungs-Bereich-Block
  erweitert.

**Bewusst nicht im MVP:**
- **Keine Volltexte**, nur Paraphrasen + Quellen-URL — vermeidet
  Doppelaufwand, weil die kanonischen Texte sich ändern (z. B. UWG-Novelle)
  und wir sonst nachpflegen müssten.
- **EFSA On-Hold-Liste** (~ 1.500 Botanicals) bleibt separater Task —
  der Importer ist analog zu PROJ-4 zu bauen (XLSX-Parser, eigene
  Collection oder als payload-Filter in eu_claims).
- **BVL-Stellungnahmen** kommen in V1.1, weil die Datenpflege ohnehin
  Kontaktpflege mit dem BVL erfordert.

## Beobachtungen aus dem Smoke-Test 2026-05-01

Bei einem Test-Input mit klaren HWG-Triggern („Apotheker empfohlen",
„ärztliches Gutachten", „keine Nebenwirkungen") wurden zwar alle Claims
korrekt als `forbidden` erkannt, aber die **HWG-Auszüge landeten nicht
zuverlässig in den Top-5-Evidence-Hits**. Das embedding-only-Retrieval
zog statt dessen HCVO- und case_law-Hits, weil die nutrient-/HCVO-
Chunks in der `regulation`-Collection mit 179 Stück das semantische
Gewicht dominieren.

**Update 2026-05-02:** Mit dem PROJ-9-Postgres-FTS-Pfad ist diese
Limitation **gefixt**. Im erneuten Smoke-Test mit identischem Input
landet HWG § 11 Abs. 1 als **Top-1-Evidence**, und „Apotheker
empfohlen" zieht zusätzlich OLG Köln 6 U 84/14 (Arzt-Empfehlung) als
verifizierten case_law-Hit. Schlüsselwörter wie „Apotheker",
„Gutachten", „Nebenwirkungen" greifen jetzt direkt durch.

## Technical Requirements
- Indexer baut Einträge mit `source_type: "regulation"` und
  `regulation_id` = Norm-Schlüssel (`LFGB`, `LMIV`, `HWG`, `UWG`).
- chunk_ids als Slug, z. B. `lfgb-12-1`, `lmiv-art7-3`, `hwg-3-1`.
- Snippets <= 600 Zeichen, damit der Prompt-Footprint pro Hit konstant
  bleibt.

## Open Questions
- Reicht eine globale `regulation`-Collection oder separate
  Sub-Collections pro Norm-Klasse? → MVP: globale Collection, RRF-Rang
  funktioniert auf gemischtem Pool gut.
- Per-Norm-Filter im Frontend (User: „nur LMIV-Treffer zeigen")? → V1.1.

## Update 2026-05-02 — Botanical-/EFSA-On-Hold-Kurzliste

**Was umgesetzt ist:**
- Pydantic-Schema [`schemas/botanical.py`](../apps/api/app/schemas/botanical.py)
  (`BotanicalEntry`: scientific_name, common_name_de, common_names,
  status, health_relationship, pending_claim_de, summary, risk_notes,
  source_url).
- Daten-Datei [`data/botanicals.json`](../apps/api/data/botanicals.json)
  mit **67 redaktionell paraphrasierten Einträgen** zu den am häufigsten
  in DACH-Supplements genutzten Botanicals und Nischen-Substanzen
  (Curcuma, Ginkgo, Ashwagandha, Mariendistel, Reishi, Cordyceps,
  Glucosamin, Resveratrol, CoQ10, Hyaluron, Kollagen, Kava,
  Johanniskraut, …). Pro Eintrag Status (`on_hold` / `non_authorised` /
  `authorised`), Übergangsregelung-Hinweise, Arzneimittel-Konkurrenz-
  Flags, BGH-/BVL-Risiken.
- Neue Qdrant-Collection `botanicals` + neuer
  `RetrievalSourceType: "botanical"` (Backend + Frontend). Indexer
  schreibt parallel in Postgres-FTS.
- System-Prompt von PROJ-10 hat jetzt einen dedizierten On-Hold-Block:
  bei Botanical-Treffern Default `borderline`, bei `non_authorised`
  → `forbidden`, Reasoning-Anweisung Übergangsregime + Arzneimittel-/
  BVL-Risiken zu nennen.
- Frontend ([`evaluated-claim-card.tsx`](../apps/web/src/components/app/evaluated-claim-card.tsx))
  zeigt Botanical-Hits mit `Leaf`-Icon und Label „Botanical (EFSA)".

**Smoke-Test 2026-05-02:** Multi-Botanical-Input
(Ashwagandha-gegen-Stress, Kurkuma-Leber, Ginkgo-Gedächtnis,
Mariendistel-Leber, Cranberry-Blasenentzündung):
- Jeder Claim bekommt den passenden Botanical-Hit als **Top-1-Evidence**
  mit `verified=true`.
- Opus liefert smarte Reformulierungen mit zugelassenen Vitamin-/
  Cholin-/DHA-Begleitclaims, exakt wie im System-Prompt vorgesehen.

## Update 2026-05-02 — EFSA On-Hold-Vollliste (1.473 Einträge)

**Was umgesetzt ist:**
- Neuer Parser [`services/efsa_botanicals_parser.py`](../apps/api/app/services/efsa_botanicals_parser.py)
  liest `questions-on-hold-botanical-claims.xlsx` (Sheet1, 1.473 Zeilen
  nach Dedup auf APPLIC. No) ein und mappt jede Zeile auf ein
  `BotanicalEntry` mit `chunk_id = efsa-<applic_no>-<food-slug>`,
  Status `on_hold`, Original-Wortlaut als `pending_claim_en`,
  Antragsteller + FoodSector als `risk_notes`.
- Neuer CLI-Importer [`scripts/import_efsa_botanicals.py`](../apps/api/scripts/import_efsa_botanicals.py)
  schreibt das Ergebnis nach `data/botanicals_efsa.json`.
- Indexer mergt jetzt `botanicals.json` (67 kuratierte) + `botanicals_efsa.json`
  (1.473 EFSA), dedupliziert auf `chunk_id` (kuratierte schlagen EFSA bei
  Konflikt). Resultierend **1.540 Botanical-Einträge** in Qdrant +
  Postgres-FTS.
- XLSX-Quelle: direkt vom EFSA-CDN als Stable-URL
  `https://www.efsa.europa.eu/sites/default/files/2021-06/questions-on-hold-botanical-claims.xlsx`
  (~ 870 KB, last-modified 2024-11). Datei liegt unter
  `apps/api/data/questions-on-hold-botanical-claims.xlsx` und wird via
  curl gepullt — Re-Pull nur nötig, wenn EFSA aktualisiert.

**Smoke-Test 2026-05-02 (Maca + Tribulus + Yamswurzel):**
- „Yamswurzel + hormonelles Gleichgewicht" → forbidden, kuratierter
  `dioscorea-villosa-hormone` Top-1 ✓
- „Maca-Wurzel sorgt für Energie & Libido" → forbidden, **5 Botanical-
  Hits gleichzeitig** (kuratiert + EFSA-Anträge in EN, FR, PL via
  multilinguales Embedding) ✓
- „Tribulus steigert Potenz" → forbidden, kuratierter Eintrag +
  EFSA-Antrag 2831 verifiziert ✓

**Stand der KB nach diesem Update:** **1.961 Wissens-Chunks**
(221 EU-Register + 188 Verordnungs-Chunks + 12 Urteile + 1.540 Botanicals).
