# BRSI shared scripts

This directory contains the **current native entity build**, reusable validators,
distribution-contract utilities, and explicitly retained historical tools.
It is **not** a directory of exclusively current production commands.

## Current native entity workflow

From the repository root:

```sh
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-current.json
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The canonical editable records are `data/entities/` (plus the deliberately
quarantined source identities and qualification evidence). Do **not** replay
historical ACAI patches or import an upstream snapshot during normal editing.

## Reusable tools and checks

- `build_native_index.py`: canonical native entity build, independent of the historical ACAI compiler.
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
- `prune_inherited_descriptions.py`, `prune_nonworking_labels.py`:
  historical, tested normalization commands; CI uses `--check` only.

## Historical or restricted workflows

- `compile_index.py`, `minimal_labels.py`, `package_candidate.py`:
  retained for migration/v0.1 reconstruction evidence or compatibility tests;
  **not** the current editable-source build.
- `work_snapshot.py`: active runner-local packing and integrity verification
  of temporary source-pinned research states; this does **not** publish, upload,
  or provide a durable private backup. The retired private uploader was never
  an active storage destination. See [working-state limits](../work/README.md).

The UBS Greek and Hebrew lexical workflows, their tests and reviewed
source-specific decisions live under
[links/dictionaries/](../links/dictionaries/), not here. Their source-pinned
CI jobs verify rebuilds without publishing. Never infer a unique contextual
sense merely from a matching dictionary or Strong identifier.

See the [phase 2 inventory](../docs/MAINTENANCE_INVENTORY.md) for removal
boundaries, [release contract](../docs/RELEASE_CONTRACT.md), and
[regression entrypoints](../tests/README.md).
