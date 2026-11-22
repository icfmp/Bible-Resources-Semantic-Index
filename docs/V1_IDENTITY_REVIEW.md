# V1 identity evidence dispositions — no inferred genealogy or city aliases

**Status:** source-reviewed corrections and explicit abstentions; **not** a claim
that every inherited ACAI identity or every textual variant has been independently
verified. Supports [issue #6](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6)
and the V1 public-projection gate.

## Editorial decisions and evidence

| Case | V1 decision | Primary witness / competing readings |
| --- | --- | --- |
| Mary, mother of John Mark | Preserve `person:Mark.mother=person:Mary.5` and the reciprocal child record. Remove assertions that a **specific unnamed husband** is Mark's father or either Mary's spouse; leave both source-only `HusbandOfMary*` identifiers **unreviewed** and without unsupported family edges. | [Acts 12:12](https://www.biblegateway.com/passage/?search=Acts+12%3A12), [Matthew 27:56](https://www.biblegateway.com/passage/?search=Matthew+27%3A56), Mark 15:40. None of these passages names the husband or equates the two mothers called Mary. |
| Caleb / Azubah / Jerioth | Preserve `person:Caleb.2` as father and all individual name/word witnesses. Withhold assignment of a *unique mother* for Jesher, Shobab and Ardon, as well as reciprocal Azubah-as-mother assertions pending the disputed antecedent. Do **not** merge Azubah and Jerioth or conclude either is not a mother. | [1 Chronicles 2:18](https://classic.net.bible.org/passage.php?passage=1Ch+2%3A18), [SIL translator notes](https://tips.translation.bible/story/sil-translators-notes-on-1-chronicles-218/). Different translation analyses distinguish two women or take Jerioth as an alternate name. |
| Zimmah / Jahath / Shimei | Withhold the *single merged-entity father assertion* and competing reciprocal `offspring` edges. Retain **both source verse and exact original-word occurrences** on `person:Zimmah`; retain both independently attested genealogical texts. The two witnesses are **not** repaired, combined or declared erroneous. | [1 Chronicles 6:20](https://biblehub.com/1_chronicles/6-20.htm) and [6:42](https://classic.net.bible.org/verse.php?book=1Ch&chapter=6&verse=42), respectively Heb. 6:5 and 6:27. |
| Lud / Ludim | Retain the already approved narrowly justified separation: Gen 10:13 and 1 Chr 1:11 (Mizraim's Ludim) vs Gen 10:22 and 1 Chr 1:17 (Shem's Lud). Later mentions remain unreviewed. | [PR #92](https://github.com/icfmp/Bible-Resources-Semantic-Index/pull/92) and its case-level source receipts. |
| Gadara / Gerasa / Gergesa | Keep distinct historical city IDs, source Greek word IDs and verses. Remove unqualified cross-city alternate labels and the editorial artifact `Var`. Keep regional demonym text readings as **source-witness candidates**, not synonyms proving a site or approved canonical city match. `Gergesa` is not created as a new entity merely to eliminate textual-variant ambiguity. | [Matthew 8:28](https://classic.net.bible.org/passage.php?passage=Mat+8%3A28-34), [Mark 5:1](https://classic.net.bible.org/passage.php?passage=Mar+5%3A1-19), Luke 8:26 and [critical-variant analysis](https://classic.net.bible.org/passage.php?passage=Mar+5%3A1-19). |

Case-level `bsi.editorial_field_changes` receipts on modified native records preserve
**the former source-derived field values**, the removed field names/aliases,
justifications and source pointers; `bsi.source_sha256` still identifies the
immutable original. No source verse, exact WLC/SBLGNT word ID, source ID,
canonical ID, biblical punctuation, or published ZIP was modified.

## Remaining source uncertainty is an explicit *abstention*

The old broad identity worklist also covers **641 same-name candidate groups**
from source labels. This is a triage inventory, not evidence that there are 641
incorrect identifications. The ten cases previously reported without unique
key-verse/original-word/hint evidence remain unreviewed; their identities must
not be automatically merged, assigned a new biographical qualifier or promoted
to reviewed status. Their detailed source pointers remain recoverable via
`scripts/audit_name_ambiguities.py` and the [original source-triage
record](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/6#issuecomment-7083272773).
The ten are: `HusbandOfMary`, `HusbandOfMary.2` (unsupported unnamed
husband identifiers, whose female-name aliases were removed);
`Judah`/`Judah.2` (shared Ezra 3:9 original-word witness);
`SecondProstitute` (role identity without explicit name token);
and `Caesarea.2`, `Gadara.2`, `Heres.2`, `Neapolis.2`,
`ValleyOfMizpeh` (historical or reference-only geographic candidates).
These source IDs remain **unreviewed**; absence of a differentiating witness
is not permission to merge or delete one. The criterion for V1 is
**safe abstention**, not inventing missing manuscript evidence.

The current native index carries source IDs, canonical IDs, source reference
lists and typed original-word occurrence claims; **it does not export**
`father`, `mother`, `offspring`, `partners`, `group_origin`,
`referred_to_as` or inherited display-name aliases in its `entities` payload.
Those original source relationship and alias values are intentionally separate
from the independently reviewed public semantic assertions. A person/word
occurrence is still a source claim, **not** a verified identity proof or
contextual lexical sense. The standalone V1 projection regression test enforces
the family/alias exclusion.

**Important limitation:** the nonpublishing candidate still contains all
permitted canonical source *identity IDs*, including source-unreviewed
unanchored placeholders. Their presence is not a verified person identification
and must not be turned into user-facing named biographies or precise kinship.
A later data-model change to hide or quarantine generic placeholder identities
requires a separate, consistent editorial and release-compatibility review.
Do not claim those source-level identities have been adjudicated by this pass.

## Scope and release gate

This closes the concrete, source-conflicted **V1 genealogy/variant claims** with
reversible corrections or explicit evidence-based abstentions, *not* the historical
research question of every homonym. Any future work to resolve a particular
unreviewed textual/ethnographic claim requires exact edition witnesses, a scoped
issue and new editorial evidence. A V1 release remains blocked under [#62](https://github.com/icfmp/Bible-Resources-Semantic-Index/issues/62)
until rights/consumer/owner approval, irrespective of this issue's status.
