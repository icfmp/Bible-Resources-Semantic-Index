# Source-backed entity relations — development v1

**Status: internal candidate projection only; no approved semantic graph,
public release, Bible integration or added relation evidence.**

This document defines the first *read-only* contract for BRSI entity relations
([issue #24](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/24)).
It does not replace the canonical entity JSON, original-language witnesses,
editorial receipts or the existing [external-resource crosswalk](../links/schema.v1.json).

## What is actually represented

The canonical `data/entities/` records already contain typed, inherited
references to other identities. A link is captured with its *exact original
source field*, array/compound-field path, source record ID and original
source-record SHA-256. The [v1 schema](../relations/schema.v1.json) models
**claims made by those fields**, not independently demonstrated facts.

| Original field | Candidate predicate | Direction and limitation |
| --- | --- | --- |
| `father` | `reported_father` | The subject record names a father; do not infer an inverse child claim |
| `mother` | `reported_mother` | The subject record names a mother; disagreements remain separate |
| `offspring` | `reported_offspring` | The subject lists an offspring target, which may legitimately be a collective group |
| `partners` | `reported_partner` | Original association; do **not** infer marriage or reciprocal partnership |
| `siblings` | `reported_sibling` | The record's sibling list; never synthesize reciprocal claims |
| `tribe` | `reported_tribe` | Inherited group association, **not** asserted genetic descent |
| `group_origin` | `reported_group_origin` | Preserves an inherited origin claim; **not** an ethnic/ancestral identification |
| `subregion_of` | `reported_subregion_of` | Geographic containment claim; never infer place identity or historical permanence |
| Any other typed field | `null`, `withheld_unclassified` | Exact source claim retained for review; no fabricated meaning |

All recognized claims have `review_status=source_unreviewed`. A source
record being `editorially_reviewed` does **not** automatically approve
every relationship within it. Unknown typed fields are retained as
`withheld_unclassified`; they cannot silently become a recognized predicate.

This deliberately keeps **person**, **place**, **group**, **demonym** and
**textual-variant** identities distinct. Neither matching labels nor a
shared canonical display identity authorize merging target IDs.

## Actual records, without invented certainty

- `person:Lot.father = person:Haran` is a directional, inherited father
  **claim**. It does not create an automatically approved inverse link.
- `place:Gadara.subregion_of = [place:Decapolis]` is geographic source
  metadata. It says nothing about the unsettled
  Gadara/Gerasa/Gergesa textual-variant identification.
- `group:Ludim.group_origin = person:Lud` is preserved *as reported*.
  The existing [identity review](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6)
  specifically questions this claim; its presence in an index does not settle it.
- Disputed mother/father and collective-descendant associations likewise
  remain distinct raw source claims. The inverse-family audit reports
  disagreements for editorial review, never silently reconciles them.

Neither `references` nor `key_references` identifies a particular
relationship witness: their inherited ACAI ORG BCV8 roles are separate.
Likewise `explicit_instances`, `pronominal_referents` and
`subject_referents` provide **word-to-entity candidate links**, not
evidence of a specific father/partner/origin relationship. **No verse,
original-language word or contextual sense is attached automatically.**

## Deterministic offline construction and provenance

From the repository root:

```sh
python3 -I scripts/build_relation_index.py --data data --output /tmp/brsi-relations-v1.json
python3 -I tests/test_relation_index.py
python3 -I scripts/audit_entity_relationships.py --fail-on-unresolved
```

The output contains `claims` and `by_source`/`by_target` lookup tables.
Each claim ID is the SHA-256 of canonical JSON containing the original
`bsi.source_id`, exact JSON field path (including array offsets) and
original referenced target ID. Claims remain separate when two records
share a canonical identity. Reverse lookup is an **index of claims pointing
to a target**, not a new reverse assertion; no symmetric or transitive
relations are inferred.

`evidence.source_record_sha256` identifies the original pinned record,
**not** a hash of the latest editable BRSI JSON file. `source_commit`
and `source_snapshot_sha256` identify the frozen ACAI baseline. This
is enough to locate and re-examine the input, not proof of a relation-specific
biblical reference. Substantive reviewed changes must retain their own
editorial reason, evidence and source/version receipt.

The builder rejects stale, unresolved or quarantined targets, refuses to
overwrite `data/`, and checks that all inherited typed claims are accounted
for. It excludes any unavailable `keyterm:` target entirely, reporting
**only an aggregate count**; the excluded 868 ACAI Key Terms must not be
imported or leaked into a public projection. Runner-local output is not
uploaded. The source-lock license is carried forward for investigation;
this does **not** grant rights to republish the derived data.

## What must be established before v2 or release

1. Resolve the full set of inherited source-field kinds and decide, with
   documented source evidence and rights, which deserve reviewed predicates.
2. Add an explicit **claim-level** review/abstention ledger referencing exact
   field paths, immutable source receipts, and *relationship-specific*
   BCV8/edition/word witnesses where available. Version the ledger independently.
3. Distinguish conflicting claims, textual variant alternatives and
   homonym/ethnonym ambiguity without guessing or forcing agreement.
4. Validate consistency of the forward/reverse relation projection against
   the native entity index and relevant full pinned-source checks.
5. Obtain separate owner approval and release rights before distributing
   any new relation pack or changing the Bible application.

Until those steps, **source-unreviewed is not approved** and
**withheld-unclassified is not a semantic relation**.
