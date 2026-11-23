# BRSI repository maintenance policy

This policy applies to every new BRSI contribution, including word-to-translation
alignments such as MACULA–LSG. Keep the current instructions short, testable
and **faithful to independently pinned biblical sources**.

## File lifetime and ownership

| Content | Maintained location | Rule |
| --- | --- | --- |
| Shared production/validation tools | scripts/ | Reusable interface, tested and explicitly referenced |
| Source-specific lexical or alignment tools | links/ (source-owned subtree) | Keep source-specific rules and tests beside their provenance |
| Source evidence, individual editorial decisions, abstentions and edition locks | Existing source-owned versioned ledgers | Durable, attributed, reviewable and reversible; never auto-delete |
| One-time research experiments | Working branch, then Git history | Retire the executable after the evidence and decisions are recorded, unless a repeatable source check still needs it |
| Generated source-derived reports | Runner-local temporary directory or ignored worktree | Not part of a commit or GitHub artifact; restricted source text stays private |
| Historical released archives | Existing approved release and immutable checksums | Do not overwrite, repackage as a new release or infer license authorization |
| Documentation | README.md (navigation), current source README, docs/ (methods) | Describe the **current** contract; keep historical progress in issues, PRs and Git |

An audit may have a single caller and still be indispensable: **never delete
a source-specific verifier solely because its filename is old or its static
call count is low**. A shared producer used by several downstream reviews must
not be removed unless equivalent full-source validation is independently proven.
Never put edition-specific ad hoc exceptions into the common validator to pass
a test.

## Required changes in a pull request

1. **Before editing:** inspect the latest main, open issues/PRs, source locks,
   original rights notices and any existing implementation.
2. **Classify the change:** tool, source-specific auditor, research experiment,
   original data, reviewed editorial decision, generated evidence or publication.
3. **Tests:** each newly added maintained Python tool must be referenced by a
   source-level regression test. Include negative cases for missing source
   evidence, edited original words/notes, invalid references, unsafe lexical
   matches and publication/rights guards where relevant. A filename mention is
   not proof of sufficient test coverage; reviewers must inspect the tests.
4. **Documentation:** update only the current instructions and source-specific
   limits. Record migration history, experiment outcomes and discussions in
   the PR/issue, not as accumulating README diary entries.
5. **Rebuild and compare:** run offline tests and relevant source-pinned
   workflows. Compare actual intermediate output for modified producers and
   historical ZIP bytes where the producing path is affected. Green tests
   alone do not certify textual or editorial fidelity.
6. **Finish:** remove disposable research scripts, preserve evidence ledgers,
   verify no broken callers/links or accidentally tracked temporary reports,
   and record what was implemented, tested, editorially approved and published
   as four **different** statuses.

For all scripture and lexical sources: preserve original wording, punctuation,
annotations, versification, word IDs, Strong/LN/SDBH and edition-specific
differences. A word alignment, headword identity and independently verified
contextual meaning are three **separate** propositions. Do not invent an
alignment or infer a contextual sense from textual/lexical similarity.

## Automated gates

The standalone offline workflow runs:

- scripts/tool_registry.py --check-workflows: reject missing literal Python
  paths in checked-in Actions workflows; report static call sites without
  automatically retiring anything.
- scripts/check_repository_hygiene.py: inspect **Git-tracked** paths, fail on
  unambiguously transient build/cache/snapshot files and broken *local*
  Markdown link targets. External URLs and Markdown heading anchors are not
  verified by this offline check.
- The same hygiene checker, **on pull requests**, compares the exact fetched
  PR base commit with the checkout. Every **new** maintained Python script
  in scripts/ or links/ must have a literal reference from a Python regression
  test. Existing independently maintained tools are not retroactively
  removed or declared obsolete.
- The relevant existing offline, native, and UBS Greek/Hebrew pinned-source
  suites protect source integrity and historical release byte equivalence.

To run these checks locally:

```sh
python3 -I scripts/tool_registry.py --check-workflows --review-candidates
python3 -I scripts/check_repository_hygiene.py
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The checkers are read-only. They never reformat scripture, rewrite a review
ledger, erase uncertain source links or publish an archive. Manual review is
required for dynamic imports, editorial uncertainty, rights and architecture.

**Closure criterion:** no confirmed hygiene errors; all new tools tested;
source-specific outputs independently reproducible where touched; remaining
tools justified by a live role. Source licensing and actual publication require
separate explicit authorization.
