# Bible Resources Semantic Index (BRSI)

Open-source, offline, source-pinned **biblical entity and lexical indexes**.
BRSI identifies and disambiguates entities and original-language links so other,
separately maintained resources can describe them. **It is not an encyclopedia**
and does not maintain multilingual biographies.

**BRSI** is the current project name. Historical `BSI` IDs, release tags,
source filenames and GitHub URLs remain stable for compatibility.
This is the authoritative development repository for BSI. Bible-Resources
retains the three **historically published** BSI ZIP releases until a separate
delivery/publication migration is approved. BSI is neither the Bible application
nor a SWORD module.

**Current milestones and issues:** [BRSI roadmap](docs/ROADMAP.md) — also records which UBS research evidence is retained versus reproducibly regenerated.

**V2 only (deferred):** [semantic entity relations research prototype](docs/RELATION_MODEL.md). Its inherited claims remain unreviewed and are **not part of V1**, any V1 release candidate or the Bible app.

**V1 consumption (documentation only):** [three published ZIP formats, source-word lookup rules and an offline archive inspector](docs/V1_CONSUMPTION.md) — no implementation in Bible.

**Phase 1 release safety:** [versioned artifact and consumer contract](docs/RELEASE_CONTRACT.md) — local integrity receipts are not publication approvals and checked-in lexical baselines are not public distributions.

## Current sources of truth

| Stream | Current development inputs | Existing published edition |
| --- | --- | --- |
| Biblical entities | [5,773 editable, corrected BSI records](data/entities/), [3 quarantined originals](data/quarantined/), [source lock](data/source.lock.json), [migration manifest](data/migration/acai-baseline-materialization.json) | [Entity index v0.1.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-v0.1.0) |
| UBS Greek lexical links | [Pinned bilingual source baseline and reviewed data](links/dictionaries/ubs-greek/) | [Identifier-only v0.1.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-greek-v0.1.0) |
| BRSI LSG word index (derived from original Clear.Bible) | [Original source lock, reviewed corrections and BRSI-owned index builder](links/alignments/clear-bible-lsg/README.md); exact original bytes fetched and verified from upstream | **Maintained private index candidate, not yet released or approved for Bible** |
| UBS Hebrew lexical links | [Pinned bilingual source baseline and reviewed data](links/dictionaries/ubs-hebrew/) | [Lexical v1.0.0](https://github.com/icfmp/Bible-Resources/releases/tag/bsi-ubs-hebrew-v1.0.0) |

**Current entity data are versioned directly in Git.** We imported and
materialized the already reviewed edits exactly once: original ACAI
`e80a874e8282f996199c595378a3b3b9a43aac22` (6,644 records) was
validated, but the **868 Key Terms** were excluded from this public dataset
pending their separate third-party rights review. These excluded records are
**not** claimed to be present here. They are not to be published for now.

The migrated 5,776 entity source records retain original source IDs and
fingerprints, original-word groups, structural relations, editorial decisions
and evidence. Inherited encyclopedia descriptions have since been pruned
from the editable 5,773 active records: BRSI is an identity/link index,
not a multi-language biography store. The source text remains recoverable
from the pinned ACAI edition and Git history. The 18 redundant translated
preferred labels per entity have also been retired, leaving one working
English source label and preserved English aliases. This working label is
**source-unreviewed** unless independently approved; the optional reviewed
`bsi.identity_hint` is used for genuine homonym disambiguation. The
original keyterm-free index build was byte-compared during migration, and
each subsequent field-only cleanup preserved its index output exactly. The historical
ACAI checkout is not used for normal BSI builds. See [editing current entities](docs/EDITING_ENTITIES.md)
and [source provenance](sources/README.md).

## Build the entity index

From a fresh checkout of **this repository** (Python 3 required):

```bash
python3 -I scripts/build_native_index.py --data data --output /tmp/bsi-current.json
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The native builder consumes the **current** `data/entities/` and
`data/quarantined/` records and edition-specific qualification metadata.
It does **not** download ACAI or replay `data/editorial-decisions.json`.
That decisions file and `tests/support/legacy_acai_compiler.py` remain as historical
migration evidence and tested index-finalization support, not the regular
editing interface. Never silently rewrite biblical references, original-word
IDs, text-critical evidence, or source descriptions.

## CI and source evidence

- [Native entity build](.github/workflows/native-entity-index.yml) verifies
  the canonical entity records without an ACAI checkout.
- [Offline regressions](.github/workflows/offline-checks.yml) check BSI tools,
  source invariants and source-workflow safety.
- [Greek UBS verification](.github/workflows/bsi-ubs-greek.yml) and
  [Hebrew UBS verification](.github/workflows/bsi-ubs-hebrew.yml)
  rebuild and test against the exact pinned original-language and dictionary
  source revisions. They do not publish new releases or expose source-derived
  private working evidence as public GitHub Actions artifacts.
- [Entity relationship audit](.github/workflows/audit-native-relations.yml)
  reports inherited cross-entity links without rewriting them. Remaining
  editorial review is tracked in [issue #6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6).

**Publishing is a separate, explicitly authorized step.** The three historical
release URLs remain valid; the project does not automatically synchronize
or republish those archives. Bible-Resources should eventually consume approved
BSI releases by **version and checksum**, not copy files from a moving branch.

## Layout

```text
data/entities/         Current, editable BSI entity JSON records
data/quarantined/      Retained inactive historical identities
data/migration/        One-time source transfer manifest
data/*.json            Edition locks, original evidence and historical decisions
links/dictionaries/    Source-specific UBS Greek and Hebrew data/tools/tests
links/encyclopedias/   Future reviewed external links
scripts/               Shared BSI build, validation and research tools
tests/                 Independent regression tests
sources/               Historical source provenance (no live ACAI checkout)
docs/                  Current methods and reviewed editorial background
work/                  Rebuildability, snapshot format and data-handling limits
```

The inherited dictionary-specific research scripts intentionally remain
beside their source-locked evidence and regression fixtures. The complete
source-derived intermediate evidence is **not** stored in the public tree.
See [working-state limitations](work/README.md): a successful CI build
is not proof of permanent archival of every intermediate file.

## Contributing and maintenance

Follow [CONTRIBUTING.md](CONTRIBUTING.md) and the
[maintenance policy](docs/MAINTENANCE_POLICY.md) for code lifetime, maintained
source-local tests, current documentation and review gates. The offline CI
rejects tracked temporary files, broken local Markdown paths and newly added
Python tools without a regression-test reference; it never deletes sources
or guesses that a reviewed audit is obsolete.

## Editorial and rights policy

Preserve source provenance, source-versification differences, uncertainties,
competing candidates and evidence. No lexical lemma, Strong/LN reference or
candidate dictionary ID proves a contextually unique sense on its own.
Never invent verse text, references, entities or semantic choices to obtain
100% coverage.

The imported ACAI-derived dataset is subject to **CC BY-SA 4.0** attribution
and adaptation obligations. Source-derived UBS/MACULA fields may have
separate restrictions. Data and code licensing must be evaluated separately;
the repository's GPL code notice is not a license grant for third-party data.
The 868 Key Terms remain withheld as agreed. See [current rights and integrity rules](docs/RIGHTS_AND_INTEGRITY.md),
[the rights audit](docs/BSI_V0_1_RIGHTS_AUDIT.md)
and [issue #5](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/5)
for the specifically excluded source class.
