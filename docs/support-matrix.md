# Byte Core v0.1 support matrix

Byte Core is pre-alpha software without a supported functional release. This matrix defines the host combinations the v0.1 implementation and release gate are intended to validate; it is not a production-support promise.

Optional [guided inventory](inventory.md) uses this host check for live Nmap execution. The core prerequisite check does not require Nmap; missing Nmap refuses only live inventory scanning. Offline import and catalog tests do not establish live discovery, manufacturer capability, or native platform acceptance evidence.

## Initial host boundary

| Operating system | Architecture | Shell coverage | Automated gate | v0.1 target |
| --- | --- | --- | --- | --- |
| Ubuntu 24.04 LTS | x86_64 | Bash launcher smoke test; Zsh optional and not installed by Byte | Configured in GitHub Actions | Supported target |
| Kubuntu 26.04 LTS | x86_64 | Native Bash launcher and lifecycle evidence pending; Zsh optional | Detection and refusal fixtures run in the existing CI suite; no native Kubuntu runner configured | Supported target; native acceptance pending |
| macOS 15 | Apple silicon (`arm64`) | Bash and Zsh launcher smoke tests | Configured in GitHub Actions | Supported target |
| macOS 26 | Apple silicon (`arm64`) | Bash and Zsh launcher smoke tests | Configured in GitHub Actions | Supported target |
| Other Linux distributions | Any | Not established | None | Unsupported |
| Plain Ubuntu 26.04 without the Kubuntu evidence below | Any | Not established | Deterministic refusal tests | Unsupported |
| Linux | `arm64` or other architectures | Not established | None | Unsupported |
| Other or unrecognized macOS releases | Apple silicon (`arm64`) | Not established | Deterministic refusal tests | Unsupported |
| macOS | Intel (`x86_64`) | Not established | None | Unsupported |
| Windows, BSD, appliance operating systems, and unknown hosts | Any | Not applicable | Deterministic refusal tests | Unsupported |

`byte check` recognizes macOS and Linux separately from approving a complete operating-system release and architecture combination. A recognized platform with an unapproved release or architecture returns status 3 and identifies the unsupported combination without guessing compatibility.

## Runtime prerequisites

- Python 3.11 through 3.14 are the initial CI matrix. Python 3.11 is the minimum runtime; later Python 3 versions are not claimed until exercised by CI.
- Git must be available as `git` and return a parseable dotted numeric version. Byte Core does not yet depend on a narrower Git feature-version floor.
- The launcher requires a POSIX process environment and `/bin/sh` behavior. Bash is exercised on the configured Ubuntu and macOS runners; native Kubuntu acceptance remains pending. Zsh is exercised on supported macOS runners, where it is native; Linux users may choose to install Zsh independently, but Byte does not require or install it.
- Shell enhancements such as syntax highlighting are optional. The experimental shell lifecycle includes them only when a Zsh user supplies an explicit existing source file. Byte does not make them a prerequisite or install the package.
- Runtime operation is standard-library-first and offline. CI action setup may access GitHub infrastructure; Byte lifecycle commands do not require network access.

## Evidence boundary

The support-matrix workflow is configured to prove unit behavior and launcher smoke tests on disposable GitHub-hosted runners. Evidence requires a passing workflow run; configuration alone is not a passing result. Even a passing run does not prove every hardware revision, distribution derivative, filesystem, local security policy, package-manager configuration, or long-running deployment.

The pinned operating-system labels follow GitHub's [published hosted-runner image inventory](https://github.com/actions/runner-images#available-images). A later change in GitHub's `latest` aliases does not silently expand Byte Core's support boundary.

Before a functional v0.1 release, the release gate still requires recorded manual installation, verification, backout, preservation, and offline smoke-test evidence on the supported target platforms. Until that evidence and every other release criterion are complete, README language must continue to describe Byte Core as pre-alpha and unsupported for operational use.

The current ledger intentionally records all four targets as pending in `release/v0.1/manual-evidence.json`, separately from the pending independent fresh-user review. Runtime checks and the release checker share the exact target set in [`platform_support.py`](../src/byte_core/platform_support.py). A three-platform ledger or an Ubuntu 26.04 entry cannot substitute for Kubuntu. The final gate and record format are defined in the [release checklist](release-checklist.md); no pending entry is support evidence.

The optional [Ubuntu dev container](dev-container.md) exercises Ubuntu 24.04 x86_64 user-space behavior and disposable lifecycle tests. Container or emulated results must be labeled as such; they do not replace native platform observations, live Codex integration, or an independent fresh-user review. The dev-container recipe does not extend the CI matrix or complete any evidence-ledger entry.

## Kubuntu 26.04 identification and remaining evidence

[Issue #36](https://github.com/kodiakdirus/byte-core/issues/36) requires explicit Kubuntu 26.04 x86_64 support and isolated native lifecycle testing before v0.1. Detection, deterministic tests, and a pending ledger entry are implemented. Native lifecycle acceptance and release evidence remain pending; these code changes do not establish a functional release.

Linux identification reads standard operating-system release metadata as data. `ID`, `VERSION_ID`, and optional `VARIANT_ID` provide programmatic identifiers; display names and derivative relationships alone do not establish a flavor. Missing or malformed required identifiers become `unknown`. Identifiers must be lowercase ASCII letters, digits, dots, underscores, or hyphens, start with a letter or digit, and fit within 64 characters. See the [os-release specification](https://manpages.ubuntu.com/manpages/resolute/man5/os-release.5.html).

The exact `kubuntu/26.04` release identity requires one of these criteria, followed by the separate `x86_64` architecture check:

- `ID=kubuntu` and `VERSION_ID=26.04`.
- `ID=ubuntu`, `VERSION_ID=26.04`, and `VARIANT_ID=kubuntu`.
- `ID=ubuntu`, `VERSION_ID=26.04`, no `VARIANT_ID` field, and an exact local package record showing `kubuntu-desktop` for `amd64` fully installed, with no package error flag and either install or hold selection.

The package fallback queries only `kubuntu-desktop:amd64` using `/usr/bin/dpkg-query`, the fixed `/var/lib/dpkg` database, disabled paging, a two-second timeout, and a minimal locale-controlled environment. It accepts only one successful exact record of at most 1,024 bytes. An unavailable query, malformed or extra output, another architecture, or an unpacked, broken, or removed package provides no flavor evidence. An explicitly different or malformed `VARIANT_ID` blocks the fallback. This query neither installs packages nor contacts package repositories. The [dpkg-query manual](https://manpages.debian.org/trixie/dpkg/dpkg-query.1.en.html) defines the queried package fields and status semantics.

This criterion identifies an installed Kubuntu desktop environment, including an Ubuntu installation converted with the [Kubuntu desktop metapackage](https://packages.ubuntu.com/resolute/kubuntu-desktop); it does not prove which installation image was originally used. A KDE session, `ID_LIKE=ubuntu`, or a Kubuntu display name alone never qualifies. Removing the metapackage may therefore make an otherwise customized desktop unrecognized. Plain Ubuntu 26.04 remains `ubuntu/26.04` and unsupported; Ubuntu 24.04 detection retains its existing boundary. Other Kubuntu versions and architectures remain unsupported.

No GitHub-hosted Kubuntu label is assumed. Existing hosted runners exercise fictional metadata and package-query fixtures, including refusal cases, while the [Kubuntu evidence template](../release/v0.1/evidence/kubuntu-26.04-x86_64-template.md) requires separately authorized native installation, verification, backout, preservation, and offline observations. A container, an emulated environment, a fixture, or a passing host check does not complete that record.

## Expanding support

A new host combination becomes a supported target only through a reviewed change that adds deterministic detection, automated coverage where feasible, documented manual evidence requirements, and known limitations. Recognition by `platform.system()` or `platform.machine()` alone is not evidence of support.
