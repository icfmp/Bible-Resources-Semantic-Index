# BRSI V1 — Offline consumption and compatibility guide

**Scope:** three *existing, separately published* BSI/BRSI ZIP archives.
This is a practical read-only contract for a future consumer, **not**
implementation in `icfmp/Bible`, a new BRSI release, an app integration
approval, or redistribution permission for original UBS/MACULA content.

## 1. Select the exact published packages, not development indexes

| Kind | Published tag and exact archive | What a consumer gets |
| --- | --- | --- |
| `entities` | [`bsi-v0.1.0`](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-v0.1.0) — `BSI-0.1.0.zip` | Source-backed biblical identity records, exact original-word-to-**candidate-entity** reverse links, references and explicit qualification |
| `ubs_greek` | [`bsi-ubs-greek-v0.1.0`](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-greek-v0.1.0) — `BSI-UBS-Greek-0.1.0.zip` | MACULA SBLGNT token → UBS NT Greek 1.0 EN/FR **entry IDs** and **provisional** sense alternatives/status |
| `ubs_hebrew` | [`bsi-ubs-hebrew-v1.0.0`](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-hebrew-v1.0.0) — `BSI-UBSHebrew-0.9.4-v1.0.0.zip` | MACULA WLC token/lexical features → UBS Biblical Hebrew 0.9.4 EN/FR headword candidates, including separately reviewed **entry-only** word links |

These are **three independently versioned historical releases**, not one
homogeneous combined database. Their exact SHA-256 digests and byte lengths
are maintained in
[`release/historical-assets.lock.json`](../release/historical-assets.lock.json).
The actual GitHub release asset metadata was inspected on 2026-11-22;
the three historical archives already exist. There is no reason to reissue
their versions merely to document how they can be read.

Do **not** use `links/dictionaries/ubs-greek/index.json` or
`links/dictionaries/ubs-hebrew/index.json` as substitutes: these are richer
**development** baseline indexes, not the same public outputs. Likewise,
the current locally staged native entity ZIP is a **different, unapproved**
candidate; historical entity assets are not regenerated automatically from
new BRSI `main` commits.

## 2. Verify downloaded bytes before opening any index

Download all three ZIP files from the tag pages above into one directory.
From the checked-out BRSI repository root:

```sh
python3 -I scripts/inspect_v1_published_assets.py \
  --entities /path/to/BSI-0.1.0.zip \
  --greek /path/to/BSI-UBS-Greek-0.1.0.zip \
  --hebrew /path/to/BSI-UBSHebrew-0.9.4-v1.0.0.zip
```

The offline checker uses the *independently pinned release-asset digests*
already enforced by `scripts/verify_historical_asset.py`, checks ZIP safety,
the adjacent `manifest.json`, the internal `index.json` digest when
declared, and the three different public lookup shapes. A changed ZIP or
source-format mismatch **fails closed**. It does not fetch anything,
download sources, execute ZIP members, modify `Bible`, publish, or generate
a new artifact.

The output contains one concise read-only receipt per archive, including
its kind, original tag, matched ZIP digest and number of lookup records.
**The resulting summary is not a rights determination or editorial review.**

## 3. What the current public JSON actually means

The following refer to *published archive contents*. They do **not**
describe the larger private candidate reports built in source-pinned CI.

| Lookup | Input key | Returned representation | Safe interpretation |
| --- | --- | --- | --- |
| Entities `index.json.by_word` | `sblgnt:n...` or `wlc:o...` (exact source-corpus-qualified MACULA ID) | Array of `{entity_id, link_type}` claims | Zero or several source-backed **entity candidates**. Preserve link type; never assume the first candidate is unique |
| Entities `index.json.entities` | Exact entity ID / indexed source ID | Record with `id`, `kind`, canonical/source IDs, refs, occurrence links and review metadata | This is an identity index, **not** a description, translation or biography. Use original `references` and `key_references` independently |
| Greek `index.json.by_word_id` | Exact `n...` SBLGNT MACULA word ID | `status`, `entry_ids[]`, `provisional_lexid`, `candidate_lexids[]`, `evidence_tier` | An `entry_id` is an UBS MainId. Even one `provisional_lexid` is **not a verified contextual meaning** |
| Hebrew `index.json.by_macula_word` | Exact `o...` WLC MACULA word ID | Word-specific, source-audited **entry-only** override record when present | Use alongside original lemma, exact Strong, `sdbh` and H/A language checks. **Missing override is not proof that the word has no lexical mapping** |
| Hebrew `index.json.by_sdbh` / `by_strong` | Original SDBH sense ID / exact H-or-A Strong code | Candidate UBS entry IDs | Use `lookup_word` policy with independent Strong-family corroboration; do not treat same numeric SDBH and UBS LEXID as proof of lexical identity |

Relevant maintained rules:
[`ubs-greek/build_public_identifier_release.py`](../links/dictionaries/ubs-greek/build_public_identifier_release.py)
defines the **Greek published allowlist**;
[`ubs-hebrew/build_index.py`](../links/dictionaries/ubs-hebrew/build_index.py)
defines the Hebrew `lookup` and `lookup_word` policies;
[`ubs-hebrew/promote_verified_ubs_release.py`](../links/dictionaries/ubs-hebrew/promote_verified_ubs_release.py)
checks the Hebrew approved public-data promotion without changing lexical links.

### Minimal read-only illustration

After running the ZIP inspector successfully, this example only queries
the **Greek public index** (the path is deliberately an already verified
release ZIP). It returns the complete status and candidate set; it does
**not** choose a contextual sense:

```python
import json
import zipfile

with zipfile.ZipFile("/path/to/BSI-UBS-Greek-0.1.0.zip") as archive:
    greek = json.loads(archive.read("index.json"))

token = "n40001001003"  # MACULA SBLGNT, Matthew 1:1
row = greek["by_word_id"].get(token)
if row is None:
    print("unknown_original_word_id")
else:
    print(row["status"], row["entry_ids"],
          row["provisional_lexid"], row["candidate_lexids"])
```

Do not apply this Greek `by_word_id` lookup to the **entity**
`by_word` (which needs an edition prefix), or to the **Hebrew**
`by_macula_word` (which is an additional, partially populated
word-specific override layer). There is no single shared `lookup_word`
implementation valid for all three artifacts.

## 4. Expected edge cases and honest limitations

- **No source token / unknown ID:** return no match, not a fabricated
  headword, verse, identity or name. A valid pointer in another edition is
  not an exact MACULA token in this edition.
- **Ambiguous identity or lexical entry:** retain *all* candidates and
  their source-review state. Do not pick the first, merge different
  persons/places, or normalize suffixes without source evidence.
- **Greek provisional sense:** a UBS LEXID may be source-supported while
  **no independently checked contextual-sense interpretation exists**.
  Show the UBS entry rather than presenting a provisional sense as settled.
- **Hebrew SDBH collision:** numeric equality across MACULA and UBS
  editions alone is unreliable. The Hebrew original-word-aware lookup
  checks Strong family, language and original word metadata; it must be
  preferred whenever pinned WLC data is available.
- **Missing language:** EN/FR are the two locked UBS dictionary *editions*,
  with shared lexical identifiers. These ZIPs **do not bundle dictionary
  definition translations**. A caller must obtain a separately licensed,
  edition-compatible dictionary dataset. No fabricated French fallback.
- **Unknown/withdrawn entity:** `quarantined` and 868 withheld Key Terms
  must not become reader-facing identities. Missing names cannot be filled
  by importing ACAI multilingual encyclopedia prose.
- **Version/digest mismatch:** refuse the artifact; don't silently switch
  to the latest GitHub release, rebuild a private baseline, or accept its
  own self-declared hash as an independent trust anchor.
- **Absent verses or textual variants:** preserve edition-specific
  reference qualifications. Do not reintroduce omitted verses, merge
  variants, or infer a source token from a reference alone.
- **V2-only graph:** entity-to-entity semantic relations are **not a
  product V1 capability**, even though internal experimental data exists.

## 5. Future Bible implementation boundary

There is currently **no integration in `icfmp/Bible`**. This page
describes the existing files so that a future application implementation
can be planned without reverse-engineering development branches.

For any future consumer, the required sequence is:

1. Select **separately approved exact release tags and hashes** for each
   resource; keep their versions independent.
2. Verify archive bytes and expected internal format **offline**,
   before loading or replacing installed packs.
3. Store accessible original MACULA word IDs with their **exact
   WLC/SBLGNT edition**, and retain evidence/status flags on lookups.
4. Handle missing locales and ambiguous entities/word senses without
   showing misleading reader-facing assertions.
5. Load the separately licensed UBS dictionary editions only when
   their own rights, provenance and identifier compatibility are checked.
6. Integrate into `Bible` **only after a separate owner-authorized
   application issue/PR and release-contract review**.

The three historical archives are currently verifiable, but a *new*
product-V1 distribution, a combined pack or a Bible integration is not
approved by these facts. See
[`docs/RELEASE_CONTRACT.md`](RELEASE_CONTRACT.md) and
[release issue #62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62).

## 6. How to reproduce validation

For current working source, not historical public bytes:

```sh
python3 -I -m unittest discover -s tests -p 'test_*.py'
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-entities.json
python3 -I scripts/audit_entity_relationships.py --fail-on-unresolved
```

The Greek/Hebrew full source-pinned workflows run their own independent
original-source checks, exact ID parity, decisions, abstentions and public
allowlist tests. The local inspector makes no claim to substitute for them.

**Completion rule:** source/byte integrity, actual editorial correctness,
field-level rights, public publication, and application usability are **five
different milestones**. A verified SHA-256 only proves that you have the
same bytes as the independently pinned release, not that every lexical
interpretation is correct.
