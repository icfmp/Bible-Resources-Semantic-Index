# MACULA–LSG: maintained high-throughput cohort method

This is the **current production contract**, not a progress diary. It applies
to the from-scratch alignment tracked by [#200](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/200).
Update this document in the **same commit as every workflow or tooling improvement**:
commands, data contracts, editorial rules, checkpoints, limitations and
measured throughput must remain accurate. Record historical cohort results
and experiments in the issue and versioned decision ledgers, not here.

## Editorial invariants

- Read the original-language passage and the pinned LSG reading text in
  context; neither source may be edited. Preserve exact native word IDs,
  verse identity, French occurrence offsets, edition differences and
  versification. Work from the committed projections and their manifests.
- A colon denotes a translation correspondence; a tilde denotes only a
  grammatical/discourse attachment. Prefer the smallest useful groups;
  many-to-many and discontinuous correspondences are legitimate.
- An omitted original occurrence may be explicitly accounted for with an
  evidence note, but never counted as a lexical translation. Never attach
  unknown words to nearby tokens to reach a numerical target.
- Exact proposals from earlier **same-stream** editorial evidence are hints
  only. No legacy alignment, LSG Strong associations, Clear.Bible alignment
  or Aquifer. No automatic acceptance or contextual UBS-sense claim.
- Complete the first pass across the **entire cohort** before starting the
  second. Technical subdivisions are not separate cohorts. A reread by
  the same editor is not independent certification.
- Effective lexical coverage is translated distinct nouns, verbs,
  adjectives and adverbs / all distinct original occurrences of those
  categories, including omissions in the denominator. The 95% threshold
  applies to each chapter. Both inventories must be accounted for. The
  tool must report an unmet threshold, not hide or force it.

## Maintained tools and contracts

[macula_lsg_compact.py](../scripts/macula_lsg_compact.py) remains the original
single-chapter packet/token/ordinal helper. The cohort layer
[macula_lsg_cohort.py](../scripts/macula_lsg_cohort.py) reuses its source paths,
Unicode token offsets and ordinal resolution. Do not fork a second set of
tokenization or map semantics. The cohort commands currently support Hebrew
WLC/LSG; the Greek projection already exists, but needs its own explicit
word-class and versification adapter before this layer can process it.

The commands below are run from a repository checkout. Use a fresh local
scratch directory (for example /tmp/brsi-cohort). Keep text-bearing packets
local; the Git-tracked evidence consists of identifiers, ordinal maps,
source pins, editorial notes and progress receipts. Do not publish packets
or restricted dictionary/source-derived fields.

### 1. Prepare once, for the complete cohort

Inspect the working branch, issue, previous checkpoint and source manifests.
Choose consecutive canonical LSG chapter scopes. Example for the current
20-chapter cohort, after checking the proposed native-to-target routing:

    python3 scripts/macula_lsg_cohort.py plan Josh.11-24 Judg.1-6 \
      --confirm-identity --out /tmp/brsi-cohort/plan.json

Identity is an explicit editorial choice, not a result inferred from equal
verse counts. Where native and LSG numbering differ, use --routing instead.
The routing JSON contains native_chapters (if different from target chapter
scopes), identity_default (true only for explicitly selected unchanged
references), and routes (native verse reference -> target verse reference).
For example, the known Deuteronomy boundary can be expressed by mapping
Deut.28.69 to Deut.29.1 and Deut.29.1–28 individually to Deut.29.2–29.
Do not rely on an undocumented automatic shift. Shared target boundaries
are permitted; a missing target inventory is rejected.

The plan locks both manifest blobs, the chapter projection Git blobs,
the LSG prose digests, the original MACULA blobs and the exact native
reference routing. The plan is rechecked against local source files on
every subsequent command. It does not mark any chapter aligned.

Generate a compact packet for unprocessed rows:

    python3 scripts/macula_lsg_cohort.py prepare /tmp/brsi-cohort/plan.json \
      --bank work/macula-lsg-numbers-021-deuteronomy-004-candidate-bank.json \
      > /tmp/brsi-cohort/first-pass.txt

Use --scopes Josh.11-15 etc. only to limit the displayed packet size.
Keep the same plan across all technical groups. H/F are numbered native
and French occurrences; C? lists unaccepted exact proposals, with the
1-based bank entry ID. French punctuation is retained in the packet.
The packet header identifies the plan, draft and optional candidate bank.

### 2. First pass: submit maps, not reconstructed JSON ledgers

Review each entire source/target verse pair. Enter compact decisions as a
JSON object keyed by native verse reference. Examples (illustrative, not
assertions about the biblical text):

    {
      "Josh.11.1": "1:2;2-3:1;4~2",
      "Josh.11.2": {
        "map": "1:1;2:3-4;3~2",
        "omissions": [{"ordinals": "4", "note": "Explain the source omission."}]
      }
    }

Ordinals are 1-based; commas indicate discontinuous occurrences and hyphens
inclusive ranges. A target such as 2.3-4 identifies tokens in verse 2 of
the **routed LSG chapter**. Cross-chapter routing of complete native verses
is supported; an individual relation spanning two target chapters is not
yet represented by the chapter ledger contract. Stop and record such a case
instead of flattening or guessing. Target-only verses without a native
route also require an explicit future contract rather than a fabricated link.

Accumulate new decision files without rewriting previously completed maps:

    python3 scripts/macula_lsg_cohort.py draft /tmp/brsi-cohort/plan.json \
      --decisions /tmp/brsi-cohort/group-01.json \
      --out /tmp/brsi-cohort/draft-01.json

For a later group, add --base /tmp/brsi-cohort/draft-01.json and choose a new
output file. Duplicate first-pass rows fail closed. Use --draft on prepare
to skip already drafted verses. Bounds, duplicate relations and explicit
omissions are checked; a draft is allowed to have unresolved occurrences.

Resume the current interrupted cohort without redoing Joshua 11–12:

    python3 scripts/macula_lsg_cohort.py draft /tmp/brsi-cohort/plan.json \
      --legacy work/macula-lsg-joshua-011-compact-manual-01.json \
      --legacy work/macula-lsg-joshua-012-compact-manual-01.json \
      --out /tmp/brsi-cohort/draft-01.json

Legacy import checks exact projection and native blob identities and target
routing, imports only manual_map rows, and does not convert an unresolved
ordinal into an accepted omission. In particular, Josh.12.4 remains to be
decided editorially. Keep the existing cohort checkpoint and candidate
preparation files; they are not review evidence.

### 3. Second pass: review every verse, record only differences

Freeze the complete first-pass draft. Do not reconstruct every ledger or
repeat every unchanged map. Generate compact H/F/A lines (source, target,
initial/effective alignment); --pairs additionally resolves the displayed
relation groups into text when useful, especially for difficult idioms or
cross-verse relations. --scopes controls packet size, not cohort size.

    python3 scripts/macula_lsg_cohort.py audit /tmp/brsi-cohort/plan.json \
      --draft /tmp/brsi-cohort/draft-final.json \
      > /tmp/brsi-cohort/audit.txt

Create a review envelope bound to the exact plan and immutable draft:

    python3 scripts/macula_lsg_cohort.py review-template /tmp/brsi-cohort/plan.json \
      /tmp/brsi-cohort/draft-final.json --out /tmp/brsi-cohort/review-01.json

The editor fills reviewed with the **explicit references actually reread**
and corrections with replacement maps **only for changed rows**. Optional
notes are restricted to significant editorial issues. A map-only replacement
retains previous omission evidence and notes; to remove a previously recorded
omission, supply an explicit empty omissions array with the corrected map.
Never prepopulate reviewed or infer it from missing corrections.

Multiple envelopes may be prepared without repeating earlier work. Supply
them in order with --review on audit, report and finalize. Use
--skip-reviewed on audit to display only remaining rows. Repeated reviewed
references, changes without review, no-op corrections, unknown references
and stale draft or plan hashes are rejected. After initial review, an
explicit amendment may correct a previously reviewed row: add
amends_effective_sha256 from the preceding report, list only the previously
reviewed corrected references and give the changes. The preceding effective
digest must match exactly. Preserve all earlier deltas; no silent rewrite.

### 4. Rebuild and inspect once for the cohort

    python3 scripts/macula_lsg_cohort.py report /tmp/brsi-cohort/plan.json \
      /tmp/brsi-cohort/draft-final.json --review /tmp/brsi-cohort/review-01.json

Add further --review arguments for additional batches. The report lists
drafted/reviewed/corrected counts, missing original IDs and French tuples,
omissions, relation-kind counts and per-chapter lexical coverage. The
effective digest and review envelope digests make replay auditable.
It is an integrity report, not a substitute for reading the sources.

    python3 scripts/macula_lsg_cohort.py finalize /tmp/brsi-cohort/plan.json \
      /tmp/brsi-cohort/draft-final.json --review /tmp/brsi-cohort/review-01.json \
      --out /tmp/brsi-cohort/rebuilt

Finalize refuses an incomplete first/second pass or any chapter with
unaccounted occurrences or below 95% lexical coverage. It reconstructs
identifier-only chapter ledgers, target offsets, native segments, coverage
and reverse-lookup consistency; it retains effective maps and report.
Outputs are staged candidates for editorial acceptance, not publication.
No source, tracked ledger, issue or branch is edited by the CLI itself.

The existing [raw-source validator](../links/alignments/macula-lsg/validate_chapter.py)
remains a separate gate; exact OSIS bytes, upstream MACULA XML, the UBS bridge
and individual dictionary senses must not be certified from projection checks
alone. Greek adapter, general cross-target-chapter relations, raw-source
publication validation and independent editorial review remain pending.

### 5. Persist and resume

Use the working branch specified in #200. Accumulate ordinal decisions in
temporary Git blobs or a local scratch directory and keep intermediate tree
SHAs when needed. Group one cohort's completed ledgers, plan, immutable draft,
review envelopes and receipt in a single commit; keep original decisions
and amendments. Verify the branch head before writing and after committing.
Record a durable partial checkpoint if interrupted; never mark it complete.
Synchronize issue checkboxes only when the corresponding editorial pass
and criteria are actually satisfied. No intermediate PR, automated chapter
test run or publication. Publication is owner-approved separately (#62).

If working through GitHub-only tools rather than a shell, the same contracts
apply: fetch compact source groups, persist maps/deltas rather than full
text, retain tree receipts, and do not claim a Python command or validation
ran unless it actually ran. The CLI must be executed in an environment with
the checkout before relying on its output. Connector limitations are
technical subdivision limits, not editorial progress.

## Throughput and continuous improvement

Measure actual work, separately for both passes: native verses read,
manual rows written, rows corrected, chapter count, coverage, source
inventory and residual anomalies. Record actual completed rows and cohort
size, not source loading or candidate generation as editorial progress.
Prefer one source read per group, compact packets, unchanged-map omission,
one reconstruction and one final commit. Never trade semantic precision
for a higher throughput figure.

Each change to the method requires:
1. an updated current contract here and links to the maintained code;
2. regression coverage for new tooling, including negative/fail-closed cases;
3. a factual record of what was implemented, actually executed and verified,
   what remains pending, and any change in observed throughput in #200.

The initial cohort CLI has authored regression coverage in
[tests/test_macula_lsg_cohort.py](../tests/test_macula_lsg_cohort.py).
Under the current direct-commit/no-intermediate-automated-tests decision,
execution and real-corpus end-to-end equivalence remain pending. Do not
describe the new CLI as production-validated until those checks actually
pass; retain the prior reviewed maps and original raw-source validator.
