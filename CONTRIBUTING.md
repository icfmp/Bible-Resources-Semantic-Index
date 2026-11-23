# Contributing to BRSI

BRSI is an identity and alignment index, **not** an editor of biblical source
texts. Changes must be independently reproducible, source-traceable and
reversible. Preserve original word IDs, references, punctuation, annotations,
versification, editorial exceptions and source-edition decisions.

Start with the [maintenance policy](docs/MAINTENANCE_POLICY.md), then the
[maintained tooling inventory](docs/MAINTENANCE_INVENTORY.md) and
[source rights rules](docs/RIGHTS_AND_INTEGRITY.md).
If editing an existing UBS stream, consult its source-owned README and exact
source lock before changing code or data.

Open focused pull requests: state the source revisions, what has changed,
tests and negative controls run, original/derived data left untouched and
whether any editorial or publication approval is required. Keep temporary
reports out of Git and write past decisions into issues/PRs, not endless
README progress logs.

Run the relevant test suite and:

```sh
python3 -I scripts/tool_registry.py --check-workflows
python3 -I scripts/check_repository_hygiene.py
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

For newly added Python tools, include a regression test in the same PR. The
offline workflow checks new tool test references using the pull request's base
commit; source-specific full rebuilds remain separate hard safety gates.

**No merge** when the affected tests, source integrity checks or mandatory
review approvals are unresolved. **No release** without independently verified
redistribution rights and an explicit publication decision.
