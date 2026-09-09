# Your first session with Byte

Start here if someone sent you Byte Core and you are wondering what to open or ask it to do. This introduction ends with a verified, disposable example deployment and an explanation of its five files. Byte Core remains pre-alpha; use only fictional data for this exercise.

## What you are opening

Byte Core is a framework for keeping infrastructure knowledge and changes explicit and reviewable. Its current implementation supplies local commands, starter documents, and rules for checking, planning, applying, verifying, and backing out changes.

There are three parts to your first session:

| Part | What it does |
| --- | --- |
| The `byte-core` checkout | Holds the reusable program, public documentation, and repository instructions. Open this folder in Codex. |
| Codex | Provides the conversation: explains Byte, runs bounded checks, and helps you review a proposed change. |
| A disposable deployment folder | Holds your fictional example configuration and documents, outside the checkout. Byte creates it only after you review the plan. |

The executable entry point is `./bin/byte` inside the checkout. There is no separate Byte application to launch, service to start, or Byte plugin to install. Initialization creates documents; it does not discover devices or configure infrastructure. Codex is optional for the commands themselves.

## 1. Get the checkout and open Codex

You need Python 3.11 or later within Python 3 and the current POSIX filesystem backend for this exercise. Git is needed to clone the repository, but not to initialize the example deployment. Run `byte check --feature lifecycle` before proceeding; the [readiness and release-evidence matrix](support-matrix.md) explains feature prerequisites separately from native acceptance targets. OS name, release, or architecture alone does not block the exercise.

The [Ubuntu dev container](dev-container.md) provides an isolated terminal environment for unit tests and this lifecycle walkthrough. It does not install Codex or establish native platform or conversational acceptance evidence.

In a terminal, choose a folder for public source projects and run these commands one at a time:

```sh
git clone https://github.com/kodiakdirus/byte-core.git
cd byte-core
```

If you already have a checkout, use it without cloning over it. For an assigned review, use the exact commit supplied by the maintainer; otherwise this is an introductory trial of the checkout you have.

Open the `byte-core` folder in your local Codex interface and start a conversation there. Select the folder containing `README.md`, `AGENTS.md`, and `bin/byte`. Keep real deployment folders out of this exercise. If you need to set up Codex itself, follow the [official OpenAI setup guide](https://learn.chatgpt.com/docs/quickstart); in the desktop app, select Codex for this coding workspace.

Codex discovers project guidance through `AGENTS.md`, as described in the [official instructions guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md). Byte's [integration contract](codex-integration.md) explains its optional advisory hook. The walkthrough does not depend on a hook message appearing or on changing your personal Codex settings.

## 2. Send this first message

Copy this fresh example request into the conversation:

```text
Byte, guide me through docs/getting-started.md for my first session.
Read this checkout's AGENTS.md and use its safety and ownership rules.
Explain what Byte does and confirm which checkout we are using.
Run ./bin/byte check --feature lifecycle and explain the result. If a
required capability is unavailable, stop setup and explain what is missing.
When the prerequisites pass, prepare a new disposable example outside the
checkout using only the public starter templates and fictional data.
Save an initialization plan, explain its exact targets and backout,
and wait for me to review it before applying it. After I approve,
apply that same saved plan, verify it, and explain the five files.
Do not read real deployment data, change my shell profile, install
system software, or publish anything. Stop after this introduction.
```

Byte should explain the checkout and check result first. `Result: ready` means the selected feature prerequisites passed; it does not certify native platform acceptance or production readiness. Missing prerequisites are a valid stopping point. Byte can explain them and prepare a separately reviewed remedy; it must not install tools or bypass checks automatically.

## 3. Review the proposed setup

When lifecycle prerequisites pass, Byte should create a new temporary parent folder and save a plan beside a still-absent `deployment` folder. The plan file records exact local paths, so keep it private and outside the repository. The temporary folder and saved plan are the only preparation writes.

Before you approve initialization, the explanation should identify:

- the exact new deployment folder, separate from the source checkout;
- the five files below, with no existing content to overwrite;
- the plan ID, which binds this specific proposed change; and
- the backout boundary: failed initialization cleans up only unchanged files created by that invocation, and preserves ambiguous state for review.

If the target is unclear or points to existing work, stop and resolve that first. Approval applies to this initialization only. Byte should then run `apply` against the saved plan and report `Result: initialized`, followed by `verify` against that same plan and `Result: verified`. If Codex cannot access the disposable location under your current permissions, use the terminal alternative below; broader access is not a prerequisite.

## 4. Understand what was created

Ask Byte to walk through these files in the disposable folder:

| File | What belongs here |
| --- | --- |
| `deployment.toml` | Configuration. The starter contains only `schema_version = 1`. |
| `manifest.md` | Declared components and relationships. It does not establish live device state. |
| `runbook.md` | Reviewed operating, verification, and recovery procedures. |
| `audit-log.md` | Completed changes, reasons, validation evidence, and backout outcomes. |
| `notebook.md` | Lessons, preferences, and unresolved questions. |

These copies belong to the deployment as soon as they are created. The public source templates remain Core-managed. Empty inventory is expected: Byte has not inspected your infrastructure and should not invent it.

For this introduction, read the files before editing them. Initialization verification checks their exact starter bytes; later edits intentionally make that original plan's verification fail. See the [document roles and validation boundary](canonical-documents.md) for how the documents are meant to evolve.

You have finished the first session when verification passes and you can locate and explain the five files. You have created a document skeleton, not installed Core or connected a live environment.

## Next: build a useful inventory

After the first-session exercise, the optional [guided inventory walkthrough](inventory.md) continues from the skeleton. Start with its fictional offline import to discover example devices, review a service hint, confirm a model, look up a cited example capability, and save a verified catalog. Ask Byte to explain and prepare each plan; it should help write the selection and capability inputs, then show you the proposed catalog for review.

Live discovery is a separate choice. It requires a reviewed explicit network range and optional Nmap; initialization never starts a scan. The backend preserves declared names and notes when later observations are reviewed using stable device IDs. It does not automatically research models on the web or configure hardware. This optional step is outside the first-message exercise's instruction to stop after initialization.

## Optional: configure your shell helpers

After the introductory exercise, ask Byte to prepare a deployment-owned helper configuration using the [guided setup workflow](setup.md). It should explain your choices for development directory, assistant application, optional shell presentation, and any explicitly selected devices or repositories. The supplied template starts with interactive features disabled and no operational targets.

```text
Byte, continue with docs/setup.md using fictional settings for this trial.
Explain the optional helpers and leave unknown choices unset. Prepare a
new private settings file outside Core, run setup check, and save a plan
for a separate new destination. Explain the checks, exact target, and
backout, then wait for my approval of that plan. After approval, apply
and verify it. Explain the next shell steps and stop before editing a
profile, launching an application, or contacting any device or repository.
```

Expect a readiness report first, followed by a saved plan with an `id`. After exact approval, successful application reports `settings_saved`, and verification reports `verified`. The destination preserves the prepared TOML and uses private mode `0600`. Missing configured prerequisites stop planning; unset optional features remain available for later configuration. The [settings reference](helpers.md#settings-reference) explains each choice.

You can validate that configuration and source the shell asset in a disposable Bash or Zsh session before deciding whether to install a profile block. Loading settings does not contact devices or synchronize repositories. Reachability, wake, and synchronization each have an offline plan followed by a separate approved execution step. These operations are outside the initialization rehearsal.

## Terminal alternative

Use this route if you prefer to run the commands yourself or Codex cannot run local tools. From the checkout, run each block separately in the same Bash or Zsh terminal. Stop on any unexpected result.

```sh
./bin/byte --help
./bin/byte check
```

Continue only after `Result: ready`. Create a disposable parent; leave its `deployment` child absent so initialization can create it:

```sh
BYTE_TUTORIAL_ROOT=$(mktemp -d)
```

If `mktemp` fails, stop. Save the plan before initialization so you can verify against it afterward:

```sh
./bin/byte plan init --deployment-root "$BYTE_TUTORIAL_ROOT/deployment" \
  > "$BYTE_TUTORIAL_ROOT/init-plan.json"
```

Open `init-plan.json` in a text editor to review the target, file list, and backout actions. Keep the checkout unchanged during this exercise. Then start the existing guided command:

```sh
./bin/byte init --deployment-root "$BYTE_TUTORIAL_ROOT/deployment"
```

The command displays the target, five files, backout, and plan ID. Confirm it matches the saved plan. To apply, paste the full displayed plan ID at the prompt and press Enter. Any different response cancels without creating the deployment. Successful initialization reports `Result: initialized`.

```sh
./bin/byte verify --plan "$BYTE_TUTORIAL_ROOT/init-plan.json"
```

Expect `Result: verified`. Read the files described above in your text editor. The temporary-root variable belongs to this terminal session; if you close it, recover the exact location from your local session before continuing rather than guessing a path.

## Experimental installation script (source checkout only)

For guided installation from a reviewed source checkout, run:

```sh
python3 scripts/setup_byte_core.py
```

To download fresh source from the fork before setup, run:

```sh
python3 scripts/setup_byte_core.py --from-repo
```

A standalone copy of this script also offers the download workflow when no adjacent Byte Core checkout exists. The default source is `Lakoswolf/byte-core-Testing` on GitHub, using its current default branch (`HEAD`). Override it explicitly when needed:

```sh
python3 scripts/setup_byte_core.py --from-repo \
  --repository Lakoswolf/byte-core-Testing --ref main
```

Repository selection accepts `OWNER/NAME` on github.com, not credential-bearing URLs. `--ref` accepts a branch, tag, or full commit SHA. The download requires Git and an interactive terminal. It uses existing Git credential configuration for private access; configure authentication separately rather than entering credentials into this script. Git environment overrides are not forwarded. Each Git operation has a five-minute timeout.

The script asks for an existing download parent and confirms the repository/ref before networking. It creates a private `byte-source-*` directory, fetches the requested revision into a new checkout, checks out the resolved commit in detached mode, and records the repository, requested ref, and full commit in `source.json`. Existing checkouts are untouched. Hooks and recursive submodule fetching are disabled; Git stderr is suppressed to avoid reproducing authentication diagnostics.

After the download it displays the commit and asks whether to use that revision's code. Declining retains the source for inspection and starts no setup. `--download-only` stops there without importing downloaded Python code. Continuing uses the current standalone wizard with the downloaded Core implementation and candidate builder, then follows the same location, preview, and exact-plan approvals below. The source is checked for local changes before handoff; keep it unchanged throughout setup. A commit identifies source, not release authenticity or native acceptance. Review and trust the selected repository before allowing its code to run.

Use `--source-parent` to propose the existing download parent. Every run creates fresh source rather than updating another checkout. Failed or interrupted downloads remain for inspection. Submodules, Git LFS hydration, package installation, publication, and installed-Core updates are outside this downloader. GitHub only supplies published commits: local changes must be committed and pushed before a download can include them. Downloading does not publish this wizard or other local work.

The wizard installs the current local candidate and optionally creates the five starter files described above. Byte Core remains experimental and unsupported for operational use. Python 3.11 or later in the Python 3 series and the current POSIX lifecycle backend are required; OS version labels do not gate readiness. The script builds from the selected source; it does not authenticate a release.

The wizard guides these choices:

1. Continue with experimental setup? The default is no.
2. Use the proposed local candidate version? The proposal comes from local release-note filenames, not a remote release check.
3. Create starter deployment documents too? Choose no to install Core alone and preserve an existing deployment.
4. Choose an existing preparation parent. The prompt offers your home folder; enter another absolute path if preferred. Suggested new children are `byte-core`, `byte-core-state`, and `byte-core-deployment` for program files, installation state, and starter documents. Confirm those locations or enter your own. Existing targets are preserved and require another location.
5. Only prepare plans for review? The default is yes. Choose no to continue to installation after plan review.
6. Confirm prerequisite checks and preparation. The script saves a private candidate and exact plans, then offers to display the complete plans.
7. If installing, review the saved plans and enter each full plan ID. These exact-plan approvals are required before any installation or initialization is applied. A yes/no response cannot replace them.

Enter `q`, `quit`, or `cancel` at wizard questions to stop; end of input also cancels. Invalid yes/no answers are repeated. Pressing Enter uses the displayed default. Interrupting stops further work and retains any preparation or partial state for review.

All paths are literal absolute paths: the script does not expand `~`, variables, or shell expressions. The preparation parent must already exist. The selected new roots must have existing parents, be disjoint, and remain outside the checkout and Git metadata. Selected symlinks and parent traversal are refused; existing parent aliases are canonicalized. The wizard checks these conditions before preparing files and again before applying plans. Existing installations require the separate [update workflow](installation.md#update-planning).

For explicit locations, the original command-line mode remains available:

```sh
python3 scripts/setup_byte_core.py --version 0.1.0 \
  --work-parent /absolute/existing/private-parent \
  --core-root /absolute/existing/private-parent/core \
  --state-root /absolute/existing/private-parent/state \
  --deployment-root /absolute/existing/private-parent/deployment
```

| Option | Behavior |
| --- | --- |
| `--from-repo` | Download fresh GitHub source before setup. Standalone use enables this automatically. |
| `--repository` | GitHub `OWNER/NAME`; defaults to `Lakoswolf/byte-core-Testing`. Also enables download mode. |
| `--ref` | Branch, tag, or full commit SHA; defaults to remote `HEAD`. |
| `--source-parent` | Existing absolute parent proposed for the private source download. |
| `--download-only` | Download and identify source without running its Python code or preparing installation plans. |
| `--guided` | Ask wizard questions even when arguments are supplied; supplied paths are proposed for confirmation. |
| `--version` | Local candidate label with matching release notes, such as `0.1.0`. |
| `--work-parent` | Existing parent for a new mode-`0700` preparation directory containing the artifact and mode-`0600` plans. |
| `--core-root`, `--state-root` | New absolute program and state directories with existing parents. |
| `--deployment-root` | New absolute starter-document directory; optional when initialization is skipped. |
| `--skip-init` | Install Core alone; cannot be combined with `--deployment-root`. |
| `--plan-only` | Prepare plans without applying them. With all required arguments and no `--guided`, this runs without prompts. |

Missing required arguments start the wizard in a terminal. Without a terminal, supply every required argument and `--plan-only` for noninteractive preparation. There is no automatic approval option. Non-guided installation retains the full plan-ID prompts.

The script checks its interpreter before importing Core, then checks the actual POSIX launcher's `python3` and lifecycle prerequisites before preparation and again after approval. A compatible versioned interpreter does not fix a launcher whose `python3` is too old. See [installation prerequisites](installation.md#prerequisites). The core-installation phase does not install dependencies, probe devices, or launch applications. After successful guided installation, the optional finish-setup phase below offers helper settings, profile integration, and an explicitly selected notebook editor with separate approvals.

Each selected operation must apply and verify successfully. The completion message includes a shell-quoted command using the installed launcher's full path, document roles when initialized, and the installed guide location. The optional profile step below can add the launcher to `PATH` in future shells after its separate plan approval.

Preparation-only mode retains its artifact and plans for later reviewed `byte apply --plan` and `byte verify --plan` calls. Apply and verify install before init. Rerunning the wizard creates fresh preparation rather than resuming saved plans. Keep the checkout, artifact, plans, and target parents unchanged during setup; concurrent filesystem modification remains outside the wrapper's guarantees.

Exit status `0` means the selected workflow completed, including preparation-only mode. Argument errors return `2`, incompatible Python or failed prerequisites return `3`, wrapper refusal or cancellation returns `5`, and interruption returns `7`. Core failures retain their [CLI exit statuses](cli.md#exit-statuses).

Install and init are separate operations, not a transaction. If initialization fails after installation, Core remains installed. Preserve the saved plans, artifact, and remaining state and follow the [installation recovery and removal contract](installation.md). The wrapper does not automatically delete or retry. Preparation files contain local paths and must not be published. Native release acceptance and dependency installation remain separate; selected helper and profile steps have their own verification results.

### Permanent locations and finishing setup

For everyday use, choose permanent absolute locations in your home directory or another persistent directory. The wizard proposes `byte-core`, `byte-core-state`, and `byte-core-deployment` under the selected parent. Locations under `/tmp` are suitable only for disposable testing. Existing installations are preserved: selecting a new permanent installation does not move, replace, or remove a trial installation.

After a guided installation, the wizard offers optional configuration. You can decline and return later without reinstalling:

```sh
python3 scripts/setup_byte_core.py --finish-setup /absolute/private/install-plan.json
```

Add `--starter-plan /absolute/private/init-plan.json` to verify the original starter files and offer notebook onboarding. This requires unchanged original starter files; after customization, omit that option and edit your deployment documents directly. `--finish-setup` verifies the saved install plan against installed bytes before proceeding. It uses that installation in place, so it does not convert a `/tmp` trial into a permanent installation. It cannot be combined with new-installation path/version options.

The optional flow asks:

1. **Helper settings:** choose an existing TOML file, or create one with yes/no choices for prompt, prefix-history search, convenience aliases, and a development-directory shortcut. Assistant launching is optional and requires an explicit executable plus literal new/resume argument arrays. Network targets, repositories, highlighters, and other advanced settings remain explicit TOML customization; none are inferred or contacted.
2. **Review the helper plan:** new settings default to `~/.byte-helpers.toml`, displayed as an absolute path, and must use an absent file with an existing parent. The script saves prepared TOML and a private exact plan. Full plan-ID approval creates the settings through `byte setup apply`, followed by verification. Existing files are checked and left unchanged.
3. **Shell integration:** choose Bash or Zsh, the existing home directory whose `.bashrc` or `.zshrc` may change, and a new permanent session-script path (proposed as `~/.byte-session.sh`). The selected shell must already be installed. The script displays the complete generated entrypoint before asking to save it.
4. **Review the profile plan:** the session script selects the helper file, adds the installed `bin` directory to `PATH` without repeated duplication, and sources the installed generic shell asset. The existing shell planner binds this entrypoint, backs up the original profile, preserves its content/mode, and requires separate full plan-ID approval before modification. Existing managed blocks are refused rather than replaced. Keep the generated session script available; editing it invalidates its shell plan.
5. **Starter documents:** the wizard explains each document's purpose and can open the new notebook in an explicitly named editor. It passes the notebook as one argument without shell evaluation. It does not populate deployment facts or launch an assistant automatically.

Choose new settings and session-script paths outside Core and installation state. A profile may not target either installation tree. Existing files are never overwritten by the wizard. Settings and the session script must be separate files. Plan and backup artifacts remain private and retained.

`--finish-setup INSTALL_PLAN --plan-only` prepares the optional helper/profile plans without publishing helper settings or modifying profiles. It does create the reviewed new session script and private preparation files so the shell planner can bind the source. Apply and verify a prepared helper plan before its profile plan. This is separate from initial-installation `--plan-only`, which stops after the install/init plans; no installation exists yet for optional configuration.

Each step is independent: cancelling or failing shell integration leaves an already installed Core and completed helper settings intact. Retain the exact plans, source files, and `.byte-backups` files for recovery. Shell removal requires its separate reviewed removal plan; it does not remove helper settings, the session script, Core, or deployment documents. The wizard performs no automatic removal or rollback of earlier completed stages.

After profile verification, open a new selected-shell terminal and run:

```sh
command -v byte
byte check
bytehelp
```

The parent terminal is unchanged. An existing alias or function named `byte` can take precedence over `PATH`; review such a conflict separately. Bash login-shell startup depends on the user's login profile sourcing `.bashrc`; this wizard changes only `.bashrc` or `.zshrc`, never the login shell or login profile. Real prompt/history behavior should be checked in the selected interactive session. `bytewhere` can help inspect local configuration, but keep its output private.

The custom session entrypoint is bound by the shell plan. Its installed imports and launcher remain covered by the installation plan, not recursive shell-source hashing; retain and verify both plans. Optional highlighter loading, live assistant behavior, network operations, and native release acceptance are not established by this wizard.

## When something does not work

Byte follows the [troubleshooting guide](troubleshooting.md): explain the expected behavior, distinguish what was checked from what remains uncertain, and choose a useful bounded check. If you correct a fact, Byte should reconsider conclusions that depended on it. Longer investigations can use an optional private checkpoint; this introduction requires no extra document or data collection.

| What you see | What to do |
| --- | --- |
| `byte: command not found` | Use `./bin/byte` from the checkout. This exercise does not install a command onto your `PATH`. |
| `./bin/byte: No such file or directory` | Confirm the terminal or Codex project is the checkout containing `bin/byte`. |
| `Result: prerequisites unavailable` | Stop initialization and read the failed capability check. Git is needed for cloning, not initialization. Ask for an explanation or a separately reviewed remedy; do not bypass safety checks to finish the tutorial. |
| `ModuleNotFoundError: No module named 'tomllib'` from `./bin/byte` | The launcher can fail before its readiness report when `python3` is too old. Select Python 3.11+ as `python3` before retrying. The experimental setup script checks its own interpreter first. |
| `initialization cancelled` | No initialization was applied. Rerun the guided command when ready to review and confirm. |
| `target_exists` | The target is already present. Preserve it; start a new disposable example instead of overwriting it. |
| `verification_failed` | Stop and compare the saved plan with the example files. An edited starter no longer matches its initialization plan. |
| `recovery_required` | Preserve the plan and remaining files. Review ownership and the failed operation before any cleanup or retry. |

## Finish and give feedback

You can leave the disposable example in place for review. To discard it, first resolve and inspect the exact temporary parent created for this exercise, confirm it contains only the example and its plan, then remove that specific folder with your file manager. Stop if its identity or contents are uncertain. There is no system installation to undo. `byte remove --deployment-root` deliberately preserves deployment documents and will not delete this example for you.

Tell the maintainer which guide section was confusing, what you expected, and the relevant stable error code, if any. Use a fresh fictional description; do not send plans, absolute paths, screenshots of private context, transcripts, or broad logs.

For later source-repository work, Byte's [GitHub workflow](github-workflow.md) explains how to ask for a reviewable change, publication, merging, or branch cleanup. Byte should carry out the authorized work and leave a clear handoff. This guidance is included in Core; the first-session exercise does not publish anything or grant GitHub access.

When you are ready for a complete candidate review, follow [deployment acceptance testing](deployment-testing.md) from a fresh disposable root. That guide adds packaging, installation, shell integration, removal, preservation, and offline evidence. This introductory session alone does not satisfy the [independent fresh-user release review](release-checklist.md#fresh-user-review).
