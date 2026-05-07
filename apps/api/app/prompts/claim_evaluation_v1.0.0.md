---
task: claim_evaluation
version: 1.0.0
model: claude-opus-4-7
author: Dominik / KlickNerds
created_at: 2026-04-24
description: >-
  Per-claim user prompt for PROJ-10 full evaluation. Pairs with the
  claim_evaluation_system prompt, which carries the HCVO rules. Variables
  required: claim, evidence (list of RetrievalHit-shaped dicts), context.
---
## Zu bewertender Claim

- Wortlaut: **"{{ claim.claim_text }}"**
- Typ: `{{ claim.claim_type }}`
{% if claim.nutrient %}- Nährstoff: {{ claim.nutrient }}
{% endif %}{% if claim.substance %}- Substanz: {{ claim.substance }}
{% endif %}- Implizitheit: {{ claim.implicitness }}

{% if context -%}
## Umliegender Kontext (±100 Zeichen aus dem Originaltext)

```
{{ context }}
```
{% endif -%}

## Rechtsquellen aus der ClaimGuard-Wissensbasis ({{ evidence|length }} Treffer)

{% if evidence -%}
{% for hit in evidence -%}
### [{{ loop.index }}] chunk_id `{{ hit.chunk_id }}` · {{ hit.source_type }} · Score {{ '%.2f'|format(hit.score) }}

**{{ hit.reference }}**

{{ hit.snippet }}

{% endfor -%}
{% else -%}
_Keine passenden Treffer in der Wissensbasis._ Setze Status `unclear` und
`confidence < 0.6`, sofern du nicht aus offensichtlichem Krankheitsbezug
sicher `forbidden` ableiten kannst.
{% endif -%}

## Arbeitsanweisung

1. Bewerte den Claim nach den Bewertungs-Heuristiken aus dem System-Prompt.
2. Achte besonders auf wörtliche Treffer in zugelassenen Register-Einträgen.
3. Begründe in 2–4 Sätzen.
4. Bei `borderline`/`forbidden`: eine konkrete Reformulierung.
5. `legal_hints` (0–3 Einträge): nur Quellen mit einer **chunk_id aus der
   Liste oben**. Trage die `chunk_id` ins gleichnamige Feld ein.
6. Rufe das Tool `record_claim_evaluation` auf.
