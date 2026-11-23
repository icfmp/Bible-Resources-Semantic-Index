# UBS Hebrew v1.1: one-pass semantic feasibility audit (not a release)

## Decision: substantial potential, no automatic semantic approval

One bounded, original-source-pinned audit was run over **all 475,911
MACULA Hebrew WLC words** against the existing independently
source-reviewed UBS Hebrew 0.9.4 EN/FR **v1.0** lexical crosswalk. No
original word, dictionary article, SDBH annotation, Strong identifier,
released ZIP or Bible application component was changed.

The v1.0 entry mapping is already strong within its deliberately
restricted indexed-headword scope (**240,373 / 242,747 = 99.022%** for
the five selected lexical classes). Improving the last fractional
percent of lexical coverage is *not* this audit's goal.

### One-pass results

| Source-reviewed audit disposition | Original words |
| --- | ---: |
| **One UBS candidate sense alone cites the source verse** and MACULA has exactly one token of that same verified UBS lexical headword in that verse | **53,981** |
| Multiple original MACULA words with the same UBS lexical headword in the source verse (word-to-sense ownership unclear) | 49,485 |
| Original UBS references noncanonical and/or EN/FR source reference inventories disagree | 83,711 |
| UBS headword has only one original sense ID, but no independent contextual validation | 45,058 |
| No UBS sense reference cites this word's original verse | 748 |
| Multiple authentic UBS sense IDs cite the same verse | 78 |
| Original UBS headword has no source sense inventory | 129 |
| **Total v1 entry-only words examined** | **233,190** |

The **53,981** *potential additional* source verse-witness candidates
span **1,768 distinct UBS lexical headwords**. These are not validly
countable as new verified sense links merely by running the audit.

**All prior v1 Strong/SDBH source corroboration and word-aware lexical
entry links stay unchanged.** The generic original MACULA SDBH integer
is **never** assumed to name the same UBS 0.9.4 contextual sense:
those two editions contain proven semantic ID collisions.

### Specific confidence boundary

A source UBS dictionary's example references are **not** guaranteed
to exhaustively cite every context for a meaning. A lexeme may have
multiple meanings even if only one sense cites a given verse.
The one-UBS-lexeme occurrence per source verse check excludes one
common form of false precision, but does not prove the dictionary's
verse citation identifies a unique original MACULA word or an
appropriate contextual sense in the source text.

The audit therefore **does not select any new UBS LEXID**, even for
the 53,981 promising source verse-witness cases. No semantics have
been independently checked against original word-specific syntax,
morphology and narrative context, and no new word sense data is ready
to distribute.

### Go/no-go conclusion

**GO for one *separately scoped, sample-validated* v1.1 semantics
experiment**, because 53,981 authentic source-reference candidates
are a material improvement opportunity; **NO-GO for immediate mass
assignment or publication**. A successful v1.1 release would need to
show that representative sampled candidates from frequent lexical
families actually preserve UBS 0.9.4 contextual meaning under the
original MACULA WLC word segmentation. The 83,711 atypical/reference
disagreement cases are an explicit blocker to blind automatic
extension across all entries, not a backlog to auto-resolve.

A future experiment must:

1. Recheck several high-frequency candidate families using the exact
   UBS original sense definitions and original WLC morphological and
   verse context, including known differing-edition SDBH cases.
2. Demonstrate a conservative, source-justified selection rule that
   succeeds on meaningful independent positive and negative examples.
3. Record the particular original word ID, lexical sense ID, alternate
   source candidates, source witnesses and editorial rationale; never
   invent or overwrite original SDBH, Hebrew forms or original source
   Strong codes.
4. If validation cannot support a significant **batch-sized** gain,
   explicitly accept the v1.0 semantic gap. Do not repeatedly pursue
   gains of a few tenths of a percentage point.
5. Request separate owner approval before applying any new editorial
   sense layer or creating a v1.1 public resource.

### Exact reproducibility

This **completed, nonpublishing one-off** is reproducible from the
[immutable historical auditor](https://github.com/icfmp/Bible-Resources-Semantic-Index/blob/6352363ac9eb2935061c3d6b421be45de202ffb5/links/dictionaries/ubs-hebrew/audit_v11_semantic_feasibility.py)
(and its original tests at that revision) using:

- UBS Hebrew Dictionary 0.9.4 EN/FR at
  `a15a96cfaa4ca18a6c0339016645ba1e534db3c8` (CC BY-SA 4.0).
- MACULA Hebrew WLC at
  `47db250bd55d0d8577f2a94fba114ef16c35b23c` (CC BY 4.0,
  original component-source caveats apply).
- The immutable, source-reviewed final v1.0 275-word lexical candidate
  built by [`build_final_reviewed_candidate.py`](
  build_final_reviewed_candidate.py).

The **maintained** pinned-source workflow still rebuilds the v1.0 candidate,
checks original revisions and lexical counts, and independently verifies the
historically released v1.0 ZIP. It deliberately **does not rerun this finished
v1.1 research experiment on every change**. Reproduction of the exact 53,981
candidate witness census requires checking out the historical auditor at the
revision linked above and obtaining the original source editions. Generated
private witness output was runner-local; **no verified durable full research
archive or publicly redistributed UBS definitions is claimed**.

These figures are historical feasibility findings, not a continuing v1.0
acceptance or publication gate. The source-specific human screening decision
remains in [the V1.1 pilot](V11_CONTEXTUAL_PILOT.md).
