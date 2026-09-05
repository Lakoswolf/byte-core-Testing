# Byte Core

> **Status: pre-alpha repository bootstrap**

Byte Core is an independent community project exploring a safe, friendly, Codex-centered framework for self-managed infrastructure.

The repository has established its public foundation and initial configuration-ownership boundary. The v0.1 candidate is ready for supported-platform deployment testing, but no functional release or supported installed command-line interface exists yet. Installation and operational use are not currently supported.

## Start here

New to Byte? Follow [Your first session with Byte](docs/getting-started.md). Open a fresh checkout in Codex, use the supplied first message, and let Byte guide you through checking your computer and creating a disposable example deployment. The guide includes expected results, explanations of the generated documents, and a terminal alternative.

Byte Core supplies the commands, templates, and working rules; Codex provides the conversational interface. A deployment is a separate folder of operator-owned configuration and documents. Your first session explores that structure using fictional data, without connecting to infrastructure.

If you are reviewing a release candidate, continue with [deployment acceptance testing](docs/deployment-testing.md) after the introduction.

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
| Environment checks | Read-only `check` through a POSIX launcher and Python standard-library implementation | [CLI](docs/cli.md); Python 3.11–3.14 and the exact host matrix |
| Deployment initialization | Guided `init`, saved `plan init`, exact-plan `apply` and `verify`; creates a minimal TOML file and four documents | [Canonical documents](docs/canonical-documents.md); no infrastructure discovery |
| Configuration | Internal schema-1 layered TOML resolution with type checks and source tracking | [Configuration](docs/configuration.md); no public resolver command or schema migration |
| Core lifecycle | Exact-plan install, local update, removal, verification, replay checks, and bounded failure recovery | [Installation](docs/installation.md); explicit roots and local artifacts |
| Guided updates | Local candidate checking and planning; exact-plan application with plan-ID confirmation | [CLI](docs/cli.md); no remote update discovery |
| Shell integration | Reversible Bash/Zsh profile blocks and generic shell helpers | [Shell integration](docs/shell-integration.md); explicit opt-in, no package installation |
| Byte Care | Explicit `doctor` reports, local storage, and optional reviewed GitHub create/comment transport | [Byte Care](docs/byte-care.md); no automatic collection or submission |
| Codex guidance | Repository `AGENTS.md`, configured advisory SessionStart hook, and a first-session guide | [Codex integration](docs/codex-integration.md); no Byte skill or plugin package |
| Candidate validation | Deterministic artifact and archive builders, integrity/privacy gates, and unit tests | [Release checklist](docs/release-checklist.md); manual evidence is still required |

`byte remove --deployment-root` is a read-only preservation check. Installed Core removal uses `plan remove` and `apply`; deployment-owned documents are preserved.

The intended v0.1 host and runtime boundary, automated evidence, and remaining manual evidence are published in the [support matrix](docs/support-matrix.md). The matrix defines release targets without changing the repository's pre-alpha support status.

## Inspect the source checkout

For a quick terminal inspection with Git and Python 3.11 through 3.14:

```text
git clone https://github.com/kodiakdirus/byte-core.git
cd byte-core
./bin/byte --help
./bin/byte check
python3 -m unittest discover -s tests
```

Run these commands one at a time. If `check` reports `unsupported`, stop before lifecycle operations and consult the [first-session troubleshooting guide](docs/getting-started.md#when-something-does-not-work). The [CLI contract](docs/cli.md) explains exact plans and exit statuses; the [installation contract](docs/installation.md) explains ownership and recovery. The repeatable [v0.1 release checklist](docs/release-checklist.md) remains blocked on recorded platform evidence and an independent fresh-user review.

## Remaining release work

- Add explicit Kubuntu 26.04 x86_64 detection, coverage, and isolated lifecycle evidence under [issue #36](https://github.com/kodiakdirus/byte-core/issues/36). It is planned v0.1 work, not a currently accepted host.
- Record reviewed manual evidence for the supported target platforms, including preservation, backout, and offline behavior.
- Complete an independent fresh-user review and resolve its findings under [issue #5](https://github.com/kodiakdirus/byte-core/issues/5).
- Resolve remaining acceptance criteria and implementation gaps, review the exact candidate, and pass the final release gate before approving `v0.1.0`.

Remote update discovery, automatic diagnostic collection/reporting, configuration migration, artifact signing, package-manager installation, and production support remain unavailable. The component contracts describe narrower implementation limits, including configuration path validation, shell verification, and Byte Care version reporting.

The first bootstrap release, [`v0.0.1`](https://github.com/kodiakdirus/byte-core/releases/tag/v0.0.1), is published as a pre-release with no release assets. It records the repository bootstrap and is not a functional Byte Core release.

## Non-goals for v0.1

Byte Core v0.1 is not intended to provide:

- full configuration management;
- automatic network discovery;
- credential storage;
- automatic remote infrastructure mutation;
- multi-administrator or centrally managed enterprise operation;
- a web interface;
- native PowerShell deployment;
- anonymous telemetry; or
- automatic patch deployment.

See [roadmap issue #1](https://github.com/kodiakdirus/byte-core/issues/1) for the maintained architecture and release roadmap.

## Contributing

Byte Core is currently in a sole-contributor bootstrap stage, but thoughtful future participation is welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes.

Do not submit secrets, real infrastructure inventory, private transcripts, or private diagnostic data.

## Security

Do not report unpatched vulnerabilities in a public issue. Follow [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## License

Byte Core is licensed under the [Apache License 2.0](LICENSE).

Contributors retain ownership of their contributions. Intentional contributions are submitted under Apache-2.0 as described in [CONTRIBUTING.md](CONTRIBUTING.md).

## Independent project

Byte Core is an independent community project. It is not affiliated with or endorsed by OpenAI.
