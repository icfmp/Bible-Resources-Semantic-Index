# Original upstream provenance (historical)

The canonical, **editable** BSI entity data now lives in
[../data/entities/](../data/entities/), not in an ACAI checkout.

## Frozen historical baseline

- Source: [ACAI at pinned commit e80a874](https://github.com/icfmp/ACAI/tree/e80a874e8282f996199c595378a3b3b9a43aac22).
- Original imported entity set: **6,644** JSON records across eight categories.
- Original source license: **CC BY-SA 4.0** (Mission Mutual / BiblioNexus attribution).
- Exact original SHA-256 snapshot: in [../data/source.lock.json](../data/source.lock.json).
- One-time migration manifest: [../data/migration/acai-baseline-materialization.json](../data/migration/acai-baseline-materialization.json).
- Current editable corrections: each BSI record contains provenance and any reviewed editorial evidence.
- All 868 ACAI keyterms remain counted but excluded from this public BSI source branch, pending field-level permission verification for Paratext UBS material ([issue #5](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/5)).

The source is **not fetched or patched by the current BSI builder**. Source
checkout and the old patch-replay generator survive only in Git history and
the draft migration's independent equivalence checks, not as the active editing
process. Do not edit the pinned ACAI original.

MACULA Hebrew/Greek and UBS dictionaries remain independent, edition-pinned
lexical evidence sources. Their texts and permission-only annotations must
not be copied into public releases without explicit rights clearance.
