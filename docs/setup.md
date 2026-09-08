# Guided helper setup

The experimental `byte setup` workflow turns an explicitly prepared standalone helpers TOML into a new deployment-owned settings file, checks local prerequisites, and provides the next shell integration steps. It remains a bootstrap proof, with no supported installed CLI or production release claim.

`byte check --feature setup` checks the current POSIX secure file I/O backend. The settings-specific readiness checks below remain separate: they validate only explicitly configured choices, without a blanket Git or operating-system requirement.

## Prepare the choices

Ask Byte to help configure the [shell helpers](helpers.md). The assistant should explain available settings, identify which features you want, and prepare only settings you have supplied or confirmed. Keep unknown paths, application choices, repositories, device addresses, and relays unset. Ordinary customization belongs in the standalone TOML; editing Core scripts is unnecessary. This file is separate from `deployment.toml` and uses the [helper settings reference](helpers.md#settings-reference).

Start with `./bin/byte helpers config example`, which prints generic defaults and commented fictional examples. Save the output to a **new private file outside Core**, and edit that file in your preferred editor. Do not source TOML as shell code. Choose a separate, absent destination for the installed helper settings. Both files and their existing parent directories must be absolute paths without symlinks or parent traversal. Setup creates no directories and never overwrites existing settings.

The assistant should explain the selected paths and offline checks before preparing the plan. It should review the prerequisites and complete plan with you, obtain approval for that exact plan ID, apply it, verify the result, and then explain the separately approved shell setup. A request to configure helpers does not itself authorize application launches, repository synchronization, network probes, wake packets, profile changes, or third-party code execution.

## Check and review

The following commands use descriptive placeholders; substitute your explicitly chosen absolute private paths. From a checkout, use `./bin/byte` in place of `byte`.

```text
byte setup check --settings ABSOLUTE_PREPARED_TOML
byte setup plan --settings ABSOLUTE_PREPARED_TOML --output ABSOLUTE_NEW_HELPERS_TOML
```

`check` prints JSON and exits nonzero for unavailable configured prerequisites. It validates the complete standalone schema, checks the existence of configured development/repository directories, checks readability of a selected highlighter, and checks availability of a selected assistant executable. A command-name executable uses PATH lookup only; an absolute executable path is checked directly. No application is launched, no shell code is sourced, no repository contents or profiles are read, and no traffic is sent. The checks do not establish that a directory is a Git repository, that application arguments work, or that a device or relay is reachable.

Missing optional choices appear as `unconfigured`; configured unavailable paths or executables appear as `missing` and prevent planning. A selected application needs an executable. Each launcher needs its corresponding `new_args` or `resume_args`; a missing array leaves that launcher unconfigured and does not prevent setup of other helpers. An explicit empty array is valid. Highlighting requires a configured readable file and a later manual review of that code; Bash selection refuses enabled highlighting. Devices retain unknown readiness. Optional features begin disabled in the generic starter.

`plan` prints a deterministic JSON plan containing the exact source path and SHA-256 digest, absent destination, destination-directory identity, mode `0600`, prerequisite report, backout instructions, next steps, and content-bound `id`. It contains local paths and must stay private. It does not embed the settings contents. Save its output in a new private local JSON file and review it before applying. Creating or saving a plan does not execute it.

To include an exact shell-planning command in the next steps, supply all three optional selections:

```text
byte setup plan --settings ABSOLUTE_PREPARED_TOML --output ABSOLUTE_NEW_HELPERS_TOML --home-root ABSOLUTE_HOME_ROOT --shell zsh --shell-script ABSOLUTE_BYTE_SHELL_ASSET
```

These options check the explicitly selected directory and bounded regular shell-asset file. They do not read or modify the profile, create a shell plan, install a shell, or source the asset. The shell asset's contents and profile state are not bound to the helper setup plan; review the asset and generate a fresh [shell lifecycle plan](shell-integration.md#managed-profile-block) when reaching that separate step.

## Apply, verify, and load

After reviewing the saved plan and its full ID:

```text
byte setup apply --plan ABSOLUTE_PRIVATE_PLAN_JSON --approve REVIEWED_PLAN_ID
byte setup verify --plan ABSOLUTE_PRIVATE_PLAN_JSON
```

Apply rechecks the source bytes, prerequisites, destination absence, and destination-directory identity. It writes the original TOML bytes, including comments and line endings, to a mode-`0600` temporary file and exclusively publishes the complete file. Concurrent creation of the destination is refused. Apply never replaces an existing file, including one created by a previous apply. Verification checks its directory identity, exact digest, regular-file type, and mode. Verification can run after the prepared source is removed. Editing the destination later is expected customization, but the original setup plan will then correctly fail byte verification; use `byte setup check --settings ABSOLUTE_HELPERS_TOML` to validate current choices.

Successful apply and verify print the next steps as JSON data. Run the returned `export BYTE_CORE_HELPERS_CONFIG=...` command in your chosen shell before sourcing the reviewed shell asset. The [helper selection rules](helpers.md#file-selection-and-validation) still apply: `helpers --config` takes precedence over that selector. For persistence, place the selector in your deployment-owned shell configuration before Byte's source block as a separately reviewed edit; setup does not edit profiles or persist environment variables. Independently plan, approve, and verify managed profile integration using `byte shell`. After loading the asset, run `bytehelp` and `bytewhere`, and check selected optional features individually. Keep `bytewhere` output private.

## Recovery and limits

The plan's backout identifies the single newly created file and its expected digest. If backing out, first verify the exact path and unchanged digest; remove only that file. Preserve any file edited since setup and resolve it separately. The original prepared file is unchanged, and setup creates no profile changes to undo. Setup does not automate deletion or manage retention of your prepared settings and saved plan. Retain those private artifacts for review or remove them through your normal explicit local cleanup.

A failed write can require checking the destination and a temporary `.byte-setup-*` file in its parent; never remove unrelated files. Avoid concurrent directory renames during apply. Descriptor-based publication prevents symlink redirection, but this is not a transaction against every possible concurrent filesystem mutation. A post-publication verification failure is not success and does not authorize deleting an independently changed destination.

Automated evidence uses only fictional temporary settings, directories, shell assets, and mocked executable lookups. Native macOS, actual assistant applications, real third-party highlighters, interactive user sessions, and live device/relay behavior remain unvalidated by this setup workflow.
