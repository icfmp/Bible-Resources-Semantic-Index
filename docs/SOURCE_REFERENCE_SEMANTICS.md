# BRSI biblical reference fields and source qualification

BRSI keeps two **independent inherited ACAI lists** for each entity:

- `references`: original ACAI general verse-reference claims.
- `key_references`: original ACAI key-verse claims.

Both are eight-character `BBCCCVVV` (BCV8) strings under the
**Copenhagen Alliance ORG** source versification. They are not necessarily
written in the chapter/verse numbering of a particular reader translation.
The pinned ACAI documentation defines the **format** of both fields, but
**does not say** that `key_references` must be a subset of `references`.
Nor does it document that a `key_references` item has a corresponding
`explicit_instances` original-word anchor. Such extra assumptions would
change the meaning of inherited evidence.

## Verified original-source witnesses

The original JSON, **before** BRSI migration and later prose-only cleanup,
can be inspected at the exact source pin recorded in
`data/source.lock.json`:

- [ACAI people schema](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/people/README.md)
  and [places schema](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/places/README.md)
  independently document the two BCV8 fields and ORG versification.
- [Valley of Mizpeh original](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/places/json/ValleyOfMizpeh.json):
  `key_references=["06011008"]`, with **no** general
  `references` field and no original-language token witness.
- [Mount Heres original](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/places/json/Heres.2.json):
  `mentioned_in_bible=true`, but no key/general verse lists or word anchors;
  it has an existing `subregion_of=place:TerritoryOfDan` relationship.
- [Ashtaroth original](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/deities/json/Ashtaroth.json):
  `key_references` includes `11011005`, which is not among the original
  general `references`. These fields were not introduced or merged by BRSI.

The read-only audit from [PR #47](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/47)
found **477** current records with at least one key verse absent from their
general reference list, and **118** marked biblical despite lacking both
general references and explicit original-word anchors. This is a **review
queue, not a list of 477/118 proven defects**.

## Exact identifier bytes, not visual similarity

MACULA original-word IDs and ACAI ORG BCV8 verse IDs are **ASCII digit**
sequences with their edition-pinned prefix/width. Unicode lookalike digits
(e.g. Arabic-Indic or superscript numerals) are never interchangeable with
original source IDs, even though some general-purpose programming-language
digit predicates accept them.

The source-link finalizer therefore rejects non-ASCII digits and non-string
word IDs before constructing any reverse lookup. This is a *byte/identity*
check only: it does not renumber verses, restore absent textual readings,
reassign original-language token references or normalize source punctuation.

## Technical invariants

The native builder uses `scripts/reference_policy.py` to reject malformed
`references` and `key_references` **independently**. Both must be present
as lists of ASCII-digit BCV8 identifiers; an empty list is acceptable.
The policy does **not** filter duplicates, enforce chronological order,
copy missing verses from one field to another, invent word anchors, or make
automatic ORG-to-ENG conversions. This is intentional source fidelity.

The original-word groups (`explicit_instances`,
`pronominal_referents`, `subject_referents`) are separately pinned to
Macula WLC/SBLGNT editions and require independent source validation.

A new `references` or original-word assignment needs positive, edition-
specific biblical evidence and a reversible editorial receipt. A key verse
is **not itself** proof that a person/place name occurs as a token in that
verse. Some original witnesses may be ambiguous, non-biblical, apocryphal
or outside the chosen textual edition. Do not manufacture a verse to satisfy
a subset test.

## Further editorial review

- Inherited owner/alias relations: [#6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6)
- Source reference and structural validation: [#23](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/23)

Keep the original source, editorial changes and any unresolved doubts
traceable; the BRSI release manifest must distinguish inherited evidence
from reviewed interpretations.
