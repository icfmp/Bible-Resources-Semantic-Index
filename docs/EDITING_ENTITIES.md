# Editing current BSI entities

The **versioned current entity files** under `data/entities/` are the editable
BSI dataset. They are **not** rebuilt by replaying historical ACAI patches.

## Editing rule

1. Edit the relevant `data/entities/<original-category>/<source-name>.json` file.
   Preserve the stable `bsi.source_id` identifying the historical source, even
   if the reviewed `id` or `type` is changed.
2. Record the reason, original word/verse evidence and provenance of any
   substantive editorial change in the same file's `bsi` metadata and in
   the pull request. Do not silently delete a reference, word grouping,
   localization, duplicate, or ambiguity.
3. Run `python3 -I scripts/build_native_index.py --output /tmp/bsi-current.json`.
   The builder reads **only** the current tracked records and source/edition
   qualification metadata: it does not fetch ACAI or replay edits.
4. Validate CI, including exact word-ID structure and ambiguous reverse
   lookups, before merging.
5. If an identity was quarantined, keep its original evidence under
   `data/quarantined/`, with a reason; never silently drop its source record.

## Preserved migration evidence

- Pinned original source: `icfmp/ACAI@e80a874e8282f996199c595378a3b3b9a43aac22`.
- Original source fingerprint and category counts:
  `data/migration/acai-baseline-materialization.json`.
- Every native record retains `bsi.source_id`, `bsi.source_sha256`,
  original source primary ID, and reviewed rationale when applicable.
- The original `data/editorial-decisions.json` is **historical evidence**,
  not a patch list for normal future builds.
- The legacy builder and one-time comparison tools exist only to audit the
  extraction until migration acceptance. They are not the future editor.

**Rights boundary:** 868 ACAI `keyterms` are accounted for but not included
in the committed native working set pending explicit source-field clearance,
tracked by issue #5. Do not manually reintroduce their original payloads.

**Release boundary:** editing the current data does not automatically publish
a new resource. Releases require distinct source/rights and version checks.
