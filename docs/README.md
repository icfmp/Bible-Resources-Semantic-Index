# BRSI documentation

Start with the [repository README](../README.md) for the current native
entity/lexical index and [roadmap](ROADMAP.md) for open work. This directory
holds **durable project-wide rules and current workflows**, not chronological
development logs or a second source of truth.

## Where to go

| Need | Maintained reference |
| --- | --- |
| Edit an entity and preserve source/identity evidence | [Editable native records](EDITING_ENTITIES.md) |
| Understand origin, excluded third-party fields and permissions | [Rights and integrity](RIGHTS_AND_INTEGRITY.md) and [source provenance](../sources/README.md) |
| Verify the existing historical public ZIP formats | [V1 consumption and offline inspection](V1_CONSUMPTION.md) |
| Stage and validate a **nonpublishing** candidate | [Release/consumer integrity contract](RELEASE_CONTRACT.md) |
| Find active scripts, callers and retirement rules | [Tool maintenance inventory](MAINTENANCE_INVENTORY.md) and [shared scripts](../scripts/README.md) |
| Understand deferred entity graph research | [V2 relation model](RELATION_MODEL.md) |
| Check current blockers and priorities | [Roadmap](ROADMAP.md) and GitHub issues |

## Source-specific material

UBS [Greek](../links/dictionaries/ubs-greek/README.md) and
[Hebrew](../links/dictionaries/ubs-hebrew/README.md) retain their own
edition pins, original-word decisions, source review ledgers, rights evidence
and full-source verification workflows. Other independently sourced external
entries must be verified edition by edition; BRSI does not duplicate their
article text.

**Current documentation rule:** a reusable policy belongs here once;
source-specific editorial evidence belongs with the source; issue/PR/Actions
record dated execution. Completed one-shot scripts and historical progress
diaries are recoverable by immutable Git revision, not maintained as a second
pipeline on `main`. Do not delete unique reviewed decisions, abstentions,
source locks, old published release evidence, or rights records under the
pretext of removing old experiments.

The old v0.1 handoff, named-entity and topic pilots and first-release
rights/readiness records still exist as **historical evidence**, not current
commands. New work must follow the present source-specific guides and
source/rights/publication gates instead of replaying those historical steps.
