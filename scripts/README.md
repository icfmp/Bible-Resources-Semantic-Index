# BSI shared scripts

Only the source-neutral **entity index** tools live here:

- `compile_index.py` — immutable ACAI source snapshot + audited entity index
- `resolve.py` — source-word and edition-aware candidate resolver
- `distribution_profile.py` — keyterm-free public projection
- `minimal_labels.py` — minimal approved source label selection
- `package_candidate.py` — deterministic candidate archive and manifest
- `audit_person_overlaps.py` — reusable person-word overlap analysis
- `build_native_index.py` — current Git-owned, keyterm-free native entity build
- `write_integrity_receipt.py` — simple local SHA-256 and byte-size receipt
- `release_contract.py` — strict v1 multi-kind manifest and consumer-pin verifier; **never publishes**

The historical `package_candidate.py` and `minimal_labels.py` reproduce the *old v0.1 source workflow*; they do not automatically stage current edited native data or validate new lexical publication rights. See [phase 1 release contract](../docs/RELEASE_CONTRACT.md).

Regression tests are in [../tests/](../tests/). Source locks, reviewed edits
and exception inventories are in [../data/](../data/); outputs go into
ignored `../dist/`. See [../README.md](../README.md).

UBS Hebrew- and Greek-specific scripts are **not generic**: they are kept
with their pinned dictionary editions in `../links/dictionaries/`.
Never infer a contextual sense or republish source wording from the
presence of a matching lexical ID.
