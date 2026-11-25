# Source rights and local integrity boundary

This document explains the **current development repository**, not a release
approval or a replacement for source-specific license notices.

## Separate code and data rights

- `COPYING` contains the **GPL-3.0 license text for BSI software**. It does
  **not** by itself relicense independently authored source datasets.
- The imported ACAI JSON entity records are source-pinned at
  `data/source.lock.json`; ACAI identifies the JSON/Markdown release as
  **CC BY-SA 4.0**, with BiblioNexus / Mission Mutual attribution.
  Edited BSI entity records remain adaptations subject to the same
  attribution and share-alike obligations. Their `bsi.source_id`,
  `bsi.source_sha256` and editorial decisions retain traceability.
- Exact original-language word identifiers refer to pinned MACULA WLC/SBLGNT
  editions. Those identifiers do **not** confer redistribution permission for
  the underlying manuscript text, token annotations or full source TSVs.
- UBS Greek and Hebrew research uses exact edition-pinned dictionary data.
  Refer to `links/dictionaries/ubs-greek/` and
  `links/dictionaries/ubs-hebrew/` for their source/rights and release
  readiness evidence. A source repository's public availability is **not**
  permission to republish every field.
- **868 imported ACAI Key Terms are excluded** from current BSI source data
  and publication, pending separate field-specific permission investigation.
  Permission-only Paratext/UBS content must not be reintroduced incidentally.
- Inherited multilingual biographies and redundant translated display names
  were retired from editable BRSI records. The retained English source labels
  and some aliases are **source-unreviewed**, not independently approved;
  see `docs/LOCALIZATION_REVIEW.md` for the fail-closed reader-export rule.

The existing historical releases and their original attribution documents
remain in `icfmp/Bible-Resources`. Do not rewrite historical archives.
Source rights and publication eligibility must be reviewed separately for
each new BSI release. The earlier review for v0.1.0 is
`docs/BSI_V0_1_RIGHTS_AUDIT.md`.

## Reproducible local file-integrity receipt

After a fresh native entity build, run:

```sh
python3 -I scripts/build_native_index.py --data data --output /tmp/bsi-current.json
python3 -I scripts/write_integrity_receipt.py \
  --entity /tmp/bsi-current.json \
  --greek links/dictionaries/ubs-greek/index.json \
  --hebrew links/dictionaries/ubs-hebrew/index.json \
  --output /tmp/bsi-integrity-receipt.json
```

The receipt contains only SHA-256 and exact byte sizes for these three local
files. It is deterministic given identical file bytes, and intentionally lacks
timestamps, host paths and repository-wide source dumps. It describes the
**current local files**, not the historical release ZIP archives.

A valid checksum proves neither canonical equivalence nor source rights,
lexical completeness, semantic correctness or editorial acceptance. In
particular, hashing checked-in lexical baselines does **not** replace the
independent source-pinned Greek and Hebrew verification workflows. No receipt
is a publication authorization; a future distribution contract must add
exact source Git commit, declared version, approved release scope, attribution,
artifact checksums and explicit owner approval.
