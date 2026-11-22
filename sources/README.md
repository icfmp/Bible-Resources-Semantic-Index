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

The source is **not fetched or patched by the current BRSI builder**. Legacy
source-checkout and one-time migration helpers are archived in Git history.
The historical ACAI compiler now lives exclusively in
[regression support](../tests/support/legacy_acai_compiler.py) to independently
test old source-to-index behavior. Shared source-link validation resides in
the maintained [entity core](../scripts/entity_index_core.py), not that
historical compiler. Never use source replay as the current editing process
or modify the pinned ACAI originals.

MACULA Hebrew/Greek and UBS dictionaries remain independent, edition-pinned
lexical evidence sources. Their texts and permission-only annotations must
not be copied into public releases without explicit rights clearance.
