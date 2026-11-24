# MACULA ↔ authored LSG 1.0.2: whole-verse semantic pilot

Status: **private research; no model run, no independent human gold and no
approved semantic link yet**. Follows issue [#187](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/187).
This replaces word-by-word prescreening as the **reasoning method**; original
MACULA IDs and exact authored French word coordinates remain the output
identifiers, not the units of linguistic interpretation.

## Why verse-first

A word's lexical gloss, another word's nearby location and a MACULA XML
constituent **cannot independently prove translation**. The two negative
controls (#194, #195) showed this. A model/analyst must first interpret
the **complete original-language verse** and the **complete authored French
verse**, identifying clauses, grammatical relations, omissions/additions and
reordering **before** choosing exact source-group ↔ French phrase spans.

The generator uses pinned, immutable, separately sourced material:

- The **frozen source-verse clustered** human-review dossier, which carries
  full original MACULA token sequence, surfaces, lemmas, morphology and
  optionally POS; complete French verse NFC text, exact word IDs and character
  offsets; neighboring **French** verses where present; and the selected
  selected original IDs. Upstream missing-link cause labels are **not**
  disclosed to the model, so they cannot bias the independent reading.
- The exact Bible Resources authored **BRLSG1910 1.0.2** edition digest and
  original source/correspondence index digests from that dossier.
- It selects **100 NT and 100 OT complete verses** only from the original
  **training** partition. Neither calibration nor blind validation is allowed
  into a model's prompt, selection or response. Adjacent French context is
  also removed whenever its source verse belongs to calibration/blind.
- Cross-versification disputes and absent same-coordinate authored verses
  are **excluded from the initial pilot**, not silently remapped.
- Original-language *neighboring verses* and verified XML `<wg>` source
  constituents are **not included in this first generated task**. They must
  be supplied from separately pinned authentic sources before anyone claims
  a syntactically verified clause or adjacent-original-verse interpretation.
  Clause boundaries in this pilot are **model hypotheses**, not proven XML.

## Research workflow

Source-pinned GitHub CI regenerates the private dossier, then runs:

```sh
python3 -I scripts/prepare_macula_lsg_verse_semantic_pilot.py \
  --mode prepare \
  --private-dossiers /tmp/brsi-semantic-private-review-dossiers.json.gz \
  --dossier-lock links/alignments/clear-bible-lsg/semantic-review-dossiers.lock.json \
  --private-pilot /tmp/brsi-semantic-verse-tasks.json.gz \
  --report /tmp/brsi-semantic-verse-tasks-source-free.json
```

No Scripture-bearing task is committed, uploaded as an artifact or printed in
Actions logs. The output contains **full original and target verse context**,
not isolated word pairs. It is private and deliberately does **not** include
any machine-generated candidate or training gold.

Only after an external contextual model has interpreted the private
source-locked tasks can it write a **private** JSON response. No unspecified
model/API is invoked by the generator. A model must return **one analysis per
complete verse**, and within each:

1. Original whole-verse meaning and French whole-verse meaning, **separately**
   explained in context; never copy lexical glosses and call this reasoning.
2. Ordered, complete original-token clause groupings with corresponding
   French clause spans. French clause order may be different from original
   order. Clause segmentation is proposed unless independently source-verified.
3. Ordered, complete source-token groups inside each clause, with one of
   three **mutually exclusive** dispositions:
   - `phrase_span`: one or more exact contiguous authored French word spans
     expressing the original group; two-to-one/many-to-many and overlapping
     French target spans across source groups are allowed.
   - `grammatical_unpaired`: the source function is conveyed by a construction,
     with **no distinct French span**, and a specified grammatical function.
   - `undetermined`: evidence is insufficient; no French span is invented,
     and an uncertainty reason must be recorded.
4. A substantive **contextual explanation** for each group. Do not assign a
   Strong gloss or nearest word as if it proved a contextual equivalence.

The machine response has this shape (IDs and words below are **synthetic**,
not biblical text or actual alignment evidence):

```json
{
  "schema_version": 1,
  "pilot_id": "<exact pilot_id from private task file>",
  "review_status": "machine_candidate_only",
  "automatic_approved_links": 0,
  "publication_authorized": false,
  "results": [{
    "task_id": "<task_id>",
    "original_verse": "<8-digit original verse ID>",
    "source_verse_sense": "An independent contextual reading of the entire original verse.",
    "french_verse_sense": "An independent contextual reading of the complete authored French verse.",
    "clauses": [{
      "original_macula_ids": ["<original-ID-1>", "<original-ID-2>"],
      "french_spans": [{"word_ids": ["<verse>:1", "<verse>:2"]}],
      "clause_sense": "What this clause expresses as a complete proposition.",
      "alignments": [{
        "original_macula_ids": ["<original-ID-1>", "<original-ID-2>"],
        "french_spans": [{"word_ids": ["<verse>:1", "<verse>:2"]}],
        "decision": "phrase_span",
        "contextual_reason": "Why the expression has this contextual sense in both full verses.",
        "grammatical_function": null,
        "uncertainty_reason": null
      }]
    }]
  }]
}
```

To validate a machine-produced private response:

```sh
python3 -I scripts/prepare_macula_lsg_verse_semantic_pilot.py \
  --mode validate \
  --private-pilot /tmp/brsi-semantic-verse-tasks.json.gz \
  --pilot-receipt /tmp/brsi-semantic-verse-tasks-source-free.json \
  --machine-response /tmp/brsi-private-verse-model-proposals.json \
  --report /tmp/brsi-private-verse-validation-source-free.json
```

The validator first verifies the private pilot's exact byte digest against\nthe source-locked preparer's receipt; edited task text or coordinates fail.\n\nStructural validation requires every original token in every selected verse
to be addressed **exactly once**; each original source group is contiguous
and ordered, and each French span is an attested contiguous word-coordinate
sequence within the **exact authored verse**. The same French words may be
associated with more than one original phrase group (many-to-one). No
grammatical-unpaired or undetermined result may claim a forced French word.
Unknown, duplicated or cross-verse IDs, missing tokens and hidden
`approved` flags fail closed. Outputs remain private; receipts have only
counts and SHA-256 digests.

**This validation checks schema, completeness, source identity and status,
NOT semantic correctness.** Machine explanations may be wrong. Do not
reinterpret non-empty model output, matching hashes or 200 processed verses
as accepted gold, accuracy, coverage improvement or permission to publish.
Independently reviewed OT/NT human-gold comparisons and separate
source-edition/publication gates remain mandatory.

## Tests

```sh
python3 -I -m unittest discover -s tests -p 'test_macula_lsg_verse_semantic_pilot.py' -v
```

Source-pinned full-corpus reconstruction must also run. Existing files in
Bible Resources, original MACULA/LSG sources and the application are not
modified by this pilot.
