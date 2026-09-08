# Fork divergence log

This log records intentional local differences for an upstream maintainer to evaluate independently. It is a review index, not a release announcement, an upstream commitment, or an exhaustive comparison of repository history. Git diffs and commits remain the source of exact code changes.

Initial coverage begins with the setup-script changes against checkout baseline `d3072a1ba8ac8941afbf50cf119106d010a727ac`. Earlier differences, if any, have not been audited. This baseline identifies the local starting point; it is not evidence of the current upstream head. The entries below are implemented in this fork. Their upstream disposition remains unverified; a fork commit is not evidence of upstream adoption.

Fork review for FORK-001 through FORK-003: [pull request #3](https://github.com/Lakoswolf/byte-core-Testing/pull/3). This targets the fork's `main`, not the upstream repository; its current review and check state is available on the pull request.

## Maintaining the log

- Add a stable `FORK-NNN` entry for each distinct intentional difference in behavior, documentation, or repository guidance. Update an existing entry when refining the same change; do not create an entry for every edit or test run.
- Record the problem, implemented behavior, affected relative paths, validation, limitations, and an adoption or backout boundary. Keep this summary current in the same change as its implementation.
- Add exact commit references once committed and public issue or PR links once publication is authorized and verified. Until then, say that references are pending. Do not invent references or infer upstream acceptance from local tests.
- Track local state separately from upstream disposition. Useful local states are implemented, superseded, and removed; upstream states are unverified, proposed, accepted, and declined. Record evidence for a disposition change. Accepted requires verification of the integrated result, including partial or alternative implementations.
- Retain resolved entries with their final disposition and replacement references. Before removing a local difference after upstream adoption, compare the actual behavior and preserve any remaining work.
- Keep only public-safe engineering summaries and fresh fictional examples. Exclude personal runtime installations, deployment facts, absolute local paths, environment values, prompts, transcripts, and raw diagnostics. A test summary is evidence of the stated checks, not platform acceptance.

This is a manually maintained workflow supported by repository instructions. It has no automatic diff detector, publication action, or guarantee that every contributor will update it. For a handoff, review the current diff and log together; include new files that are still untracked, which plain `git diff` does not show. Prepare focused commits or PRs when authorized, then attach their references to the relevant entries. Follow the [GitHub workflow](github-workflow.md) for publication and integration checks.

## Index

| ID | Difference | Local state | Upstream disposition |
| --- | --- | --- | --- |
| [FORK-001](#fork-001-guided-local-candidate-setup) | Guided local candidate setup | Implemented; committed | Unverified |
| [FORK-002](#fork-002-launcher-prerequisite-checks) | Launcher prerequisite checks | Implemented; committed | Unverified |
| [FORK-003](#fork-003-divergence-tracking-guidance) | Divergence tracking guidance | Implemented; committed | Unverified |

## FORK-001: Guided local candidate setup

**Problem:** The first-session guide creates a five-file deployment skeleton, while experimental Core installation is a separate workflow. A reusable entry point can make a local installation trial easier to review and repeat.

**Implemented:** The source-only setup script takes an explicit candidate version and Core, state, deployment, and preparation paths. It checks its Python interpreter and Core readiness, builds a local artifact, saves private install/init plans, requires both full plan IDs, and applies and verifies each operation. It supports preparation-only use, refuses overlapping or existing target roots, and preserves plans and partial state for review.

**Affected files:** `scripts/setup_byte_core.py`, `tests/test_setup_script.py`, [README](../README.md), [first-session guide](getting-started.md#experimental-installation-script-source-checkout-only), [installation contract](installation.md), and [candidate notes](release-notes/v0.1.0.md). The script and tests are source-checkout tooling and are excluded from candidate artifacts; the affected documentation is packaged.

**Validation:** Focused tests cover approval, cancellation, path refusal, plan drift, failure sequencing, and real lifecycle operations with fixture readiness. The full unit suite, candidate build, changed-public-file and artifact privacy scans, and whitespace checks passed for the implementation including FORK-002. Manual release acceptance remains pending.

**Limits and adoption:** This composes experimental commands; it does not install prerequisites, configure a shell, authenticate releases, or provide a supported installed CLI. Install and init are separate operations, with no combined rollback. Upstream may adopt the orchestration independently of this log. Removing it requires removing its source-only tests and updating the linked documentation; deployment-owned files must remain preserved.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending. Depends on FORK-002 for the current complete launcher preflight.

## FORK-002: Launcher prerequisite checks

**Problem:** A compatible versioned interpreter can run the setup script while the installed POSIX launcher would select an incompatible `python3` from `PATH`.

**Implemented:** The wrapper also runs the checkout's actual launcher with read-only `check`, using a 15-second timeout. This checks the launcher's Python, Git, POSIX execution, and host support before preparation and again after both approvals. Failure returns status `3` with guidance and applies neither plan. The installation contract explicitly documents required and optional tools.

**Affected files:** `scripts/setup_byte_core.py`, `tests/test_setup_script.py`, [installation prerequisites](installation.md#prerequisites), [first-session guide](getting-started.md), [README](../README.md), and [candidate notes](release-notes/v0.1.0.md).

**Validation:** All 16 focused tests and all 375 unit tests passed. Explicit runtime-selection checks confirmed refusal with an incompatible `python3` on `PATH` and success with a compatible selection. Candidate building, privacy scans, and whitespace checks passed. This does not replace native platform acceptance or independent review.

**Limits and adoption:** Checks are point-in-time observations. Missing Python cannot be bootstrapped by a Python script. The wrapper does not install packages or edit `PATH`; the bare launcher can still fail before displaying readiness when Python is too old. This change currently builds on FORK-001. Removing it reopens the mismatch and requires corresponding documentation changes.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending.

## FORK-003: Divergence tracking guidance

**Problem:** Exact diffs alone do not explain why a fork differs, which parts are independently useful, or whether upstream has adopted a change.

**Implemented:** This log provides stable IDs, bounded public summaries, implementation references, validation, limitations, and separate local/upstream states. Repository guidance requires future intentional differences to update it in the same change. Contribution and handoff documentation point here.

**Affected files:** This log, [repository guidance](../AGENTS.md#fork-divergence-record), [contribution guide](../CONTRIBUTING.md#changes-and-review), [GitHub handoff guide](github-workflow.md#leave-a-clear-handoff), [README](../README.md#contributing), and [candidate notes](release-notes/v0.1.0.md). As a document under `docs/`, this log is included by the existing candidate builder; the script and test paths named above refer to the source checkout only.

**Validation:** All 375 unit tests passed, including the focused candidate-artifact and Codex-guidance checks. Documentation review, relative-link checks in the checkout and candidate artifact, whitespace checks, candidate building, and privacy scans passed. This entry adds no executable behavior or automated enforcement and does not complete manual release acceptance.

**Limits and adoption:** Coverage starts at the stated baseline; upstream disposition must be checked rather than assumed. Upstream can adopt the code proposals without adopting fork bookkeeping. Backout removes this log and its guidance references together.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending.
