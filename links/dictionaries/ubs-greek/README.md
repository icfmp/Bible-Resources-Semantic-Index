# UBS Greek NT — maintained lexical crosswalk

This directory maintains the **source-pinned, bilingual lexical bridge** between
MACULA SBLGNT Greek and the United Bible Societies Greek NT Dictionary.
Its reviewed editorial ledgers are source-specific evidence, not new dictionary
definitions and not a license to infer contextual meaning.

## Source identity and rights

| Input | Locked edition |
| --- | --- |
| UBS Greek NT Dictionary, English and French | Edition **1.0**, `ubsicap/ubs-open-license@a15a96cfaa4ca18a6c0339016645ba1e534db3c8` |
| MACULA SBLGNT Greek words | `Clear-Bible/macula-greek@8423afe47b9e8f24b7772e808af45c7159a6fe7e` |

The original UBS dictionaries are **CC BY-SA 4.0** (© United Bible
Societies), and the MACULA dataset has a **CC BY 4.0** notice. The pinned
MACULA source also identifies third-party annotations **used with permission**:
permission for each redistributed output field must be checked independently.
See [source/release rights review](RELEASE_READINESS.md) and the shared
[rights policy](../../../docs/RIGHTS_AND_INTEGRITY.md). Never copy UBS
definitions, original Bible text, or restricted MACULA annotations into a
public BRSI index merely because they are available upstream.

## What is maintained

- `index.json` is the **checked-in development baseline** produced by
  `build_index.py`. It is not a public release payload. The bridge uses
  versioned original-word IDs, MACULA Strong and Louw–Nida metadata, and
  edition-specific UBS `MainId`/`LEXID` references.
- `v1_reviewed_*.json` files and other named review ledgers preserve
  source-specific approved headword links, explicit abstentions and
  word-level evidence. Original Greek word IDs and source annotations
  remain unchanged.
- `build_consolidated_v1_review_index.py` creates a **private** complete
  original-word lookup using the reviewed ledgers and provisional source
  candidates; it does not certify a contextual sense.
- `build_public_identifier_release.py` reproduces the historical
  rights-minimized **identifier-only** v0.1.0 ZIP for byte-parity
  verification, not for automatic publication.
- `test_*.py` covers the maintained source-specific algorithms and
  negative decisions. [Pinned Greek CI](../../../.github/workflows/bsi-ubs-greek.yml)
  is the authoritative full-source reconstruction and historical-asset check.
- The **224** original Strong multi-headword source cases and the **ὁπότε**
  temporal POS-specific decision are still verified by their independent
  source auditors, called **inside** the reviewed builders. Their redundant
  preliminary temporary report-file stages have been retired. The
  `v1_reviewed_ambiguous_headwords.json` and
  `v1_reviewed_hopote_temporal_headword.json` editorial ledgers remain
  unchanged, preserving 220 exact-word headword reviews, four abstentions,
  and the original conjunction/adverb annotations.
- The **five composite-Strong original words** are rechecked directly from
  the original exception register by their reviewed builder, without
  splitting the original Strong annotations or inferring a sense.
- The independent complete **137,741-word provisional-sense census** and
  **15,237-word unresolved-source analysis** are executed directly inside
  their private candidate builders. Their auditors and negative tests
  remain maintained; the earlier temporary-report CLI handoffs were
  duplicative, not durable editorial evidence.
- The UBS/MACULA **token-position calibration** also executes directly
  inside the 40-word provisional source-position builder. It checks the
  authentic bilingual source reference lists and original 122,504-word
  reference calibration before staging any suggestion; numeric token
  position factors alone are never proof of word or sense identity.

The source-local `source/` and `work/` checkouts are temporary and ignored.
Do not commit unpublished detailed UBS/MACULA original-word research dumps.

## Current verified boundaries

| Measure | Result |
| --- | ---: |
| Shared UBS EN/FR entries and lexical senses | 5,507 entries / 9,160 senses |
| Original MACULA SBLGNT word IDs | 137,741 |
| Historical Strong-based UBS entry candidates | 128,090 |
| Additional individually reviewed original-word lexical headwords | 9,604 |
| Original words with source-supported entry candidates | 137,694 |
| Original words without an approved UBS 1.0 headword | **47** |
| Historical multiple-headword Strong candidates | 224 (220 word-specific reviews, 4 unresolved) |

The **47 original-word exclusions** and the 26 affected Greek families remain
documented in the [editorial disposition](remaining_47_source_editorial_report.md).

The source-pinned Greek workflow now uses the **459-word original-source
missing-headword report** directly for the maintained bilingual UBS
`AlternateLemmas` audit. The audit conservatively partitions it into
**three case-only word witnesses** (reviewed by a separate exact-word
ledger) and **456 still-unlinked original word witnesses**, without an
accentless-spelling research intermediary. The final unique bilingual
AlternateLemma + original individual-word LN checks authorize **409
specific lexical headword reviews**, leaving the **47** unapproved words
unchanged. The removed exploratory accentless-matching script remains in
[immutable Git history](https://github.com/icfmp/Bible-Resources-Semantic-Index/blob/c5025d4580973d6ea3588069f00550e4705cd8b9/links/dictionaries/ubs-greek/audit_456_lexical_variants.py).

Do not turn inflection resemblance, accent stripping, the same Strong code,
the same Louw–Nida domain or a verse co-occurrence into an exact lexical
headword link. The maintained [explicit alternate-lemma tests](test_ubs_explicit_alternate_lemmas.py)
check this rule; a completed 47-word diagnostic was retired to Git history.

The private v1 research candidate classified **123,195** word IDs with
provisional UBS sense suggestions and **14,546** without an assigned provisional
sense. **Zero** contextual word-sense assignments are independently certified
by those counts. Greek morphology, Strong, LN codes and textual readings
must never be rewritten to satisfy a coverage target.

## Contributor verification

From the repository root, run the offline source-local regressions:

```sh
for test_file in links/dictionaries/ubs-greek/test_*.py; do
  python3 -I "$test_file" || exit 1
done
```

For a source rebuild, use the [pinned Greek workflow](../../../.github/workflows/bsi-ubs-greek.yml):
it acquires the exact upstream commits, verifies inputs, reconstructs the
lexical evidence, validates source-specific reviewed decisions, builds the
public-scope **historical** projection and checks its immutable archive.
Do not replace this with a fresh unpinned download or manually guess a mapping.

The [historically published identifier-only v0.1.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-greek-v0.1.0)
is not a publication approval for a new BRSI build. New publication remains
subject to [issue #62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62).

**Historical evidence:** the detailed first-pass, batch-by-batch lexical
investigation remains in [the immutable pre-cleanup README](https://github.com/icfmp/Bible-Resources-Semantic-Index/blob/f97f70446f0db0d4574fddcf2f589b74e98f30c2/links/dictionaries/ubs-greek/README.md).
Use the current reviewed ledgers and tests for maintained behavior; do not
reintroduce completed per-batch one-shot executables to `main`.
