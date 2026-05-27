# PROJ-19: Erweiterte Rechtsquellen (LFGB / LMIV / HWG / UWG)

## Status: In Progress
**Created:** 2026-05-01
**Last Updated:** 2026-05-27 (B)
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

## Update 2026-05-27 — Deterministisches HWG-Vokabular + Sperrliste

**Trigger:** Kundenfeedback (Ashwagandha-/Reishi-Pillar-Page) zeigte zwei
Lücken, die mit der reinen LLM-Detection nicht zuverlässig gefangen
wurden:
1. HWG-Sprache wie „Heiltradition", „Anwendungsgebiete",
   „Symptom-Tagebuch", „Eindosierung" wurde von der Detection v1.0.0
   nicht konsistent gemeldet.
2. Reformulationen (rewrite_service, smart_apply, polish) **bauten neu**
   Wohlbefindens-/Vitalitäts-/Entspannungs-Sätze ein, weil das Modell
   für „natürlich klingende Marketing-Copy" optimierte — der Text wurde
   nach 1× Durchlauf wieder schlechter, nicht besser.

**Was umgesetzt ist:**

- Neues Modul [`services/forbidden_terms.py`](../apps/api/app/services/forbidden_terms.py)
  mit zwei Regel-Tiers:
  - `hard` (HWG / Pharma-Vokabular, 11 Regeln): Heil-Stamm,
    Symptom-Stamm, Anwendungsgebiet/-bild, Indikation, Eindosierung,
    Therapie, Diagnose, lindern, vorbeugen, medizinische
    Beschwerden-Komposita, Wirkmechanismus.
  - `soft` (HCVO Art. 10 Abs. 3 Wohlbefinden/Vitalität, 10 Regeln):
    Wohlbefinden in jeder Form, Entspannung, Widerstandskraft,
    Abwehrkraft, Vitalität, Boost(en/er), mentale/körperliche
    Anspannung, mentales Wohlbefinden, Förderung des Wohlbefindens.
  - Matcher liefert Position, Severity, Kategorie + dedup-Summary für
    LLM-Retry-Prompts.
- Detection-Pipeline ([`claim_detector.py`](../apps/api/app/services/claim_detector.py))
  ergänzt LLM-Hits jetzt deterministisch um alle Forbidden-Term-Hits,
  die nicht bereits in einem LLM-Claim-Span stecken. HWG-Stems werden
  als `disease_based`, Vorbeugung als `reduction_based`,
  Wohlbefindens-Sprache als `wellbeing_based` klassifiziert.
- Detection-Prompt [`claim_detection_v1.1.0.md`](../apps/api/app/prompts/claim_detection_v1.1.0.md)
  bekommt explizite HWG-Zusatz-Kategorie, damit das LLM den Begriff
  selbst meldet anstatt nur den umliegenden Satz. v1.0.0 bleibt im
  Repo, der Loader wählt automatisch 1.1.0.
- Reformulation-Services hat jeweils einen Post-Write-Guard:
  - [`rewrite_service.py`](../apps/api/app/services/rewrite_service.py):
    Per-Claim-Rewrite scannt Output auf Forbidden-Terms, Retry mit
    expliziter Sperr-Begriffsliste, Drop bei 2. Fehlschlag.
  - [`smart_apply_service.py`](../apps/api/app/services/smart_apply_service.py):
    Paragraph-Rewrite mit identischer Logik; Drop = Original behalten.
  - [`polish_service.py`](../apps/api/app/services/polish_service.py):
    Vergleicht NEUE Hits vor/nach Polish (vor-existierende
    Sperr-Begriffe im User-Input dürfen bleiben), Retry mit
    expliziter Liste, Drop = unpoliertes Original.
- Alle drei Prompts haben jetzt einen statischen `Sperrliste`-Block,
  generiert aus `forbidden_terms.sperrliste_block_for_prompt()`, damit
  das LLM die Liste schon beim ersten Versuch sieht.

**Eval-Trigger:**
Die HWG-Sätze aus dem Kundenfeedback (Ashwagandha + Reishi) sind als
Regressions-Set in [`tests/test_forbidden_terms.py`](../apps/api/tests/test_forbidden_terms.py)
hinterlegt — 44 Tests grün, jede Falle aus dem Kundenbericht ist als
eigener Testfall fixiert.

**Bewusst nicht umgesetzt:**
- Keine ML-basierte Klassifikation der HWG-Treffer — der Marketing-
  Kontext rechtfertigt ein deterministisches Wortlisten-Verbot, eine
  Lernschicht würde nur False-Negative-Risiken einführen.
- Keine UI-Differenzierung HCVO vs. HWG im Frontend — die Treffer
  laufen unter dem bestehenden Card-Schema, mit `disease_based` bzw.
  `wellbeing_based` als Claim-Type. UI-Polish ist V1.1.

## Update 2026-05-27 (B) — Reformulation-Pipeline gegen Boilerplate-Müll + Final Audit

**Trigger:** Zweiter Kundendurchlauf nach (A) zeigte: die Reformulation
zerstörte Tabellen-Zellen, brach FAQ-Antworten thematisch auf
(„Baldrian"-FAQ ohne Baldrian-Antwort) und produzierte generische
Botanical-Floskeln, die bei der Re-Detection wieder als implizite
Claims auftauchten — 43 neue Claims auf einem bereits umgeschriebenen
Text. Außerdem zerlegte die `disease_shortcut`-Regel im Evaluator
neutrale Sicherheits-Header („Schilddrüse", „Autoimmunerkrankungen",
„Leberfunktion") in „Unzulässig: Hoch"-Verdikte ohne Kontextprüfung.

**Was umgesetzt ist:**

- **`disease_shortcut` kontext-aware** ([claim_evaluator.py](../apps/api/app/services/claim_evaluator.py)):
  feuert nur noch bei expliziter Krankheits-Aktions-Sprache (`heilt`,
  `lindert`, `vorbeugt`, `beugt … vor`, `kuriert`, `behandelt`,
  `hilft bei/gegen`, `reduziert das Risiko`, `schützt vor`). Bare
  Organ-/Krankheitsnomen gehen jetzt durch die LLM-Evaluation, die
  Tabellen-Header von Wirkversprechen unterscheiden kann.
- **`[DELETE]` / `[DROP_ROW]`-Marker** in [rewrite_service.py](../apps/api/app/services/rewrite_service.py)
  und [smart_apply_service.py](../apps/api/app/services/smart_apply_service.py):
  Das LLM darf — und soll — explizit Streichen statt fabulieren. In
  Markdown-Tabellenzeilen entfernt `[DROP_ROW]` die gesamte Zeile
  (Header inkl.), in Fließtext zieht `[DELETE]` nur den Satz. Die
  Tabellen-Erkennung läuft heuristisch über `^\s*\|.*\|\s*$`-Zeilen.
- **Anti-Drift im Reformulation-Prompt**: explizite Regel, dass das
  Original-Thema (Schilddrüse, Baldrian, Stress, …) im Output erhalten
  bleiben **muss**. Generische Boilerplate-Sätze sind verboten — wenn
  keine themen-treue Reformulierung möglich ist, wird gestrichen.
- **Tabellen-Header-Kontext im SmartApply-Prompt**: wenn ein Absatz
  als Markdown-Tabellenzeile erkannt wird, bekommt das LLM einen
  zusätzlichen Hinweis-Block, der die linke Spalte als Header
  identifiziert und thematische Treue zur rechten Spalte einfordert.
- **Konvergenz-Check in SmartApply** ([smart_apply_service.py:SmartApplyResult](../apps/api/app/services/smart_apply_service.py)):
  nach dem Rewrite läuft Detection nochmal über den umgeschriebenen
  Text. `residual_claims` listet alle Claims, die noch übrig sind —
  Frontend kann „Nochmal manuell prüfen"-Banner zeigen.
- **Polish härter** ([polish_service.py](../apps/api/app/services/polish_service.py)):
  ausdrückliche Regel „**keine inhaltlichen Ergänzungen** — Polish
  ist Sprach-Korrektur, nicht Marketing". Polish darf Lücken
  übergangs-glätten, aber **nicht** mit neuen Sätzen füllen.
- **Finaler Compliance-Audit (Opus 4.7)** — neuer Service, Prompt,
  Schema, API-Endpoint:
  - [final_audit_service.py](../apps/api/app/services/final_audit_service.py)
    + [final_audit_v1.0.0.md](../apps/api/app/prompts/final_audit_v1.0.0.md)
    + [final_audit.py](../apps/api/app/schemas/final_audit.py)
    + `POST /api/analyses/final-audit`.
  - Single-Pass-Opus-Call über den Gesamttext mit holistischer
    Checkliste: kaputte Tabellen, kaputte Listen, Duplikate,
    verwaiste Sätze, Topic-Drift, FAQ-Antwort verfehlt Frage,
    Sachfehler, zirkulärer Inhalt, impliziter Claim durch Kontext,
    Kontext-Krankheitsbezug, UWG §§ 5/6, HWG-Verstoß, Lazy-
    Disclaimer.
  - Returns strukturierte `AuditFinding`-Liste (severity +
    category + location_quote + finding + recommendation),
    `overall_assessment` und `shippable`-Flag. Read-only — nicht
    autorewrite. Nutzer entscheidet welche Findings angegangen
    werden.

**Test-Regression:**
- [test_disease_shortcut_guard.py](../apps/api/tests/test_disease_shortcut_guard.py)
  — 18 Fälle, jeder Kunden-False-Positive als Regression fixiert
  (Schilddrüse, Autoimmunerkrankungen, Leberfunktion, … bleibt LLM).
- [test_smart_apply_drop_markers.py](../apps/api/tests/test_smart_apply_drop_markers.py)
  — Tabellen-Drop-Logik (`| Schilddrüse | [DROP_ROW] |` → Zeile weg).

**Bewusst nicht umgesetzt:**
- Kein Auto-Apply der Audit-Findings — der Nutzer muss bestätigen
  welche Stellen geändert werden. Anders wäre Kaskaden-Schaden
  vorprogrammiert.
- Keine HMPC-Monografie-Datenbank (für „Traditional Use Registration")
  — der Audit-Prompt verweist auf den Begriff, aber die Verifikation
  bleibt Nutzer-Aufgabe in V1.0.

## Update 2026-05-27 (C) — Frontend-Integration

- API-Client ([api-client.ts](../apps/web/src/lib/api-client.ts)) um
  `runFinalAudit`, `SmartApplyResponse.residual_claims`,
  `isDeleteMarker` erweitert. Vollständige TypeScript-Typen für
  `AuditFinding`, `AuditCategory`, `AuditSeverity`, `FinalAuditResult`.
- Neue Komponente [final-audit-panel.tsx](../apps/web/src/components/app/final-audit-panel.tsx):
  Trigger-Karte → Loading-State → Findings-Liste mit Severity-Badges
  (kritisch/hoch/mittel/niedrig), Kategorie-Labels, Original-Zitat,
  Empfehlung pro Finding. Shippable-Banner oben (grün versandbereit /
  gelb Nacharbeit nötig) mit Executive Summary.
- App-Seite ([page.tsx](../apps/web/src/app/app/page.tsx)):
  - SmartApply-Aufruf liest jetzt `residual_claims` und zeigt
    Konvergenz-Warnung ("N Claims im umgeschriebenen Text noch
    erkannt — bitte manuell prüfen").
  - Final-Audit-Panel ist nach dem Reformulierungs-Workflow
    eingebunden. Läuft über den polished/smart-applied Text wenn
    vorhanden, sonst über den Original-Input.
  - `applyRewritesToText` interpretiert `[DELETE]`-Marker als
    "Satz ersatzlos streichen" und glättet doppelte Whitespaces /
    verwaiste Satzzeichen anschließend.
- EvaluatedClaimCard ([evaluated-claim-card.tsx](../apps/web/src/components/app/evaluated-claim-card.tsx))
  hat jetzt eine eigene **„Streichen empfohlen"-Karte** mit
  `Scissors`-Icon für Claims, deren `rewrite_suggestion == "[DELETE]"`
  ist. Erklärt dem Nutzer, warum keine Reformulierung möglich ist
  (Sinn-Verlust), und bietet den „Streichen"-Button statt
  „Anwenden".
