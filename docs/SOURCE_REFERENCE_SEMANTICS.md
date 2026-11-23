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

## Second independent 115-case resolution batch

PR #140 adds a separate provenance chain for issue #23. The frozen inventory in data/source-key-unresolved-queue.json preserves the 243 distinct outstanding source identities after PR #139; these are *candidates*, not 243 proven errors. data/source-key-next-115-candidates.json selects 115 disjoint identities from that queue. The selection alone is not a completion claim.

Independent original-language examination was performed against the exact pinned Macula WLC and SBLGNT word editions. scripts/inspect_next_source_key_cases.py is the reusable, read-only contextual probe. data/source-key-next-115-resolved.json records each historical key, its original-language word witness ID, exact source-derived excerpt, original/contextual distinction, and independent editorial disposition.

**115 fully adjudicated additional identities:** eight reversible source-key corrections, 107 cases confirmed contextually correct without altering the inherited record. Five corrections are invalid original-language / cross-edition numbering or unrelated entities: Abishua wrongly linked to Uzzah and Ahio in 2 Samuel 6:3-4; Adoram linked to Solomon's wisdom instead of his labor office at 1 Kings 5:28; Solomon wrongly keyed to nonexistent pinned WLC 1 Kings 4:29 instead of 5:9; Capernaum wrongly keyed to Matthew 1:12; and Sickle wrongly attached to Deuteronomy 23:25's vineyard law instead of Hebrew 23:26. Three further distinct-identity corrections remove Gad's blessing from Dan, Eliphaz's family branch from Reuel and Zelophehad's daughters from Jair.

Every edit includes a specific reason, frozen original-word evidence and an exact reversible before/after source-field receipt. No original Bible text, source SHA-256, language edition or versification has been rewritten.

scripts/validate_source_key_resolution_batches.py is a reusable schema v2 validator for later independently completed batches, not a one-off 115-only matcher. It rejects duplicate or previously resolved identities, unsupported original-word IDs, altered candidate keys, non-final classifications, made-up source excerpts, bad contextual witness claims and fake/irreversible corrections. Under pinned-source CI, it checks *every* quoted target passage and every cited original-word ID against both locked WLC and SBLGNT TSVs. tests/test_source_key_resolution_batches.py includes adversarial regressions and exact real-data identity correction checks.

Run metadata checks: python3 -I scripts/validate_source_key_resolution_batches.py --data data --ledger data/source-key-next-115-resolved.json --selection data/source-key-next-115-candidates.json --previous data/source-key-resolved-115.json --pool data/source-key-unresolved-queue.json

GitHub CI adds --wlc macula-hebrew/WLC/tsv/macula-hebrew.tsv and --sblgnt macula-greek/SBLGNT/tsv/macula-greek-SBLGNT.tsv for independent source-collation.

The two disjoint resolved cohorts now contain **230 cases**. The frozen 243-case outstanding inventory has **128 as-yet-unadjudicated cases** after this batch. These are queue identities, not an error count, and issue #23 remains open for the rest of the audit.

## Final frozen 128-case disposition docket (PR #141, historical snapshot)

The 243-case queue following PR #139 is exactly partitioned into PR #140's 115
resolved identities and the separately frozen 128-case set at
[data/source-key-final-128-candidates.json](../data/source-key-final-128-candidates.json).
The initial selection and original-language contextual probe **do not themselves
certify any identity**.

The independent [final review dossier](../data/source-key-final-128-review.json)
records one precise verdict for **all 128** identities and all of their inherited
keys, with source excerpts, available neighboring word IDs, and explicit policy:

| Editorial outcome | Distinct identities | Status |
| --- | ---: | --- |
| Reversible native-record correction | 44 | Adjudicated; exact before/after receipts |
| Verified contextual or indirect key, no edit | 69 | Adjudicated; never asserted to be a direct name |
| Independently consulted Greek 1 Maccabees (Adasa, Arbela, Bostra) | 3 | External corroboration; **not** Macula-certified |
| Genuine identity/philology/geography uncertainty | 12 | **Unresolved, excluded from completion** |

The 44 changes include correcting impossible or mis-numbered WLC source keys;
disentangling unrelated genealogies and geographic entities; repairing the
pinned Hebrew Joel 3:1 Spirit token and Genesis 1:2 Spirit word without altering
any Bible text; correcting the source identity Pul mislabeled Lud; and separating
Javan the ancestor from the separate Greek ethnographic source index.

The source witness is the pair of locked WLC/SBLGNT Macula TSV editions in
[data/source.lock.json](../data/source.lock.json). In CI,
[scripts/validate_final_source_key_audit.py](../scripts/validate_final_source_key_audit.py)
reconstructs **every** cited 66-book target excerpt and cited word ID from the
pinned originals. It also checks exact candidate provenance, disjoint previous
cohorts, native correction receipts, immutable source fingerprints, and rejects
mislabeling a simply examined case as corrected or verified.

For local metadata-only checks:

```sh
python3 -I scripts/validate_final_source_key_audit.py --data data \
  --ledger data/source-key-final-128-review.json
```

For the strict source collation, provide both checked-out WLC and SBLGNT TSV
paths with `--wlc` and `--sblgnt` (the GitHub CI workflow does this).
Secondary 1 Maccabees evidence is explicitly outside those pinned 66-book
word inventories and is separately cited, rather than invented as a Macula ID.

**Remaining work before closing the identity audit:** Beelzebub, Phoenician
juniper, Aleppo pine, Ai, Aiath, Aphek, Eglath-shelishiyah, Foundation Gate,
Gerizim, geographical Gomer, Misgab, and Ramah (Hill). Several concern
uncertain historical identity or proposed botanical species, not malformed XML
or a demonstrably corrupted Bible verse. They require defensible editorial
judgment or better source evidence; do not auto-promote to `verified_correct`.

Cumulative bookkeeping: prior 230 + these 44 corrections + 69 pinned-source
no-change decisions = **343** internally adjudicated cases; 3 additional
externally corroborated Greek Apocrypha keys are tracked separately; **12**
identities remain genuinely unresolved out of the 358-case history. Issue #23
remains open. No source Bible text, original SHA-256, release artifact or Bible
application was altered by this docket.


## Final twelve source-identity decisions (PR #142)

PR #142 **supersedes the 12-hold conclusion above**, without modifying the
original 243-case queue or either 115-case certified cohort. The prior 12-case
snapshot is frozen in
[data/source-key-last-12-candidates.json](../data/source-key-last-12-candidates.json).
The maintained 128-case
[review register](../data/source-key-final-128-review.json)
now records all of their final dispositions, independent original word IDs,
cross-source scholarly support and the distinction between an attested *word*
and a conjectured *species, site or historical equivalence*.

| Decision | Final 12 | Basis |
| --- | ---: | --- |
| Source-backed, reversible correction | 8 | A historical field or overconfident claim was amended, with original values retained |
| Contextual identity verified correct without new direct-name claims | 4 | Independent original-language and external scholarly evidence |
| Unresolved identity *key* cases remaining in the frozen cohort | **0** | No speculative botanical or geographic identification was converted into certainty |

**The eight corrected source identities** are:

- `deity:Beelzebub`: the WLC two-token Ekron **Baal-Zebub** in
  2 Kings 1:2,16 belongs to the separately indexed pagan Baal family, not
  automatically to the New Testament demon-title **Beelzebul**.
  The historical two-key confusion is corrected in both `deity:Beelzebub`
  and `deity:Baal` with complete original-word groups. New Testament
  Beelzebul retains the inherited contextual Satan canonical relationship
  of Mark 3:22–23, without making the two ancient referents identical.
- `flora:JuniperTree`: Phoenician juniper as a candidate for Hebrew
  `erez` in ritual cedarwood texts is **proposed**, not an exact botanical
  identification. The differing original `ar'ar` bush words in Jeremiah
  remain untouched. See the UBS translation guidance at
  https://tips.translation.bible/story/phoenician-juniper-coastal-juniper/.
- `flora:PineTree`: Aleppo pine as a candidate for `'ets shemen`
  ('oil tree') is **proposed**. Isaiah 44:14's distinct and botanically
  unresolved `'oren` word no longer appears as a species-specific
  Aleppo-pine key. Compare UBS Flora:
  https://freely-given.org/OBD/UBS/Flora/1.18.2.htm.
- `place:Ai` and `place:Aiath`: the frozen WLC has **Ayyah**
  in 1 Chronicles 7:28 (`o130070280141`), **Aija** in Nehemiah 11:31
  (`o160110310052`), and **Aiath** in Isaiah 10:28
  (`o230100280031`). Their exact original-word links are now
  recorded, without claiming to have resolved the archaeology of the city.
  Compare BDB's Hebrew lexicon H5857.
- `place:Eglath-shelishiyah.1`: both Hebrew prophetic passages contain
  the phrase; a proposed *place name* and a 'three-year-old heifer'
  interpretation compete. The revised label explicitly states
  **possible Moabite site**, not a known archaeological city.
- `place:Misgab.1`: Jeremiah 48:1's definite-article Hebrew
  `ha-misgab` means 'the stronghold'. A distinct named site is
  unproven; the historical source record remains but no longer asserts
  an attested biblical town.
- `place:Ramah.8`: 1 Samuel 22:6 distinguishes **Gibeah**
  (`o090220060112`) from a **height** (`o090220060142`).
  That common noun does not establish another Ramah town, and the
  spurious homonym link to Gibeah of Phinehas is withdrawn.

**Four context keys retained as independently warranted:**

- `place:Aphek` / Antipatris: Acts 23:31 says Antipatris, not Aphek;
  Tel Afek's accepted later Antipatris identification justifies the
  historical place cross-reference without inventing a Greek Aphek word
  (https://biblical-archaeology.org/en/locations/aphek/).
- `place:FoundationGate`: 2 Kings 11:6 calls the parallel
  Jehoiada guard station Gate Sur; 2 Chronicles 23:5 calls it
  Foundation Gate. Both distinct Hebrew spellings are preserved and
  the context remains verified, not rewritten
  (https://tips.translation.bible/story/translation-commentary-on-2-kings-116-2/).
- `place:GerizimMount`: Judges 9:7 explicitly names Gerizim in the
  same Shechem narrative; 9:37 speaks of the center/navel of the land
  without naming Gerizim. The earlier forbidden equation with
  Tabbur-erez **remains removed**. The inherited key is a broader
  story-setting cross-reference, not a direct original-name link.
- `place:Gomer`: Ezekiel 38:6 names the nation/people Gomer, which
  contextualizes the existing *nation* category. It does not name
  a specific geographic settlement or justify fabricated coordinates.

**Important limits:** A biblical phrase can be securely attested even when
its botanical species, exact archaeological site, or ancient referent is
not knowable. The source-key audit is resolved by **making the index
accurate about the scope of its claims**, not by manufacturing historical
certainty. The three independently documented 1 Maccabees locations remain
**outside** the 66-book WLC/SBLGNT pinned original-word corpora, exactly
as in PR #141; none is silently declared Macula-certified.

The generic validator
[`scripts/validate_final_source_key_audit.py`](../scripts/validate_final_source_key_audit.py)
now cross-checks the frozen last-twelve selection, all 128 decisions,
all 358 unique original cohort cases, original target excerpts and all
last-twelve cited original word IDs against the exact pinned WLC/SBLGNT
source editions. It rejects forged or missing lexemes, undocumented
source changes, duplicate cases, weak unsupported contextual proofs and
the loss of original editorial receipts. Additional positive and
adversarial regression tests are in
[`tests/test_final_twelve_source_integrity.py`](../tests/test_final_twelve_source_integrity.py)
and the extended final audit suite.

**Final frozen-cohort accounting:** 230 prior + 52 corrected + 73 verified
contextual + 3 separately Greek/1 Maccabees corroborated = **358/358
historical identities given a source-qualified disposition**.
This closes *this specific frozen identity-keys backlog* but **does
not automatically close the broader issue #23**, validate every
remaining lexical/place source field outside this selection or authorize
a release. The underlying original Bible text, immutable ACAI source
fingerprints, original word editions and Bible application remain unchanged.
