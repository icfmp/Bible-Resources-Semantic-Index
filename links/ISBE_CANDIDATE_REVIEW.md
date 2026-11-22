# V1 external resource candidate — historical ISBE (assessment only)

**Status: candidate edition, not an approved BRSI crosswalk or redistribution clearance.**

This assessment supports [#25](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/25) without claiming that coincident biblical names establish matching identities.

## Source and version boundaries

| Layer | Verifiable source | Consequence for BRSI |
| --- | --- | --- |
| Historical print work | *International Standard Bible Encyclopedia*, James Orr edition (1915), as identified by the [ISBE project's source policy](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/source-policy.md) | Historical identity alone does **not** prove that a digital article is error-free or legally cleared for all uses |
| CrossWire digital edition | SWORD ISBE module **2.2**, retained unchanged under `sources/crosswire/isbe-2.2/ISBE.zip` with provenance manifest | Its configuration declares `DistributionLicense=Public Domain`; this declaration is not a standalone field-level legal assessment |
| BRSI-adjacent normalization | `icfmp/Bible-Resources-ISBE/cleaned/en/ISBE.xml`, TEI P5 4.12.0 working master | The work is still under editorial validation and is **not** a public BRSI dictionary release |
| ISBE article locator | `cleaned/en/article-index.json`, matched to one `<div type="entry">` per original entry | Stable target ID: `isbe-` + first 20 hex digits of SHA-256 of the **exact original SWORD key**, not a lowercased or normalized guessed title |

Evidence: [ISBE README](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/README.md), [article format](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/article-format.md), [source policy](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/source-policy.md).

At the time of this assessment, the ISBE project reports **9,380** TEI entries, a source-faithful canonical master, and unresolved printed-edition and digital-source rights reviews. The source-preserving conversion is distinct from a reviewed article-to-BRSI-entity concordance. The ISBE article ID is designed to survive future language editions, but each **content edition/revision** must still be pinned individually.

## Minimum contract for an eventual crosswalk

1. Freeze the exact ISBE **Git commit**, canonical TEI checksum, article-index checksum and editorial edition/revision, *then* record the complete BRSI producer commit in the V1 crosswalk provenance. A moving `main` URL is not an edition pin.
2. Verify an ISBE `entry_id` by exact key-to-hash computation and by presence in that pinned source's article index. A syntactically well-formed `isbe-...` is not sufficient.
3. Compare the **actual article scope** and cited biblical evidence with the proposed BRSI identity. Name equality, English aliases and shared Bible references are candidate-generation hints only, never editorial proofs.
4. Preserve multiple biblical persons or locations with the same headword as distinct candidates. Record `ambiguous_entries`, `identity_unresolved` or another supported **withheld** reason until someone checks the source. Do not silently choose the first ISBE article.
5. Confirm redistribution of **mapping metadata** separately from the digital article text, editorial annotations and any later modernization or translation. Do not copy any article text into BRSI.
6. Validate future crosswalks with `python3 -I scripts/validate_external_crosswalk.py --scan --data data`, plus a **source-specific** pinned ISBE entry-ID existence check before approval. The current generic validator checks BRSI IDs and metadata, **not** whether foreign entry IDs actually exist.

## Current result

**No accepted ISBE mapping has been created.** No BRSI source record or ISBE article has been edited, and no artifact is published. In particular, the existing ISBE project's **internal** repaired cross-references are not automatically evidence of cross-project BRSI identity equivalence.

**Next independent evidence needed:** exact ISBE source-version lock and article-index lookup, sample real article/entity pairs with verse-level disambiguation, and explicit rights review. Until these exist, retain this as a nonpublishing candidate source assessment, not as an approved JSON edition in `links/encyclopedias/`.
