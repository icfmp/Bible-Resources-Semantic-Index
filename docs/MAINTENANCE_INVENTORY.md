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
| UBS Hebrew | 37 total; 19 `test_*.py` modules | [Pinned Hebrew workflow](../.github/workflows/bsi-ubs-hebrew.yml) and its source-local builders | Original source locks, reviewed JSON identity/disposition/abstention ledgers, v1 and v1.1 reviews |

Active source-pinned UBS workflows reconstruct source material from exact
upstream revisions, check original-word identifiers and source-specific
editorial ledgers, then compare reconstructed **historical public ZIP bytes**
against immutable release locks. A source-derived private report or research
probe is not a new publication authorization; all rights, negative decisions
and original source annotations remain separately protected.

- **Greek headwords:** the reviewed 224-source-word Strong ambiguity and
  temporal ὁπότε cases are audited directly in their builders; the
  original 459-word missing-headword witness is partitioned into 3
  separately reviewed case-only words and 456 source words checked against
  authentic bilingual UBS `AlternateLemmas`. Exactly 409 individually
  authorized headword links and 47 explicit abstentions remain in the
  final source-specific ledgers; accent/inflection/Strong resemblance is
  never sufficient evidence of lexical identity. Five approved-word
  stages (577/155/138/32/2) share the exact original-word witness and
  status-only transition guard, but keep their original, distinct
  editorial and language-specific Strong/grammar decisions.
- **Greek no-LN headwords:** the complete original 1,218-word/8-family
  lexical-entry-only audit still reruns against pinned UBS and MACULA
  originals inside the separate reviewed builder, without a redundant
  runner-only temporary report.
- **Greek composite Strong and provisional senses:** the 5-original-word
  compound-Strong source audit, full 137,741-word UBS/MACULA sense
  *candidate* census, and 15,237-word unresolved-source priority
  classification run **inside** their maintained builders. Each retained
  source-specific auditor checks the original data directly, without a
  redundant temporary JSON handoff. All 123,195 provisional source-based
  suggestions remain *unverified contextual meanings*, with 14,546
  unresolved, and must not be republished or silently promoted. The final
  40-word provisional source-position tier likewise recalibrates authentic
  UBS citation locators directly from pinned bilingual sources and its
  source-unique MACULA candidates. No global source token-number equivalence
  is assumed. The 258-word source-verse provisional tier also
  reruns the full bilingual UBS LEXReferences and original MACULA
  137,741-word census inside its builder; a source-verse citation is
  not independent contextual semantic approval.
- **Hebrew:** v1.0 remains source-pinned, including the original-word
  identity and H/A Strong/SDBH anti-collision rules. The six committed
  JSON baselines (index plus five source-evidence snapshots) are
  mandatory strict-content gates. The historically completed v1.1
  53,981-candidate / 72-word NO-GO experiment is retained in versioned
  editorial reports, **not** the maintained v1.0 workflow.
- **Shared protection:** `verify_generated_json.py` fails on missing or
  altered source-basis evidence. `verify_historical_asset.py` verifies
  exact previously published assets without uploading or publishing a
  resource. Source-specific auditors and all source-local `test_*.py`
  modules remain independently maintained.

Retired one-off programs, runner-only reports, source-revision links
and batch-by-batch audit outcomes are recorded in
[maintenance issue #145](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/145)
and the merged PRs, not duplicated as a development diary here.

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
