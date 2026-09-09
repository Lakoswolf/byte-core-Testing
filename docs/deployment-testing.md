# Byte Core 0.1.0 deployment-candidate testing

This guide is the public handoff for manual native acceptance testing. It uses a fresh checkout, a deterministic candidate artifact, disposable fictional roots, and exact plans. It does not install Byte into operating-system directories, require elevated privileges, or claim that 0.1.0 has been released.

If this is your first encounter with Byte, begin with [Your first session with Byte](getting-started.md). It explains the project, provides a Codex-guided introduction, and walks through a small example before this full acceptance test. Start this test with a fresh disposable root after completing that introduction.

Use only a disposable test environment. Do not substitute real deployment configuration, inventory, credentials, logs, or documentation.

## Required native acceptance targets

- Kubuntu 26.04 LTS on `x86_64`, using Bash
- macOS 26 on Apple silicon (`arm64`), using Zsh

Python 3.11 or later within Python 3 must be available; CI currently exercises 3.11 through 3.14. Git is required for checkout/review operations, not ordinary lifecycle work. Optional Zsh syntax highlighting is not part of this smoke test and is never installed by Byte.

These are the required release-evidence targets, with both native acceptance records still pending. Readiness uses feature capabilities rather than OS labels; successful rehearsals elsewhere are useful but cannot replace these records. Kubuntu evidence requires the [documented flavor identification](support-matrix.md#kubuntu-2604-identification-and-remaining-evidence); plain Ubuntu observations, KDE session labels, and fixture-only detection tests do not substitute. No native Kubuntu CI runner is configured. Keep the source checkout for build scripts and evidence templates, which are not included in the candidate archive.

## 1. Prepare a reviewed checkout

Clone the public repository, check out the exact commit under review, and confirm that the checkout is clean:

```text
git clone https://github.com/kodiakdirus/byte-core.git
cd byte-core
git checkout COMMIT_SHA
git status --short
python3 -m unittest discover -s tests
./bin/byte check --format json
```

Record the full `COMMIT_SHA`, Python version, Git version, operating-system version, architecture, and shell. `byte check --feature lifecycle` must report `ready`, and the informational host details must be recorded accurately. For a required native record, independently confirm the target identity; do not relabel a different host. Other capable hosts may run a rehearsal with its actual environment clearly identified.

## 2. Build and package the candidate

Create one new disposable root and build the unpacked artifact:

```text
BYTE_TEST_ROOT=$(mktemp -d)
python3 scripts/build_release_artifact.py \
  --version 0.1.0 \
  --output "$BYTE_TEST_ROOT/byte-core-0.1.0"
python3 scripts/check_v01_release.py \
  --artifact "$BYTE_TEST_ROOT/byte-core-0.1.0" \
  --evidence release/v0.1/manual-evidence.json
python3 scripts/package_release_candidate.py \
  --artifact "$BYTE_TEST_ROOT/byte-core-0.1.0" \
  --output "$BYTE_TEST_ROOT/byte-core-0.1.0.tar.gz"
```

Record the archive SHA-256 printed by the packager. On Kubuntu, independently verify it with `sha256sum`. On macOS, use `shasum -a 256`.

Extract the archive into a new directory and use the extracted copy for every remaining step:

```text
mkdir "$BYTE_TEST_ROOT/extracted"
tar -xzf "$BYTE_TEST_ROOT/byte-core-0.1.0.tar.gz" \
  -C "$BYTE_TEST_ROOT/extracted"
BYTE_CANDIDATE="$BYTE_TEST_ROOT/extracted/byte-core-0.1.0"
"$BYTE_CANDIDATE/bin/byte" --help
"$BYTE_CANDIDATE/bin/byte" check --format json
```

## 3. Initialize fictional deployment documents

Every plan is private local test state because it contains absolute paths.

```text
"$BYTE_CANDIDATE/bin/byte" plan init \
  --deployment-root "$BYTE_TEST_ROOT/deployment" \
  > "$BYTE_TEST_ROOT/init-plan.json"
"$BYTE_CANDIDATE/bin/byte" apply \
  --plan "$BYTE_TEST_ROOT/init-plan.json"
"$BYTE_CANDIDATE/bin/byte" verify \
  --plan "$BYTE_TEST_ROOT/init-plan.json"
```

Review the four generated canonical documents. Add one fictional deployment-owned sentinel line to `notebook.md`, then record its SHA-256 before lifecycle testing.

## 4. Install and verify Core in disposable roots

```text
"$BYTE_CANDIDATE/bin/byte" plan install \
  --artifact-root "$BYTE_CANDIDATE" \
  --core-root "$BYTE_TEST_ROOT/core" \
  --state-root "$BYTE_TEST_ROOT/state" \
  --core-version 0.1.0 \
  > "$BYTE_TEST_ROOT/install-plan.json"
"$BYTE_CANDIDATE/bin/byte" apply \
  --plan "$BYTE_TEST_ROOT/install-plan.json"
"$BYTE_CANDIDATE/bin/byte" verify \
  --plan "$BYTE_TEST_ROOT/install-plan.json"
"$BYTE_CANDIDATE/bin/byte" apply \
  --plan "$BYTE_TEST_ROOT/install-plan.json"
```

The first apply must report `installed`, verification must report `verified`, and replay must report `already_installed`.

## 5. Test reversible shell integration

Use a disposable home, not the tester's real profile:

```text
mkdir "$BYTE_TEST_ROOT/test-home"
BYTE_TEST_SHELL=zsh
```

Use `BYTE_TEST_SHELL=bash` for the Kubuntu target. Then run:

```text
"$BYTE_CANDIDATE/bin/byte" shell plan \
  --home-root "$BYTE_TEST_ROOT/test-home" \
  --shell "$BYTE_TEST_SHELL" \
  --shell-script "$BYTE_CANDIDATE/shell/byte-shell.sh" \
  > "$BYTE_TEST_ROOT/shell-plan.json"
"$BYTE_CANDIDATE/bin/byte" shell apply \
  --plan "$BYTE_TEST_ROOT/shell-plan.json"
"$BYTE_CANDIDATE/bin/byte" shell verify \
  --plan "$BYTE_TEST_ROOT/shell-plan.json"
"$BYTE_CANDIDATE/bin/byte" shell plan-remove \
  --home-root "$BYTE_TEST_ROOT/test-home" \
  --shell "$BYTE_TEST_SHELL" \
  > "$BYTE_TEST_ROOT/shell-remove-plan.json"
"$BYTE_CANDIDATE/bin/byte" shell remove \
  --plan "$BYTE_TEST_ROOT/shell-remove-plan.json"
"$BYTE_CANDIDATE/bin/byte" shell verify \
  --plan "$BYTE_TEST_ROOT/shell-remove-plan.json"
```

Review the version-2 install plan's profile mode and selected source-file digests/modes before applying it. Confirm the profile is absent again when Byte created it. If testing an existing fictional profile, confirm unrelated content and its mode are unchanged. The source snapshot covers the explicit entrypoint, optional highlighter, and selected packaged native asset; it does not recursively cover arbitrary imports or prevent changes after verification. Keep the candidate source files unchanged during this test.

For optional helper-configuration acceptance, follow [Guided helper setup](setup.md) with newly prepared fictional settings and a separate absent destination under the disposable test root. Record prerequisite checks, exact-plan approval, mode-`0600` creation, verification, and preservation of existing files. Setup does not perform the shell profile steps above, execute applications, or contact devices. Retain or back out the new settings file according to the reviewed setup plan; later-edited files must be preserved.

## 6. Remove Core and prove preservation

```text
"$BYTE_CANDIDATE/bin/byte" plan remove \
  --manifest "$BYTE_TEST_ROOT/state/installation.json" \
  --preserve-root "$BYTE_TEST_ROOT/deployment" \
  > "$BYTE_TEST_ROOT/remove-plan.json"
"$BYTE_CANDIDATE/bin/byte" apply \
  --plan "$BYTE_TEST_ROOT/remove-plan.json"
"$BYTE_CANDIDATE/bin/byte" verify \
  --plan "$BYTE_TEST_ROOT/remove-plan.json"
"$BYTE_CANDIDATE/bin/byte" apply \
  --plan "$BYTE_TEST_ROOT/remove-plan.json"
```

The first removal must report `removed`, verification must report `verified`, and replay must report `already_removed`. The disposable Core and state roots must be absent. Recalculate the deployment document hashes and prove the fictional sentinel and all other deployment-owned bytes are unchanged.

For a replay refusal check, move only this exercise's fictional deployment folder to a new sibling path after successful removal, preserving its files. Replay the same Core removal plan: expect exit 4 with `preserved_root_changed`, not `already_removed`. Move the folder back to its exact planned path, then repeat verification and replay; expect `verified` and `already_removed`. Recheck the preserved bytes. The [preservation-root checks](installation.md#removal-planning) do not establish directory identity or historical document contents.

## 7. Prove offline behavior

Repeat the candidate check, initialization plan/verify, install plan/verify, shell plan/verify, and removal plan/verify while network access is disabled by a method appropriate to the disposable test environment. Record the method and result. Do not change firewall or network policy on an operational host merely to perform this test.

The GitHub Byte Care transport and explicit `inventory scan` path intentionally use the network and are excluded from this offline test. Do not use `--github-submit` or live scans here; scanner execution is covered with mocked results and bounded non-network child processes, and reporting uses mock-only tests. The optional [inventory walkthrough](inventory.md#offline-first-a-fictional-walkthrough) can exercise XML import, capability lookup, catalog publication, and verification offline using the source checkout's fictional fixtures.

## 8. Record evidence

Copy the matching template from `release/v0.1/evidence/`, replace every placeholder with fresh non-sensitive observations, and submit it through a focused pull request. Do not include usernames, home paths, hostnames, addresses, inventory, credentials, broad logs, or terminal transcripts.

The independent reviewer separately completes `fresh-user-review-template.md` from a fresh checkout without private assistance. A project implementer cannot self-certify that criterion.

The release ledger changes from `pending` to `passed` only after each record and the exact tested commit are reviewed. The final command is:

```text
python3 scripts/check_v01_release.py \
  --artifact "$BYTE_TEST_ROOT/byte-core-0.1.0" \
  --evidence release/v0.1/manual-evidence.json \
  --require-complete
```

It must remain blocked until both platform records and the independent review are present and reviewed. The ordinary candidate gate currently reports three pending entries; fixture or container success does not change those statuses.
