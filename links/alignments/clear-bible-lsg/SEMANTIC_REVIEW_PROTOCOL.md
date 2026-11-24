# MACULA ↔ LSG contextual alignment: 2,000-case human evaluation protocol

Status: **research; nonpublishing; 0 human-gold cases reviewed**. This protocol
implements the first *sampling* stage of [#187](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/187).
It is distinct from the already completed **2,000-verse NT lemma-to-word
negative-control experiment** in [#186](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/186).
The latter returned 447 correct / 865 attempted predictions (51.676%
precision) on its independent 1,000-verse validation half and approved **zero**
new correspondences. It did **not** establish OT accuracy or phrase alignment.

## Immutable inputs and output boundary

- Original alignment and original MACULA source identifiers: pinned Clear.Bible
  revision and independently attested Aquifer revision recorded in
  [aquifer-correspondence.lock.json](aquifer-correspondence.lock.json).
- French authority: the exact authored Bible Resources **BRLSG1910 1.0.2**
  OSIS SHA-256, not a generic "LSG 1910" or Clear.Bible numeric target ID.
- Input: source-locked, privately reconstructed
  MACULA ↔ curated LSG development gzip. Never modify that gzip or upstream
  source material to make a test pass.
- Local outputs: a **private** sample with original MACULA selectors, source
  coordinates and review placeholders; a **text-free public diagnostic**
  receipt with sample composition and private-file SHA-256.
- No biblical text, original-language lemma, French word surface, human
  annotations or proposed semantic equivalence in the public receipt.
- No LSG/OSIS/SWORD modification, Bible app integration, publication,
  approved translation or automatic candidate promotion.

## Sampling design — 2,000 cases, not 2,000 verses

The original-ID population is the locked set of **119,691 unresolved**
identifiers; the exact source-aware partition is:

| Original-source evidence category | Population | Human-review sample |
| --- | ---: | ---: |
| Explicit Aquifer nonEquivalent | 62,892 | 500 |
| Another part of the same original Hebrew word is linked | 8,762 | 500 |
| No Aquifer source alignment row | 27,223 | 500 |
| Aquifer row exists but authored LSG French word cannot be uniquely located | 20,814 | 500 |
| **Total** | **119,691** | **2,000** |

The sampling unit is an **original MACULA ID**, not a verse, a French word or
an apparent missing dictionary meaning. The generator applies a
revision-pinned, seed-stable SHA-256 rank to **all source IDs within each
stratum**, selecting the first 500 without replacement. Every source ID in
the same stratum has the same selection probability. Neither books nor
frequent lemmas are specially favored, and unpaired source units remain
eligible. Retaining duplicate-source-verse cases avoids introducing a
systematic bias against dense verses.

This 500/500/500/500 allocation deliberately **oversamples smaller evidence
categories**. Report per-stratum precision and coverage separately; any
119,691-ID population estimate must reweight by the four **known population
counts**. Multiple cases from the same verse are *clustered*, not independent:
do not use naive token-wise Wilson confidence intervals as if every
observation were independent.

The sample is generated **before** proposing semantic links, and no reviewer
is shown a model's proposed answer during the gold-label phase.

## Manual gold annotation

Independently locate the case in the exact pinned MACULA SBLGNT/WLC source and
published LSG 1.0.2. Read the clause and relevant surrounding context; do not
assume that the original verse and target verse coordinates are equivalent
when there is a documented source-versification disagreement.

For each original source ID, choose **one** of these evidence outcomes:

1. **Exact French span(s) attested**: one or several authored LSG word
   coordinates, which can overlap other source units. Record an explicit
   reviewed original-source group when the sense is carried by an entire
   original phrase. Require the French passage to express the original
   sense; equality of surface words alone is not sufficient.
2. **Grammatical/semantic function conveyed without separate French span**:
   the relevant original unit is translated as part of an already identified
   French construction or grammatical contrast, but there is no unique
   distinct word span to highlight. Distinguish a reviewed *unpaired* source
   from an unsupported guess.
3. **Undetermined**: missing edition-exact witness, conflicting witnesses,
   verse-coordinate ambiguity, uncertain syntax, or other unresolved
   evidence. Do not manufacture a word span or claim this is a failed
   translation.

A review record must retain: original MACULA selector(s), exact canonical
LSG 1.0.2 word coordinates, referenced original and target verses, decision,
reviewer/source evidence, explicit uncertainty, version and adjudication
provenance. One-to-many and many-to-one alignments are valid. Hebrew clitics,
prefixes and suffixes must not be normalized away.

The sampler's three gold fields start **null**. They are *placeholders*, not
approval or absence-of-equivalent decisions. The initial sample generator
does not edit them. Actual manually annotated gold must be stored separately
and privately, with individual reviews and adjudicated final decisions.
Blind reviewers should initially be independent; double-review at least 10%
of cases distributed across all categories and explicitly adjudicate
disagreements. This proposed 10% is a protocol target, not a completed review.

## Training, model comparison, and acceptance gates

Only **after** fixing the gold sample and source revision:

- Split by **source verse clusters**, with no shared verse across
  train/calibration/blind validation; retain comparable category coverage.
  Choose tuning parameters on calibration alone and keep blind labels unseen
  until a method is frozen. Since the full 2,000-case set is a review sample,
  never count a held-out source token as another independent observation
  if its verse or translation witness was used for learning.
- Compare plain lexical lemma-to-word matching (#186), strict independently
  located anchors (#184–185), and candidate phrase/syntax aligners under
  identical held-out conditions. Evaluate SimAlign/awesome-align only if
  their exact versions, models, licenses and reproducible Greek/Hebrew
  test behavior are independently verified. Do not declare these tools
  suitable before testing.
- Measure *correct original-to-French spans*, false positive spans,
  unsupported/abstained cases, wrong multiword boundaries, hallucinated
  mapping of unpaired grammatical material, candidate coverage and
  disagreement by category, Testament, book and review status. Compute
  cluster-aware intervals and population-stratum weights where appropriate.
- Predeclare acceptable precision, abstention policy and minimum
  independent sample size **before** blind validation. Do not choose a
  passing threshold from the blind results. A statistically promising
  candidate remains distinct from an editorially approved link.
- A human-reviewed unpaired grammar case can be **correctly left without
  any French highlighted word**. Denominator metrics must not count it as
  a word-link error.

The resulting aligner may eventually output many-to-many candidate spans
with independent provenance, explicit confidence and reviewed/not-reviewed
status. Source edition, rights, publication and Bible consumer gates
[#166](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/166)
and [#62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62)
remain separate. No automatic rollout is authorized by this pilot.

## Reproduction (local development, not publication)

After regenerating the exact private correspondence index in the maintained
source-pinned workflow:

    python3 -I scripts/sample_macula_lsg_semantic_review.py \
      --original-index /tmp/brsi-macula-lsg-correspondence.json.gz \
      --correspondence-lock links/alignments/clear-bible-lsg/aquifer-correspondence.lock.json \
      --private-unreviewed-cases /tmp/brsi-lsg-semantic-review-unreviewed.json \
      --report /tmp/brsi-lsg-semantic-review-sample-receipt.json \
      --per-stratum 500

The sampling report must pin the private case-list SHA-256 and count all four
cohorts exactly. A source revision mismatch, existing French word link on an
"unlinked" original ID, altered category partition or undersized cohort
fails closed. Keep both generated files out of the repository until the
source-free receipt has been independently verified and explicitly approved.
