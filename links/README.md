# BRSI external dictionary and encyclopedia links — V1

This is the reserved home for **small, edition-pinned, independently reviewed
entity-to-external-entry mappings**. It is independent of the entity-to-entity
semantic relation graph, which is deferred to **product V2**.

There is no verified external entity-to-article mapping in this repository yet.
No article text, lexical definitions, biographies, images, or restricted UBS
content is copied into these mappings. The existing UBS Greek/Hebrew lexical
bridges are separate source-specific research resources; their entries are
**not** automatically BRSI person/place/term cross-references.

## Candidate source assessment

The historical International Standard Bible Encyclopedia has a [V1 source/edition
feasibility assessment](ISBE_CANDIDATE_REVIEW.md). It identifies a stable
article-key mechanism and outstanding rights and source-matching gates;
**no article-to-entity mapping has been approved or added**.

## One file per independently verified resource edition

```text
links/
  schema.v1.json
  dictionaries/<resource-id>-<edition>.json
  encyclopedias/<resource-id>-<edition>.json
```

Use the [v1 crosswalk schema](schema.v1.json). A resource declares an exact
edition, revision, stable source URL, license and complete 40-character pinned
BRSI source commit. `license` identifies the upstream license and does **not**
alone establish permission to redistribute copyrighted articles, definitions
or annotations. Any publication requires separate approval.

An entity/entry pair has exactly one reviewed relation type within an edition:
`same_subject` and `related_subject`, for example, cannot both be asserted for
the same pair. Distinct entry IDs and independently reviewed identities remain
separate; this rule does not infer which identity is correct.

Approved rows contain a **current exact BRSI entity ID**, exact external
entry ID, the narrowest accurate link type, `review_status: "reviewed"`, and
explicit source evidence checked by a human. Matching names, Strong numbers,
MACULA word IDs or a plausible biblical verse are **not sufficient**.

## Recording decisions not to link

The optional `abstentions` list is an additive, backwards-compatible extension
of the link-only schema. It records `review_status: "withheld"` and source
evidence for one of:

- `ambiguous_entries`: two or more unresolved external candidates;
- `identity_unresolved`: the BRSI entity itself needs disambiguation;
- `source_entry_missing`: no matching source entry found in this edition;
- `source_rights_unverified`: this link/source field has not cleared review;
- `edition_unverified`: source version/provenance cannot be confirmed.

The same entity/entry pair cannot be both a reviewed external link and a
withheld candidate in the same edition file. Such contradictory decisions fail
validation; different entity IDs or different external entry IDs remain
independent and are not automatically equated.

An absent mapping is **unknown**, not an automatic `same_subject` match. A
withheld mapping is not an approved link. Preserve conflicting candidates
rather than guessing a single identity. Never create links to unavailable
868 ACAI Key Terms or quarantined identities.

## Validation before proposing a PR

From the repository root:

```sh
python3 -I scripts/validate_external_crosswalk.py --scan --data data
python3 -I -m unittest discover -s tests -p 'test_*.py'
```

The first command checks all mapping JSON files **directly** under
`links/dictionaries/` or `links/encyclopedias/` against the canonical native
entity index; it does not treat the nested UBS lexical-index development files
as encyclopedia mappings. Presently, zero live external crosswalk editions
is a correct result. It requires no network access and changes no data.

The verifier enforces the schema's reviewed/withheld statuses, full BRSI
producer commit, required edition/revision/license/source URL, duplicate
prevention, and exact current BRSI identities. Its synthetic tests are
explicitly **not** real reviewed editorial associations.

No data pack, Bible application integration or public release is created
by running these checks. See [rights and integrity](../docs/RIGHTS_AND_INTEGRITY.md)
and [release contract](../docs/RELEASE_CONTRACT.md).

## Separate translation-token alignments

Clear.Bible MACULA → LSG manual word/segment alignments live under
[alignments/clear-bible-lsg/](alignments/clear-bible-lsg/README.md), with their
own pinned upstream edition, original source/target selectors, per-group
multiplicity and explicit uncertainty states. This is **not** a
dictionary/encyclopedia entry crosswalk: never run the external entity-link
validator on it or turn the links into UBS lexical or contextual senses.
No translation text is copied into BRSI; generated candidate files are
nonpublishing until source rights, target-edition identity and owner approval
are established.
