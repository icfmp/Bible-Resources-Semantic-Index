# BRSI shared scripts

This directory holds **maintained shared tools only**: native entity builds,
source-neutral validators, nonpublishing release checks and reusable audits.
Completed one-off probes belong in Git history, not alongside active commands.
Source-specific UBS tools, tests and review ledgers remain beside their
pinned sources; historical replay helpers required solely by regression tests
belong under `tests/support/`, not here.

## Current native entity workflow

From the repository root:

```sh
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-current.json
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The canonical editable records are `data/entities/` (plus the deliberately
quarantined source identities and qualification evidence). Do **not** replay
historical ACAI patches or import an upstream snapshot during normal editing.

## Existing public V1 artifact inspection (read-only)

The independent, already published entity/Greek/Hebrew release ZIPs can be
checked together with `inspect_v1_published_assets.py`. It imports the
maintained `verify_historical_asset.py` byte-lock verifier, inspects the
three **different** public payload shapes, never downloads anything and
never changes the application. See [V1 consumer guide](../docs/V1_CONSUMPTION.md).

## Reusable tools and checks

- `build_native_index.py`: canonical native entity build, independent of the historical ACAI compiler.
- `build_translation_alignments.py`: generic, original-byte-locked
  Scripture Burrito translation-selector importer; creates nonpublishing
  edition-qualified candidate JSON and SHA-256 receipts from exact upstream
  source/target token corpora. See [Clear.Bible LSG](../links/alignments/clear-bible-lsg/README.md).
  It does not resolve lexemes or infer missing French words.
- `audit_translation_pivot_parity.py`: nonpublishing comparison of
  Clear.Bible SBLGNT/WLCM original token IDs against exact, independently pinned
  BRSI MACULA SBLGNT/WLC corpora. Its per-book evidence and SHA-256 digest
  are locked under [the LSG candidate directory](../links/alignments/clear-bible-lsg/README.md).
  Missing original lemmas and morphological Hebrew suffix IDs are preserved
  as explicit limitations; no guessed translation/lexical-sense mapping.
- `audit_curated_translation_edition.py`: reusable, nonpublishing, source-pinned producer of the **complete BRSI-owned French word inventory** (NFC verse-relative word spans, word/verse SHA-256 witnesses and exact pinned LSG 1.0.2 identity; no source text included), as well as the
  source-pinned comparison of original translation-token TSV surfaces with
  an immutable curated OSIS edition. Counts verse-level textual equality,
  punctuation and segmentation mismatches and aligned-token boundary
  classes without inferring any word link or rewriting references. See
  [LSG 1.0.2 audit](../links/alignments/clear-bible-lsg/README.md).
  Its optional, private, deterministic **BRSI-owned index outputs** retain exact
  source IDs: NT source-word→French **exact NFC-word-attested** candidates
  (every located original target ID checks against the actual authored LSG
  word surface and SHA-256) and OT
  source-word→French **verse-reference-only** candidates. All unresolved
  punctuation, word boundaries, target inventory and versification remain
  explicit; these are not certified word mappings or distributable packages.
- `build_curated_lsg_word_correspondence.py`: maintained, reproducible
  BRSI producer of the **MACULA→curated French word index for both Testaments**.
  It consumes two independently pinned original alignment witnesses
  (Clear.Bible and Aquifer/Mission Mutual), retains all 308,404 original
  alignment groups, and resolves original source MACULA identifiers to
  **exact NFC-matching French word spans** in the immutable Bible Resources
  LSG 1.0.2. Duplicate words, source-edition disagreements and absent
  surfaces remain explicit. It also indexes all 607,217 authentic original
  MACULA IDs even if translation evidence is missing; no missing word is
  inferred, no Bible/OSIS source file is rewritten. The full output is a
  private, reproducible candidate, **not a release**.
- `audit_macula_lsg_contextual_lexical_pilot.py`: maintained **read-only**
  source-pinned linguistic hypothesis baseline; source MACULA lemma/POS
  observations train French token proposal distributions on an exact,
  independently pinned authored LSG edition. It withholds **2,000
  separate NT verses** with direct original Clear.Bible source-text
  word attestations, with separate calibration/validation partitions,
  measures precision (including false matches and Wilson bounds),
  and partitions every unlinked original source ID into four evidence
  strata. A separate private source-ID→French-word *hypothesis* file
  remains outside the repository; the exact report is pinned under
  [the LSG alignment source](../links/alignments/clear-bible-lsg/README.md).
  **The initial observed 51.7% blind word-position precision is a
  NO-GO for mass auto-links.** This is neither a contextual translation
  model nor an OT independently gold-validated aligner; original
  source-word IDs, authored French text and existing links stay unchanged.
- `sample_macula_lsg_semantic_review.py`: nonpublishing, original-ID
  **stratified semantic gold review sampler** (#187). Uniform deterministic
  selection of 500 still-unlinked original MACULA IDs in each of four
  independently pinned evidence strata. It emits **2,000 unreviewed cases**
  privately, a public text-free SHA-256/sample-composition receipt, and
  never presumes a semantic link from a lexical coincidence. Multiple
  source IDs in one verse remain possible; later blind comparison must
  cluster by verse. See the
  [human-review protocol](../links/alignments/clear-bible-lsg/SEMANTIC_REVIEW_PROTOCOL.md).
- `calibrate_aquifer_lsg_target_ids.py`: continuous source-pinned safety
  calibration against 91,649 independent original NT word witnesses.
  It demonstrates why identical **numeric** target IDs between independently
  tokenized French corpora cannot be treated as equal French word locations.
  This verifier runs on every relevant correspondence PR and prevents silent
  ordinal-based OT reconstruction. See
  [correspondence origin and exact-count receipt](../links/alignments/clear-bible-lsg/README.md).
- `audit_translation_target_gaps.py`: source-locked, nonpublishing
  classification of missing translation target selectors and cross-verse
  patterns in private candidates. No token replacements, inferred
  versification map, source wording or publication; runs on pinned LSG CI.
- `tool_registry.py`: read-only caller inventory (`--json`) and offline
  workflow-path validation (`--check-workflows`). It inventories shared and
  source-owned tools without guessing that a missing static caller means a
  file is safe to remove. Review dynamic importers and pinned releases too.
- `verify_generated_json.py`: generic **fail-closed** pinned JSON baseline
  comparison, used by both Greek and Hebrew full-source CI workflows:
  `python3 -I scripts/verify_generated_json.py --generated /tmp/created.json
  --baseline links/dictionaries/<edition>/index.json`. It rejects missing
  baselines, duplicate object fields, NaN/Infinity, self-comparisons and
  differences in typed values; it does not replace independent source or
  editorial checks. The same verifier also protects the five committed Hebrew
  source-evidence snapshots; a missing historically pinned snapshot fails
  instead of being silently treated as a not-yet-created initial import.
- `validate_external_crosswalk.py`: nonpublishing, offline V1 **external
  resource entry** crosswalk validator, separate from the deferred V2
  entity-relationship graph. It enforces source edition locks, current entity
  identity and explicit abstentions; never generates mappings.
- `build_relation_index.py`: **deferred V2 research only**, read-only, unapproved source-claim graph projection with stable claim IDs and inverse lookups. Its regression checks do not make it a V1 build or release dependency; it never publishes or infers relations. See [relation model](../docs/RELATION_MODEL.md).
- `entity_index_core.py`: shared deterministic identity, reference, original-word
  and source-qualification validation; used by the canonical builder and the
  retained legacy migration regression. This is the **maintained** finalizer.
- `resolve.py`, `reference_policy.py`, `identity_policy.py`,
  `localization_policy.py`, `offspring_target_policy.py`: shared policy
  and resolution logic.
- `distribution_profile.py`, `stage_entity_candidate.py`,
  `release_contract.py`, `verify_historical_asset.py`,
  `write_integrity_receipt.py`: projection, staging and integrity checks,
  **not authorization to publish**.
- `audit_*.py`: non-mutating entity data and relationship audits.
- Canonical identity and source-localization constraints are enforced directly
  in `build_native_index.py` and covered by native/index-only tests. The old
  one-time ACAI prose/label pruning programs are preserved only in Git history.

## Historical test support and research retention

- The historical ACAI compiler was moved to
  [test support](../tests/support/legacy_acai_compiler.py), separate from
  production scripts. Original v0.1 label/ZIP preparers remain only in Git
  history. The current native index does not import or replay ACAI sources.
- The former runner-only `work_snapshot.py` archive tool was retired: its
  output was not retained, distributed, or used as a verified recovery copy.
  Source-pinned rebuilds and historical archive integrity tests remain active.
  See [working-state limits](../work/README.md).

The UBS Greek and Hebrew lexical workflows, their tests and reviewed
source-specific decisions live under
[links/dictionaries/](../links/dictionaries/), not here. Their source-pinned
CI jobs verify rebuilds without publishing. Never infer a unique contextual
sense merely from a matching dictionary or Strong identifier.

See the [maintained tooling map](../docs/MAINTENANCE_INVENTORY.md) for the
current caller and source boundaries, [release contract](../docs/RELEASE_CONTRACT.md), and
[regression entrypoints](../tests/README.md).
