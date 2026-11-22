# Family-link review: reciprocal claims are not automatic facts

The inherited ACAI people dataset has structural links such as `father`,
`mother`, `offspring` and `partners`. These links are **original source
claims**, not necessarily statements independently corroborated by a direct
biblical verse. Their destinations have already passed exact-ID integrity
checks, but valid IDs alone cannot prove the relationship is correct.

The read-only command:

```sh
python3 -I scripts/audit_family_relation_consistency.py --limit 30
```

compares a person's `offspring` claims against the child's explicit
`father` or `mother` where that parent has a recorded binary source
`gender` field. It resolves inherited aliases through current
`bsi.canonical_id`, so two source name forms of the same reviewed identity
do **not** produce a spurious contradiction.

The audit distinguishes these cases without modifying any record:

- Reciprocal parent claims that agree canonically.
- A child lacking the counterpart parent field.
- Parent roles unavailable in source metadata.
- A **potential conflict** where the child names a different parent of the
  same role.
- An `offspring` link to a non-person reviewed type, such as a collective
  group or tribe. This may denote lineage collectively rather than a child
  person; it needs **source-specific semantic review**, not deletion.
- An `offspring` link to a restricted `keyterm:` source, which must remain
  **unavailable** in approved BRSI data, versus an otherwise absent exact
  current source ID. The audit reports these separately and cannot create,
  import or expose a restricted Key Term to fill a link.

No negative inference is permitted: a missing reciprocal relationship
is not evidence that two persons are unrelated. More than one claim can be
valid, especially where genealogical representation is editorially complex
or incomplete. Likewise, the tool does not enforce a theological model of
family relationships or invent unnamed spouses.

## Tracking concrete editorial decisions

Case-level biblical evidence, ambiguous identities and corrected values belong
to [issue #6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6)
and the `bsi.editorial_field_changes` receipts on the actual entities, rather
than accumulating as historical case reports in this generic process guide.

In particular, do not silently settle apparent contradictions by merging
same-name persons, identifying a woman’s unnamed spouse, selecting between
genealogical textual traditions, or treating collective descendant groups as
individual children. Positive original-source evidence and tests are mandatory.
