# BRSI roadmap — current work and release gates

This page is the **short operational map**, not a development diary.
Actual decisions, discussion, complete test evidence and source-specific
corrections belong in linked GitHub issues/PRs and edition review ledgers.
Historical states are recoverable by Git revision.

## Verified current baseline

- **Entities:** 5,773 active editable source identities plus three explicitly
  quarantined records. The 868 permission-restricted ACAI Key Terms remain
  excluded. Original source locks, exact original-word witnesses, reviewed
  corrections, abstentions and reversible receipts are versioned.
- **Native source audit:** [#23](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/23)
  is **closed**. All 462 originally detected key-reference/general-reference
  discrepancies were examined: 399 previously certified, 58 further verified
  contextual references, five corrected discrepancies. Current state has
  457 legitimate key-only pairs and **zero unaccounted pairs**. A key verse
  is not required to appear in the general reference list.
- **Lexical source links:** pinned UBS [Greek](../links/dictionaries/ubs-greek/README.md)
  and [Hebrew](../links/dictionaries/ubs-hebrew/README.md) datasets, with
  separate review ledgers and source-specific validation. A dictionary
  candidate is not an independently certified contextual sense.
- **Historical assets:** three separately versioned BSI/UBS ZIPs remain
  published in `icfmp/Bible-Resources`. Reproducible verification is
  documented; **no new BRSI release has been approved**.

## Work order

| Priority | Work | State and required next action |
| --- | --- | --- |
| P1 | Native identities, canonical source and original-word validation ([#6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6), [#23](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/23)) | **Completed.** Keep regression and source-evidence gates active. Never invent a reference, name, relation or token to reach a metric. |
| P1 | Standalone migration, nonpublishing producer/consumer integrity contract ([#1](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/1), [#21](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/21)) | **Technical work completed.** Keep historical public asset hashes/source identities immutable. |
| P1 | New public artifacts and downstream delivery ([#62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62)) | **Blocked on explicit owner approval and per-field redistribution rights.** No silent release, app edit or catalogue update. |
| P2 | Generic tooling and durable documentation ([#22](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/22), [#145](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/145)) | Initial migration cleanup completed; second-pass one-shot retirement and source-guide consolidation in review. Preserve useful tests and unique editorial evidence. |
| P2 | Edition-specific external article links ([#25](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/25)) | **Scoped only to existing UBS bridges, then ISBE, then a future offline Wikipedia-derived resource.** UBS is the existing lexical source, not an additional dictionary-import task. ISBE's edition/article IDs and rights must be independently approved before mappings; **do not start Wikipedia mapping before ISBE work is completed**. |
| P3 | Offline pack format and independent Bible consumer contract ([#26](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/26)) | Design/update/rollback/locale/failure cases remain; no Bible app changes without separate authorization. |

### Different data stream: MACULA ↔ Louis Segond alignment

The verified word-to-word alignment for the LSG is **not** an external
dictionary/article crosswalk and is not supplied by UBS lexical IDs.
[The Bible application issue #282](https://github.com/icfmp/Bible/issues/282)
already identifies the Clear.Bible alignment candidate and edition mismatch
risk. BRSI can separately curate a source-pinned alignment **only after**
the real Hebrew/Greek-to-LSG payloads, licences, corpus editions and token
correspondences have passed an evidence-based feasibility review. No import,
publication or correction is authorized by this roadmap note. The requested
repository cleanup comes first.

## Explicitly deferred or excluded

- [#24](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/24):
  semantic entity-to-entity graph is **product V2 only**. Existing private
  research and regression code do not make it a V1 data or UI requirement.
- [#27](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/27):
  original Greek/Hebrew contextual UBS sense research is **deferred**.
  Hebrew 53,981 source/verse candidates and a 72-word screening pilot do
  **not** justify automatic sense promotion; Greek provisional candidates
  remain unreviewed.
- [#5](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/5):
  all 868 restricted Key Terms remain excluded until separately permitted.
- Private research artifacts: preserve **unique** reviewed reasoning and
  source/word witnesses in the appropriate review ledgers; regenerate
  reproducible intermediate reports, without a blanket public CI upload
  or second duplicate archive.

## Maintenance and completion standard

Use the [source/tool inventory](MAINTENANCE_INVENTORY.md), [source integrity
policy](RIGHTS_AND_INTEGRITY.md) and [release contract](RELEASE_CONTRACT.md).
Current general instructions belong in `docs/` and `scripts/`; pinned
edition-specific judgments and tests belong beside that edition. Delete
superseded one-shot command chains only after checking live callers,
downstream output, source-evidence uniqueness and the appropriate CI.

**Implemented is not tested, source-certified, legally cleared or published.**
A task is complete only after the relevant independent verification has
passed, the change is versioned, and the corresponding issue/PR records
the result. Publishing always requires explicit owner authorization.
