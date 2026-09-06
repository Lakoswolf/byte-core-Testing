# Optional shell integration

Byte Core's experimental shell integration is an explicit, reversible layer for Bash and Zsh. It does not change the login shell, install packages, select a shell framework, inspect host identity, or infer deployment paths.

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

Planning requires an explicit existing home root, `bash` or `zsh`, and an absolute readable shell-asset path. Bash targets `.bashrc`; Zsh targets `.zshrc`. A plan records the exact original profile checksum and mode, generated block, expected result checksum, preconditions, postconditions, backout rule, and content-bound plan ID.

Apply refuses changes to profile existence or bytes after planning. It creates a mode-`0600` backup under `.byte-backups/` before atomically replacing the profile using the mode recorded in the plan. Existing content is retained byte-for-byte. Reapplying an exact plan is idempotent.

Removal has a separate read-only planning phase and a distinct removal backup. It accepts exactly one well-formed Byte block, preserves all unrelated content byte-for-byte, and restores profile absence when installation created a previously missing profile. Missing, duplicate, malformed, stale, or altered blocks are refused.

Plan and backup files contain exact local paths and profile content or copies. They are private local artifacts and must not be committed.

## Optional Zsh syntax highlighting

Syntax highlighting is never a dependency. A Zsh installation plan may include an explicit absolute `--syntax-highlighting` file selected by the operator. Byte verifies that file exists and then adds it to the exact managed block. Omitting the option produces no syntax-highlighting behavior.

Bash plans reject this option. Byte does not locate, download, install, upgrade, configure, or remove a syntax-highlighting package.

## Current boundary

This is an internal bootstrap proof, not a supported installed shell product. Optional prompt and history-keybinding customization is implemented; history files are not inspected or rewritten. Helpers do not discover repositories, install completions or dependencies, infer device configuration, automatically publish changes, or install remote wake senders. Reachability and wake requests do not prove device identity, capabilities, or power state. Manual native-platform and real application/network evidence remains pending.

Current shell verification checks profile bytes and managed-block presence, not permission-only drift or the contents of the sourced shell and syntax-highlighting files. Plans bind those source paths but do not checksum their contents. Review those explicit files before sourcing them. Removal restores profile absence or unrelated content, but keeps its private backup files for recovery.
