# Byte Core readiness and release evidence

Byte Core is pre-alpha software without a supported functional release. Runtime readiness and release acceptance answer different questions: readiness checks the prerequisites for a selected feature; release acceptance records reviewed observations for an exact candidate.

## Feature readiness

`byte check --feature FEATURE` is read-only and defaults to `lifecycle`. Operating-system name, release, and architecture are informational. They do not form an allowlist, and an unknown label alone does not block a feature.

| Feature | Required capability |
| --- | --- |
| `runtime` | Python 3.11 or later in the Python 3 series |
| `lifecycle` | Runtime plus the current POSIX filesystem backend |
| `inventory` | Runtime plus POSIX secure file I/O for offline inventory work |
| `inventory-scan` | Offline inventory prerequisites plus an available Nmap executable |
| `setup` | Runtime plus POSIX secure file I/O |
| `helpers` | Runtime plus POSIX secure file I/O and process capabilities; configured executables are checked by the relevant settings or operation |
| `shell-bash` | Lifecycle prerequisites plus Bash |
| `shell-zsh` | Lifecycle prerequisites plus Zsh |
| `git` | Runtime plus an available Git executable with a parseable version |
| `reporting` | Runtime plus POSIX secure file I/O for saved reports |

A passing check returns exit 0. JSON retains `supported: true`, meaning the selected prerequisites passed, and includes the selected `feature`. Check statuses are `pass`, `fail`, or `info`. Missing prerequisites return exit 3; informational host details never grant operation approval. See the [CLI contract](cli.md#byte-check).

Python 3.11 is the minimum; newer Python 3 minor versions are not rejected solely because they are newer. CI exercises Python 3.11 through 3.14. That coverage is evidence for those versions, not a maximum runtime version or a guarantee about untested versions.

Git is required for Git operations, not ordinary initialization or filesystem lifecycle work. Nmap is required only for live inventory scans. The explicit `shell-bash` and `shell-zsh` readiness checks require the selected interpreter. Shell profile planning and file operations use lifecycle filesystem prerequisites, so configuration may be prepared before an interpreter is installed. Optional assistant executables, highlighters, device tools, repositories, and other configured resources retain their existing per-operation validation. An unrelated missing tool does not disable every feature.

Readiness does not prove that a particular destination is writable, that every filesystem honors the needed semantics, or that an operation will succeed. Exact plans, path ownership, modes, symlink restrictions, current-state validation, and postcondition checks remain enforced at the operation boundary. Byte does not install prerequisites, bypass a failed safety check, modify itself, or change settings during discovery. An assistant may explain a failure and prepare a separately reviewed change under the existing approval rules.

## Release acceptance targets

| Native target | Automated evidence | Required v0.1 manual record |
| --- | --- | --- |
| Kubuntu 26.04 LTS, `x86_64` | Identification and capability fixtures; no native Kubuntu hosted runner configured | Pending |
| macOS 26, Apple silicon (`arm64`) | GitHub Actions unit and Bash/Zsh launcher checks configured | Pending |

The independent fresh-user review remains separately pending. `release/v0.1/manual-evidence.json` requires exactly those two native platform records and the independent review. Ubuntu 24.04 and macOS 15 are no longer mandatory native acceptance targets; they may still run features whose prerequisites pass. Other OS releases and architectures are likewise evaluated by capability without being certified by a passing check.

The workflow also runs unit and launcher checks on Ubuntu 24.04. The optional [Ubuntu dev container](dev-container.md) exercises disposable candidate lifecycle, shell, and offline rehearsals. Container, fixture, virtual-machine, and emulated results must be labeled accurately; they cannot replace the required native observations or independent review.

The configured runner labels follow GitHub's [hosted-runner image inventory](https://github.com/actions/runner-images#available-images). CI configuration requires a passing run before it becomes evidence. Even passing checks do not establish every filesystem, hardware revision, local security policy, shell session, or live Codex integration behavior.

Before a functional v0.1 release, the [release checklist](release-checklist.md) still requires reviewed installation, verification, backout, preservation, and offline observations for the exact candidate on both native targets. A passing readiness check does not change the ledger. Historical observations remain tied to their recorded candidate and cannot establish the current candidate's acceptance.

## Kubuntu 26.04 identification and remaining evidence

Kubuntu identification remains useful for truthful release evidence under [issue #36](https://github.com/kodiakdirus/byte-core/issues/36). It is informational at runtime; failing to identify a flavor does not refuse otherwise available capabilities.

Linux identification reads standard operating-system metadata as data. `ID` and `VERSION_ID` produce a sanitized release label. `ID=kubuntu` or `ID=ubuntu` with explicit `VARIANT_ID=kubuntu` produces a Kubuntu label for the reported release. Display names and derivative relationships do not establish a flavor. Missing or malformed required identifiers become `unknown`; accepted identifiers contain lowercase ASCII letters, digits, dots, underscores, or hyphens, start with a letter or digit, and fit within 64 characters.

Identification does not invoke a package manager or inspect installed desktop packages. A Kubuntu desktop with only Ubuntu metadata therefore reports an Ubuntu label. Native acceptance review must independently establish the actual target, record how it was established, and preserve any difference from the informational label. A KDE session or Ubuntu ancestry alone does not establish native Kubuntu acceptance. Plain Ubuntu observations cannot be relabeled as Kubuntu.

macOS identification reports the major release from the standard platform API. Other or unrecognized OS identities remain `unknown`; this alone does not fail a capability check.

The source-only template is `release/v0.1/evidence/kubuntu-26.04-x86_64-template.md`. Required native installation, verification, backout, preservation, and offline observations remain pending. A passing host check or fixture does not complete that record.

## Windows and future backends

The Python-only `runtime` readiness check can pass on Windows. The current filesystem and process backends require POSIX capabilities; native Windows lifecycle and shell integration remain future work. The POSIX `bin/byte` launcher is not a native Windows launcher. A Windows backend needs a separate reviewed design for secure filesystem operations, process behavior, launchers, and acceptance evidence. No native Windows implementation, PowerShell deployment, or release date is committed.
