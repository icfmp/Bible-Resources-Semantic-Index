# BRSI LSG word index — generated from original Clear.Bible alignments

## Maintained pipeline

**Clear.Bible is our immutable original alignment source; the index is ours.**
BRSI maintains the original commit/files/SHA-256 witnesses in [manifest.json](manifest.json),
editable **source-evidenced BRSI corrections** in [corrections.json](corrections.json),
and a reproducible indexed output built from those originals. The canonical
French text authority is Bible Resources **LSG 1.0.2**, pinned in
[curated-1.0.2.lock.json](curated-1.0.2.lock.json). Original upstream bytes,
MACULA word identifiers, LSG verse text and SWORD modules are never rewritten.

The pipeline is **original Clear.Bible → our reviewed source corrections →
our BRSI-owned generated index**. It is not an extra live compatibility layer,
not an eBible text modification and not a manual re-creation of Clear.Bible
alignment. The exact original sources are reproducibly acquired by pinned
Git revision and verified against each original file's SHA-256 and Git blob;
they are **not falsely described as copies committed to this repository**.
The derived index itself is a separate BRSI artifact, which must be approved
and versioned before release.

Currently the full private development index preserves **104,807 original
NT alignment records**, with bidirectional lookup by original MACULA ID and
by French edition word position. **91,649** rows yield a uniquely located
*diagnostic* French word position and **13,158** remain explicitly unresolved.
These numbers are **not an editorial certification or a published release**.
The full **203,597 original OT rows** are now also maintained in **our own
BRSI OT verse-reference index**, searchable by original MACULA Hebrew ID
and by source-attested French LSG 1.0.2 verse reference. Exactly **920**
original source/target verse disagreements are preserved verbatim. Because
Clear.Bible supplies no French OT word-token inventory, that **original-only**
OT index retains **no approved French word position**. The separately
maintained [cross-witness MACULA→LSG index](#source-backed-hebrewgreek--actual-lsg-word-locations-development)
supplies provisional OT **word locations from independent explicit
MACULA→French surface attestations**, without pretending they follow from
Clear.Bible's numeric target selectors. Neither index asserts that the
linguistic translation choices are all editorially approved. The deterministic
[OT source-rebuild receipt](curated-1.0.2-parity.lock.json) pins the complete
private OT index SHA-256 and exact bytes, separately from the NT word index.
See [the pinned BRSI index build](../../../.github/workflows/pinned-curated-lsg-edition.yml)
and [full reproducible private index receipt](curated-1.0.2-parity.lock.json).

### Bible Resources LSG 1.0.2 — owned French word inventory

The BRSI-maintained edition-index producer now regenerates an **independent
authorial French word inventory from the actual, SHA-256-pinned Bible Resources
LSG 1.0.2 OSIS**, not from raw eBible or Clear.Bible target-token ordinals.
The entire authored corpus produces **31,170 verses and 722,596 word
coordinates** (OT: 23,211 verses / 548,864 words; NT: 7,959 verses / 173,732
words). These are *our tokenization counts*, not an original alignment count
or a claim of 722,596 proved Hebrew/Greek translation links.

- A BRSI word coordinate is `BCV:one_based_ordinal`; internally it carries an
  exact Unicode NFC start/end **codepoint span relative to the extracted
  authored OSIS verse body**, not an XML byte position and not a Clear.Bible
  original target ID.
- The source-derived extraction excludes authorial notes, book headings,
  chapter headings and figures from *word indexing* while preserving those
  in the **unchanged** LSG source. Apostrophes and hyphens inside a word
  remain attached; punctuation/capitalization are never silently edited.
- The private, deterministically compressed inventory stores **full
  SHA-256 witnesses for each original word surface and complete verse**,
  but no word or verse text. The pinned CI checks every resulting span and
  hash back against the exact authored OSIS, rejects corpus drift, and pins
  the complete inventory's size and SHA-256 in
  [the full source report](curated-1.0.2-parity.lock.json).
- This is our **own BRSI token inventory**, not a translation alignment
  overlay or an assertion that an upstream target `word_ordinal` matches our
  word ordinal. Its sole source of French lexical surfaces is our published
  LSG 1.0.2, and the generated data stay private until separately approved.

The next alignment pass must compare original, immutable Clear.Bible token
surfaces against those exact authorial positions, retain original MACULA
identifiers, and abstain wherever source/editorial word evidence is missing.
In particular, the OT French target TSV is still empty upstream; **an
ordinal-only association is not a Hebrew→French word proof**.

### Key rule

A source correction is a change to **our maintained index** justified by
pinned witnesses, not a patch to Clear.Bible's original or Bible Resources'
LSG 1.0.2. Resolved and unresolved records must both remain traceable
back to exact original alignment IDs. Do not invent target tokens, flatten
1:n relations or silently convert source-versification coordinates.


**Not a dictionary, original-word identity ledger, contextual sense database or public release.** This maintained resource provides two independent, exact-edition groups of upstream *translation-token* selectors: SBLGNT → LSG (NT) and WLCM → LSG (OT). It does not rewrite the Bible text or MACULA linguistic data.

## Pinned source

- [Clear-Bible/Alignments](https://github.com/Clear-Bible/Alignments/tree/c99bd0ae6946775f932517656308ca19fc706921) at `c99bd0ae6946775f932517656308ca19fc706921`, 11 May 2026.
- Upstream [README](https://github.com/Clear-Bible/Alignments/blob/c99bd0ae6946775f932517656308ca19fc706921/README.md) and [LICENSE](https://github.com/Clear-Bible/Alignments/blob/c99bd0ae6946775f932517656308ca19fc706921/LICENSE.md) label the *data* CC BY 4.0, distinct from MIT *code*. NT TOML identifies SBLGNT and Louis Segond 1910, manual Biblica alignment. OT TOML is inconsistent: under a `WLCM-LSG-manual` filename its `alignment.identifier` is `WLCM-IRVHin-manual`; preserve and flag this upstream issue rather than treating that ID as proof of edition identity.
- Original alignment files: `data/fra/alignments/LSG/{SBLGNT,WLCM}-LSG-manual.json`; original token corpora: `data/sources/{SBLGNT,WLCM}.tsv` and `data/fra/targets/LSG/{nt,ot}_LSG.tsv`. Files, Git blob witnesses, sizes and (once independently computed) byte SHA-256 digests are declared in [manifest](manifest.json).
- **Upstream OT target TSV contains only its header, 66 bytes**. Consequently no OT French-token membership or omission census can be verified from the published TSV; every structurally otherwise sound OT group remains `target_unverified`, never `source_attested`. This does not imply the alignments are absent or incorrect.
- Existing BRSI UBS Greek/Hebrew streams use separately pinned editions of MACULA. Matching a Clear.Bible source selector to an internal token is not a proof of whole-edition equivalence. Target LSG equivalence to the app/SWORD edition has **not** been established. Never infer this from the label “1910.”

## Independent source-pivot audit (source compatibility, not a remapping)

The separately maintained [original-word parity auditor](../../../scripts/audit_translation_pivot_parity.py)
and [source-pinned CI](../../../.github/workflows/pinned-lsg-pivot-parity.yml)
compare **all** original token IDs in the Clear.Bible SBLGNT/WLCM TSVs
against the exact independently pinned BRSI MACULA SBLGNT/WLC TSV
editions used by the UBS bridges. The report partitions original tokens
present in both editions, source-only and pivot-only, plus the aligned
source token IDs that can or cannot be looked up through BRSI. It records
per-book aggregates, full-file SHA-256 and exact revision IDs without
exporting original text, lemmas or third-party dictionary fields.

For aligned tokens with the *same exact ID*, the auditor separately
counts **NFC-identical, different and unavailable source lemmas**.
The WLCM TSV's missing lemma column is an explicit `unavailable`, not
permission to reconstruct a spelling or claim a confirmed identity.
The auditor does not silently normalize different token ID systems,
merge editorial distinctions, certify original readings or choose an
UBS contextual sense. The source checksums and summary will be frozen
in the maintained [pivot manifest](pivot.lock.json) and
[pivot parity evidence](pivot-audit.lock.json) after full independent
source-driven validation; neither is a public release.

## Nonpublishing deterministic build

Use a local exact checkout of the upstream commit (the CI job performs a sparse pinned clone), then:

```sh
python3 -I scripts/build_translation_alignments.py \
  --manifest links/alignments/clear-bible-lsg/manifest.json \
  --corrections links/alignments/clear-bible-lsg/corrections.json \
  --upstream-root /path/to/Alignments-at-pinned-revision \
  --output-dir /tmp/brsi-lsg-alignment
```

The builder checks original file byte size, exact Git blob SHA-1 and optionally pinned SHA-256, rejects duplicate JSON keys, invalid token IDs and duplicate corpus tokens, and preserves **each original alignment row**, its order, original source and target selectors and optionally original source record ID. It also computes exact source/target lookup IDs with explicit prefix normalization while retaining the unchanged original selector for every row. All 1:1, 1:n, n:1, n:m, incomplete and overlapping groups survive without guessed replacements.

Outputs `nt.json`, `ot.json`, deterministic `nt.json.gz`/`ot.json.gz`
and `receipt.json` are **private**, nonpublishing candidate artifacts.
The [checked-in receipt lock](receipt.lock.json) pins the validated source
fingerprints, original coverage counts and output byte digests; CI must
recreate these byte-for-byte or fail closed. They include selector-level evidence and deterministic SHA-256, record- and token-level coverage, overlap counts, unattested IDs, mismatched verse labels and unresolved cases. `source_attested` confirms **source and target token membership only**; it is not independent manual translation review. `target_unverified` does not assert that an OT token exists. No source text, translation words or dictionary prose is exported. The empty [corrections ledger](corrections.json) can apply later source-verified changes in a separate overlay; each must carry exact original witness and independently documented evidence. An overlay never modifies the original inputs.

## First complete pinned-source audit (23 November 2026)

The complete [source-pinned workflow](../../../.github/workflows/pinned-lsg-alignment.yml)
confirmed 104,807 Greek–French and 203,597 Hebrew–French group records.
In this particular upstream snapshot, all available group records have 1:1
selector topology; this empirical fact does **not** narrow the generic
schema, which retains 1:n, n:1, n:m and unresolved records.

- **NT:** 137,741 original source token IDs, 104,807 with an alignment;
  210,628 target token IDs, 103,811 aligned tokens attested in the actual
  target TSV. Exactly **996 alignment targets are absent from that TSV**;
  they remain unresolved. Unaligned source/target tokens are not inferred
  to have a missing translation.
- **OT:** 469,476 source token IDs in Clear.Bible's specific WLCM edition,
  203,597 aligned; **the French target TSV is empty except for its header**.
  Of 203,597 original alignment groups, **920** have source/target numeric
  verse identifiers that differ; these may reflect a genuine versification
  difference or another data error, and were not corrected by guessing.
  The other 202,677 groups have structurally consistent references but
  **cannot be called fully verified target links**.
- **Independent MACULA coordinate audit, verified on pinned sources:** all
  137,741 Clear.Bible Greek IDs appear exactly in BRSI SBLGNT, with the
  **104,807 aligned words' Greek lemmas identical after NFC**. All 469,476
  Clear.Bible WLCM source IDs appear exactly in BRSI WLC, including the
  **203,597 linked Hebrew IDs**; BRSI WLC additionally includes **6,435
  suffix-bearing Hebrew IDs**, which remain separately identifiable and are
  not coerced to numeric originals. Clear.Bible WLCM lacks a lemma column,
  so its aligned Hebrew original lemmas remain **uncorroborated**.
  See [independent parity receipts](pivot-audit.lock.json), whose comparison
  is enforced by pinned CI. ID-coordinate parity does **not** establish
  identical source texts/editions, guarantee a correct translation or resolve
  downstream LSG tokenization. GitHub upstream
  [issue #5](https://github.com/Clear-Bible/Alignments/issues/5) tracks
  historical WLC source ID compatibility.

## Read-only classification of outstanding token gaps

The maintained [target-gap auditor](../../../scripts/audit_translation_target_gaps.py)
is run by the pinned alignment workflow after full candidate and original-file
checksum verification. It checks the target TSVs again against their pinned
SHA-256 digests, then classifies unattested NT target token IDs by target
verse availability and ordinal range, and OT cross-verse references by
book/chapter/verse shifts and repeated source→target reference pairs. Its
text-free report remains runner-local, and is not a publication or a corrected
alignment. Numeric ordinal proximity **never proves** a replacement word;
repeated verse shifts **never prove** a legitimate versification conversion.
The original problem counts must still match the full importer receipt.

The checked-in [target-gap audit lock](target-gap-triage.lock.json) freezes
the **full pinned source audit**, not a reviewed translation correction:
all 996 NT missing selectors lie strictly **after** the last attested
ordinal in their target verse (836 distinct verses; 683 are exactly
one primary word ordinal higher, 199 two higher, 71 three higher; other
gaps also exist). The 920 OT cross-verse alignment records resolve to
**320 distinct source→target BCV pairs**: 820 records have differing
verses in the same chapter, 100 differ by chapter, and none crosses
book boundaries. These patterned coordinates help prioritize independent
edition/versification comparison but certify **zero** changes. The
workflow checks the generated report against this JSON lock fail-closed.


## Comparison with Bible Resources' curated Louis Segond 1910 v1.0.2

**Reader edition authority is the verified and published Bible Resources
[LSG 1.0.2](https://github.com/icfmp/Bible-Resources/releases/tag/lsg-1.0.2),
not an unmodified eBible source archive.** The [curated source lock](curated-1.0.2.lock.json)
pins the exact Bible Resources release commit `7092d6e9318eeff46081feb831c207efa5859af2`,
corrected 30.5 MB OSIS SHA-256
`2b8342a67d8e97b433670450fe9dd9e58917a7fcfc0cb4d321882ca8219dc3bd`,
module version `1.0.2`, module ID `BRLSG1910`, and `Segond` versification.
The upstream editorial changes and verified 803 chapter-opening headings are
preserved unmodified.

The maintained generic [edition-surface auditor](../../../scripts/audit_curated_translation_edition.py)
uses **both** immutable source revisions and the existing lossless alignment
candidate receipts. It reads source-authored OSIS verse bodies but excludes
notes and headings from comparison; it does not rewrite Bible text, MACULA IDs,
translation selectors, notes, versification or the existing empty corrections
ledger. Its full metadata-only [curated edition audit lock](curated-1.0.2-parity.lock.json)
is regenerated and compared by [pinned CI](../../../.github/workflows/pinned-curated-lsg-edition.yml).
No Scripture text or word lists are committed as a product of this audit.

- **NT surface:** all **7,959** curated numbered NT verses have corresponding
  Clear.Bible target TSV verses; **7,946** have the same concatenated Unicode
  alphanumeric character sequence after NFC/casefold, ignoring punctuation and
  spacing. **13** differ; **8** occur in four adjacent pairs whose **combined**
  character sequences are equal (Phil 1:4–5, 1:28–29, 3:10–11, 4:15–16).
  The remaining **five** individual mismatches are John 2:17, Rom 13:9,
  Phil 4:20 and Titus 3:8, 3:14. No numerical reference was rewritten.
- **NT segmentation diagnostic:** the actual 210,628 target TSV token surfaces
  are distinct from curated-word boundaries in many places. Of the **103,811
  aligned targets whose IDs exist** in that TSV, **91,649** cover exactly
  one curated diagnostic word's character boundaries, **7,457** carry no
  alphanumeric characters, **4,574** split a curated word boundary, and
  **131** occur in text-mismatching verses. The other **996 aligned target IDs**
  remain unattested in the original target TSV. All these are classifications,
  **not independently approved original→French mappings**; NFC/casefold plus
  punctuation removal is weaker than exact text, authorial punctuation and
  edition-specific token proof.
- **OT reference availability:** all **203,597** original target selectors
  point to a numbered verse present in the curated authored OSIS, but the
  original Clear.Bible OT target TSV still has no French token rows. Thus **zero**
  OT French word identities are independently verified. The 920 differing
  source/target verse pairs still need independent versification witnesses.

### Source-verified NT textual exception triage

The maintained report also classifies **all** divergent NT verse character
streams using original-target/curated-text witnesses, with no hard-coded
verse-specific edit and no source text copied into the index. At the pinned
Clear.Bible revision and reviewed Bible Resources LSG 1.0.2:

- **8** verses in four adjacent Philippians pairs differ only in the
  allocation of identical combined characters across verse boundaries;
  preserve both original references until an independent versification decision.
- **2** source verses, John 2:17 and Rom 13:9, contain characters absent from
  Clear.Bible's published French target TSV. This proves a target-*inventory*
  omission relative to our edition, **not** that an original alignment for
  those words can be inferred.
- **3** verses show only French orthographic spelling differences after
  *diagnostic* folding (Phil 4:20 `a/à`; Titus 3:8 and 3:14 `œ/oe`).
  Their exact original words and source wording remain unchanged.

The exact case coordinates, categories and nonediting guarantees are pinned
in [the generated parity report](curated-1.0.2-parity.lock.json) and checked
against whole-corpus original inputs on every relevant PR. This improves
editorial triage; it does not turn unresolved word IDs into certified links.

### Source-backed Hebrew/Greek → actual LSG word locations (development)

To continue without falsely assigning original OT target ordinals, BRSI now
also reads the public, independently published **Bible Aquifer
LouisSegond1910** chapter-level alignment witnesses, pinned separately
in [auxiliary-word-witness.lock.json](auxiliary-word-witness.lock.json).
That witness has actual **French target-token text**, plus explicit MACULA
source-token identifiers, which are absent from the published Clear.Bible
OT target TSV. Its publisher identifies the Bible text as public domain
but the **alignment layer as CC BY-SA 4.0 (Mission Mutual)**. Keep the
sources and their licenses distinct: this is not a provenance-free merge.

The deterministic BRSI producer
[`build_curated_lsg_word_correspondence.py`](../../../scripts/build_curated_lsg_word_correspondence.py)
reads original complete Clear.Bible alignment groups, the Aquifer chapter
word-surfaced groups, and the **exact pinned authored LSG 1.0.2 OSIS**.

- For every Aquifer French target token, locate its word only if the **actual
  NFC French surface** occurs in our authored verse at a word boundary, in
  a position that is **unique across all optimal order-preserving matches**.
  A duplicate word with ambiguous position, text difference, split word or
  unavailable verse remains unresolved; never guess from the target number.
- Match Aquifer source IDs to preserved original MACULA IDs. Record whether
  the independently located French word also agrees with the original
  Clear.Bible **target selector**. Preserve separate statuses for
  cross-source consensus, independently witnessed supplementary word
  alignment, selector-only evidence, conflicts and unresolved cases.
  The complete original Clear.Bible group list, source IDs and target IDs
  survive unchanged.
- Calibrate original target ID use against the 91,649 exact NT word
  attestations already in BRSI. Source-provenance, ambiguity and conflicting
  source alignments remain visible in every record.
- The [separate pinned full build](../../../.github/workflows/pinned-lsg-word-correspondence.yml)
  regenerates this **private development index**, checks full original
  corpus coverage and protects an exact output SHA-256 receipt. No Scripture,
  SWORD modules, original dataset or Bible application are changed.

This produces a usable, independently substantiated set of **MACULA ↔
our actual French word locations**, rather than indefinitely retaining all
OT records at verse-only level. The source evidence classes must remain
visible to the eventual consumer. LLM-assisted Aquifer links are **not
independent editorial approval by BRSI**, even when their word surfaces
and MACULA IDs match. Public redistribution additionally requires the
separate alignment CC BY-SA 4.0 attribution and publication review.

### Full original-word coverage from the two pinned alignment witnesses

The first full 1,188-chapter source-driven build preserved **all 308,404
original Clear.Bible source groups**, retained their source/target
identifiers, and independently checked the **607,217 distinct original
MACULA source IDs** against the exact locked SBLGNT/WLCM token corpora.
The following original-word indexes are *development evidence*, not an
editorially approved French reverse interlinear:

| Canon | Original MACULA IDs | With French word-surface evidence | Without evidence |
| --- | ---: | ---: | ---: |
| NT | 137,741 | **126,305** | 11,436 |
| OT | 469,476 | **361,200** | 108,276 |
| Total | 607,217 | **487,505** | 119,712 |

For NT, **91,649** words continue to use the directly verified original
Clear.Bible target TSV and authored LSG. A further **9,908** source groups
have independently located Aquifer word candidates, plus **24,748**
MACULA source IDs not part of the original Clear.Bible alignment groups.

For OT, **175,918** original groups have an independently witnessed Aquifer
source→French word location, plus **185,282** additional MACULA original
IDs with linked French word evidence. The other **108,276** original
MACULA IDs explicitly remain unlinked; this is **not evidence of an
untranslated Hebrew word**.

Original target-ID numerical equivalence across data sources is **not**
trusted: in an exhaustive NT gold calibration, **20,106** same-number
Aquifer French token IDs pointed to a *different French word location* than
the independently text-verified Clear.Bible word. Therefore only the
Aquifer **MACULA source ID** and its **explicit French token surface**
can supply an OT word hypothesis. The sequence locator also refuses
ambiguous repeated-word positions. The complete status/coverage receipt
is maintained in [aquifer-correspondence.lock.json](aquifer-correspondence.lock.json);
every source input is pinned and CI regenerates/compares its SHA-256.

The source-linked Aquifer alignments include model-assisted judgments. A
matching word surface verifies the **referent French span**, but does not
alone prove the **linguistic merit of the Hebrew/Greek translation link**.
Each record therefore retains its evidence class, original MACULA IDs,
original Clear.Bible selectors and `linguistically_reviewed_by_brsi=false`.
The producer neither rewrites the LSG nor invents any missing alignments.

### Investigating the current 119,712 unlinked original MACULA source IDs

The source-pinned classification first partitioned 119,723 unlinked MACULA
IDs in PR #177; subsequent exact-surface recovery in PR #178 lowered the
current count to **119,712**, without automatic editorial approvals. It checks **each original source ID**
against Aquifer's explicit `meta.nonEquivalent.source` entries, its original
source-to-target alignment records and the original WLCM Hebrew word-part
coordinates already in the BRSI-owned index.

| Primary source-evidence category | NT | OT | Total |
| --- | ---: | ---: | ---: |
| Listed in Aquifer `nonEquivalent.source` | 3,378 | 59,514 | **62,892** |
| Another original Hebrew part of the same numbered word has an attested French link | 0 | 8,770 | **8,770** |
| Aquifer source alignment exists, but its target cannot be uniquely located in our authored LSG 1.0.2 | 2,756 | 18,069 | **20,825** |
| No usable source alignment record in Aquifer | 5,302 | 21,923 | **27,225** |
| **Unlinked source ID total** | **11,436** | **108,276** | **119,712** |

These categories are **diagnostics, not editorial judgments**:

- An Aquifer `nonEquivalent.source` annotation reports that *Aquifer's
  particular source alignment* gives no target equivalent; it is **not
  proof that the original Hebrew/Greek element is untranslated** or an
  authorization to drop it. Among all original IDs, 4,597 have both an
  Aquifer nonEquivalent annotation and a **separate BRSI word-link witness**;
  the annotation cannot be promoted to a universal prohibition.
- Hebrew word-part evidence says only that another original part with
  the same numbered Hebrew word has a link; it **does not inherit that
  French word position** for the unlinked part.
- The 20,825 French-location cases are the **next text-evidence recovery
  queue**, for independent verse-local word matching and repeated-word
  disambiguation. The 27,225 source-record absences require genuinely
  additional evidence; numbers, lemmas or co-occurrence alone are not
  word alignment proof.

Every original ID is individually indexed with its own primary evidence
category in `unlinked_cause_by_original_macula_id`. The full set
partitions the same **119,712** unlinked IDs, and the full source-pinned
workflow verifies that no member was accidentally assigned a French
word. Detailed numbers, source fingerprints, no-approval controls and the
exact rebuilt SHA-256 are locked in
[aquifer-correspondence.lock.json](aquifer-correspondence.lock.json).
The existing Scripture, word locations, source IDs, licenses and original
Clear.Bible alignment records are unchanged.

### Conservative recovery of complete, uniquely occurring words

PR #178 adds one **separately labeled** fallback to the source-audited
ordered-LCS locator. When a complete NFC-identical Aquifer French target
word occurs **once and only once** among the source verse's target words,
and **once and only once** among the authored LSG 1.0.2 words of the
same verse, the uniquely attested target span can be recovered even
if the larger target sequence is not ordered identically.

This conservative proof has retrieved **24 source target-word surfaces**
(5 NT, 19 OT) omitted by strict ordered sequence comparison, which add
**11 distinct original MACULA source IDs** with French word evidence
(1 NT, 10 OT). The current linked-source total is therefore
**487,505 of 607,217**, with **119,712** still explicitly unlinked.

Crucially, **24 target-token locations are not 24 newly linked source
tokens**; multiple targets can belong to an already linked MACULA source.
No unsupported missing French word was inserted. Any repeated word,
surface spelling difference, unavailable verse or unresolvable original
source relationship still abstains.

Every serialized Aquifer source link now includes the original target
selector, the version-qualified authored French word ID, its **exact
word SHA-256**, and a location proof method:

- `forced_ordered_exact_word`: position forced by every optimal
  order-preserving word alignment.
- `unique_exact_surface_without_order_proof`: complete matching word
  uniquely found in both verse word inventories, regardless of other
  source-edition word-order differences.

The full source-pinned CI separately reads **each** indexed word surface
from the original published LSG 1.0.2 OSIS and checks every recorded
hash, position, reference and proof category. The evidence does not
constitute automatic Hebrew/Greek translation-meaning review. The full
updated source-derived output and its deterministic gzip digest are
locked in [aquifer-correspondence.lock.json](aquifer-correspondence.lock.json);
no public release or Bible application change is implied.

### What remains among the 20,825 Aquifer word-location failures

A further complete pinned-source audit differentiates source-edition word
surface divergence from genuinely repeated-word location ambiguity. It
examines **all Aquifer original source→target witnesses** whose source
MACULA ID has no attested LSG 1.0.2 French word location. The exact
French target surface must be taken from Aquifer's recorded target token,
not guessed from either numeric ordinal.

| Original target-location failure | NT source IDs | OT source IDs | Total |
| --- | ---: | ---: | ---: |
| Complete original Aquifer French word **not exactly present** anywhere among our authored LSG words in that target verse | 2,596 | 17,284 | **19,880** |
| Exact French word exists, but a **repeated surface** prevents a uniquely proven location | 151 | 769 | **920** |
| Several original target witnesses have **different failure causes** | 9 | 16 | **25** |
| **All source IDs in target-location recovery queue** | **2,756** | **18,069** | **20,825** |

This is **not** evidence that 19,880 Greek/Hebrew translation links are
wrong. It means that the target word string in the *specific Aquifer
French corpus* has no **exact NFC-identical full-word surface** in
our independently curated LSG 1.0.2 corresponding verse. Differences
may arise from apostrophe/hyphen styles, letter-case, orthography,
tokenization, wording or a genuine editorial edition difference. No
historical French text is rewritten to force equality.

The other 920 require stronger local context before linking a repeated
French word to an original MACULA source. The 25 mixed cases retain
multiple original target testimonies; none was silently chosen.

Each of the **20,825** source IDs gets an independent second-level,
text-free classification in
`unlocated_french_target_cause_by_original_macula_id`, while the
maintained index retains its **119,712** primary unlinked causes.
The exact aggregate is pinned in
[aquifer-correspondence.lock.json](aquifer-correspondence.lock.json),
and source-pinned CI refuses an incomplete or non-reproducible partition.
Future recovery work should first measure **strict, explicitly graded
orthographic equivalences** against exact French word spans, separately
from substantive translation changes, and reject nonunique matches.

### Independent strict orthography census for the 19,880 missing French surfaces

Before attempting any additional word-location transform, BRSI re-read all
**19,880 original MACULA source IDs** in the exact-word-absent recovery
queue, with their **original Aquifer target-token text**, the original
verse-wide token inventory (including `nonEquivalent.target`), and
the unchanged published **Bible Resources LSG 1.0.2** verse text.

The separate maintained **read-only** auditor
[`audit_curated_lsg_surface_variants.py`](../../../scripts/audit_curated_lsg_surface_variants.py)
tests only concrete source-original French whole-word variations:
case-only, `œ/oe` and `æ/ae` ligatures, case+ligature, accents (diagnostic
only), and straight/curly apostrophe. Even a diagnostic match requires
that the normalized complete word occur **exactly once in both original
and curated French verse inventories**. No target ordinal or neighbouring
word position is guessed.

| Exact-word-absent source-ID diagnostic | NT | OT | Total |
| --- | ---: | ---: | ---: |
| No safely unique candidate under any strict orthographic rule | 2,576 | 17,213 | **19,789** |
| One or more normalization methods would match but occurrences remain ambiguous | 19 | 63 | **82** |
| Source ID has several original target-word diagnostics | 1 | 8 | **9** |
| Unique, exactly checkable case/ligature/accent/apostrophe variant | **0** | **0** | **0** |
| **Original MACULA source IDs audited** | **2,596** | **17,284** | **19,880** |

**This audit recovered no new alignment** and does not weaken the existing
word-location rules. The source data has no uniquely located target word
that differs from the authored French verse *only* in those exact
orthographic classes. The prior apostrophe-only producer experiment in
[#180](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/180)
was correctly closed unmerged for zero output gain; this audit further
explains why adding generic case/ligature/accent rewriting would be an
unjustified maintenance burden.

In particular, `a` versus `à` can change meaning, so accent folding
is **never used as proof of a translation link**. The **82 ambiguous
cases** similarly cannot be resolved by arbitrarily picking the first
or closest French word. The next source-driven task is to examine actual
**lexical wording and verse segmentation differences**. The maintained
audit receipt
[`orthographic-diagnostic.lock.json`](orthographic-diagnostic.lock.json)
pins the 19,880-ID partition, the original revision IDs, the exact
curated OSIS and source index fingerprints, and the full private
per-ID diagnostic SHA-256; no original French Scripture text is committed.

### Why an OT target selector ordinal is NOT our French word index

A complete source-driven *negative calibration* against the **91,649**
independently attested NT French word links shows that the original
Clear.Bible target primary word ordinal equals our authored LSG word ordinal
for only **25,435** links; for **66,214** links the ordinals **differ**
(about 72.25%). This is expected when tokenization distinguishes
punctuation or word parts. The original ID `BBCCCVVVWWW(P)` must **never**
be interpreted as `our_curated_BCV:word_ordinal` without a separately
verified token-to-span witness.

An independent full **203,597-OT-target-selector** numeric bounds check
against our exact authorial LSG inventory finds **40,281** original target
ordinals *exceeding* the total authored words of their own target verse,
and **163,316** within the count. Being numerically in range is **not**
an attestation of the French word identity or its position. None of the
203,597 OT rows was converted into a French word match; the 920 original
source/target versification differences are unchanged.

Both complete counts are frozen in the
[full source report](curated-1.0.2-parity.lock.json) and rechecked by the
[pinned workflow](../../../.github/workflows/pinned-curated-lsg-edition.yml).
The correct next proof is to recover the original OT LSG **token surfaces and
tokenizer/edition**, or independently establish a tokenizer whose *exact*
identity can be verified for every target selector. A plausible number
is not that proof.

### Deterministic BRSI-owned NT word and OT verse indexes (private pending review)

The same pinned [curated audit workflow](../../../.github/workflows/pinned-curated-lsg-edition.yml)
also regenerates two **private** compressed, BRSI-owned, source-ID-preserving
bidirectional indexes for the actual curated LSG v1.0.2: NT source word→French
diagnostic word positions, and OT original Hebrew word→French **verse only**.
No OT word mapping is inferred. No generated corpus is committed,
uploaded as a public GitHub Actions artifact, released or sent to the Bible app.
Its full deterministic SHA-256 and byte size are protected by
[curated-1.0.2-parity.lock.json](curated-1.0.2-parity.lock.json), with a separate
readback/decompression and original-source record-count guard.

- Of **104,807 original NT MACULA→Clear.Bible target selector records**,
  **91,649** can be projected to a single unambiguous **diagnostic** curated
  word position within their original same-verse character stream.
  Their original MACULA token IDs, Clear.Bible target IDs and record order
  remain in each owned index row; inverse lookup keys identify original IDs
  and curated LSG word positions without editing either source. Every row still says
  `editorially_approved: false`.
- **Exact word-surface attestation (full-corpus verified): all 91,649**
  located NT target word candidates have the **same exact NFC French word
  surface** in the original Clear.Bible target TSV and independently pinned
  Bible Resources LSG 1.0.2 OSIS. The generated index stores the exact
  authorial NFC codepoint span and independent SHA-256 witnesses of the
  authored word and original target token for **each row**, verified against
  both independently pinned inputs on CI. This is considerably stronger
  than the earlier alphanumeric-only verse diagnostic but **still not
  contextual semantic or manual translation-alignment approval**. The
  source MACULA IDs and original target selectors remain unchanged.
- **13,158** records explicitly abstain: **7,457** target punctuation/symbol
  surfaces, **4,574** target surfaces splitting our diagnostic word
  boundaries, **131** records in text-mismatching verses, and the original
  **996** unattested upstream target IDs. No invented text, target selector,
  French word, missing verse or automatic cross-verse rewrite fills these.
- Initial coordinates were found with an alphanumeric stream check, but the
  strengthened source-verified producer **independently attests exact original
  NT target word surfaces to authored French words**. All 91,649 candidate
  surfaces happen to match **exactly after NFC** in the current pinned
  source snapshot; no case-folding, accent removal, punctuation stripping or
  word replacement is needed for those records. This does **not** assert that
  the original Greek→French linguistic choices are each independently
  reviewed, nor justify filling the remaining original target-ID gaps.
  The generated index is still **not** a public release.

This comparison makes the edition/gap review **more precise**, not complete.
Do not backfill missing target IDs from word positions, use raw eBible in place
of this pinned curated edition, or expose French aligned words in the app based
only on normalized surface matches. Keep publication and Bible consumer gates
open until target token IDs, textual exceptions, versification and source-field
rights have separate approvals.

**No fabricated alignments, upstream source edits, editorial approvals or
claims of full-corpus coverage** follow from a clean transformation.

Do not commit generated index files or upload them as public CI artifacts until license, attribution, text-versification and target-edition gates are completed and a **new publication** is explicitly authorized under [#62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62). See [integration issue #162](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/162). Future Bible consumers must select an edition-qualified package using a version and checksum, preserve all candidate groups and unresolved states, and independently demonstrate that the tokenization matches their LSG text before showing any alignment.
