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

The optional `scripts/setup_byte_core.py` automates a larger exercise: it checks the host, builds a candidate from this checkout, saves installation and initialization plans, asks for both full plan IDs, and applies and verifies each operation. This includes experimental Core installation; it goes beyond the five-file introduction. Use a reviewed public source checkout and fictional starter data. Installation remains unsupported for operational use.

Run `python3 scripts/setup_byte_core.py --help` from the source checkout to inspect its arguments. The script is development tooling and is not included in installed artifacts. Every selection is explicit:

| Argument | Required value |
| --- | --- |
| `--version` | Candidate version such as `0.1.0`, with matching local release notes. This labels the local build; it does not authenticate a release. |
| `--core-root` | Absent absolute directory for Core releases. |
| `--state-root` | Absent absolute directory for installation manifests and state. |
| `--deployment-root` | Absent absolute directory for the five starter files. |
| `--work-parent` | Existing private absolute directory for a fresh mode-`0700` preparation directory containing the artifact and mode-`0600` plans. |
| `--plan-only` | Optional: stop after building and displaying saved plans without prompting or applying. |

The three target roots must have existing directory parents and must not overlap. All selected paths must be outside the checkout and Git metadata and must not contain the checkout. Selected symlinks and parent traversal are refused; existing parent aliases are canonicalized. Paths are literal arguments: the script does not expand variables or `~`, infer home paths, or read a settings file. The invoking shell still performs its normal quoted-variable expansion. There are no implicit configuration overrides.

For example, in Bash or Zsh, explicitly create a disposable private parent and use its new children. Stop if parent creation fails:

```sh
BYTE_SETUP_TRIAL=$(mktemp -d)
```

Then run:

```sh
python3 scripts/setup_byte_core.py --version 0.1.0 \
  --work-parent "$BYTE_SETUP_TRIAL" \
  --core-root "$BYTE_SETUP_TRIAL/core" \
  --state-root "$BYTE_SETUP_TRIAL/state" \
  --deployment-root "$BYTE_SETUP_TRIAL/deployment"
```

Use Python 3.11–3.14. The script checks the interpreter before importing Core and refuses an incompatible version with an actionable message. It also checks the actual POSIX launcher's `python3` and Git on `PATH` and host support before preparation and again after approval. A compatible versioned interpreter alone cannot satisfy this check when the launcher still selects an older `python3`. See [installation prerequisites](installation.md#prerequisites) for the complete requirements and troubleshooting. The script does not install Python, Git, packages, or Codex; change shell profiles or `PATH`; contact infrastructure; or publish anything. Missing lifecycle prerequisites stop before preparation writes.

Review the displayed exact targets, hashes, and backout actions before entering each plan ID. Both approvals are required before either plan is applied. Any other response or end of input cancels, retaining preparation files. `--plan-only` intentionally retains its artifact and plans for separate reviewed `byte apply --plan` and `byte verify --plan` commands; rerunning the script creates fresh preparation rather than resuming them.

Success requires installation apply/verify followed by initialization apply/verify. The script prints the installed launcher, deployment location, and five file roles. This is not a supported release or a completed platform acceptance test. Read the starter files before editing them.

Exit status `0` means the requested workflow completed (preparation only with `--plan-only`). Argument errors return `2`, incompatible Python or failed launcher prerequisites return `3`, wrapper refusal or cancellation returns `5`, and interruption returns `7`. Core command failures retain their [CLI exit statuses](cli.md#exit-statuses).

The two operations are not one transaction. If initialization fails after installation, Core remains installed. On failure or interruption, stop and preserve the saved plans, artifact, and remaining state; the wrapper does not delete or automatically retry anything. Each Core operation retains its existing bounded recovery behavior. Follow the [installation recovery and removal contract](installation.md) before proposing removal of Core. Deployment documents require a separate explicit cleanup decision. Preparation directories remain until you inspect and explicitly remove the exact directory; plans and output contain private local paths and must not be published. Concurrent filesystem modification remains outside the wrapper's guarantees; keep the checkout, artifact, plans, and target parents unchanged while it runs.

## When something does not work

Byte follows the [troubleshooting guide](troubleshooting.md): explain the expected behavior, distinguish what was checked from what remains uncertain, and choose a useful bounded check. If you correct a fact, Byte should reconsider conclusions that depended on it. Longer investigations can use an optional private checkpoint; this introduction requires no extra document or data collection.

| What you see | What to do |
| --- | --- |
| `byte: command not found` | Use `./bin/byte` from the checkout. This exercise does not install a command onto your `PATH`. |
| `./bin/byte: No such file or directory` | Confirm the terminal or Codex project is the checkout containing `bin/byte`. |
| `Result: prerequisites unavailable` | Stop initialization and read the failed capability check. Git is needed for cloning, not initialization. Ask for an explanation or a separately reviewed remedy; do not bypass safety checks to finish the tutorial. |
| `ModuleNotFoundError: No module named 'tomllib'` from `./bin/byte` | The launcher can fail before its readiness report when `python3` is too old. Select Python 3.11–3.14 as `python3` before retrying. The experimental setup script checks its own interpreter first. |
| `initialization cancelled` | No initialization was applied. Rerun the guided command when ready to review and confirm. |
| `target_exists` | The target is already present. Preserve it; start a new disposable example instead of overwriting it. |
| `verification_failed` | Stop and compare the saved plan with the example files. An edited starter no longer matches its initialization plan. |
| `recovery_required` | Preserve the plan and remaining files. Review ownership and the failed operation before any cleanup or retry. |

## Finish and give feedback

You can leave the disposable example in place for review. To discard it, first resolve and inspect the exact temporary parent created for this exercise, confirm it contains only the example and its plan, then remove that specific folder with your file manager. Stop if its identity or contents are uncertain. There is no system installation to undo. `byte remove --deployment-root` deliberately preserves deployment documents and will not delete this example for you.

Tell the maintainer which guide section was confusing, what you expected, and the relevant stable error code, if any. Use a fresh fictional description; do not send plans, absolute paths, screenshots of private context, transcripts, or broad logs.

For later source-repository work, Byte's [GitHub workflow](github-workflow.md) explains how to ask for a reviewable change, publication, merging, or branch cleanup. Byte should carry out the authorized work and leave a clear handoff. This guidance is included in Core; the first-session exercise does not publish anything or grant GitHub access.

When you are ready for a complete candidate review, follow [deployment acceptance testing](deployment-testing.md) from a fresh disposable root. That guide adds packaging, installation, shell integration, removal, preservation, and offline evidence. This introductory session alone does not satisfy the [independent fresh-user release review](release-checklist.md#fresh-user-review).
