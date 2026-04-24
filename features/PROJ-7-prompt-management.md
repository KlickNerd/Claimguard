# PROJ-7: Prompt-Management

## Status: In Progress
**Implementierungsstand:** `PromptLoader` mit YAML-Frontmatter-Parsing, semantischem Versions-Sort (1.10.0 > 1.2.0) und Jinja2 StrictUndefined live. Erste Prompts `claim_detection_v1.0.0.md` (Sonnet 4.6) und `claim_evaluation_v1.0.0.md` (Opus 4.7) inkl. vollständigem HCVO-Kontext. FastAPI-Router `/api/prompts` stellt Liste, Metadaten und Render-Endpoint bereit. 15 pytest-Tests grün. Eval-Runner (CLI + Dataset) offen — kommt mit PROJ-8 Backend-Anschluss.
**Created:** 2026-04-23
**Last Updated:** 2026-04-23
**Backlog-Referenz:** F-030

## Dependencies
- None (Infrastruktur für Pipeline)

## User Stories
- Als Entwickler möchte ich Prompts versioniert und außerhalb des Codes pflegen, damit ich ohne Deploy iterieren kann.
- Als Entwickler möchte ich Prompt-Versionen gegen ein Eval-Set vergleichen, damit ich Regressionen vermeide.
- Als Betreiber möchte ich jederzeit wissen, welche Prompt-Version in Produktion läuft, damit ich Reports zurückverfolgen kann.

## Acceptance Criteria
- [ ] Prompts als Markdown-Dateien in `apps/api/app/prompts/`
- [ ] Dateiname: `{task}_{version}.md` (z.B. `claim_detection_v1.2.0.md`)
- [ ] Jeder Prompt hat YAML-Frontmatter: `version`, `model`, `task`, `author`, `created_at`, `description`
- [ ] Jinja2-Template-Engine für Variablen-Einsetzung
- [ ] `PromptLoader`-Klasse lädt Prompts beim API-Start, Caching im Memory
- [ ] Jede Analyse speichert verwendete Prompt-Version in `analyses.prompt_version`
- [ ] Eval-Runner (CLI): `python -m apps.api.scripts.run_eval --prompt claim_detection_v1.2.0 --dataset eval_set.jsonl`
- [ ] Eval-Output: Precision, Recall, F1 pro Claim-Typ, Diff gegen vorherige Version
- [ ] Eval-Set mit min. 30 annotierten Beispieltexten in Repo (`apps/api/eval/datasets/`)
- [ ] CI-Check: neue Prompt-Version muss Eval-F1 >= Baseline erreichen, sonst Warning

## Edge Cases
- **Prompt-Datei fehlt beim Start:** Hard-Fail mit klarer Fehlermeldung, kein Silent-Fallback
- **Ungültiges Jinja2-Template:** Exception wird beim Start geworfen, Deployment stoppt
- **Variable im Template nicht übergeben:** Strict-Mode → Exception, kein leerer String
- **Zwei Prompts mit gleicher Version (Merge-Konflikt):** CI-Check verhindert Merge
- **Eval-Set-Beispiel hat mehrdeutige Ground-Truth:** Markiert als `disputed: true`, wird in Metriken ausgegraut
- **Breaking Change in Output-Schema:** neue Major-Version, Pipeline-Code muss mit-angepasst werden

## Technical Requirements
- Library: `jinja2` für Templates, `python-frontmatter` für YAML-Frontmatter
- Versions-Schema: SemVer (`major.minor.patch`)
- Eval-Dataset-Format: JSONL mit `{input_text, expected_claims: [...]}`
- Prompt-Hot-Reload im Dev-Mode, Cold-Load in Prod

## Open Questions
- Prompt-A/B-Testing in Prod (z.B. 10 % Traffic auf neue Version)? → V1.1
- UI zur Prompt-Bearbeitung? → **MVP: nein, nur Git-Flow**
- Eval-Runs automatisch bei PR in CI? → **Ja, GitHub Actions wenn Prompt-Dateien geändert**

---
<!-- Sections below are added by subsequent skills -->

## Tech Design (Solution Architect)
_To be added by /architecture_

## QA Test Results
_To be added by /qa_

## Deployment
_To be added by /deploy_
