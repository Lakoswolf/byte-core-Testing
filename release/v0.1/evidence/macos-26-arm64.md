# macOS 26 arm64 manual evidence

Status: passed manual deployment-candidate test.

Tested commit: `5e653f9bef37d26ff83b3844ceaeabb17b00547b`
Candidate archive SHA-256: `b5cef86ed4863a39b04aad8b3afe68fb66697a50efd557957599c792a0e7033e`
Runtime: macOS 26.6.2 (build 25G83), arm64; Python 3.13.15; Git 2.50.1
Shell: Zsh 5.9

## Installation

Completed the reviewed-checkout, deterministic build, package, extraction, host check, fictional deployment initialization, exact-plan Core installation, and disposable Zsh integration steps from the deployment-candidate guide. The extracted candidate reported the `macos/arm64/macos/26` target as supported. Initialization, installation, and shell integration completed successfully.

## Verification

The initialization, Core installation, and shell plans verified successfully. Reapplying the exact Core installation plan reported `already_installed`.

## Backout

Exact-plan Zsh removal verified successfully and restored the disposable profile to its original absent state. Exact-plan Core removal verified successfully, removed the disposable Core and state roots, and reported `already_removed` when replayed.

## Preservation

The complete before-and-after SHA-256 inventory for all fictional deployment-owned documents was byte-for-byte identical after Core removal. The fictional notebook sentinel remained present and unchanged.

## Offline

Repeated the host check, initialization, installation, Zsh integration, and Core removal lifecycle under a macOS `sandbox-exec` profile with `deny network*`. A loopback connection attempt was rejected by operating-system policy, and every required offline lifecycle command completed and verified successfully.

## Limitations

The macOS system Python was below the supported range. Testing used an isolated Python 3.13 environment placed first on `PATH`, as required by the documented Python 3.11-through-3.14 runtime contract. No candidate-specific limitation was observed.
