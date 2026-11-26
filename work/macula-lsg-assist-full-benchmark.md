# Full-corpus assisted alignment benchmark

Issue #200; experimental working-branch evidence, not release or production certification.

## Outcome

All 153 eligible training chapters at the pinned checkpoint were scanned, excluding the two original development chapters (Genesis 22 and Deuteronomy 1) and the two locked holdouts (Genesis 15 and Exodus 12). The 18-chapter pilot thresholds were unchanged. The full experiment was executed in bounded batches through the GitHub connection after direct local DNS access to github.com failed. Source projection and reviewed-ledger blob IDs are recorded for every training chapter. The holdout-only counters contain ordinal keys, aggregate counts and identifiers, not original or translated text.

| Metric on the same 72 holdout verses | 18-chapter pilot | 153-chapter training |
| --- | ---: | ---: |
| Prefilled word pairs | 114 | 206 |
| Word pairs in reference | 114 | 206 |
| Identical relation groups | 100 | 161 |
| Reference lexical groups | 1135 | 1135 |
| Reference groups found among all proposals | 384 | 550 |
| Remaining alternatives displayed if requested | 799 | 1621 |

The prefill count rose 80.7%. All selected word pairs were present in this particular same-editor reference, but only 161/206 were identical groups; the other 45 need grouping review. The strict group agreement on prefill is 78.2%, not 100%. The alternative set recovers 48.5% of the reference lexical groups but creates considerable review overhead.

A simple exact-group delta proxy yields 974 additions plus 45 deletions versus 1,135 original lexical entries (116 fewer operations, 10.2%). The pilot proxy saved 86 operations (7.6%). This is not a measured wall-clock editing speedup, does not include contextual relations, and does not establish semantic accuracy.

## Source and boundary handling

The streaming benchmark accepts the source-local segment lock when a French ledger contains multiple native chapter segments. 298 translation relations in declared foreign segments, 3,983 other-verse or noncontiguous-target relations, and 266 noncontiguous-source relations were excluded from evidence, not changed or validated. Genesis 31 initially failed on the explicitly documented Genesis 32:1 boundary, then was recovered by the generic rule. Unknown IDs without an explicit foreign segment remain errors. No ledger was edited.

The ordinary three-chapter and explicit-boundary two-chapter comparisons produced identical prefill and review-alternative records between direct and streaming engines. These are development observations, not publication validation. The pure streaming engine and the corrected direct engine are recorded separately. The optional local runner was updated but not executed locally.

## Reproduction and practical next step

From a checkout of this branch, with the checkpoint's original corpus:

```sh
node work/macula-lsg-assist-runner.cjs benchmark-stream
node work/macula-lsg-assist-runner.cjs benchmark
```

The first regenerates the holdout-specific counters in memory from the full training split. The second uses the direct full-bank algorithm and reports the development and holdout splits. The stored numeric report and counter receipt preserve the executed result. The direct full-bank packet command can build the bank from eligible audited chapters at runtime; no full persistent production index was created by this experiment. Keep source-derived text, generated packets and working banks local or in memory; no redistribution or canonical ledger change is authorized.

Do not flood the editor with all alternatives. Keep the high-confidence proposals in the verse packet and expose other candidates on demand. The main next step is measuring actual editing time on real verses while retaining the two editorial passes. This modest proxy gain does not justify increasing complexity indefinitely. The Deuteronomy 5–24 draft (494 rows) still needs its full second editorial pass and three possible omissions verified. No chapter status or source text changed.
