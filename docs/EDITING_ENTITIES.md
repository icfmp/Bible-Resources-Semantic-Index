# Editing current BSI entities

The **versioned current entity files** under `data/entities/` are the editable
BSI dataset. They are **not** rebuilt by replaying historical ACAI patches.

## Editing rule

1. Edit the relevant `data/entities/<original-category>/<source-name>.json` file.
   Preserve the stable `bsi.source_id` identifying the historical source, even
   if the reviewed `id` or `type` is changed.
2. Record the reason, original word/verse evidence and provenance of any
   substantive editorial change in the same file's `bsi` metadata and in
   the pull request. Do not silently delete a reference, word grouping,
   localization, duplicate, or ambiguity.
3. Run `python3 -I scripts/build_native_index.py --output /tmp/bsi-current.json`.
   The builder reads **only** the current tracked records and source/edition
   qualification metadata: it does not fetch ACAI or replay edits.
4. Validate CI, including exact word-ID structure and ambiguous reverse
   lookups, before merging.
5. If an identity was quarantined, keep its original evidence under
   `data/quarantined/`, with a reason; never silently drop its source record.

## Minimal identity identification (not encyclopedic prose)

BRSI is a **source-backed index of identities and links**, not a multilingual
encyclopedia. Keep the stable source/canonical IDs, kind, verse and original-word
witnesses, reviewed structural relations, provenance and uncertainty.

When `person:Mary.2` alone is unclear, use an optional **single-language
editorially checked** `bsi.identity_hint` to distinguish it from namesakes:

```json
{
  "name": "Mary",
  "qualifier": "mother of James the younger and Joses",
  "language": "eng",
  "evidence_references": ["41015040"],
  "review_status": "editorially_reviewed"
}
```

The qualifier is a **short identifying precision, not a biography**. Prefer
existing verified identity relations and exact source word/verse identifiers
for machine matching. Provide a hint only where a human genuinely needs to
distinguish a key. Evidence references must be present in that entity's current
source references; source/provenance of wider editorial conclusions remains in
`bsi.editorial_evidence`. The hint's review status is independent of the
whole entity's `bsi.review_status` and must not imply an unrelated field is
reviewed. `scripts/identity_policy.py` checks every provided hint at build
time, without requiring invented hints on all historical records.

Inherited `localizations.*.descriptions` are **not BRSI data**. They may be
pruned from current records with exact upstream ACAI snapshot/record hashes
and historical Git commits retained as recovery evidence. Do not paste the
removed prose into new `identity_hint` fields. Never remove source word
groups, verse references, canonical identity information or necessary
source-backed aliases merely because they are not descriptive prose.

## Adding new BSI-owned entities

Do not invent an ACAI source identity for new research. A new reviewed
person/place/group can be added in its matching category; a newly identified
literary work goes in `data/entities/works/`. For a new literary work named
`Example`, the stable source identity is `bsi:work:Example`, the current
entity identity is `work:Example`, and the `bsi` metadata must contain:

- `origin: "bsi"`, `source_id: "bsi:work:Example"`,
  `source_primary_id: "bsi:work:Example"` and
  `canonical_id: "work:Example"`
- `review_status: "editorially_reviewed"`, a nonempty
  `editorial_reason` and a nonempty list of `editorial_evidence`
- An appropriate `type`, `references`, `key_references` and original-word
  groups only when independently supported by the source.

The suffix of `bsi.source_id` must continue to match the original BSI
filename even if the *current* entity ID is editorially renamed later.
Do not give a BSI-native record a fabricated ACAI `source_sha256`.
The source-lock and migration manifest describe the **historical import**,
not a ceiling on future BSI entities. Every originally imported source ID
must remain accounted for, even if its record is later quarantined.
New entities must pass `tests/test_native_growth.py`.

The original Key Terms remain excluded from this public dataset; creating a
new file must not be used to bypass that restriction.

## Preserved migration evidence

- Pinned original source: `icfmp/ACAI@e80a874e8282f996199c595378a3b3b9a43aac22`.
- Original source fingerprint and category counts:
  `data/migration/acai-baseline-materialization.json`.
- Every native record retains `bsi.source_id`, `bsi.source_sha256`,
  original source primary ID, and reviewed rationale when applicable.
- The original `data/editorial-decisions.json` is **historical evidence**,
  not a patch list for normal future builds.
- The legacy builder and one-time comparison tools exist only to audit the
  extraction until migration acceptance. They are not the future editor.

**Rights boundary:** 868 ACAI `keyterms` are accounted for but not included
in the committed native working set pending explicit source-field clearance,
tracked by issue #5. Do not manually reintroduce their original payloads.

**Release boundary:** editing the current data does not automatically publish
a new resource. Releases require distinct source/rights and version checks.
