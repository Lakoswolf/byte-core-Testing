# Byte lifecycle command contract

Byte Core uses one `byte` command for lifecycle operations. The command separates checking, planning, applying, verifying, and backing out changes so that read-only discovery cannot silently become mutation.

The current bootstrap implements `check`, guided initialization and helper setup, exact-plan installation, update and removal, reversible shell integration, configurable shell and operational helpers, optional guided inventory, and local diagnostics with optional reviewed GitHub reporting. These remain experimental proofs, not a supported installed CLI. For a guided introduction, start with [Your first session with Byte](getting-started.md).

## Grammar

```text
byte [--help]
byte check [--format text|json]
byte init --deployment-root ABSOLUTE_PATH
byte plan init --deployment-root ABSOLUTE_PATH
byte plan install --artifact-root ABSOLUTE_PATH --core-root ABSOLUTE_PATH --state-root ABSOLUTE_PATH --core-version VERSION
byte plan update --manifest ABSOLUTE_PATH --artifact-root ABSOLUTE_PATH
byte plan remove --manifest ABSOLUTE_PATH [--preserve-root ABSOLUTE_PATH]
byte apply --plan PLAN.json [--format text|json]
byte verify --plan PLAN.json [--format text|json]
byte update --check --manifest ABSOLUTE_PATH --artifact-root ABSOLUTE_PATH [--format text|json]
byte update --plan --manifest ABSOLUTE_PATH --artifact-root ABSOLUTE_PATH
byte update --apply PLAN.json
byte setup check --settings ABSOLUTE_PREPARED_TOML
byte setup plan --settings ABSOLUTE_PREPARED_TOML --output ABSOLUTE_NEW_HELPERS_TOML [--home-root ABSOLUTE_PATH --shell bash|zsh --shell-script ABSOLUTE_PATH]
byte setup apply --plan ABSOLUTE_PLAN_PATH --approve PLAN_ID
byte setup verify --plan ABSOLUTE_PLAN_PATH
byte shell plan --home-root ABSOLUTE_PATH --shell bash|zsh --shell-script ABSOLUTE_PATH [--syntax-highlighting ABSOLUTE_PATH]
byte shell apply --plan PLAN.json [--format text|json]
byte shell verify --plan PLAN.json [--format text|json]
byte shell plan-remove --home-root ABSOLUTE_PATH --shell bash|zsh
byte shell remove --plan PLAN.json [--format text|json]
byte doctor --mode off|local-only|ask-before-reporting|automatic-sanitized --component COMPONENT --phase PHASE --error-code CODE --exit-code STATUS [--configuration-schema-version VERSION] [--report-root ABSOLUTE_PATH] [--github-dry-run|--github-submit] [--repository kodiakdirus/byte-core] [--transport-root ABSOLUTE_PATH] [--format text|json]
byte remove --deployment-root ABSOLUTE_PATH [--format text|json]
byte inventory plan --network IPV4_CIDR --output ABSOLUTE_PATH [--mode discover|inspect] [--target IPV4_ADDRESS]
byte inventory scan --plan ABSOLUTE_PLAN_PATH --approve PLAN_ID [--format text|json]
byte inventory import --plan ABSOLUTE_PLAN_PATH --approve PLAN_ID --xml ABSOLUTE_XML_PATH [--format text|json]
byte inventory lookup --capabilities ABSOLUTE_PATH --manufacturer NAME --model MODEL
byte inventory plan-catalog --observations ABSOLUTE_PATH --selection ABSOLUTE_PATH --output ABSOLUTE_PATH [--capabilities ABSOLUTE_PATH] [--previous ABSOLUTE_PATH]
byte inventory apply --plan ABSOLUTE_PLAN_PATH --approve PLAN_ID [--format text|json]
byte inventory verify --plan ABSOLUTE_PLAN_PATH [--format text|json]
```

Unknown commands and unsupported options are usage errors. A reserved command must fail clearly; it must not perform a partial or substitute operation.

## Exit statuses

| Status | Name | Meaning |
| ---: | --- | --- |
| 0 | success | The requested operation completed and its stated postconditions hold. |
| 2 | usage | The command, option, or argument is invalid. |
| 3 | unsupported | The command is unavailable or the detected environment is outside the current support boundary. |
| 4 | invalid-input | Deployment-owned input failed validation. |
| 5 | refused | Safety or ownership checks refused the requested operation. |
| 6 | verification-failed | An applied operation did not satisfy its expected postconditions. |
| 7 | recovery-required | An interrupted or failed mutation requires explicit recovery. |
| 70 | internal-error | Byte Core could not complete the operation because of an internal failure. |

Commands may add structured error codes without changing these process-level categories. Success is never reported solely because a process ran; the command must validate its stated result.

## Output contract

Human-readable text is the default for commands that offer a format option. Planning commands emit JSON directly; `--format json` selects a JSON result on supported noninteractive result paths. JSON uses UTF-8, deterministic key ordering, and standard output. Guided initialization/update and report-review prompts use text; host-readiness refusals before mutation also currently use text even when JSON was requested. Callers must inspect the exit status before parsing. Usage and internal failures use standard error.

Environment-check summaries and diagnostic payloads exclude credentials, environment-variable contents, usernames, home-directory paths, private inventory, arbitrary command output, and inferred deployment facts. Exact plans, interactive target/destination previews, lifecycle JSON results, and initialization recovery guidance contain explicit local paths needed for review. Shell plans also include the proposed managed block. These outputs are private local artifacts, not public diagnostics; never publish them as a transcript or report. Usage errors may repeat supplied arguments, so do not put secrets in command arguments.

## `byte check`

`byte check` is read-only environment discovery. It checks:

- Python is within the currently tested 3.11 through 3.14 range;
- the operating system is macOS or Linux;
- the process environment is POSIX-compatible;
- the machine architecture can be normalized;
- the complete host is an approved v0.1 target (macOS 15 or 26 on `arm64`, or Ubuntu 24.04 or explicitly identified Kubuntu 26.04 on `linux/x86_64`); and
- Git is available and reports a parseable version.

The command does not:

- create, edit, rename, or remove files;
- read deployment configuration or canonical deployment documents;
- inspect shell profiles;
- execute Git operations against a repository;
- access the network;
- resolve credentials;
- collect environment variables or arbitrary command output; or
- claim that installation, initialization, updates, or removal are available.

A supported check returns status 0. A recognized but currently unsupported environment returns status 3 with every check result still shown. An unexpected internal failure returns status 70 with a sanitized error.

The [v0.1 support matrix](support-matrix.md) records the exact operating-system, architecture, runtime, shell, automated-evidence, and manual-evidence boundary. A recognized operating system is not sufficient by itself to claim host support.

Kubuntu recognition requires explicit operating-system/variant identification or a bounded local query proving the Kubuntu desktop metapackage is installed. Display names, KDE session variables, and Ubuntu ancestry alone do not qualify. Plain Ubuntu 26.04 remains unsupported. The package query is read-only and sends no traffic; raw package records are not reported. Kubuntu automated coverage uses fixtures on existing runners, while native acceptance evidence remains pending.

Zsh and shell enhancements are optional on Linux and are not environment-check prerequisites. Byte does not install a shell or modify shell profiles as part of `check`, installation, or initialization.

## Initialization lifecycle

`byte plan init` is read-only and emits a deterministic JSON plan to standard output. The operator may redirect that output to a private local plan file. A plan binds its schema, operation, absolute deployment root, exact relative targets, expected SHA-256 content digests, preconditions, postconditions, backout actions, and plan ID.

`byte apply` accepts only a valid, untampered plan. It re-derives the approved starter content, validates the plan ID and hashes, creates a previously absent deployment root, and creates every file exclusively. It never overwrites an existing path. An exact replay succeeds only when verification proves the existing deployment still matches the plan; any conflicting state is refused.

`byte verify` checks the exact file set and hashes, parses the identity-neutral TOML skeleton, and runs canonical-document validation.

`byte init` is the guided human interface over the same engine. It displays the deployment root, plan ID, exact created files, and backout boundary. Mutation begins only after the operator types the full plan ID.

If apply fails, Byte removes only files created by that invocation whose content still matches the plan. If a created file changed or safe cleanup is otherwise impossible, Byte preserves the remaining state and returns `recovery-required` rather than deleting ambiguous content.

The initial configuration contains only `schema_version = 1`; it does not invent deployment identity or infrastructure facts. The four copied canonical documents become deployment-owned immediately.

Plan files contain exact local target paths and are private local artifacts. They must not be committed to the public repository.

After consequential work, record its governance basis in the deployment-owned
`audit-log.md` when one influenced the activity. Record the standard name and
version, canonical digest or blob when available, applicable addendum, controls
applied, verification basis, validation basis, and limitations. This record is
optional traceability metadata. When used, classify evidence as `verified`,
`reported`, `inferred`, `assumed`, or `unknown`; record freshness as `confirmed`,
`changed`, or `not observable`; and use a precise outcome status such as
`blocked`, `implemented-not-verified`, `verified-not-validated`, `validated`, or
`closed-with-known-limitations`. Byte Core does not retrieve or require an
external governance repository, and the record must not contain credentials,
private transcripts, or broad diagnostic output.

## Removal boundary

Deployment initialization creates only deployment-owned configuration and canonical documents. Accordingly, `byte remove --deployment-root` performs a read-only preservation check for that deployment boundary. It validates the explicit deployment root, configuration schema, and canonical documents; removes nothing; and reports `core_integration_absent`.

Configuration, canonical documents, operator-added files, and unrelated content remain byte-for-byte unchanged. Missing, symbolic-link, malformed, or ambiguous deployment roots are refused. Installed Core files are removed only through `byte plan remove` followed by `byte apply`.

## Installation lifecycle

`byte plan install` and `byte plan remove` are read-only. Their output can be passed unchanged to `byte apply` and `byte verify`.

An install plan inventories a complete, bounded artifact tree; records each relative path, SHA-256 digest, and executable/non-executable mode; targets an immutable `releases/VERSION` directory; and embeds a checksummed installation manifest. Core and state roots are explicit, absolute, non-overlapping paths.

The manifest owns only Core release files and Byte-generated state. It records the manifest schema, Core version, active state, logical roots, release path, artifact digest, managed files, generated state paths, and directories that may be removed only when empty. It must not contain deployment configuration, canonical documents, credentials, inventory, or copied deployment truth.

Install apply reloads and validates the bounded plan, re-scans the artifact, creates absent Core and state roots exclusively, verifies the immutable release, publishes an immutable manifest generation and compatibility copy, and atomically publishes checksummed `active.json` last. A journal supports conservative pre-activation cleanup. Ambiguous cleanup or any post-activation failure returns recovery-required and preserves state for inspection.

Install verification requires the exact manifest, activation metadata, release paths, hashes, and modes. Exact apply replay reports `already_installed`; conflicting existing roots are refused.

A removal plan accepts only an active, integrity-valid compatibility manifest and its complete immutable manifest store. It re-reads every managed release and refuses missing, modified, mode-changed, symbolic-link, escaped, or unowned targets. Its removal list comes exclusively from those manifests. Explicit preservation roots must exist, must not overlap Core-owned paths, and are recorded as postconditions.

Removal apply reloads the exact plan, rebuilds it from the still-active installation, and refuses any difference before mutation. It removes the activation marker first, then only listed files and empty directories. Exact replay succeeds only when every planned target is absent and every preservation root still exists. An interrupted removal returns `recovery_required` and refuses silent partial replay; the reviewed plan is the recovery record.

Plan output contains exact local paths and is a private local artifact. This slice does not implement artifact signing, operating-system defaults, privilege escalation, or release provenance.

## Experimental update lifecycle

`byte plan update` is read-only. It requires a fully verified active installation and a local artifact containing a valid `release.json`. The descriptor—not a caller-supplied version—binds the strictly newer Core version, supported configuration-schema range, explicit migration status, release-notes path, complete file inventory, artifact checksum, and descriptor checksum. The planner inventories those files into a fresh immutable release target and records the descriptor checksum, exact manifest, and activation transition. The existing release is preserved as the backout target. Dirty Core files, altered activation state, missing or changed release content, incompatible schemas, undeclared migrations, existing target releases, same-version replacement, and downgrade requests are refused.

The planner never reads or writes deployment-owned content. An exact update plan may be passed to `byte apply` and `byte verify`. Apply re-verifies both artifacts, creates and verifies the new release, preserves checksum-addressed current and next manifests, re-verifies the backout release, and atomically replaces `active.json` as the commit point. `installation.json` is only a compatibility copy.

Before activation, failure cleanup removes only unchanged paths created by the invocation. After activation, Byte restores the prior activation only when the attempted activation is unchanged and the prior immutable manifest and release still verify; it preserves the new release. Any ambiguity returns recovery-required with the operation journal intact.

The experimental top-level workflow composes these primitives:

- `byte update --check` emits a deterministic eligibility summary without mutation.
- `byte update --plan` emits the exact JSON plan without mutation.
- `byte update --apply PLAN.json` revalidates the current installation and local artifact against that exact plan, displays the checksummed release notes and every target, and mutates only after the operator types the full plan ID. Unsupported hosts are refused before the plan is loaded or a confirmation is requested.

Interactive apply uses text output so its preview and confirmation prompt cannot be confused with machine-readable JSON. Cancellation performs no mutation. Generic `byte apply --plan` remains the non-guided exact-plan engine.

The descriptor and artifact checksums detect mismatch and accidental modification; they do not authenticate publisher identity. This proof does not migrate configuration, fetch releases, verify signatures or tag provenance, garbage-collect releases, or provide automatic update selection. It is not a supported installed command-line interface.

## Optional guided helper setup

`byte setup check` validates an explicitly prepared standalone helpers TOML and checks configured local prerequisites without launching applications, sourcing shell code, inspecting repository contents, or contacting devices. Missing optional choices stay unconfigured; configured unavailable paths or executables prevent planning.

`byte setup plan` binds the prepared file's path and exact digest, a new destination outside Core and Git metadata paths, its existing directory identity, mode `0600`, prerequisite results, backout, and next steps. Keep deployment-owned settings outside version control. It prints private-local JSON and creates nothing. The optional home/shell/asset selections must be supplied together and produce a later shell-planning command; they do not create a shell plan or bind its profile/source state.

`byte setup apply` requires the full reviewed `--approve` ID, rechecks those facts, and exclusively publishes the original TOML bytes as a new mode-`0600` file. Existing files, including a previous apply's output, are never overwritten. `byte setup verify` checks directory identity, regular-file type, exact digest, and mode; it can run after the prepared source is removed. Later customization intentionally makes the original byte verification fail; use `setup check` to inspect current choices.

All setup results are JSON. The workflow creates no directories, profiles, applications, or operational plans and does not persist the environment selector. Settings validation remains separate from authorization to use those settings. Recovery and the separately reviewed loading/profile steps are documented in [Guided helper setup](setup.md).

## Optional helper commands

The `helpers` namespace supplies the configurable runtime behind the sourced Bash/Zsh shortcuts. Its standalone configuration is selected by `--config ABSOLUTE_PATH`, then `BYTE_CORE_HELPERS_CONFIG`, then generic defaults. It does not extend the layered deployment resolver. The complete settings and workflow are in [Helper setup](helpers.md).

```text
byte helpers [--config ABSOLUTE_PATH] config example|validate
byte helpers [--config ABSOLUTE_PATH] config get shell.SETTING
byte helpers [--config ABSOLUTE_PATH] assistant new|resume -- ARGUMENTS...
byte helpers [--config ABSOLUTE_PATH] git-status -- STATUS_ARGUMENTS...
byte helpers [--config ABSOLUTE_PATH] prompt --shell bash|zsh
byte helpers [--config ABSOLUTE_PATH] canisync plan
byte helpers [--config ABSOLUTE_PATH] canisync apply --plan ABSOLUTE_PATH --approve PLAN_ID
byte helpers [--config ABSOLUTE_PATH] labstatus plan --device NAME [--device NAME...]
byte helpers [--config ABSOLUTE_PATH] labstatus run --plan ABSOLUTE_PATH --approve PLAN_ID
byte helpers [--config ABSOLUTE_PATH] wakelan plan --device NAME
byte helpers [--config ABSOLUTE_PATH] wakelan run --plan ABSOLUTE_PATH --approve PLAN_ID
```

Plans and operational results are JSON and may contain private local paths, refs, and device settings. No output is automatically persisted or sent to Byte Care. Planning is offline; operational execution checks the supported host matrix and exact approval. Configuration/plan refusals return `4`, an unsupported host or missing operational prerequisite returns `3`, failed sync preflight after approval returns `5`, partial sync or an uncertain relay timeout returns `7`, and network execution errors return `70`. A completed reachability observation with no response is not a tool error or a claim of offline state. Assistant and Git-status invocations propagate their child's exit status.

## Optional shell lifecycle

The `byte shell` namespace applies the same separation to Bash and Zsh profile integration. `plan` and `plan-remove` are read-only and emit exact private-local JSON plans. `apply`, `verify`, and `remove` load those plans without guessing a home directory or profile.

Version-2 shell plans bind profile existence, bytes, and mode. Installation also binds checksums and modes for the explicit entrypoint, optional `--syntax-highlighting` file, and the selected adjacent native asset when using the packaged `byte-shell.sh` name. Apply, replay, and verification refuse drift in those facts. Version-1 plans must be regenerated. Apply and remove preserve unrelated profile content and use distinct recoverable backups; exact replay is idempotent. A malformed, duplicate, stale, missing, or linked managed block is refused.

The source snapshot follows a fixed dependency contract, with a 4 MiB limit per selected source. It does not recursively bind arbitrary imports, the helper launcher/Python backend, or highlighting later selected through helper configuration. Checks occur during apply, replay, and verification; they do not intercept future shell sourcing. Removal remains possible without unchanged installed source files. See the [shell contract](shell-integration.md#current-boundary) for source coverage and recovery limits.

Zsh syntax highlighting is included only when the operator supplies `--syntax-highlighting` during planning. Byte does not require Zsh on Linux, install packages, modify the login shell, or add syntax highlighting implicitly. The full boundary is documented in the [shell-integration contract](shell-integration.md).

## Byte Care diagnostics

`byte doctor` constructs a fixed-schema report from explicit Byte-owned error fields and normalized runtime identifiers. It never collects arbitrary logs, environment variables, configuration values, inventory, prompts, transcripts, paths, or command output.

Every invocation requires an explicit mode. `off` writes nothing. `local-only` privacy-scans and stores the report under an explicit private-local root. `ask-before-reporting` displays the exact JSON and destination and requires the full stable fingerprint before local storage. `automatic-sanitized` is refused because automatic outbound reporting is unsupported.

Local doctor modes do not access the network. `--github-dry-run` uses the user's authenticated `gh` session to search up to 100 open issues in the official repository and display the proposed create/comment action without GitHub mutation; local report storage still follows the selected mode. `--github-submit` additionally requires the full fingerprint, preserves the exact Markdown locally, limits retries after recorded success, and then asks `gh` to perform that reviewed action. GitHub authorizes the user's own account; Byte ships no token. No mode deploys a fix. See the [Byte Care contract](byte-care.md) for schema, storage, consent, version reporting, transport, and hard-crash limitations.

Remote update discovery and automatic outbound reporting remain unavailable.

## Optional inventory setup

The `inventory` namespace keeps read-only planning, active discovery, offline import, exact-model lookup, reviewed catalog publication, and local verification separate. `--target` may repeat for inspection. Inventory file arguments must be absolute with existing parent directories. Plans and lookup emit JSON; other actions offer text or JSON result summaries. Inventory content is private deployment state and never goes through Byte Care reporting.

`inventory scan`, `import`, and `apply` require the full reviewed plan ID via `--approve`; the CLI does not prompt or infer approval. The assistant should present the plan and collect approval before invoking them. Live scanning alone invokes Nmap and enforces the supported host check. Import, lookup, catalog planning/application, and verification remain offline. Malformed, failed, or out-of-scope scan output is refused; output files are exclusive and previous snapshots are preserved. There is no automatic replay of a scan.

The complete [inventory contract](inventory.md) documents fixed scan limits, identity versus observation, local capability-catalog schemas, result provenance, stale-input checks, error codes, and backout. It also explains why initialization verification is not a general inventory or edited-document verifier.
