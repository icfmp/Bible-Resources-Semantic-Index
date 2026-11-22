# BRSI — Maintained tooling and source boundaries

This is the **current working inventory**, not a migration diary. Historical
removal decisions, exact file-level proofs and CI outcomes are recorded in
[issue #22](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/22)
and its merged pull requests. Do not keep copies of retired programs here.

## Canonical source and provenance

| Data | Authority and constraint |
| --- | --- |
| `data/entities/`, `data/quarantined/` | Canonical, editable BRSI-owned identity data and explicit quarantine. Do not reimport ACAI or replay patch sequences. |
| `data/source.lock.json`, `data/migration/`, editorial/qualification JSON | Frozen ACAI attribution, original hashes, retained source IDs, reviewed decisions and abstentions. Do not delete or silently rewrite. |
| `links/dictionaries/ubs-greek/index.json` | Checked-in Greek lexical baseline, regenerated only from source-pinned UBS/MACULA editions. |
| `links/dictionaries/ubs-hebrew/index.json` | Checked-in Hebrew lexical baseline, regenerated only from source-pinned UBS/MACULA editions. |
| `links/dictionaries/ubs-*/v1_*.json` and documented review ledgers | Durable editorial identity decisions and source evidence, **not** disposable temporary output. |
| `release/`, `sources/`, `work/` | Distribution locks, upstream provenance, recovery limitations. None is authorization to republish. |

All **868 restricted ACAI Key Terms** remain outside the public entity data.
The native builder must not rewrite original word IDs, verse references,
editorial metadata or translation-source choices.

## Shared scripts — 19 Python files

| Maintained role | Scripts | Current caller or protection |
| --- | --- | --- |
| Canonical native index | `build_native_index.py`, `entity_index_core.py` | Native entity CI and synthetic native growth tests; the current builder does not import the ACAI-era compiler |
| Identity and relation policy | `identity_policy.py`, `localization_policy.py`, `offspring_target_policy.py`, `reference_policy.py` | Native build and corresponding offline tests |
| Read-only identity audits | `audit_entity_relationships.py`, `audit_family_relation_consistency.py`, `audit_identity_surface.py`, `audit_name_ambiguities.py`, `audit_person_overlaps.py`, `audit_reclassified_entity_fields.py` | Native/reclassified/offline workflows for invoked audits; remaining reusable audit covered by standalone tests |
| Lookup and distribution helpers | `resolve.py`, `distribution_profile.py`, `release_contract.py`, `stage_entity_candidate.py` | Dedicated unit tests; candidate/contract verification in native CI, never direct publication |
| Integrity and historical-asset checks | `write_integrity_receipt.py`, `verify_historical_asset.py` | Native build / pinned lexical CI and their tests |
| Runner-local evidence packaging | `work_snapshot.py` | Greek/Hebrew CI packs and verifies a **temporary** private research state, without upload or durable-storage claim |

Only current reusable scripts belong in `scripts/`. The historical ACAI
source-replay compiler is isolated in
[`tests/support/legacy_acai_compiler.py`](../tests/support/legacy_acai_compiler.py)
and exercised by `tests/test_build.py`; it is **not** a production
source-import path.

## Source-specific lexical processes

| Stream | Python tools and tests | Executable entrypoint | Retained editorial authority |
| --- | ---: | --- | --- |
| UBS Greek | 78 total; 36 `test_*.py` modules | [Pinned Greek workflow](../.github/workflows/bsi-ubs-greek.yml) and its source-local builders | Original source locks, reviewed JSON headword/word-ID ledgers, explicit sense abstentions |
| UBS Hebrew | 43 total; 21 `test_*.py` modules | [Pinned Hebrew workflow](../.github/workflows/bsi-ubs-hebrew.yml) and its source-local builders | Original source locks, reviewed JSON identity/disposition/abstention ledgers, v1 and v1.1 reviews |

The Greek and Hebrew workflows first verify exact upstream commits and
source checksums, then reconstruct source-backed indexes, check reviewed
decisions and compare historical public archives. Every source-local
`test_*.py` runs individually via a fail-fast glob. Their full research
chains remain where the source-specific build genuinely depends on them;
a report-only stage with no downstream use is not a reason to keep an
obsolete script forever.

Detailed editorial assumptions and source exceptions belong in each
source's README, not in a generic shared script or a special-case rule
inside the application.

## CI entrypoints

- `offline-checks.yml`: native/workspace unit tests, identity audits and UBS
  baseline smoke tests, with no external source checkout.
- `native-entity-index.yml`: canonical native entity build, candidate
  integrity and source-lock checks; explicitly nonpublishing.
- `audit-native-relations.yml` and `audit-reclassified-fields.yml`:
  independent relational and inherited-field audits.
- `bsi-ubs-greek.yml` and `bsi-ubs-hebrew.yml`: full pinned-source
  lexical reproducibility and historical-archive verification. Runner
  evidence remains local; no source-derived restricted data upload.

## Rules for further retirement

1. Check real callers, imports, active workflow steps, offline tests and
   current documentation; also verify no workflow references a missing
   Python script.
2. Distinguish a reproducible temporary report from a unique reviewed
   source decision, abstention, rights receipt or provenance record.
3. Verify old and new index bytes, published archive hashes and source locks
   when touching a producing chain. Never infer a semantic sense from
   Strong, `sdbh` or `LEXID` resemblance alone.
4. Validate the affected offline/native and source-pinned workflow(s) on
   a PR before merging. Preserve failing evidence; no bypasses to make CI green.
5. Never turn verification or candidate generation into publication.
   Rights and authorized release remain gated by
   [issue #62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62).

Historical actions and obsolete scripts are recoverable from Git commits
and PRs. This file describes only the supported **present**.
