# Byte Core

> **Status: pre-alpha repository bootstrap**

Byte Core is an independent community project exploring a safe, friendly, Codex-centered framework for self-managed infrastructure.

The repository has established its public foundation and initial configuration-ownership boundary. The v0.1 candidate is ready for deployment testing, but no functional release or supported installed command-line interface exists yet. Installation and operational use are not currently supported.

## Start here

New to Byte? Follow [Your first session with Byte](docs/getting-started.md). Open a fresh checkout in Codex, use the supplied first message, and let Byte guide you through checking your computer and creating a disposable example deployment. The guide includes expected results, explanations of the generated documents, and a terminal alternative.

Byte Core supplies the commands, templates, and working rules; Codex provides the conversational interface. A deployment is a separate folder of operator-owned configuration and documents. Your first session explores that structure using fictional data, without connecting to infrastructure.

If you are reviewing a release candidate, continue with [deployment acceptance testing](docs/deployment-testing.md) after the introduction.

For guided automation of local candidate installation and starter initialization, the source checkout provides an [experimental setup script](docs/getting-started.md#experimental-installation-script-source-checkout-only). Run `python3 scripts/setup_byte_core.py` for yes/no guidance, location choices, optional starter documents, and a preview-only option. After installation it offers helper settings, separately approved Bash/Zsh profile integration, and starter-notebook onboarding; `--finish-setup INSTALL_PLAN` returns to those steps later. Add `--from-repo` to download fresh source from this fork, with repository/ref selection and commit review. Installation requires approval of each saved plan; it does not install prerequisites or establish release acceptance evidence.

After the document skeleton, explore [guided device inventory](docs/inventory.md). Its offline walkthrough uses fictional devices; live discovery is a separate, explicitly approved step with optional Nmap.

For disposable unit and candidate lifecycle testing, use the [Ubuntu dev container](docs/dev-container.md). It provides a read-only source mount, a terminal rehearsal, and optional Dev Containers editor configuration. Container observations remain separate from required native release evidence.

## Architectural rule

> Byte Core owns behavior and structure; each deployment owns identity and truth.

Byte Core is intended to provide reusable behavior, validation, templates, and lifecycle tooling without embedding the identity or private state of any particular deployment.

## Safety principles

Byte Core is being designed to:

- keep secrets and private inventory out of version-controlled Core files;
- preserve deployment-owned configuration and documentation across updates;
- distinguish checking, planning, applying, verifying, and backing out changes;
- resolve exact targets before destructive operations;
- preserve fallback access before critical connectivity changes;
- avoid inventing infrastructure facts;
- require validation evidence before claiming success; and
- keep diagnostics and reporting opt-in, minimal, and reviewable.

Ignored files remain private local state, not safe storage for secrets. Ignore rules are defense-in-depth and do not authorize sensitive material to be placed in the repository.

## Current capabilities

The checkout provides these experimental capabilities for disposable testing. They are not stable public APIs or a supported installed CLI.

| Area | Implemented behavior | Contract and limits |
| --- | --- | --- |
| Feature readiness | Read-only `check --feature` for the selected runtime, filesystem, process, or tool prerequisites | [CLI](docs/cli.md); Python 3.11+, informational OS details, separate release evidence |
| Deployment initialization | Guided `init`, saved `plan init`, exact-plan `apply` and `verify`; creates a minimal TOML file and four documents | [Canonical documents](docs/canonical-documents.md); no infrastructure discovery |
| Guided inventory | Explicit Nmap discovery/inspection plans, offline XML import, cited local model lookup, and reviewed catalog snapshots | [Inventory](docs/inventory.md); optional active probing, no automatic network selection or device configuration |
| Configuration | Internal schema-1 layered TOML resolution with type checks, source tracking, and contained workspace-path resolution | [Configuration](docs/configuration.md); no public resolver command or schema migration |
| Guided helper setup | Offline prerequisite checks and exact-plan creation/verification of a new mode-`0600` helper settings file | [Setup](docs/setup.md); explicit choices and approval, no overwrites, package installation, or profile changes |
| Core lifecycle | Exact-plan install, local update, removal, verification, replay checks, and bounded failure recovery; source-only guided setup script | [Installation](docs/installation.md); explicit roots and local artifacts |
| Guided updates | Local candidate checking and planning; exact-plan application with plan-ID confirmation | [CLI](docs/cli.md); no remote update discovery |
| Shell integration | Reversible Bash/Zsh profile blocks with profile-mode and selected-source verification; configurable navigation/assistant helpers and optional prompt/history/highlighting/aliases | [Shell integration](docs/shell-integration.md); explicit opt-in, fixed source dependency coverage; third-party highlighting needs a fresh shell to undo |
| Operational helpers | Exact-plan configured repository synchronization, numeric-IP reachability, direct or SSH-relayed wake requests | [Helper setup](docs/helpers.md); separate deployment-owned TOML, explicit execution approval, no automatic publication or verified power state |
| Byte Care | Explicit `doctor` reports, local storage, and optional reviewed GitHub create/comment transport | [Byte Care](docs/byte-care.md); no automatic collection or submission |
| Codex guidance | Repository `AGENTS.md`, configured advisory SessionStart hook, and a first-session guide | [Codex integration](docs/codex-integration.md); no Byte skill or plugin package |
| GitHub workflow guidance | Reusable instructions for scoped changes, truthful PRs, checks on the reviewed commit, and verified branch cleanup | [GitHub workflow](docs/github-workflow.md); advisory, with no automatic publication or granted access |
| Troubleshooting guidance | Evidence labels, focused diagnostic checks, correction handling, and optional investigation checkpoints | [Troubleshooting](docs/troubleshooting.md); advisory, with no automatic collection or completed live assistant acceptance evidence |
| Candidate validation | Deterministic artifact and archive builders, integrity/privacy gates, and unit tests | [Release checklist](docs/release-checklist.md); manual evidence is still required |
| Container testing | Ubuntu 24.04 x86_64 recipe for unit tests and disposable candidate lifecycle rehearsals | [Dev container](docs/dev-container.md); container evidence does not replace native platform or fresh-user review |

`byte remove --deployment-root` is a read-only preservation check. Installed Core removal uses `plan remove` and `apply`; deployment-owned documents are preserved.

The [readiness and release-evidence matrix](docs/support-matrix.md) separates feature prerequisites from automated coverage and required native acceptance. OS names, releases, and architectures do not form a runtime allowlist; a ready feature still requires its exact operation checks and approval.

## Inspect the source checkout

For a quick terminal inspection with Git for cloning and Python 3.11 or later within Python 3:

```text
git clone https://github.com/kodiakdirus/byte-core.git
cd byte-core
./bin/byte --help
./bin/byte check
python3 -m unittest discover -s tests
```

Run these commands one at a time. If `check` reports `prerequisites unavailable`, stop before lifecycle operations and consult the [first-session troubleshooting guide](docs/getting-started.md#when-something-does-not-work). The [CLI contract](docs/cli.md) explains exact plans and exit statuses; the [installation contract](docs/installation.md) explains ownership and recovery. The repeatable [v0.1 release checklist](docs/release-checklist.md) remains blocked on recorded platform evidence and an independent fresh-user review.

## Remaining release work

- Complete isolated native Kubuntu 26.04 x86_64 lifecycle evidence under [issue #36](https://github.com/kodiakdirus/byte-core/issues/36). Detection and fixture coverage are implemented; no native Kubuntu CI runner or passed acceptance record is claimed.
- Record reviewed manual evidence for the required native acceptance targets, including preservation, backout, and offline behavior.
- Complete an independent fresh-user review and resolve its findings under [issue #5](https://github.com/kodiakdirus/byte-core/issues/5).
- Resolve remaining acceptance criteria and implementation gaps, review the exact candidate, and pass the final release gate before approving `v0.1.0`.

The release ledger contains two pending platform targets—Kubuntu 26.04 x86_64 and macOS 26 arm64—and a separate pending independent review. Ubuntu 24.04 and macOS 15 are no longer required native acceptance targets; their available capabilities may still run. Native Windows lifecycle remains future work; a Python-only runtime check can pass there, but no native backend or release date is committed. Remote update discovery, automatic diagnostic collection/reporting, configuration migration, artifact signing, package-manager installation, and production support remain unavailable. Component contracts describe remaining limits, including concurrent filesystem changes, shell source coverage, Byte Care version reporting, and live Codex hook evidence.

The first bootstrap release, [`v0.0.1`](https://github.com/kodiakdirus/byte-core/releases/tag/v0.0.1), is published as a pre-release with no release assets. It records the repository bootstrap and is not a functional Byte Core release.

## Non-goals for v0.1

Byte Core v0.1 is not intended to provide:

- full configuration management;
- unattended network discovery or automatic device configuration;
- credential storage;
- automatic remote infrastructure mutation;
- multi-administrator or centrally managed enterprise operation;
- a web interface;
- native PowerShell deployment;
- anonymous telemetry; or
- automatic patch deployment.

See [roadmap issue #1](https://github.com/kodiakdirus/byte-core/issues/1) for the maintained architecture and release roadmap.

## Contributing

Intentional local changes are indexed in the [fork divergence log](docs/fork-divergence.md), with rationale, validation, limitations, and upstream disposition for maintainer review.

Byte Core is currently in a sole-contributor bootstrap stage, but thoughtful future participation is welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes.

Do not submit secrets, real infrastructure inventory, private transcripts, or private diagnostic data.

## Security

Do not report unpatched vulnerabilities in a public issue. Follow [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## License

Byte Core is licensed under the [Apache License 2.0](LICENSE).

Contributors retain ownership of their contributions. Intentional contributions are submitted under Apache-2.0 as described in [CONTRIBUTING.md](CONTRIBUTING.md).

## Independent project

Byte Core is an independent community project. It is not affiliated with or endorsed by OpenAI.
