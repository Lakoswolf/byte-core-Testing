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
| [FORK-001](#fork-001-guided-local-candidate-setup) | Guided local candidate setup | Implemented; included in fork PR #3 | Unverified |
| [FORK-002](#fork-002-launcher-prerequisite-checks) | Launcher prerequisite checks | Implemented; included in fork PR #3 | Unverified |
| [FORK-003](#fork-003-divergence-tracking-guidance) | Divergence tracking guidance | Implemented; committed | Unverified |
| [FORK-004](#fork-004-governance-basis-traceability) | Governance-basis traceability | Implemented; committed | Unverified |

## FORK-001: Guided local candidate setup

**Problem:** The first-session guide creates a five-file deployment skeleton, while experimental Core installation is a separate workflow. A reusable entry point can make a local installation trial easier to review and repeat.

**Implemented:** The source-only setup script offers a no-argument wizard with yes/no choices for continuing, a local candidate version, optional starter documents, confirmed locations, and preparation-only mode. It retains explicit command-line arguments and adds `--guided` and `--skip-init`. Repository mode accepts a GitHub repository/ref, downloads a fresh checkout pinned to a resolved commit, records source identity, and asks before using downloaded code. A standalone script can bootstrap source, and `--download-only` stops before downloaded-code execution. Existing checkouts and local unpublished work remain unchanged. It checks its Python interpreter and Core readiness, builds a local artifact, saves private install/init plans, requires each selected full plan ID, and applies and verifies each operation. It supports preparation-only use, refuses overlapping or existing target roots, and preserves plans and partial state for review. After installation, optional finish-setup offers basic helper choices or an existing TOML, a reviewed session entrypoint with persistent settings selection and PATH, separate exact-plan profile integration, and notebook-editor onboarding. `--finish-setup` verifies an existing install plan without reinstalling; `--starter-plan` optionally verifies the original starter files.

**Affected files:** `scripts/setup_byte_core.py`, `tests/test_setup_script.py`, `tests/test_setup_finish.py`, [helper setup](setup.md), [shell integration](shell-integration.md), [README](../README.md), [first-session guide](getting-started.md#experimental-installation-script-source-checkout-only), [installation contract](installation.md), and [candidate notes](release-notes/v0.1.0.md). The script and tests are source-checkout tooling and are excluded from candidate artifacts; the affected documentation is packaged.

**Validation:** Focused tests cover approval, cancellation, path refusal, plan drift, failure sequencing, and real lifecycle operations with fixture readiness. The full unit suite, candidate build, changed-public-file and artifact privacy scans, and whitespace checks passed for the implementation including FORK-002. Manual release acceptance remains pending.

**Limits and adoption:** This composes experimental commands; it does not install prerequisites, change the login shell, authenticate releases, or provide a supported installed CLI. Optional profile integration uses the existing shell engine and preserves backups; its custom wrapper binds only the entrypoint while installed imports remain covered by the installation plan. Earlier completed stages survive a later cancellation. Source downloads require Git, existing authentication, and a terminal; they do not hydrate submodules/LFS or synchronize existing checkouts. Install and init are separate operations, with no combined rollback. Upstream may adopt the orchestration independently of this log. Removing it requires removing its source-only tests and updating the linked documentation; deployment-owned files must remain preserved.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending. Depends on FORK-002 for the current complete launcher preflight. The guided-wizard and finish-setup refinements are included in fork pull request #3.

**Wizard validation:** All 60 setup-focused tests and all 427 unit tests passed. Tests cover yes/no parsing, cancellation, nonterminal refusal, custom and existing paths, overlapping targets, target changes during review, install-only mode, exact-plan approvals, and real lifecycle operations with fixture readiness. A terminal walkthrough with real prerequisite checks verified private preview plans and absent installation targets. Repository tests cover source/ref validation, download-only and cancellation paths, revision drift, dirty source, symbolic-link refusal, Git failures/timeouts, and isolated Git context. Standalone GitHub download and pinned-commit download-to-preview checks passed against published fork commit `d3072a1ba8ac8941afbf50cf119106d010a727ac`; the source record matched the clean checkout and installation targets stayed absent. That revision predates the wizard and readiness refinements; use the branch or commit containing this change to download the current implementation. Optional-setup tests cover verified-install reuse, malformed plans, preview-only behavior, independent approvals/cancellation, preservation of original profile bytes/modes/backups, existing settings, Bash/Zsh command lookup, quoted paths, and an explicitly selected editor using a mocked launch. A disposable Linux VM rehearsal verified helper publication, profile integration, persistent configuration selection, fresh interactive Bash command lookup, and enabled aliases while preserving the original test profile and backup. Real home migration and editor interaction were not exercised. The automated candidate gate passed. Native acceptance, live applications/network operations, and an independent fresh-user review remain pending; this refinement does not complete those records.

## FORK-002: Launcher prerequisite checks

**Problem:** A compatible versioned interpreter can run the setup script while the installed POSIX launcher would select an incompatible `python3` from `PATH`.

**Implemented:** The wrapper also runs the checkout's actual launcher with read-only `check`, using a 15-second timeout. After integration of upstream `912cdae`, this checks the launcher's Python and POSIX lifecycle prerequisites before preparation and again after all selected approvals. OS identity is informational and Git is no longer a lifecycle prerequisite. The source wrapper now follows the Python 3.11+ minimum without a Python 3 minor-version ceiling. Failure returns status `3` with guidance and applies no plan. The installation contract explicitly documents required and optional tools.

**Affected files:** `scripts/setup_byte_core.py`, `tests/test_setup_script.py`, [installation prerequisites](installation.md#prerequisites), [first-session guide](getting-started.md), [README](../README.md), and [candidate notes](release-notes/v0.1.0.md).

**Validation:** All 16 focused tests and all 375 unit tests passed. Explicit runtime-selection checks confirmed refusal with an incompatible `python3` on `PATH` and success with a compatible selection. Candidate building, privacy scans, and whitespace checks passed. This does not replace native platform acceptance or independent review.

**Limits and adoption:** Checks are point-in-time observations. Missing Python cannot be bootstrapped by a Python script. The wrapper does not install packages or edit `PATH`; the bare launcher can still fail before displaying readiness when Python is too old. This change currently builds on FORK-001. Removing it reopens the mismatch and requires corresponding documentation changes.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending.

## FORK-004: Governance-basis traceability

**Problem:** The external Technical & Analytical Assistance Standard can
influence a Byte activity without leaving a durable, bounded record of which
guidance, evidence state, freshness state, and outcome status informed it.

**Implemented:** The deployment-owned audit-log starter and contracts provide an
optional governance basis with standard identity, version, digest/blob,
addendum, controls, evidence classification, verification and validation basis,
freshness state, outcome status, and limitations. Byte does not retrieve the
external standard or make it a runtime dependency.

**Affected files:** `templates/canonical/audit-log.md`,
`docs/canonical-documents.md`, `docs/cli.md`,
`tests/test_canonical_documents.py`, and this divergence log.

**Validation:** Focused canonical-document tests, the full unit suite, public
template and documentation privacy scans, shell syntax checks, and whitespace
checks passed. The record is optional and manually maintained; it does not
prove that the external standard was followed or that a stated validation is
correct.

**Limits and adoption:** This is traceability metadata, not automatic
enforcement. Removing it requires reverting the starter fields, contract text,
test assertions, and this entry together. Upstream may adopt the terminology or
the audit-record shape independently.

**References:** Implementation commit: `368fd4e`. Upstream issue/PR references pending.

## FORK-003: Divergence tracking guidance

**Problem:** Exact diffs alone do not explain why a fork differs, which parts are independently useful, or whether upstream has adopted a change.

**Implemented:** This log provides stable IDs, bounded public summaries, implementation references, validation, limitations, and separate local/upstream states. Repository guidance requires future intentional differences to update it in the same change. Contribution and handoff documentation point here.

**Affected files:** This log, [repository guidance](../AGENTS.md#fork-divergence-record), [contribution guide](../CONTRIBUTING.md#changes-and-review), [GitHub handoff guide](github-workflow.md#leave-a-clear-handoff), [README](../README.md#contributing), and [candidate notes](release-notes/v0.1.0.md). As a document under `docs/`, this log is included by the existing candidate builder; the script and test paths named above refer to the source checkout only.

**Validation:** All 375 unit tests passed, including the focused candidate-artifact and Codex-guidance checks. Documentation review, relative-link checks in the checkout and candidate artifact, whitespace checks, candidate building, and privacy scans passed. This entry adds no executable behavior or automated enforcement and does not complete manual release acceptance.

**Limits and adoption:** Coverage starts at the stated baseline; upstream disposition must be checked rather than assumed. Upstream can adopt the code proposals without adopting fork bookkeeping. Backout removes this log and its guidance references together.

**References:** Implementation commit: `4b750981ca7b2c8ad2b41f15a8252a58d776aa23`. Upstream issue/PR references pending.
