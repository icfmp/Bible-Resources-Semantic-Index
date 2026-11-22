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

## Retiring inherited encyclopedia prose

`localizations.*.descriptions` are not BRSI index data. To remove them
without editing IDs, original-word witnesses, references, relationships,
source-backed aliases, or independently reviewed short identity qualifiers:

```sh
# Dry run: show counts, change no files
python3 -I scripts/prune_inherited_descriptions.py --categories deities fauna flora
# Explicit, reviewable writing pass
python3 -I scripts/prune_inherited_descriptions.py --categories deities fauna flora --write
# Strict postcondition for selected categories
python3 -I scripts/prune_inherited_descriptions.py --categories deities fauna flora --check
```

The existing corpus has already been cleaned (PRs #33–#36); use the same
commands only for audited future imports or to check that no prose returns.
The tool validates the entire selected batch before writing, reports counts
without logging source biographies, and removes only description arrays and
their now-obsolete `descriptions` hold selectors. Other hold selectors and
all identity fields are retained. Run native index builds **before and after**
each batch and compare their SHA-256, then run all native/lexical/regression
checks. No generated biographies or universal hint-filling are allowed.
A hint is optional and requires independent verse-level review.

Recover original inherited prose from the exact pinned ACAI commit and
`bsi.source_sha256`, not from a parallel BRSI description archive. Existing
Git history also keeps each discarded working-field version.

## One-language working labels

ACAI originally supplied 19 translated `preferred_label` fields per
record. A language-neutral **source ID**, canonical identity, verse/original
word evidence and source-backed relations provide actual machine linking;
a single existing English name serves as an internal human identification
aid, with a separate short reviewed `bsi.identity_hint` if needed.

Do not silently convert source-unreviewed English names or aliases into
approved identity assertions. The existing reviewed-hold mechanism still
blocks contradictory English labels for the relevant records.

For explicitly approved redundant inherited display names, use
`scripts/prune_nonworking_labels.py` in categories:

```sh
python3 -I scripts/prune_nonworking_labels.py --categories deities fauna flora
python3 -I scripts/prune_nonworking_labels.py --categories deities fauna flora --write
python3 -I scripts/prune_nonworking_labels.py --categories deities fauna flora --check
```

The tool **fails** if any non-English localization includes a field other than
`preferred_label`, or if any field is under an unresolved language-specific
editorial hold. A non-English dictionary link, article identifier or genuine
source alias must never be thrown away as if it were a display translation.
Compare native built indexes byte-for-byte before/after every batch.
Original ACAI labels remain retrievable from the pinned source commit and
`bsi.source_sha256`; do not duplicate all languages in an archival sidecar.

## Finding genuine name ambiguity

`python3 -I scripts/audit_name_ambiguities.py --sample-limit 15`
reports source labels that *could* refer to multiple independently indexed
canonical identities. It groups by source type and the name before one
trailing display-only parenthetical qualifier; this is merely **triage**.
For example, the same raw name might designate two biblical persons, while
two source records that share one reviewed canonical ID are not necessarily
two historical people.

A collision is **not** evidence that names refer to the same individual.
The audit now also labels candidates with a unique existing **key verse**
or a unique **explicit original-word witness** among canonical namesakes.
This is a convenient *editorial sorting aid*, **not** approval of an
identity or proof that two similarly named figures are different.
If neither anchor distinguishes a name, the case remains openly unresolved.
All source witness fields stay untouched.

A distinct `bsi.identity_hint` must be justified manually using existing
biblical references, exact original-word evidence and relevant reviewed
family/place links. Never automatically derive qualifiers from unreviewed
source biographies, aliases, or apparent name similarities. Candidate reports
remain read-only and source text is not changed.

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
