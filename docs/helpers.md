# Configurable shell and operational helpers

These are experimental bootstrap commands for disposable testing, not a supported installed product. The [shell lifecycle](shell-integration.md) manages profile integration; the helper runtime uses explicitly selected deployment-owned settings. Neither requires importing a private shell implementation.

## First setup

Ask Byte to prepare a helper configuration with you using [Guided helper setup](setup.md). It should explain the available settings, keep unknown paths and device details unset, check configured prerequisites, and review the exact setup plan before creating the new settings file. Operational and profile changes have their own later plans and approvals.

For an offline terminal trial, run each block separately from the checkout in Bash or Zsh. Stop if a command fails. Create a new disposable configuration outside Core:

```sh
BYTE_HELPERS_TRIAL=$(mktemp -d)
```

Resolve the new directory to its physical absolute path (temporary directories can have symlinked parents on macOS):

```sh
BYTE_HELPERS_TRIAL=$(cd "$BYTE_HELPERS_TRIAL" && pwd -P)
```

Prepare the generic starter in that newly created directory, then check and plan a separate new helper file:

```sh
./bin/byte helpers config example > "$BYTE_HELPERS_TRIAL/prepared.toml"
./bin/byte setup check --settings "$BYTE_HELPERS_TRIAL/prepared.toml"
./bin/byte setup plan \
  --settings "$BYTE_HELPERS_TRIAL/prepared.toml" \
  --output "$BYTE_HELPERS_TRIAL/helpers.toml" \
  > "$BYTE_HELPERS_TRIAL/setup-plan.json"
```

Review the saved JSON plan: source digest, new destination, mode `0600`, prerequisite report, backout, and full `id`. Generic defaults leave optional choices unconfigured. Replace `REVIEWED_PLAN_ID` below with that full ID only after approving the plan:

```sh
./bin/byte setup apply \
  --plan "$BYTE_HELPERS_TRIAL/setup-plan.json" \
  --approve REVIEWED_PLAN_ID
./bin/byte setup verify --plan "$BYTE_HELPERS_TRIAL/setup-plan.json"
```

Setup preserves the prepared bytes, creates the destination with mode `0600`, and refuses an existing destination. It runs no applications or network operations and makes no profile changes. After successful verification, select the created file:

```sh
export BYTE_CORE_HELPERS_CONFIG="$BYTE_HELPERS_TRIAL/helpers.toml"
./bin/byte helpers config validate
```

Expected validation output:

```text
Helper configuration valid. No applications or network operations were started.
```

Source the asset in the current Bash or Zsh session:

```sh
. ./shell/byte-shell.sh
bytehelp
bytewhere
```

This does not write a shell profile. `bytehelp` lists the available commands; `bytewhere` shows local asset, launcher, and configuration paths. Those paths are private local context, not public diagnostic material. Optional presentation starts disabled. Edit the deployment-owned TOML file in your preferred editor to enable or configure features; do not source that TOML file.

For persistent integration, separately review and apply a [shell profile plan](shell-integration.md#managed-profile-block). The existing profile planner does not select a helper configuration for you: the deployment chooses how to set `BYTE_CORE_HELPERS_CONFIG` before sourcing the asset. Ordinary Core updates preserve the external configuration.

## File selection and validation

`byte helpers --config ABSOLUTE_PATH ...` overrides `BYTE_CORE_HELPERS_CONFIG`. If neither is supplied, only generic defaults apply. No host-based file discovery, environment interpolation, `~` expansion, or executable configuration is supported. Only this explicit environment selector is read to select helper settings; arbitrary environment values are not collected or reported.

This is a standalone schema-1 TOML document, separate from the layered deployment resolver. Do not put helper keys into `deployment.toml`. Unknown keys, duplicate TOML keys, incorrect types, unsupported schema versions, and malformed settings are refused. Input files and saved plans must be absolute regular files without symlinks or parent traversal; input size is capped at 2 MiB. Configured operational paths are also explicit absolute paths, without parent traversal. Their existence and target state are checked when the relevant helper runs or plans.

The [starter template](../templates/helpers.toml) contains generic defaults and commented fictional examples. The helper CLI prints, validates, and reads settings; optional `byte setup` creates one new reviewed settings file. Neither provides a configuration editor, migrates old files, or automatically saves plans/results. Keep operational configuration and output outside the public Core checkout. Later settings edits remain deployment-owned; use `setup check` to validate them because the original setup plan intentionally binds the original bytes.

## Settings reference

Every file requires `schema_version = 1`. Tables and arrays below are optional until their corresponding feature is used.

| Setting | Type and default | Meaning |
| --- | --- | --- |
| `shell.development_directory` | Absolute path; unset | Destination for `dev`. |
| `shell.prompt`, `shell.history`, `shell.aliases`, `shell.highlighting` | Boolean; `false` | Initial opt-in preferences for an interactive session. |
| `shell.prompt_label` | Nonempty text up to 128 characters; `Byte` | Literal prompt label, never inferred from host identity. |
| `shell.prompt_color` | `none`, `cyan`, `green`, or `yellow`; `none` | Prompt color. |
| `shell.prompt_directory`, `shell.prompt_git` | Boolean; `true` | Include the directory basename and Git context. |
| `shell.highlighting_file` | Absolute path; unset | Explicit Zsh code to source; required when highlighting is enabled. |
| `shell.highlighting_command_style`, `shell.highlighting_unknown_style`, `shell.highlighting_path_style` | Text up to 128 characters; unset | Optional zsh-syntax-highlighting styles; unset values preserve plugin styling. |
| `assistant.executable` | Command name on PATH or absolute executable path; unset | Application selected by the user. |
| `assistant.new_args`, `assistant.resume_args` | Separate arrays of literal strings; unset | Required for the respective launch mode. Explicit empty arrays are allowed. Up to 64 arguments, each up to 4096 characters. |
| `repositories` | Array of tables; empty, maximum 64 | Each entry requires a unique `name`, absolute `path`, `remote`, and `branch`. |
| `devices` | Array of tables; empty, maximum 64 | Each entry requires a unique `name`; other settings depend on the operation. |
| `devices.addresses` | Up to 8 distinct numeric IPv4/IPv6 addresses; empty | Reachability targets. DNS names and IPv6 scope identifiers are not supported here. |
| `devices.mac` | Six colon-separated hexadecimal octets; unset | Nonzero unicast MAC, required for a wake plan. |
| `devices.broadcast`, `devices.port` | Numeric IPv4 destination and integer 1–65535; unset | Both required for direct wake delivery. No broadcast destination or port is guessed. |
| `devices.relay_host`, `devices.relay_command` | Host or `user@host`, and literal command array; unset | Both required for SSH delivery. Sender executable is an absolute remote path; up to 32 nonempty arguments of at most 1024 characters. |
| `network.ping_timeout` | Number greater than 0 and at most 10 seconds; `2` | Per-address ping process deadline. |
| `network.workers` | Integer 1–8; `4` | Maximum concurrent reachability checks. |
| `network.relay_timeout` | Number greater than 0 and at most 30 seconds; `10` | SSH request and direct UDP socket timeout. |

Device/repository names are case-sensitive, at most 80 characters, and contain letters, digits, dots, underscores, or hyphens, beginning with a letter or digit. Text settings reject control characters. Arguments are passed as distinct values; punctuation is never evaluated as shell code. The SSH transport quotes each configured remote argument for a POSIX-compatible remote shell.

## Everyday shell commands

- `bytehelp`, `bytewhere`, and `bytesafety` explain commands, local integration context, and Core's generic operational rules.
- `dev` changes to the configured development directory. `byte_repo PATH` validates an explicit Git worktree before changing directories. Failed validation preserves the original working directory.
- `byten [ARGS...]` and `byter [ARGS...]` invoke the selected application's new/resume arguments once, with the current Git root as its working directory. Literal `{project}` occurrences in configured arguments become that root. Additional invocation arguments follow the configured arguments unchanged. Core does not install, update, restart, select credentials for, or inspect sessions of the application. Configure arguments appropriate to the application's documented interface.
- `bytegit [STATUS_ARGUMENTS...]` invokes Git status and preserves its exit status. This explicit Git invocation uses normal Git behavior and local configuration; it is not a GitHub publishing or cleanup command.
- `rebyte` reloads the active shell asset while preserving current feature enable/disable preferences. Settings are read when used. To apply changed prompt color settings, toggle the prompt off and on; initial preferences in TOML apply when a fresh interactive shell first loads the asset.

`caniroot`, `byteroot`, `v`, `doggit`, and `wakesd` are not provided. No compatibility aliases are installed for them.

## Optional interactive features

`byteprompt`, `bytehistory`, `bytealiases`, and `bytehighlight` each accept `on`, `off`, or `status`. They are opt-in in interactive Bash/Zsh; sourcing in a noninteractive shell does not enable presentation features.

Prompt disable restores the previous prompt and relevant shell option. The Git component shows branch or detached commit and a dirty marker when available. Repository-defined filters and partial clones are excluded from passive prompt inspection; submodule changes may be omitted. Errors omit Git context instead of making the shell unusable. Prompt text is treated as data.

History search changes the Up/Down bindings in the standard Emacs and Vi insertion maps, with restoration on disable. It does not inspect or rewrite history files. Zsh arrow-key string macros and Bash arrow-key shell-command bindings are preserved by refusing enablement until the user resolves the conflict; Bash also refuses when it cannot inspect command bindings. Alias enablement adds only absent shortcuts; disablement removes only unchanged definitions created by Byte. `ll` runs `ls -l`, `la` runs `ls -A`, and `..` changes to the parent directory.

Highlighting requires Zsh and a readable, explicitly selected code file. It is not a package installer. Styles are applied only when the selected package exposes the `ZSH_HIGHLIGHT_STYLES` associative array. Sourcing third-party code can change arbitrary shell state: `off` reports that it cannot safely undo those changes. Set the initial highlighting preference to `false` and start a fresh shell to return to a session without it. A failed source is reported as partial rather than successfully loaded. Review selected code before enabling it.

## Reachability and wake plans

Configure device entries first. Plan only named targets; repeat `--device` for multiple reachability selections:

```text
labstatus plan --device example-device
wakelan plan --device example-device
```

Each command prints an offline JSON plan with an `id`. It sends no probes or packets and does not contact a relay. Save that output in a new private local file, review all selected addresses/delivery settings and the ID, then explicitly approve execution:

```text
labstatus run --plan ABSOLUTE_PRIVATE_PLAN_PATH --approve REVIEWED_PLAN_ID
wakelan run --plan ABSOLUTE_PRIVATE_PLAN_PATH --approve REVIEWED_PLAN_ID
```

CLI execution checks the [supported host matrix](support-matrix.md). Edited plans, changed selected-device settings, and wrong approval IDs are refused before traffic. Plan IDs bind content; they are not signatures, one-time tokens, or independent authorization. Reusing an unchanged approved network plan repeats its operation.

Reachability runs one ICMP echo process per selected address, with a bounded worker pool and deadline. Results distinguish `reachable`, `no_response`, `unavailable`, `error`, and devices with `no_addresses`. A missing reply does not prove a device is offline. There is no automatic LAN/Tailscale route selection, identity inference, inventory/catalog rewrite, or capability research. This is separate from [guided discovery](inventory.md).

Direct wake sends one UDP magic packet to the configured destination/port. `sent` means the socket accepted the packet; power state remains unknown. SSH delivery invokes the configured remote sender once and reports `requested` on successful exit. It ignores SSH configuration, disables forwarding and local commands, requires existing host-key trust and noninteractive authentication, and does not install a sender or modify SSH files. `relay_host` must resolve independently of SSH-config aliases. A timeout reports `unknown` because the sender may have run. Sent probes and wake requests cannot be recalled.

## Repository synchronization plans

`canisync plan` inspects only explicitly configured local repositories and prints JSON. Each must be an existing, clean, non-bare worktree with an attached branch, the configured remote, and an existing target branch. In-progress Git operations, conflicting linked worktrees, duplicate/shared repositories, partial clones, submodules, configured branch merge options, and clean/smudge/process filters are refused. The exclusions prevent unexpected merge behavior, implicit commands, and lazy network access during offline inspection.

Save and review the plan before invoking:

```text
canisync apply --plan ABSOLUTE_PRIVATE_PLAN_PATH --approve REVIEWED_PLAN_ID
```

Apply rechecks local state and configuration, fetches each selected branch, checks that every target can fast-forward, then switches and fast-forwards repositories in configured order with fresh checks before each change. Fetch/prune affects only the selected remote-tracking branch; it does not fetch tags or recurse into submodules. Remote state is unknown until the approved fetch. An ahead or diverged target is refused. The plan records starting branches and commit IDs; output records each attempted fetch, switch, and update.

This is not atomic across repositories. A failed fetch or later checkout operation can leave partial changes; exit `7` requires reviewing the result before retrying. No automatic rollback occurs. Switch/merge refuse to overwrite ignored files, and automatic stashing is disabled. The helper never commits, pushes, stashes, deletes branches, resets, or resolves conflicts. Explicitly invoked Git transports can use configured authentication; they are contacted only during apply. Directory identities and refs are rechecked, but the helper does not provide a filesystem transaction or exclusive lock against another process changing the repository between a check and a Git command. Avoid concurrent repository edits while applying. It does not implement the separate advisory [GitHub workflow](github-workflow.md).

Sync respects Git's explicit `GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_SYSTEM`, and `GIT_CONFIG_GLOBAL` selectors; their effective settings still receive the same filter and configuration checks and are bound to the plan. Environment overrides that redirect the repository or index are discarded. Configuration selectors do not bypass target verification or authorize execution.

## Validation boundary

Automated checks use fictional local Git repositories, fake assistant executables, clean Bash/Zsh processes, and mocked ping/UDP/SSH operations. They verify refusal, argument handling, feature restoration, and partial-failure reporting. They do not establish compatibility with a real assistant application, third-party highlighter, live device/relay, or native macOS installation. Those manual checks remain pending; normal user profiles and system files are not changed by the test suite.
