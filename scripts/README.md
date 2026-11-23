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

## Historical test support and restricted research packaging

- The historical ACAI compiler was moved to
  [test support](../tests/support/legacy_acai_compiler.py), separate from
  production scripts. Original v0.1 label/ZIP preparers remain only in Git
  history. The current native index does not import or replay ACAI sources.
- `work_snapshot.py`: active runner-local packing and integrity verification
  of temporary source-pinned research states; this does **not** publish, upload,
  or provide a durable private backup. The retired private uploader was never
  an active storage destination. See [working-state limits](../work/README.md).

The UBS Greek and Hebrew lexical workflows, their tests and reviewed
source-specific decisions live under
[links/dictionaries/](../links/dictionaries/), not here. Their source-pinned
CI jobs verify rebuilds without publishing. Never infer a unique contextual
sense merely from a matching dictionary or Strong identifier.

See the [maintained tooling map](../docs/MAINTENANCE_INVENTORY.md) for the
current caller and source boundaries, [release contract](../docs/RELEASE_CONTRACT.md), and
[regression entrypoints](../tests/README.md).
