# BRSI V1 dictionary crosswalks

Reserved for compact **source-reviewed** BRSI entity → dictionary entry mappings,
one file per exact dictionary edition with stable article IDs, licensing,
explicit evidence and withheld decisions when a source is ambiguous.
Do not copy definitions, infer person identities from Strong codes, or
silently resolve unresolved matches. Use the [crosswalk policy](../README.md)
and [v1 schema](../schema.v1.json).

## Implemented lexical bridges

- [UBS Greek NT — bilingual English/French v1.0](ubs-greek/README.md): real source-pinned MACULA Strong and Louw–Nida → UBS entry/sense ID index. It is a lexical bridge, not an unreviewed BSI entity-to-article identity assertion. English and French definitions remain in their original UBS datasets.

- [UBS Biblical Hebrew — bilingual English/French v0.9.4](ubs-hebrew/README.md): pinned Macula WLC `sdbh` → exact UBS lexical sense ID when attested; otherwise exact Hebrew/Aramaic Strong → *entry-only* candidates, never an invented contextual sense. Definitions stay in source UBS editions.
