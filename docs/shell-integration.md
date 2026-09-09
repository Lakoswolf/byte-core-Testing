# Optional shell integration

Byte Core's experimental shell integration is an explicit, reversible layer for Bash and Zsh. It does not change the login shell, install packages, select a shell framework, inspect host identity, or infer deployment paths.

`byte check --feature shell-bash` or `shell-zsh` checks filesystem prerequisites and availability of the selected interpreter. Profile planning, apply, verification, and removal use lifecycle filesystem prerequisites, so they can prepare configuration before a shell is installed. Actual shell execution still needs that interpreter. Byte does not install it automatically.

## Generic shell asset

[`shell/byte-shell.sh`](../shell/byte-shell.sh) provides a POSIX-compatible basic layer and loads adjacent native assets for Bash or Zsh. Repeated sourcing preserves per-shell feature preferences. Its original basic helpers remain available:

- `byte_status`, which reports only that the generic integration is active; and
- `byte_repo PATH`, which validates an explicit directory as a Git worktree before changing the caller's directory.

The asset contains no hostnames, usernames, addresses, inventory, credentials, or deployment paths. Unknown hosts receive the same generic behavior.

## Configurable shell helpers

The following helpers are implemented for experimental Bash/Zsh use. They do not establish a supported shell API. The [helper setup guide](helpers.md) documents configuration, command syntax, approval boundaries, and limitations. Runtime helpers need the asset's adjacent native files and `../bin/byte` launcher, Python, and any explicitly invoked prerequisites.

| Helper | Behavior and configuration |
| --- | --- |
| `bytehelp`, `bytewhere` | Explain available helpers and show relevant local integration context. Keep local context out of public reports. |
| `bytesafety` | Explain Core's generic operational rules; deployment-specific guidance remains deployment-owned. |
| `rebyte` | Reload the explicitly selected shell asset while preserving feature preferences. |
| `dev` | Navigate to an explicitly configured development directory. |
| `byten`, `byter` | Invoke the configured application once at the current Git root using separate new/resume argument arrays. Session semantics belong to the selected application; Core does not inspect session data. |
| `bytegit` | Show Git status with optional arguments. This name does not imply automatic synchronization, publication, or branch cleanup. |
| `byteprompt` | Optional prompt with configurable label, colors, and directory/Git components; preserve and restore the user's prompt and relevant shell option. |
| `bytehistory` | Optional prefix history search with enable, disable, status, and restoration behavior. |
| `bytehighlight` | Source an explicit optional Zsh highlighter; optional styles for zsh-syntax-highlighting. Third-party changes require a fresh shell to undo. |
| `bytealiases`; `ll`, `la`, `..` | Toggle optional convenience aliases while preserving existing user definitions. |
| `labstatus` | Check explicitly configured inventory targets through a reachability backend. |
| `canisync` | Synchronize explicitly configured repositories, remotes, and branches through a separately validated backend. |
| `wakelan` | Request wake-on-LAN for an explicitly selected configured device, with configurable delivery and relay settings where applicable. |

Deployment-specific project-root shortcuts and an editor shortcut are excluded. `bytegit` is the Git-status helper; `wakelan` is the generic wake helper. No deployment-specific compatibility aliases are provided.

All helpers follow the [configuration design requirements](configuration.md#designing-configurable-tools). Ordinary setup edits deployment-owned settings rather than scripts. No helper invents a repository layout, device identity, address, relay, or application location.

Interactive features are opt-in; prompt, history bindings, and Byte-created aliases have disable behavior. Arbitrary third-party highlighting code cannot be reversed safely in place. Operational helpers delegate to backends with explicit scope, validation, and failure reporting. Offline plans do not contact devices or remotes. Execution requires a saved plan and its reviewed ID. Configuration does not authorize network traffic or mutation.

## Managed profile block

Planning requires an explicit existing home root, `bash` or `zsh`, and an absolute readable shell-asset path. Bash targets `.bashrc`; Zsh targets `.zshrc`. A schema-version-2 plan records the exact original profile checksum and mode, generated block, expected result checksum, preconditions, postconditions, backout rule, and content-bound plan ID. Its `source_files` records bind each selected source path, SHA-256 checksum, and permission mode. Version-1 plans are refused; build and review a fresh plan instead of editing an old plan or reusing its approval.

Profiles and their planned results must each fit within 1 MiB. Planning and apply reject oversized results before creating a backup or changing the profile. Apply refuses changes to profile existence, bytes, or permission mode after planning. Installation also refuses missing, changed, or symlinked sources, including on replay. It creates a mode-`0600` backup under `.byte-backups/` before atomically replacing the profile using the mode recorded in the plan; a newly created profile uses mode `0600`. Existing content is retained byte-for-byte. Reapplying an exact plan is idempotent only while its profile and bound sources still match. Read-only verification checks profile existence, bytes, mode, block presence, and installation sources without creating or modifying profile or backup files.

Removal has a separate read-only planning phase and a distinct removal backup. It accepts exactly one well-formed Byte block, preserves all unrelated content byte-for-byte (including non-UTF-8 profile bytes outside the UTF-8 managed block), and restores profile absence when installation created a previously missing profile. Missing, duplicate, malformed, stale, or altered blocks are refused. Removal plans contain an empty `source_files` list: removal planning, loading, apply, replay, and verification do not require the previously sourced code to exist or remain unchanged. Removal still checks the reviewed profile bytes and mode. If apply verification fails, backout restores the original profile only when the written result still has the expected bytes and mode; ambiguous subsequent changes are preserved for manual recovery.

Plan and backup files contain exact local paths and profile content or copies. They are private local artifacts and must not be committed.

## Optional Zsh syntax highlighting

Syntax highlighting is never a dependency. A Zsh installation plan may include an explicit absolute `--syntax-highlighting` file selected by the operator. Byte checks that file is readable, records its checksum and mode, and adds it to the exact managed block. Omitting the option produces no syntax-highlighting behavior.

Bash plans reject this option. Byte does not locate, download, install, upgrade, configure, or remove a syntax-highlighting package.

## Setup-wizard session entrypoint

The source-only [setup wizard](getting-started.md#permanent-locations-and-finishing-setup) can generate a new, reviewed deployment-owned session script that selects helper settings, adds the chosen installation to `PATH`, and sources its packaged shell asset. It then uses this unchanged shell planner to bind the custom entrypoint and separately approve/apply/verify the profile change. Existing profiles retain their unrelated bytes and modes, with backups retained. The wrapper does not change the login shell or immediately source the user profile. Bash login profiles may separately need to source `.bashrc`.

Custom entrypoints bind only their explicit file, as described below; the installed asset and launcher remain covered by separate installation verification. The helper TOML is intentionally mutable deployment data. Shell removal leaves the wrapper and helper file available for reviewed cleanup.

## Current boundary

This is an internal bootstrap proof, not a supported installed shell product. Optional prompt and history-keybinding customization is implemented; history files are not inspected or rewritten. Helpers do not discover repositories, install completions or dependencies, infer device configuration, automatically publish changes, or install remote wake senders. Reachability and wake requests do not prove device identity, capabilities, or power state. Manual native-platform and real application/network evidence remains pending.

Installation binds the explicit entrypoint and optional `--syntax-highlighting` file, with a 4 MiB limit per source. An entrypoint named `byte-shell.sh` follows Core's fixed package layout: Bash additionally requires adjacent `byte-shell-bash.sh`; Zsh requires adjacent `byte-shell-zsh.zsh`. The selected native file's checksum and mode are also bound. Keep the Core entrypoint's packaged name and adjacent native files intact. A custom entrypoint with another name binds that explicit file only.

This is a fixed dependency contract, not recursive inspection of shell imports. The helper launcher and Python backend, arbitrary imports in custom or third-party code, and a highlighter selected later through deployment-owned helper configuration are outside this shell plan's source snapshot. The checks establish equality at apply, replay, and verification time; they do not intercept future shell sourcing or prevent later filesystem changes. Review explicitly selected code before sourcing it. Removal restores profile absence or unrelated content, but keeps its private backup files for recovery.
