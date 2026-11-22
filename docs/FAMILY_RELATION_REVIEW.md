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

No negative inference is permitted: a missing reciprocal relationship
is not evidence that two persons are unrelated. More than one claim can be
valid, especially where genealogical representation is editorially complex
or incomplete. Likewise, the tool does not enforce a theological model of
family relationships or invent unnamed spouses.

## Specific ACAI source discrepancy: the father of Mark

At pinned ACAI commit `e80a874e8282f996199c595378a3b3b9a43aac22`:

- [`HusbandOfMary.json`](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/people/json/HusbandOfMary.json)
  claims Mary of Acts 12:12 as spouse and Mark as offspring.
- [`HusbandOfMary.2.json`](https://github.com/icfmp/ACAI/blob/e80a874e8282f996199c595378a3b3b9a43aac22/people/json/HusbandOfMary.2.json)
  also claims Mark as offspring, but names the Mary of Matthew 27:56 as
  spouse and lists **only Acts 12:12** in its reference fields.
- Current BRSI `person:Mark` names only `person:HusbandOfMary` as
  father and `person:Mary.5` (Acts 12:12) as mother.

This is a **candidate source-level contradiction**. Neither Acts 12:12
nor Matthew 27:56 names either woman's husband. Therefore **do not turn
an inferred unnamed father into an attested biblical person**, and do not
delete or merge either original identity without source and editorial
review. Keep exact original source IDs and source fingerprints while this
case is open in [issue #6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6).

Source data is *not* corrected by this audit. Manual correction requires
verse-level evidence, a reversible editorial receipt and CI across
native identities, original words and family links.
