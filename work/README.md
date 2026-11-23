# BRSI source states and recovery

This is the **durability boundary**, not a second archive or an alternate
publishing process.

## Authoritative retained evidence

- Canonical editable entity records and quarantined originals:
  `data/entities/`, `data/quarantined/`.
- Source revision locks, hashes, source-field corrections, reviewed decisions,
  abstentions and individual original-word evidence in versioned Git data.
- Checked-in UBS Greek/Hebrew **development** indexes with maintained
  source-specific review ledgers. They are **not** a grant of publication rights.
- The three historic, narrow public BSI/UBS ZIPs continue to reside in
  `icfmp/Bible-Resources`, with separately verified historical fingerprints.

The **868 restricted ACAI Key Terms** are not present in current public
source records or their released indexes.

## What cannot be recovered from this repository alone

The pinned UBS workflows generate complete, source-derived private research
intermediates. They intentionally do **not** upload those rights-restricted
files as public GitHub Actions artifacts. No independently verified durable
private archive of **every** past token/verse witness exists here. This is a
known limitation, not a claim of data preservation.

A prior runner-only tool `scripts/work_snapshot.py` created and verified
short-lived archives in the same job; those archives were **never uploaded,
restored from a separate store or retained**. Since they supplied no durable
backup, the tool, its tests and the two terminal workflow stages were retired
in [issue #145](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/145).
The former private uploader had already been retired. Both implementations
remain retrievable from immutable Git revisions.

## How to reproduce a supported state

1. Check out the required BRSI Git commit.
2. Build the canonical native entity index with
   `python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-entities.json`.
3. Rebuild UBS data through the corresponding
   [pinned Greek](../.github/workflows/bsi-ubs-greek.yml) or
   [pinned Hebrew](../.github/workflows/bsi-ubs-hebrew.yml) source workflow:
   verify exact upstream commits, source hashes and reviewed ledger invariants.
4. Compare reconstructed results with the checked-in source-specific index,
   the appropriate review ledgers and historical public archive hashes.

These instructions reproduce **validated, permission-scoped outputs**. They
do not guarantee recovery of expired, uncommitted research files, contextual
meaning approval, or authorization for redistribution.

If a future research program requires truly durable private snapshots, it
needs a separately approved legal/storage plan, independently verified
upload and readback, per-file checksums, an explicit restore drill, and
strict exclusion of unlicensed public artifacts. Do not invent a second
canonical working dataset alongside Git.
