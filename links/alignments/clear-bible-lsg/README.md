# Clear.Bible LSG manual translation alignments — internal development resource

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

**No fabricated alignments, upstream source edits, editorial approvals or
claims of full-corpus coverage** follow from a clean transformation.

Do not commit generated index files or upload them as public CI artifacts until license, attribution, text-versification and target-edition gates are completed and a **new publication** is explicitly authorized under [#62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62). See [integration issue #162](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/162). Future Bible consumers must select an edition-qualified package using a version and checksum, preserve all candidate groups and unresolved states, and independently demonstrate that the tokenization matches their LSG text before showing any alignment.
