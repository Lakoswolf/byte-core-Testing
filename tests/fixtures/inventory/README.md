# Fictional inventory fixtures

These files were authored as public test inputs. They are not captured network output, real device inventory, or manufacturer claims.

- `discover.xml.txt` models two responding documentation addresses with no model identity.
- `inspect.xml.txt` models one printing-service hint. A service hint alone is not a confirmed device model.
- `selection.json` supplies a fictional operator-confirmed identity and stable catalog ID.
- `capabilities.json` supplies a fictional exact-model lookup with a reserved example URL. It does not establish any real hardware capability or enablement state.

XML is stored as `.txt` so the existing public text privacy gate scans it. Import accepts XML bytes independently of the filename suffix. These fixtures support offline rehearsal; they do not count as live network or manufacturer validation.
