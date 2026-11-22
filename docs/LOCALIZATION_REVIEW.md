# Inherited ACAI localizations: publication boundary

Entity identities marked `bsi.review_status=editorially_reviewed` are **not** necessarily backed by reviewed biographies, labels, or translations. Current BSI compact entity builds deliberately do not export `localizations`.

Some original ACAI localization claims contradict BSI's independently reviewed identity corrections. Their original text remains intact for source traceability; affected records carry `bsi.inherited_localizations`:

- `status: withheld_pending_review`: **do not use** the indicated fields as BSI-approved reader-facing metadata.
- `fields`: an explicit scope. A bare field name (e.g. `descriptions`) applies across languages; a language-prefixed field (e.g. `eng.alternate_labels`) is language-specific.
- `reason` and `source`: editorial justification and attribution.

A future reader-facing localization exporter **must** fail closed for these fields. This annotation does not constitute translated corrections or an approved rendering. Correct fields through documented language-specific review, not guesswork, and only then narrow or remove the hold. Preserve original ACAI witnesses through the pinned source and field-change receipts.

The current tracked holds cover inherited descriptions for Jashar, Perez-Uzzah, Johanan and Shallum.5; person-identity labels for Perez-Uzzah and Johanan; and geographic/demonym alternate names for Gadara in English. Gadara's descriptions of the historical Decapolis city are not blanket-withheld. None of this changes existing compact entity exports, original-language anchors, or published releases.
