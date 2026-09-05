# Repository guidance

Byte Core is a public repository. Treat every file, commit, issue, pull request, diagnostic, and generated artifact as potentially permanent public history.

## Repository map

- `src/byte_core/` contains dependency-light Python behavior.
- `bin/byte` is the POSIX launcher.
- `shell/` contains optional generic shell assets.
- `templates/` contains fictional Core-managed starter material.
- `docs/` contains public contracts and support boundaries.
- `tests/` contains unit tests and deliberately fictional fixtures.

Run the complete unit suite with `python3 -m unittest discover -s tests`. Validate public release paths with `python3 scripts/check_release_privacy.py PATH`. Check POSIX launchers and shell assets with `sh -n FILE`; use `zsh -n FILE` only when Zsh is available.

## Ownership boundary

> Byte Core owns behavior and structure; each deployment owns identity and truth.

Core-managed content may define generic behavior, structure, validation, schemas, and fictional examples.

Deployment-owned identity, inventory, configuration, credentials, documentation, and observed state must remain outside version-controlled Core content unless a future public design explicitly defines a safe example or interface.

Unknown deployment facts remain unknown. Do not invent hostnames, addresses, paths, services, credentials, device state, or other infrastructure details.

## Public-repository safety

Do not import, copy, adapt, or reconstruct private repository or deployment:

- files or Git history;
- prompts or transcripts;
- inventory or configuration;
- credentials or environment values;
- logs, diagnostics, or reports; or
- operating instructions or deployment-specific knowledge.

Create public material from approved public requirements and fresh fictional examples. Redaction does not make private source material appropriate for import.

Ignored paths are defense-in-depth, not authorized storage for sensitive information.

## Work discipline

Before changing state:

1. Check the current repository and target state.
2. Plan the exact scope, validation, and backout.
3. Apply only the approved change.
4. Verify the result with explicit evidence.
5. Preserve or execute a safe backout when required.

Keep destructive targets explicit. Preserve unrelated user work. Do not claim success without validation evidence.

Separate repository planning from implementation when a checkpoint requires review. Do not expand work into adjacent issues without approval.

## Documentation stays with the change

Documentation accuracy is part of completion. Every change to behavior, commands, configuration, support boundaries, or release status must include the corresponding documentation updates in the same change or pull request.

- Identify affected documentation while planning. Review the root README capability table, any affected component READMEs and contracts, the first-session guide, and release notes as applicable.
- Describe implemented behavior and known limitations accurately. Keep planned features, experimental proofs, supported capabilities, and validated release evidence distinct. Remove stale claims when behavior changes.
- Keep platform documentation, CI targets, release-checker targets, and the evidence ledger consistent when support changes. Never mark evidence complete without the required reviewed observations.
- Verify affected command examples and links against the implementation. Check the packaged documentation too when artifact contents or relative links are affected. State any manual or platform validation that remains unavailable.
- Summarize documentation impact in the completion report or pull request. If no documentation change is needed, state why. Do not defer required documentation to an unspecified follow-up or call the work complete while it is stale.

This rule applies only to Core-owned public material. It never authorizes reading, importing, or rewriting deployment-owned documentation or private source material. Record newly discovered implementation gaps truthfully; documenting a gap does not fulfill an unmet safety requirement or authorize unrelated implementation work.

## Completion evidence

Before claiming a change is complete:

1. Run the narrow tests for the changed component.
2. Run the full unit suite.
3. Run `git diff --check`.
4. Run the privacy scan for changed public artifact paths.
5. State which platform-specific or manual evidence remains unavailable.

Codex integration is advisory and must degrade safely. Do not parse transcripts, prompts, private logs, environment-variable values, or deployment content. A hook failure never authorizes mutation, publication, or reporting.

## Current bootstrap boundary

Byte Core has no functional release or supported installed command-line interface yet. The internal bootstrap contains experimental exact-plan initialization, installation, update, removal, shell-integration, diagnostics, and reviewed-reporting proofs. Do not claim a supported release, remote update discovery, automatic reporting, or production-ready lifecycle behavior.

The complete Codex integration and authority contract is documented in [`docs/codex-integration.md`](docs/codex-integration.md) under [issue #12](https://github.com/kodiakdirus/byte-core/issues/12). This file remains the durable repository safety baseline.
