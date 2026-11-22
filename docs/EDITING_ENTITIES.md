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

## Native source-file integrity

The native builder reads canonical JSON **strictly**: repeated object keys,
nonstandard numbers such as `NaN`/`Infinity`, unrecognized entity category
directories and nested JSON records are rejected. A file placed outside the
documented `data/entities/<category>/<name>.json` or corresponding quarantine
layout must never be silently skipped. All copied source record SHA-256 values
must be 64 lowercase hexadecimal characters; a BRSI-native record must not
claim a fabricated original ACAI fingerprint.

Every quarantined imported identity needs its own original source fingerprint,
nonempty reason and explicit supporting evidence. This prevents apparent
cleanup from silently erasing the reason for withholding an identity.

These are **format and provenance checks**, not independent biblical
verification. They do not assign new entity identities, normalize biblical
references, change editorial approval states or rewrite any source records.

## Bible references

Treat `references` and `key_references` as separate inherited ACAI ORG
BCV8 lists. A key reference does **not** prove there is an explicit matching
original-language token in that verse, and no source-defined subset rule has
been established. See [source reference semantics](SOURCE_REFERENCE_SEMANTICS.md).
Pinned source-word absence, source-verse absence and reference-qualification
manifests require an integer schema version (not a JSON boolean or float),
properly typed identifier lists, and ASCII-only BCV8 verse IDs. The source
identifiers are validated, never coerced, re-numbered or repaired automatically.

Validate original-word anchors against the exact pinned WLC/SBLGNT edition;
never generate a new biblical reference to make a test pass.

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

## Inherited encyclopedia prose — already removed

All inherited `localizations.*.descriptions` fields and obsolete
description-only review holds were removed in the historical, reviewed
migration (PRs #33–#36). **Do not reintroduce them** in BRSI: prose belongs
in separately licensed encyclopedic resources, not the identity index.

The write-capable ACAI migration pruner is no longer a maintained command.
Its original code remains in Git history, alongside the reviewed migration
diffs, pinned upstream source revision and original `bsi.source_sha256`
receipts. For any *new* externally sourced identity, import only permitted,
reviewed identity fields; never run a bulk prose-stripping command over the
current canonical tree.

Validate any change from the repository root:

```sh
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-current.json
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The builder rejects inherited prose, obsolete prose holds and unsupported
translations; permanent tests scan the full committed entity dataset.
Never remove original word groups, references, canonical IDs, necessary
source-backed aliases or independent identity evidence as part of cleanup.
A short identity hint is optional and requires independent verse-level review.
The original source text is recoverable from the pinned ACAI revision, not a
parallel BRSI description archive.

## One-language working labels

ACAI originally supplied 19 translated `preferred_label` fields per
record. A language-neutral **source ID**, canonical identity, verse/original
word evidence and source-backed relations provide actual machine linking;
a single existing English name serves as an internal human identification
aid, with a separate short reviewed `bsi.identity_hint` if needed.

Do not silently convert source-unreviewed English names or aliases into
approved identity assertions. The existing reviewed-hold mechanism still
blocks contradictory English labels for the relevant records.

The historical bulk non-English label pruner is no longer a maintained
command. The current dataset has already been normalized, and its original
translations remain recoverable from the pinned ACAI source and Git history.
For imported identities the canonical builder requires one nonempty English
working label, rejects redundant non-English localization entries, and
rejects unsupported non-English inherited field holds. No linguistic,
lexical or editorial source evidence may be discarded as a display duplicate.

Review additions and edits directly in the canonical entity JSON files, then
run the native build and full regression suite shown above. If an imported
record contains an unexpected non-English dictionary link, article identifier
or genuine source alias, investigate its provenance rather than deleting it.

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
