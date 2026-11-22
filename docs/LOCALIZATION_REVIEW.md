# BRSI identification metadata and source provenance

BRSI identifies entities and joins them to external resources; it does **not**
maintain multilingual encyclopedia text or translated display-name catalogs.

## Current native entity contract

- Preserve exact `id`, `bsi.source_id`, `bsi.canonical_id`, source SHA-256,
  verse references, original-language word witnesses, reviewed relations,
  editorial evidence and uncertainty.
- Retain the inherited `localizations.eng.preferred_label` as a **single
  working-language identification aid**, not an approved identity assertion.
  The inherited English alternate labels are retained where present, subject
  to explicit editorial holds (including Johanan, Perez-Uzzah, Gadara).
- Add an optional, **short and independently source-reviewed**
  `bsi.identity_hint` when homonyms genuinely need human disambiguation.
  Its evidence references must match verses present in the entity. No mass
  guessed qualifiers or automatic promotion from source-only labels.
- Never include `localizations.*.descriptions` or redundant translated
  preferred labels in BRSI's current native records. Native CI and the
  direct builder reject attempted reintroductions.

The older ACAI source had 19 translated `preferred_label` fields per record,
plus biographical descriptions. Four verified source-prose batches
([#33–#36](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/36))
removed all inherited descriptions, and three verified source-label batches
([#40](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/40),
[#41](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/41),
[#42](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/42))
removed only unneeded non-English display labels.

## Data lineage, reversibility and unresolved names

The complete original ACAI source remains available at the exact pinned commit
in `data/source.lock.json`, with per-record `bsi.source_sha256`; BRSI Git
history preserves the previous editable versions. Removing duplicate source
prose or translated display labels does **not** delete original evidence.
The compact native index remained **byte-for-byte identical** in every batch.

`scripts/localization_policy.py` always refuses reader-facing descriptions
and returns explicit `source_unreviewed` status for source-only names.
Editorial hold selectors can block conflicting labels/aliases even if still
present in source fields. A caller asking for a missing non-English label
receives no label; BRSI does not invent a fallback or claim it is reviewed.

The historical `scripts/minimal_labels.py` is an old v0.1 source-only
packager, **not** the approved BRSI identity exporter. Future distributions
must honor the release/rights contract and exclude the 868 permission-only
Key Terms, unapproved source identifications and all non-index prose.

This is a provenance and identification policy, not a translation roadmap.
