# BRSI regression tests (current standalone repository)

From the **repository root** run the complete native regression suite:

```sh
python3 -I -m unittest discover -s tests -p 'test_*.py'
python3 -I scripts/build_native_index.py --data data --output /tmp/brsi-current.json
```

Tests are automatically discovered by [offline CI](../.github/workflows/offline-checks.yml);
the separately source-pinned [native build](../.github/workflows/native-entity-index.yml)
also validates current BRSI entities and the unapproved phase 1 release candidate.

Greek and Hebrew UBS source-original checks live in their respective
[`ubs-greek`](../links/dictionaries/ubs-greek/) and
[`ubs-hebrew`](../links/dictionaries/ubs-hebrew/) directories and
have separate source-pinned CI jobs. Their development baselines are
**not** approved public lexical assets.

The removed monorepo test path prefix and old `entity-index.yml` workflow
are retired. Use the commands above.

Both source-pinned UBS CI workflows run every `test_*.py` file in their
respective Greek/Hebrew directories as a separate isolated Python process,
with fail-fast behavior. New source-specific regression modules are therefore
automatically included; keep the `test_` naming convention and preserve
source-pinned rebuild verification as a separate CI stage.
