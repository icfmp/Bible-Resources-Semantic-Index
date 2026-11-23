# V1 external resource candidate — historical ISBE (assessment only)

**Status: candidate edition, not an approved BRSI crosswalk or redistribution clearance.**

This assessment supports [#25](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/25) without claiming that coincident biblical names establish matching identities.

## Source and version boundaries

| Layer | Verifiable source | Consequence for BRSI |
| --- | --- | --- |
| Historical print work | *International Standard Bible Encyclopedia*, James Orr edition (1915), as identified by the [ISBE project's source policy](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/source-policy.md) | Historical identity alone does **not** prove that a digital article is error-free or legally cleared for all uses |
| CrossWire digital edition | SWORD ISBE module **2.2**, retained unchanged under `sources/original/encyclopedias/en/isbe-crosswire-2.2/ISBE.zip`, SHA-256 `4de747545d9c349ab724bc1708b01df5481e3b93e5e51077f859dd8a32023a32` | Its configuration declares `DistributionLicense=Public Domain`; this declaration is not a standalone field-level legal assessment |
| CrossWire-faithful TEI witness | `workspace/witnesses/crosswire-2.2/ISBE.xml`, SHA-256 `a54c060420518db1c15bbf54264ed3652ec45e62f93c9af106c44d101add5e25` | Exact digital-source-derived TEI reference, **not** the historically corrected text |
| Corrected historical ISBE source | `sources/cleaned/encyclopedias/en/isbe-1915/ISBE.xml`, TEI P5 4.12.0, SHA-256 `5df8a6d1311e3f5a83a6d961c6e09c27e042b0c68b4a9da54cb98821cb878d2c` | Working editorial text and future modernization base; **not a published BRSI dictionary release** |
| ISBE article locator | `workspace/witnesses/crosswire-2.2/article-index.json`, SHA-256 `bdfa352af5b372874e6d2578e86ebae38a70efb64489a91e8985f3b09f2e18e1`, matched to one `<div type="entry">` per original entry | Stable target ID: `isbe-` + first 20 hex digits of SHA-256 of the **exact original SWORD key**, not a lowercased or normalized guessed title |

Evidence: [ISBE README](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/README.md), [article format](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/article-format.md), [source policy](https://github.com/icfmp/Bible-Resources-ISBE/blob/main/docs/source-policy.md).

The current independently reviewed ISBE source tree is pinned to [ISBE commit `8bc1d312712e58750f0ad97c19f71df889afca1b`](https://github.com/icfmp/Bible-Resources-ISBE/commit/8bc1d312712e58750f0ad97c19f71df889afca1b) ([PR #78](https://github.com/icfmp/Bible-Resources-ISBE/pull/78)), which moved the archive, unchanged witness and corrected source *without altering their exact bytes or article IDs*. The corrected historical TEI's separately maintained source lock is verified by official TEI P5 tests; its rights review remains open. Do not bind a crosswalk to a moving `main` reference or to the obsolete root `cleaned/` path.

At the time of this assessment, the ISBE project reports **9,380** TEI entries, a source-faithful technical witness, a corrected historical master, and unresolved printed-edition and digital-source rights reviews. The source-preserving conversion is distinct from a reviewed article-to-BRSI-entity concordance. The ISBE article ID is designed to survive future language editions, but each **content edition/revision** must still be pinned individually.

## Minimum contract for an eventual crosswalk

1. Freeze the exact ISBE **Git commit**, canonical TEI checksum, article-index checksum and editorial edition/revision, *then* record the complete BRSI producer commit in the V1 crosswalk provenance. A moving `main` URL is not an edition pin.
2. Verify an ISBE `entry_id` by exact key-to-hash computation and by presence in that pinned source's article index. A syntactically well-formed `isbe-...` is not sufficient.
3. Compare the **actual article scope** and cited biblical evidence with the proposed BRSI identity. Name equality, English aliases and shared Bible references are candidate-generation hints only, never editorial proofs.
4. Preserve multiple biblical persons or locations with the same headword as distinct candidates. Record `ambiguous_entries`, `identity_unresolved` or another supported **withheld** reason until someone checks the source. Do not silently choose the first ISBE article.
5. Confirm redistribution of **mapping metadata** separately from the digital article text, editorial annotations and any later modernization or translation. Do not copy any article text into BRSI.
6. Validate future crosswalks with `python3 -I scripts/validate_external_crosswalk.py --scan --data data`, plus a **source-specific** pinned ISBE entry-ID existence check before approval. The current generic validator checks BRSI IDs and metadata, **not** whether foreign entry IDs actually exist.

## Current result

**No accepted ISBE mapping has been created.** No BRSI source record or ISBE article has been edited, and no artifact is published. In particular, the existing ISBE project's **internal** repaired cross-references are not automatically evidence of cross-project BRSI identity equivalence.

**Next independent evidence needed:** implement a source-specific pinned ISBE article-index existence check, independently review representative actual ISBE article/entity pairs with verse-level disambiguation, and complete the explicit rights review. The source edition, index SHA-256 and repository revision are now identified. Until these exist, retain this as a nonpublishing candidate source assessment, not as an approved JSON edition in `links/encyclopedias/`.
