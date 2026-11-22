# Phase 2 — maintenance and removal inventory

Status: **initial caller/provenance classification, not deletion approval**.
Tracking: [issue #22](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/22).

## Source-of-truth boundaries

| Path | Classification | Required preservation |
| --- | --- | --- |
| `data/entities/`, `data/quarantined/` | Current canonical entity source | Stable identity, original references, reviewed edits and quarantine |
| `data/*.json`, `data/migration/` | Locks, editorial decisions and provenance | Source fingerprints, rights, abstentions, migration evidence |
| `links/dictionaries/ubs-greek/index.json`, `ubs-hebrew/index.json` | Versioned lexical development baselines | Checked-in bytes and pinned source identity; **not automatic release approval** |
| `links/dictionaries/ubs-*/v1_*.json`, `family_register.json`, `reconciliation_candidates.json` | Source-specific editorial evidence / decisions | Do not delete as disposable generated output without confirming exact reproducibility and no irrecoverable review |
| `scripts/build_native_index.py`, `scripts/entity_index_core.py`, `scripts/*policy.py`, `scripts/resolve.py` | Shared maintained tools | Native build and tested invariants |
| `scripts/audit_*.py`, `scripts/prune_*.py` | Shared audits and tested one-time normalization | Current CI checks and regression coverage |
| `scripts/compile_index.py`, `minimal_labels.py`, `package_candidate.py` | Historical construction and tested support | Native builder now uses `entity_index_core.py`; retain legacy rebuild only for historical tests and evidence |
| `scripts/work_snapshot.py` | Active runner-local snapshot pack/verification | Rebuild integrity evidence only; no persistent private backup or upload |
| `links/dictionaries/ubs-*/audit_*.py`, `build_*.py`, `test_*.py` | UBS-specific research, builders and checks | Separate true maintained source-pinned workflows from obsolete one-offs by examining actual call graph |
| `docs/V0_1_*.md`, `docs/BSI_V0_1_*.md` | Historical editorial/release evidence | Keep only verifiable decisions and published evidence, mark as historical |
| `work/`, `sources/`, `release/` | Recovery policy, source provenance, historical release locks | Never imply publication or durable archival that did not occur |

## Removed with verified absence of callers

- `links/dictionaries/ubs-hebrew/inspect_sources.py`: initial read-only
  schema/TSV sample printer. Not referenced by either pinned source workflow,
  current tests, or indexed repository code search; its inspection is not a
  canonical build or source-specific editorial decision. Removing this helper
  does not remove any reviewed JSON ledger or frozen source baseline.

- `links/dictionaries/ubs-hebrew/analyze_alignment.py`: print-only
  exploratory comparison of original source inventory; the maintained
  `build_index.py` and pinned verifications independently check source identity.
- `links/dictionaries/ubs-hebrew/audit_variants.py` and
  `audit_top_lemmas.py`: former exploratory morphology/frequency reports,
  written only to temporary JSON files; no later workflow step consumes them.
  Retained source-specific lexical checks and decision ledgers are unchanged.
  The three associated no-longer-needed workflow stages were retired together.

- `links/dictionaries/ubs-greek/audit_sense_form_witnesses.py` and
  `audit_sense_reference_shapes.py`, plus their dedicated offline negative
  tests: exploratory reports of original UBS form and LEXReferences *shapes*
  from earlier contextual research. Both reports were runner-local and
  unconsumed downstream. Subsequent source-pinned form-supported and
  reference-/verse-supported candidate verification remains in CI, as do all
  original approved/abstained source decisions. No lexical baseline changed.

- `links/dictionaries/ubs-hebrew/audit_unmatched.py`: early diagnostic-only
  unresolved-row categorization, producing `/tmp/bsi-ubs-hebrew-unmatched-audit.json`
  with no downstream consumer, tests or retained editorial ledger. Retired
  together with its CI step; the more precise lexical gap, dictionary scope,
  source attestation and abstention verifiers are still maintained.

- `links/dictionaries/ubs-hebrew/audit_unmatched.py`: superseded read-only
  early unresolved-row census with no downstream JSON consumer or editorial
  decision ledger. Its CI stage was removed in PR #69, while the maintained
  lexical-gap, dictionary scope and abstention audits remain.
- `scripts/publish_private_work_snapshot.sh`: inactive private uploader with
  no current CI caller, no verified destination and an obsolete monorepo path.
  Removed in PR #70. The actively invoked runner-local `work_snapshot.py`
  and its regression tests were explicitly retained; these **do not upload**.

## Verified CI entrypoints

- `offline-checks.yml`: native unit tests, identity and relationship audits,
  description/label `--check` commands, baseline UBS index unit tests.
- `native-entity-index.yml`: canonical entity build and candidate validation.
- `bsi-ubs-greek.yml` and `bsi-ubs-hebrew.yml`: external source-pinned
  lexical rebuilds; their dependency chains must be followed before retiring
  a source-specific builder or audit.
- `audit-native-relations.yml`, `audit-reclassified-fields.yml`:
  independent audit workflows.

## Removal gate (mandatory)

1. Find direct calls in workflows, imports, other scripts, tests and current
   documentation; a filename that looks historical is not sufficient evidence.
2. Identify the exact source lock, reproducible generator and retained
   editorial decision ledger, if any.
3. Demonstrate that deletion does not change canonical source records,
   checked-in indexes, approved identities, version/provenance metadata or
   the historical published assets.
4. Delete in coherent batches and run the offline, native entity and
   **both** source-pinned UBS checks before merging each removal batch.
5. Keep releases disabled. Publication and redistribution rights remain
   separately gated in [issue #62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62).

This inventory deliberately does **not** certify any UBS audit/builder as
unused yet. Full caller-level inspection is the next task; losing a reviewed
lexical decision in the name of tidiness would be a regression.
