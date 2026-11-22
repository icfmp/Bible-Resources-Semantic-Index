# BRSI v1 release contract — design and local integrity gate

**Status: implemented validation contract, not publication authorization.**

BRSI (**Bible Resources Semantic Index**) is the single producer. Bible-Resources
is a future **version-pinned consumer**, never an importer of BRSI's development
branch. The Bible application requires its own integration review.

## Exactly three separately versioned artifact kinds

| Kind | Current dev input | Distribution gate |
| --- | --- | --- |
| \`entities\` | Fresh \`scripts/build_native_index.py\` compact index, with no ACAI Key Terms | Separate public-scope / rights and attribution review |
| \`ubs_greek\` | Checked-in Greek lexical **development** baseline | Only source-pinned \`build_public_identifier_release.py\` allowlisted projection, independently validated |
| \`ubs_hebrew\` | Checked-in Hebrew lexical **development** baseline | Only independently source-verified, owner-approved reviewed public headword-ID projection |

**DO NOT PACKAGE \`links/dictionaries/ubs-{greek,hebrew}/index.json\`
as a new public asset.** Those files are development baselines and may contain
source annotation fields not cleared for redistribution. The historic public
Greek identifier-only and Hebrew reviewed ZIPs are not those two files.

The data adaptation is CC BY-SA 4.0, but independently copyrighted original
UBS/MACULA source fields have their own scope. The 868 ACAI Key Terms remain
excluded. The source pins are \`data/source.lock.json\` for ACAI/MACULA, and
the separately locked Greek/Hebrew UBS source workflows. Stable original
word IDs are not proof of reviewed contextual dictionary senses.

## Standalone migration paths verified

Current contributor instructions and shared code use **repository-root**
paths such as `scripts/build_native_index.py` and
`links/dictionaries/ubs-greek/`, not the removed old
`bible-semantic-index/` monorepo prefix. Native offline CI now tests this
explicitly. Historical v0.1 handoff documents deliberately preserve the
former paths as a dated record, with a warning that they are not current
commands. Existing Bible-Resources **release asset URLs** remain valid and
unchanged.

## Sidecar manifest (v1)

Machine-readable contract: [\`release/manifest.schema.json\`](../release/manifest.schema.json).

The strict \`scripts/release_contract.py\` implementation records:

- Contract/schema ID, one artifact kind, exact payload schema ID, version and
  **40-character source-producing Git commit**.
- Every original data edition, pinned Git commit, source repository and
  license; explicit source attribution and the Key Terms restriction.
- Artifact filename, **exact byte size**, and lowercase SHA-256 of actual bytes.
- Input class: an entity-native index; a **nonpublic lexical baseline**;
  or a specifically reviewed public projection.
- Explicit publication state: \`candidate_unapproved\` for the native entity
  index, \`local_integrity_only\` for lexical development baselines, or
  \`owner_approved_release\` (future, separate authorized publication).
- \`publication.approved=false\`, \`tag=null\` and
  \`rights.redistribution_cleared=false\` **for every locally staged receipt**.

No declaration inside an untrusted manifest can by itself prove legal
permission, author identity, GitHub release authenticity, or review of a
dictionary source. A future release needs a separate owner authorization
and validated public-projection builder, and its checksum must be pinned
by the consumer independently of the manifest.

### Reproduce local integrity receipts (no distributable ZIP)

\`\`\`sh
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-entities.json

revision="$(git rev-parse HEAD)"
python3 -I scripts/release_contract.py local-receipt \
  --kind entities --input /tmp/brsi-entities.json \
  --producer-revision "$revision" \
  --output /tmp/brsi-entities-receipt.json

python3 -I scripts/release_contract.py local-receipt \
  --kind ubs_greek --input links/dictionaries/ubs-greek/index.json \
  --producer-revision "$revision" \
  --output /tmp/brsi-greek-local-integrity.json

python3 -I scripts/release_contract.py local-receipt \
  --kind ubs_hebrew --input links/dictionaries/ubs-hebrew/index.json \
  --producer-revision "$revision" \
  --output /tmp/brsi-hebrew-local-integrity.json

python3 -I scripts/release_contract.py verify \
  --manifest /tmp/brsi-entities-receipt.json \
  --artifact /tmp/brsi-entities.json
\`\`\`

The two Greek/Hebrew receipts mean **checked-in file bytes identified**,
not independently reconstructed public Greek/Hebrew artifacts. Source-locked
Greek/Hebrew CI remains a distinct mandatory check before any candidate
could become an actual public ZIP.

The native-build workflow runs this gate in \`/tmp\`. **It never uploads,
publishes or commits the baseline index data, the receipts or the future
candidate.** There is no release workflow, repository secret or automatic
tag. Local receipts are deterministic for the same input bytes, exact commit
and source lock.


### Deterministic entity-only ZIP candidate

The current native entity profile can additionally be staged into an
**unapproved local archive** containing only the keyterm-free \`index.json\`,
source lock, attribution notice, license note, README and an internal manifest
with exact member SHA-256/byte sizes. No translations, biographies, keyterms,
private original-word source TSVs, dictionary prose or UBS lexical baselines
can be injected.

\`\`\`sh
python3 -I scripts/stage_entity_candidate.py stage \
  --index /tmp/brsi-entities.json \
  --producer-revision "$(git rev-parse HEAD)" \
  --output /tmp/brsi-entities-unapproved.zip \
  --receipt /tmp/brsi-entities-unapproved.json

python3 -I scripts/stage_entity_candidate.py verify \
  --archive /tmp/brsi-entities-unapproved.zip \
  --receipt /tmp/brsi-entities-unapproved.json
\`\`\`

\`scripts/stage_entity_candidate.py\` fixes ZIP timestamps, member order,
compression, JSON serialization and file permissions, then verifies every
member and the overall ZIP hash. Its **sidecar receipt** has input class
\`nonpublishing_entity_zip_candidate\`, \`candidate_unapproved\` status, false
rights clearance and no release tag. The ZIP is **not** an approved public
release, even when technically deterministic and correct. Further source
license/editorial approval and a distinct release workflow are mandatory.

Native CI independently stages the same entity candidate **twice** from
the exact source commit and compares both ZIPs and both sidecar JSON receipts
**byte-for-byte**. The manifest validator additionally refuses source sets
from the wrong BRSI stream and missing/wrong pinned MACULA/UBS revisions;
the public Greek projected payload schema is distinct from its richer
checked-in development baseline. Schema names and original source locks
cannot be silently changed in a candidate manifest.

No analogous generic ZIP stage exists for checked-in UBS Greek/Hebrew
development indexes. Their independently source-verified **public allowlist**
builders remain the only candidate starting point, and a separate release
approval is required.

## Future consumer contract (Bible-Resources)

After a **separate, explicit** owner-approved release, its signed-off
manifest will point to a single **public-scope, allowlisted** ZIP and immutable
release tag. A consumer must receive these pins **out of band** in its
own reviewed repository: exact release tag, version, producer commit and
ZIP SHA-256. Validate the downloaded bytes and manifest with:

\`\`\`sh
python3 -I scripts/release_contract.py verify \
  --manifest /path/to/approved-manifest.json \
  --artifact /path/to/BRSI-Approved-Artifact.zip \
  --require-release \
  --expected-tag 'brsi-entities-vX.Y.Z' \
  --expected-version 'X.Y.Z' \
  --expected-revision '<40-char-immutable-BRSI-commit>' \
  --expected-sha256 '<64-char-independent-verified-archive-hash>'
\`\`\`

The placeholders are deliberately **not actual release coordinates**.

A consumer must also verify the archive structure against the applicable
**source-specific artifact validator** and inspect the artifact's rights
manifest before using any data. This v1 receipt validator checks exact
bytes and metadata; it does **not** replace the source-specific ZIP content
validator. Missing files, wrong bytes/version, changed producer commit,
unknown manifest field, unapproved candidate or wrong tag fail closed.
Do not fetch \`main\`, infer a version from the latest GitHub release, or
automatically "repair" a missing checksum.

## Historic asset digests independently locked

The three GitHub release asset **digests returned by the original
Bible-Resources Releases API** (checked 2026-11-22) are pinned at
[release/historical-assets.lock.json](../release/historical-assets.lock.json).
This is an inventory of existing assets, **not** a new release manifest:

| Historical tag | Archive ZIP SHA-256 |
| --- | --- |
| \`bsi-v0.1.0\` | \`3685b09b157f89c42f7766c4f42cf7d5c9fe1e8cde153c8f633afc7a6d2d4c41\` |
| \`bsi-ubs-greek-v0.1.0\` | \`eeaf6f1b0dfa7335c522c52374a1d5261412819e074520a455a4822b728eddaf\` |
| \`bsi-ubs-hebrew-v1.0.0\` | \`e448c7e4b6c0cb892789d78b487a3afe3dbe18cfb8c0b13be5fd910deabf640f\` |

Both UBS original-source workflows now rebuild their own historically
approved *public-scope projections* and independently verify them
**byte-for-byte** against those historical published ZIP digests, via
\`scripts/verify_historical_asset.py\`. Never mistake this historical
reproduction for a new BRSI release or source-redistribution authorization.
The current native entity candidate has **newer edited source records**, so
its local ZIP deliberately differs from the historical entities 0.1.0 ZIP.

## Historical releases remain immutable

The following existing **Bible-Resources** tags and public asset URLs are
preserved, not moved or silently reissued:

- [BSI entities 0.1.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-v0.1.0)
- [Greek 0.1.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-greek-v0.1.0)
- [Hebrew 1.0.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-hebrew-v1.0.0)

Their original manifest semantics and published hashes are **not replaced**
by this new v1 BRSI contract. A future BRSI independent release needs an
approved scope, real rebuilt public projection, source-attestation report,
exact archive SHA-256, provenance/attribution license pack and user approval.

**Tracked by** [#1](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/1)
and [#21](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/21).
