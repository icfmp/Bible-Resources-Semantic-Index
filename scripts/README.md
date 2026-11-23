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
