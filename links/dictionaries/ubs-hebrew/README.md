# UBS Hebrew — maintained MACULA WLC lexical crosswalk

This directory maintains a **bilingual, source-guarded lexical bridge** between
MACULA WLC Hebrew/Aramaic original-word occurrences and the United Bible
Societies Dictionary of Biblical Hebrew. A linked UBS entry is a candidate
**lexeme identity**, not a certified sense in the verse.

## Source identity and rights

| Input | Locked edition |
| --- | --- |
| UBS Hebrew Dictionary, English and French | **0.9.4**, `ubsicap/ubs-open-license@a15a96cfaa4ca18a6c0339016645ba1e534db3c8` |
| MACULA Hebrew WLC | `Clear-Bible/macula-hebrew@47db250bd55d0d8577f2a94fba114ef16c35b23c` |

The independently pinned bilingual UBS inventory has **7,943** shared
headword IDs and **16,619** sense IDs. UBS source terms are **CC BY-SA 4.0**,
MACULA has **CC BY 4.0** source notices, and separate per-field third-party
rights still apply. See [v1 rights/release readiness](V1_RELEASE_READINESS.md)
and the repository [rights policy](../../../docs/RIGHTS_AND_INTEGRITY.md).
No dictionary prose or original WLC text belongs in an unapproved public
BRSI package.

## Maintained data and checks

- `index.json` is a **development** bilingual lexical baseline;
  `build_index.py` verifies and deterministically rebuilds it from the
  exact locked source editions. It is not the published ZIP.
- `v1_*dispositions.json`, `v1_*approvals.json`, other named review ledgers
  and `v1_final_candidate_manifest.json` preserve source-specific
  nonidentity judgments, reviewed links, abstentions, original-word
  witnesses and reproducible release-scope evidence. These are **not**
  disposable reports.
- `build_final_reviewed_candidate.py` reconstructs the private reviewed
  word-level candidate; `package_reviewed_v1_candidate.py` creates the
  historical technical candidate, and
  `promote_verified_ubs_release.py --preview` checks its
  owner-authorized historical projection without publishing anything.
- `test_*.py` holds source-specific negative and positive regressions;
  [pinned Hebrew CI](../../../.github/workflows/bsi-ubs-hebrew.yml)
  rebuilds from actual source bytes and compares the immutable
  historical ZIP. No third-party text or rights-restricted witness dump
  is uploaded as a public workflow artifact.
- Five retained source-evidence snapshots are now checked by the **same strict
  JSON baseline verifier** as `index.json`: `reconciliation_candidates.json`,
  `reviewed_word_anchor_preview.json`,
  `positive_family_pending_original_words.json`,
  `reviewed_additional_word_anchor_preview.json` and
  `v1_disposition_coverage.json`. Each is a historical reproducibility
  witness, not a new editable editorial decision. Missing/mismatched
  snapshots fail CI; the source-level checks and explicitly reviewed
  decisions remain distinct.

### The central lexical-identity guard

Identical **MACULA `sdbh`** and **UBS `LEXID`** values can refer to
*different lexemes across editions*. Numeric equality is **not**
proof of an original-word-to-UBS sense identity. The source-aware
lookup checks the actual Hebrew/Aramaic language, precise original
word ID, Strong numeric family and corresponding UBS source headword.
A unique exact-source headword can support an **entry-only** link;
ambiguous or unsupported forms remain unlinked. Do not infer
context-specific senses, silently merge homographs or normalize away
source morphology to reach 100% coverage.

## Current verified boundaries

| Measure | Result |
| --- | ---: |
| Original WLC word occurrences in the source-pinned audit | 475,911 |
| UBS-attested selected lexical-class word scope | 242,747 |
| Source-supported UBS lexical headword candidates within that scope | 240,373 (**99.022%**) |
| Selected lexical-class words not linked within that scope | **2,374** |
| Additional original words outside that UBS scope | **5,933** |
| Source/verse-supported v1.1 contextual candidate occurrences | **53,981**, none promoted |

The **2,374** are not all errors: the reviewed partition includes
nonidentities, multiple-headword ambiguities, grammatical fragments,
single-candidate abstentions and composite annotations. The **53,981**
contextual candidates are evidence to study, not approved semantic choices.
The independently screened **72-token historical pilot concluded NO-GO** for bulk
promotion; see [v1.1 feasibility](V11_SEMANTIC_FEASIBILITY.md) and
[context pilot](V11_CONTEXTUAL_PILOT.md). These finished, nonpublishing
experiments are preserved as source-bound editorial records and immutable
Git revisions, **not re-executed by the current v1.0 verification workflow**.
An absent word override is not proof of a negative lexical identity.

## Contributor verification

Run maintained offline source-local tests from the repository root:

```sh
for test_file in links/dictionaries/ubs-hebrew/test_*.py; do
  python3 -I "$test_file" || exit 1
done
```

For all source-level assertions use [the pinned Hebrew workflow](../../../.github/workflows/bsi-ubs-hebrew.yml),
not an unpinned dictionary or an old research command. The workflow checks
source commits and Git blobs, reviewed/disallowed identities, the complete
private build, historical packaging and the real published ZIP fingerprint.
It now **requires** the already-committed `index.json` baseline to exist and
match the complete reconstructed strict JSON value. The previous
initial-import bypass is retired. The separate dictionary-scope report is
no longer generated, but its shared source-bound validator continues to run
inside the reviewed private and final candidate constructors.
Its result does not authorize a new distribution.

The [historically published Hebrew v1.0.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-hebrew-v1.0.0)
remains unchanged. Any new BRSI release requires independently reviewed
rights and explicit owner approval under [issue #62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62).

**Historical evidence:** the original batch-by-batch editorial research is
recoverable in the [immutable pre-cleanup README](https://github.com/icfmp/Bible-Resources-Semantic-Index/blob/f97f70446f0db0d4574fddcf2f589b74e98f30c2/links/dictionaries/ubs-hebrew/README.md).
The maintained authority is the current source-specific JSON review ledgers,
pinned source workflows, regression tests and explicit abstentions.
