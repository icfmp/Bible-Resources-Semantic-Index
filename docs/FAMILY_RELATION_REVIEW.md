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

## Typed collective descendant references: Mizraim and Ludim

The pinned original ACAI `people/json/Egypt.json` contained a raw TIPNR
label `Ludim@Gen.10.13-1Ch` **inside** its `offspring` list, unlike the six
remaining typed `group:` descendants. This was not an exact BRSI identity and
could not be resolved by the existing exact-ID audit.

The already existing `group:Ludim` has matching key references Genesis
10:13 and 1 Chronicles 1:11. BRSI now points `person:Egypt.offspring` to
this existing group, preserving the original raw string and field values in a
reversible `bsi.editorial_field_changes` receipt. No new child, person,
original-word witness, biblical verse, text variant or index identity is
created.

This is a **collective descendant relation**, not an assertion that a tribal
group is an individual child. The source's distinct
`group:Ludim.group_origin=person:Lud` requires its *own* evidence review:
the typed offspring repair does not settle whether different traditions
or ethnonyms called Lud/Ludim are historically equivalent.

`scripts/offspring_target_policy.py` validates that every future
`offspring` value is a typed identity string; it does not assume every
descendant is a person, nor replace the general exact-ID relationship audit.
