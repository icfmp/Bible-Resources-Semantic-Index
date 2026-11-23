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

## Shared scripts — 23 Python files

| Maintained role | Scripts | Current caller or protection |
| --- | --- | --- |
| Canonical native index | `build_native_index.py`, `entity_index_core.py` | Native entity CI and synthetic native growth tests; the current builder does not import the ACAI-era compiler |
| V2-only graph research | `build_relation_index.py` | Internal nonpublishing research/tests only; **not** product V1 or a V1 release dependency |
| Identity and relation policy | `identity_policy.py`, `localization_policy.py`, `offspring_target_policy.py`, `reference_policy.py` | Native build and corresponding offline tests |
| Read-only identity audits | `audit_entity_relationships.py`, `audit_family_relation_consistency.py`, `audit_identity_surface.py`, `audit_name_ambiguities.py`, `audit_person_overlaps.py`, `audit_reclassified_entity_fields.py` | Native/reclassified/offline workflows for invoked audits; remaining reusable audit covered by standalone tests |
| Lookup and distribution helpers | `resolve.py`, `distribution_profile.py`, `release_contract.py`, `stage_entity_candidate.py`, `validate_external_crosswalk.py` | Dedicated unit tests; candidate/contract verification in native CI, never direct publication |
| Integrity and historical-asset checks | `write_integrity_receipt.py`, `verify_historical_asset.py`, `inspect_v1_published_assets.py` | Native build / pinned lexical CI and their tests; read-only V1 public ZIP compatibility inspection |
| Caller inventory and workflow integrity | `tool_registry.py` | Read-only inventory of shared/source-owned tools, code/test/workflow/doc references; offline CI refuses nonexistent static Python workflow paths. Never infers deletion eligibility. |
| Strict regenerated baseline parity | `verify_generated_json.py` | Generic read-only comparison of two **distinct, present** strict JSON files, rejecting duplicate keys, nonstandard numbers and all value/type changes; both pinned UBS source workflows depend on it. Source checks and editorial reviews remain independent. |

Only current reusable scripts belong in `scripts/`. The historical ACAI
source-replay compiler is isolated in
[`tests/support/legacy_acai_compiler.py`](../tests/support/legacy_acai_compiler.py)
and exercised by `tests/test_build.py`; it is **not** a production
source-import path.

## Source-specific lexical processes

| Stream | Python tools and tests | Executable entrypoint | Retained editorial authority |
| --- | ---: | --- | --- |
| UBS Greek | 76 total; 35 `test_*.py` modules | [Pinned Greek workflow](../.github/workflows/bsi-ubs-greek.yml) and its source-local builders | Original source locks, reviewed JSON headword/word-ID ledgers, explicit sense abstentions |
| UBS Hebrew | 36 total; 18 `test_*.py` modules | [Pinned Hebrew workflow](../.github/workflows/bsi-ubs-hebrew.yml) and its source-local builders | Original source locks, reviewed JSON identity/disposition/abstention ledgers, v1 and v1.1 reviews |

Completed report-only probes are retired once their general exclusion rule
is covered by a maintained test and any non-reproducible editorial decision
is retained beside its source. See issue [#145](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/145) for the second-pass review; the first example
retired a terminal 47-word Greek inflection investigation, while retaining
its independent negative no-guess invariant and the 47-word source report.

The discontinued runner-only `work_snapshot.py` generated temporary archives
and verified them inside the same CI job but never stored them. It added no
independent durable evidence beyond the source-pinned checks and the historical
release parity gates. Its implementation and tests are preserved in Git history;
no private research corpus was copied, published, or lost from Git.

The completed Hebrew v1.1 semantic-feasibility and 72-word pilot
was **one-shot research**, not an active v1.0 release dependency. Three
nonpublishing pilot scripts and their three dedicated tests were retired
from `main` under [#145](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/145);
the two historical reports and original six source-specific editorial
cautions remain beside UBS Hebrew. Immutable Git revisions preserve the
reproduction commands. No v1.0 source-locked builder, negative headword
identity guard, or published archive verification was removed.

The Greek and Hebrew workflows first verify exact upstream commits and
source checksums, then reconstruct source-backed indexes, check reviewed
decisions and compare historical public archives. **A missing checked-in
baseline now fails**: the earlier Hebrew initial-import fallback is no longer
allowed. The shared strict JSON verifier compares source-rebuilt resources
against the canonical committed baselines, with no edition-specific logic.
The formerly separate Hebrew headword-scope report step was retired because
both source-pinned private/final builders already call the maintained
`audit_dictionary_scope.py` on actual WLC inputs; its tests remain.
The Greek and Hebrew workflows also use the shared
`verify_historical_asset.py` to enforce **exact released archive bytes**;
their separate temporary ZIP-fingerprint display steps were redundant with
that historical release lock and the preceding independently verified
`.sha256` sidecars, so both were removed.

The old Hebrew numeric-SDBH/UBS cross-edition **diagnostic survey**
had no persisted report, no downstream builder consumer and no independent
drift gate. The `build_index.py` lookup already rejects false direct
sense identity across original Strong numeric families and H/A languages;
`test_index.py` covers real-pattern and synthetic negative collisions.
The terminal report-only auditor was retired; its complete historical
implementation remains at [the prior Git revision](https://github.com/icfmp/Bible-Resources-Semantic-Index/blob/7ea875a5a866d678958264a8f830418ed538a7ce/links/dictionaries/ubs-hebrew/audit_direct_sense_fidelity.py).
It was never permission to infer a new UBS contextual sense.

Five Hebrew source-evidence outputs now use the **same strict JSON baseline
guard**: Strong-family reconciliation, the initial reviewed word preview,
the remaining-family witness census, the subsequent word-specific approvals,
and the v1 editorial-disposition coverage report. These five checked-in
evidence JSON files are **mandatory** and unchanged. The former optional
"pending initial pin" bypasses have been retired; source-side validators,
word-ID checks and dedicated unit tests remain in place. Every source-local
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

## Audit current callers before a removal

Run `python3 -I scripts/tool_registry.py --json` to generate a **read-only**
per-tool reference inventory, or `python3 -I scripts/tool_registry.py
--check-workflows` to fail when an active GitHub Actions workflow cites a
missing local Python script. Static references are **hints**: a missing caller
is not proof of obsolete code, and dynamic imports or historical release
checkouts require separate review. The inventory is generated when needed,
not checked in as a second stale registry.

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
