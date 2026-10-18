# Kubuntu 26.04 x86_64 automated candidate observations

Status: partial automated observations awaiting review; not a passed manual platform record.

Observed on: 2026-09-06 UTC
Tested implementation commit: `faf2c9cc312dfe1cc3dc633c39f67bb2a27b9908`
Candidate archive SHA-256: `5ea13c3c8732362618cd8e5b72b0ab2f55e4d37882b19ba9257f35bf6c4c1192`
Runtime: Python 3.14; Git 2.53.0; Bash and optional Zsh exercised.

## Environment

The host check reported `linux/x86_64/kubuntu/26.04` as supported. A separate bounded check confirmed that the qualifying flavor criterion was the installed Kubuntu desktop metapackage; no raw package record was retained. The smoke test used the native host userspace inside a fresh user/network namespace, without a container image or emulation. Child processes used a minimal environment and disposable home, configuration, cache, state, runtime, and temporary roots. Only fresh fictional settings, profiles, deployment documents, and public release fixtures were used.

The same packaged smoke test also passed separately in the Ubuntu 24.04 x86_64 dev container with networking disabled and a read-only source mount. Both runs produced the archive digest above. Two additional independent local builds and normalized archives were byte-identical to that digest.

## Installation

The extracted candidate launcher passed its host check. Fictional initialization, verification, and exact replay passed. Candidate Core installation, verification, and exact replay passed in separate disposable Core and state roots. Optional helper setup passed readiness checks, refused an incorrect approval ID without creating settings, created the exact approved TOML with mode `0600`, verified it, and refused overwriting it on repeated apply.

## Verification

The packaged CLI updated between the two existing public fictional release fixtures, then passed verification and replay. This exercises the native update engine, but is not an upgrade between two complete candidate archives or tagged releases. Bash and Zsh loaded the packaged helpers and validated the fictional settings. Managed profile integration, verification, replay, and explicit shell sourcing passed for both shells.

The implementation's 359-test suite passed locally, in the offline Ubuntu container, and natively inside a temporary user/network namespace with disposable home settings. It includes deterministic refusal, source/profile mode drift, malformed hook input, non-UTF-8 profile preservation, oversized-result refusal, and injected interruption/backout scenarios. These automated tests do not substitute for live Codex behavior or manual interruption observations.

All 16 CI checks passed for the tested implementation commit: the [support matrix run](https://github.com/kodiakdirus/byte-core/actions/runs/34014370403) covered the configured Ubuntu/macOS and Python combinations plus shell launchers, and the [privacy gate run](https://github.com/kodiakdirus/byte-core/actions/runs/34014370399) passed. These are automated hosted-runner observations, not manual platform acceptance.

## Backout

Exact-plan shell removal and verification passed for Bash and Zsh, restoring each fictional profile's original bytes. Exact-plan Core removal, verification, and replay passed. Removal of the separate fixture-updated installation passed. Only the smoke invocation's newly created fictional tree was discarded after all checks succeeded.

## Preservation

Before/after hashes of every fictional deployment file matched, including the added notebook sentinel, through the fixture update and final removal. Unrelated fictional shell profile bytes were unchanged after removal. No operational deployment data or personal profiles were part of the test.

## Offline

The native command used `unshare --user --map-root-user --net` to create a temporary isolated network namespace for the entire smoke process and its children. It did not change host firewall or network policy. The Ubuntu container used `--network none`. No network access was required by the successful candidate lifecycle, helper setup, or fixture update stages.

## Limitations

These observations do not complete issue #36 or its manual ledger entry. Remaining acceptance includes review of these observations, a full candidate-to-candidate/tagged-version update exercise, manual interruption/recovery observations, and live Codex behavioral and degraded-integration scenarios. Interactive shell/application behavior remains unvalidated. The independent fresh-user review must be performed by someone who did not implement the feature. Ubuntu and both macOS manual platform records also remain pending.

The ordinary candidate gate passed descriptor integrity, complete artifact privacy, and ledger validation. The final gate with `--require-complete` correctly refused with `manual_evidence_pending`. No `v0.1.0` tag or functional release is established by this record. Review the exact tested commit, artifact digest, and remaining criteria before promoting any evidence to passed.
