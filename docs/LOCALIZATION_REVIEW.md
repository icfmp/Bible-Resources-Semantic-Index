# Legacy localization field handling

**BRSI is an identity/link index, not a multilingual encyclopedia.**
This policy supersedes the prior plan to correct and translate all inherited
ACAI biographies. See [#30](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/30).

The original ACAI `localizations.*.descriptions` are not part of the
intended BRSI data model. They have been removed from all editable native records
through four independently verified category batches (PRs #33–#36). The exact source text remains recoverable from the
immutable pinned ACAI commit identified in `data/source.lock.json`,
each entity's `bsi.source_sha256`, and Git history. Each batch showed byte-identical native index output before/after removal,
without touching Bible references, original-word IDs, structural relations,
source IDs or reviewed identity hints. Native builds and offline CI now
reject reintroduced encyclopedia descriptions.

## Identification versus descriptions

Store a short, source-backed and independently reviewed `bsi.identity_hint`
where needed to tell similarly named entities apart. It contains a single
working-language name and short qualifier plus exact evidence verse IDs.
Human identification **does not justify** an encyclopedic biography or
nineteen translated paragraphs.

A hint does not replace source ID, canonical ID, exact original-language
word groups, existing evidence or validated cross-entity relationships.
Missing hints are allowed. No automatic disambiguation by guessing.

## Existing inheritance safeguards

The legacy `bsi.inherited_localizations` metadata records remaining
unapproved source labels/aliases (e.g. Johanan, Perez-Uzzah, Gadara).
Malformed/unknown flags are rejected by native build CI.

`scripts/localization_policy.py` **never permits reader-facing description
access**, including from native records not yet pruned. For labels and aliases,
it respects field/language holds and returns explicit source-unreviewed status.
It is not a license to present those fields as reviewed identity names.

The v0.1 `scripts/minimal_labels.py` is an old source-label builder,
not a reviewed BRSI identity provider. Any future public package must use
the validated identifier-only contract and explicitly exclude encyclopedia
text, unreviewed alias conflations and the 868 restricted ACAI Key Terms.

This is a migration and audit document, **not** a roadmap for translation.
