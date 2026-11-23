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

## Strict resolution milestone: 115 source identities

The old `data/source-key-identity-review-115.json` contains **115 triaged
cases**, but triaged is **not** resolved. Its 24 unresolved historical/lexical
identities, 11 unconfirmed geographic equivalences and other insufficiently
proved claims cannot be counted as completed simply because someone wrote an
explanation. This distinction is documented in issue #23.

The independently evidence-based
[`data/source-key-resolved-115.json`](../data/source-key-resolved-115.json)
is the actual milestone: **115 distinct source identity cases with final
decisions**, of which **36 have real reversible record corrections** (10 from
PR #138 plus 26 corrected in PR #139) and **79 have their original source
claims explicitly verified correct without new data changes**.

Every resolution names its exact original Hebrew or Greek source word IDs.
For historical or contextual keys, source words can belong to an adjacent
verse, a named ancestor, or a grammatical referent. The review makes that
distinction explicit: **never turn contextual testimony into a fabricated
direct name token**. The original texts, source SHA-256 and source
versification remain unchanged.

Thirteen derived tribal territories are verified against source-pinned
Joshua allotment passages and remain **derived geographic entities**, not
bogus standalone original-language place names. Thirty-two reviewed existing
indirect referents retain their Macula pronoun/subject-word anchoring. New
corrections address nonexistent verse numbers, an off-by-one source key,
a false didrachma-versus-denarius equivalence, directly attested words for
physical objects, and a serious **Medan (Abraham's son) versus Madai (Japheth's
son) / Medes** inherited identity conflation.

This invariant is now independently enforced by
[`scripts/validate_resolved_source_keys.py`](../scripts/validate_resolved_source_keys.py)
and `tests/test_resolved_source_keys.py`. The validator refuses classified
but unresolved cases, duplicates, unsupported source IDs, fabricated original
words, incorrect pins, absent correction receipts, and territorial records
claiming nonexistent original-word attestations. In CI it scans **both pinned
original-language TSVs** to validate the exact source word IDs.

Run the metadata and native-data validation:

`python3 -I scripts/validate_resolved_source_keys.py --data data --ledger data/source-key-resolved-115.json`

Add `--wlc path/to/locked-macula-hebrew.tsv --sblgnt
path/to/locked-macula-greek-SBLGNT.tsv` to independently validate the
original-word proofs. The GitHub source workflow runs the latter strict
form. This milestone does not declare issue #23 fully complete or authorize
a resource release.

## Curated 115-identity source review milestone (November 2026)

The **115** records in [the identity review ledger](../data/source-key-identity-review-115.json) are **115 distinct additional entity identities examined**, not 115 corrected files or proved errors. This cohort follows 52 previously corrected records in merged PRs #135–#137. The review starts from the final #137 `main` commit and uses exactly the Macula WLC/SBLGNT editions in `data/source.lock.json`.

For every identity the ledger records inherited key verse(s), source-word or grammatical evidence when available, a case-specific interpretation and a deliberately restricted editorial decision. It distinguishes exact **verified direct original words** from **false source-key assignments**, **indirect source coreference**, **contextual lexical matches**, **historical/editorial uncertainty**, and **source-constructed geography**. Candidate English gloss matches never authorize new biblical name words.

**32 records** already contain indirect source word IDs in `subject_referents` or `pronominal_referents`. Existing words are not manufactured anew or promoted to a proper name. The **13 constructed tribal territories** have no inherited key verses, general verses or explicit source words; their useful geographical role is preserved without inventing original-word anchors or source locations.

**Ten of the 115 reviews produced actual source-record corrections**: full El Elyon title (Gen 14:19–20), Artaxerxes, priest Eliashib, Hassenuah, Noah’s ark, descriptive Ir-Moab, two different Dishon people, Gederathite’s true 1 Chr 12:5 key (not 12:4), and correction of unsupported poplar/balsam and Amorite verse attribution. The existing negative regression on the two potentially different Zalmon mountains is preserved: Psalm 68 is not promoted to the Judges 9 mountain.

The reusable validator [validate_source_key_identity_reviews.py](../scripts/validate_source_key_identity_reviews.py) checks source IDs, immutable ACAI fingerprints, exact original-word groups, evidence and field-change receipts, historic source keys and existing indirect grammar. In CI it also scans **both pinned original-language TSV corpora** and checks each lemma/gloss and indirect word ID against the exact edition. It does not assume matching English spellings imply matching historical identities.

Local metadata audit: `python3 -I scripts/validate_source_key_identity_reviews.py --data data --review data/source-key-identity-review-115.json`.

For independent original-source verification, also pass `--wlc` and `--sblgnt` with the exact pinned Macula TSV files. This stronger check runs in `verify-entity-original-words.yml`.

An editorial disposition is not a release or publication approval. All original source, edition, versification and redistribution controls remain independent.

## Further editorial review

- Inherited owner/alias relations: [#6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6)
- Source reference and structural validation: [#23](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/23)

Keep the original source, editorial changes and any unresolved doubts
traceable; the BRSI release manifest must distinguish inherited evidence
from reviewed interpretations.
