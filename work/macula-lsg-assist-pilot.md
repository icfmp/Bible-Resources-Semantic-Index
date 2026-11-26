# MACULA–LSG assisted alignment research checkpoint

Issue #200. This is a working-branch experiment, not a maintained production dependency, a semantic certificate, a source correction, or a release. No audited ledger, source projection, cohort draft, check box or publication process is changed.

## What was measured

The earlier bank was derived from audited Numbers 6–20 (15 chapters). A baseline search over six excluded chapters (216 verses) showed 746 exact group matches from 1,132 exact-signature proposals; allowing lemma-class evidence gave 949/1,427. The stronger filter restricts prefill to single lexical content units, unique source and target occurrences within the verse, evidence dominance and minimum support, rejecting conflicting candidates. Other evidence remains optional review material. No automatic contextual attachment or nearest-neighbour fill.

The pilot added Genesis 10, Exodus 20 and Leviticus 19 to the earlier evidence. Development: Genesis 22 and Deuteronomy 1. Locked holdout: Genesis 15 and Exodus 12, excluded from both training and development. On the 72 held-out verses, all 114 prefill word pairs occur in the reviewed reference ledgers, with 100 exact relation groups. 114/1,135 is 10.04% of reference lexical relations; 384/1,135 (33.83%) can be found among all proposals, including alternatives. Exact equality with a reviewed ledger is not independent linguistic truth; group granularity differs. The sample is too small to claim a production accuracy rate or time saving. An unreviewed Deuteronomy 25 packet was generated in memory only, without starting the next cohort.

## Reproduce and expand

The existing compact Python helper remains authoritative for source ordinals and draft reconstruction. The new core is a pure JavaScript expression, exercised directly by the GitHub connector runtime; the optional local Node.js runner (standard library only) is a temporary experiment and does not change repository runtime requirements. The runner was authored but could not be executed against a local checkout in the connector-only session (network DNS unavailable). Full-corpus training and benchmark have not been executed. The 157 audited ledgers were inventoried, not all read.

From a checkout of this working branch:
```sh
node work/macula-lsg-assist-runner.cjs benchmark --pilot
node work/macula-lsg-assist-runner.cjs benchmark
```

The second command regenerates evidence from every eligible two-pass Hebrew chapter except the two development and two holdout chapters (153 training chapters at the checkpoint). Frozen pilot thresholds are retained so the final control is not used to tune them. The program fails on missing source locks, unknown IDs, inconsistent offsets, duplicate scopes or data-inventory mismatch. The report is numeric, not a redistributed text index.

For production packets, all eligible two-pass chapters are training inputs, but pending draft chapters are excluded. Example plan (only after the current cohort is audited):
```json
{"chapters":[{"book":"Deut","native":"Deu","chapter":25,"versification":"identity"}],"includeAlternatives":false}
```
Identity must be explicitly verified by the editor; for a different verse mapping provide a complete map from native verse numbers to French verse numbers within that chapter. Cross-chapter targets and shared French verse boundaries still require explicit handling in the established compact workflow, not an inferred identity. For current Deuteronomy 5–24, retain existing drafts and perform the second pass before starting another cohort.

```sh
node work/macula-lsg-assist-runner.cjs packet /tmp/plan.json > /tmp/packet.json
node work/macula-lsg-assist-runner.cjs apply /tmp/packet.json /tmp/edits.json > /tmp/drafts.json
```

The packet exposes original and French ordinals, prefilled relations, evidence support and remaining ordinals; optional alternatives may be displayed when needed. The editor reads each complete verse, keeps correct proposed links, removes wrong or over-coarse links, adds missing relations and confirms explicitly. Edit file example:
```json
{"Deut.25":{"1":{"confirmed":true,"drop":["4:6"],"add":"4:7;5~8","note":"Example only; use actual source ordinals."}}}
```
Every row must be confirmed. Drop keys identify exact proposed relations; additions use the existing colon/tilde compact syntax. The application step checks source locks and ordinals, then produces first-pass drafts only; do not treat output as audit completion. For cross-verse links use the established compact workflow. A later independently reread second pass remains mandatory.

Keep generated evidence, packets and reports containing source text in memory or local temporary files, never a distribution or new tracked data index. The checked-in pilot receipts contain counts, source hashes and identifier references only. The prototype is not a new long-term tool without evidence that it improves quality and throughput.

## Next decision

Run the full 153-chapter training benchmark, then measure actual editorial time and corrections on one real simultaneous cohort. Do not equate reference match or structural coverage with semantic accuracy. If the experiment does not materially improve throughput, retire it. The current cohort of 494 drafted rows still needs the second semantic pass and the three possible source omissions checked against the maintained LSG OSIS.
