# BSI working states and recovery

## What is durable today

This **public** repository stores the canonical, editable BSI entity JSON
records, reviewed editorial data, UBS Greek/Hebrew lexical source baselines,
source revision locks, scripts and tests in Git. These versioned files survive
the lifetime of a GitHub Actions run and can be checked out at an exact commit.

The first 5,776 imported entity files were independently verified against
ACAI source and the prior public index. The 868 Key Terms are **not** in
the public working dataset or current releases; they remain excluded pending
separate rights review.

The *historical published*, narrower ZIPs are GitHub Releases hosted by
`icfmp/Bible-Resources`; they are not copies of all original evidence files.

## What is NOT durable

Full source-derived original-word review output may be generated inside
the UBS Greek and Hebrew source-pinned CI jobs. This includes detailed
candidate/context evidence that cannot simply be treated as freely
redistributable. Those jobs now **do not upload any CI artifacts** containing
that evidence to a public repository.

**No permanent full-state archive of those generated private-evidence files
has been verified in this repository.** A successful build or a source lock
is not a substitute for an independently verified durable backup of every
intermediate file.

The generic `scripts/work_snapshot.py` and
`scripts/publish_private_work_snapshot.sh` remain in source control as
historical, not currently invoked tooling. Their existence does not imply a
private destination was provisioned, or that an archive was ever uploaded.
The private-storage workflow from the former Bible-Resources tree is **not
active here**. Do not re-enable it or upload full source-derived evidence
without an explicit rights and storage decision.

## Reproducible recovery available now

1. Select a known Git commit in this repository.
2. Check out the canonical entity data, Greek/Hebrew baseline indexes,
   source revision locks and pinned editorial decisions from that commit.
3. Rebuild the entity index using `scripts/build_native_index.py`; it
   requires no ACAI checkout.
4. For a Greek or Hebrew source-corpus rebuild, run the corresponding
   [Greek](../.github/workflows/bsi-ubs-greek.yml) or
   [Hebrew](../.github/workflows/bsi-ubs-hebrew.yml)
   source-pinned workflow at the selected commit. These fetch exact
   source revisions and validate generated data. External source
   availability remains a dependency for those rebuilds.
5. Compare generated output and source revisions/checksums with the
   checked-in baselines or documented historical published release receipts.

This reproduces *validated builds*, not necessarily every private
intermediate witness of the original editorial research.

## Future archival decision

If keeping **all** source-derived intermediate research evidence permanently
becomes necessary, choose a storage location only after reviewing each field's
redistribution rights and privacy requirements. A public repository and
public Actions artifacts are not a safe fallback for permission-only content.

Any accepted archival workflow should specify exact source/producer commits,
per-file SHA-256 checksums, a manifest, verified readback and documented
recovery. An archive is only considered durable **after** successful upload,
independent integrity verification and a sample restoration.

Do not create a parallel, untracked authoritative copy of the canonical
BSI entity records. The reviewed Git files remain the main editable dataset.
