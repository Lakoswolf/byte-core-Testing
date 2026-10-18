# Configuration and ownership

Byte Core separates reusable Core behavior from deployment-owned identity and truth.

> Byte Core owns behavior and structure; each deployment owns identity and truth.

This document defines ownership, configuration resolution, path semantics, updates, migrations, and privacy boundaries. An internal, read-only layered configuration resolver implements the current bootstrap contract, but it is not a stable public API or user-facing command. This document does not select final platform-specific installation paths.

## Configuration format and runtime

Byte Core v0.1 configuration uses TOML 1.0. The initial minimum runtime is Python 3.11.

Byte Core parses TOML with Python's standard-library `tomllib` module. It does not require a third-party runtime parser by default.

`tomllib` is a parser, not a general TOML writer. Experimental initialization creates a new `deployment.toml` containing only `schema_version = 1` from a deterministic template. This does not authorize general rewriting of TOML. Byte Core must not silently rewrite deployment-owned configuration.

## Designing configurable tools

New and rewritten scripts, shell helpers, and apps must expose ordinary deployment choices through documented settings instead of requiring source edits. This general design requirement does not itself add keys to the layered resolver.

- Make relevant paths, device selections, network relays, repository selections, application executables, and presentation preferences configurable. Use generic defaults only when they do not invent deployment facts. Missing required settings must explain what the user needs to configure.
- Keep settings deployment-owned and separate from Core program files. Routine updates preserve them. Provide concise setup instructions and fresh fictional examples with the implementation.
- Define each setting's type, default or required status, validation, and path base. Follow the existing layer precedence. Any command-line override must have documented precedence; do not introduce implicit environment or home expansion.
- Treat configuration as data. Do not source or evaluate configuration as shell code. Where a tool launches a configured application, represent its executable and arguments separately and validate them before invocation. Merely loading settings must not execute an application or contact a network.
- Make optional shell features independently selectable. Preserve existing user preferences and define how disabling or reloading a feature restores or retains its state.
- Validate the resolved settings before an operation and show the relevant targets during planning. Configuring a device, relay, repository, or executable does not authorize its use. Safety invariants remain enforced in code.

The experimental [shell helpers](helpers.md) implement a separate, explicitly selected `helpers.toml` interface with a starter template and read-only validation. It is not a layer of `deployment.toml`: do not add helper keys to the existing layered resolver's files. Helper paths explicitly allow absolute paths and reject parent traversal; they do not expand variables or home-directory shorthand. The helper file's selection uses `--config` before `BYTE_CORE_HELPERS_CONFIG`, then generic defaults if neither is supplied. There is no automatic file discovery or implicit configuration writing. Optional [guided setup](setup.md) checks prepared choices and, after exact-plan approval, creates a new mode-`0600` helper file from the original validated bytes without overwriting existing configuration.

## Logical roots

Byte Core uses logical roots so that ownership does not depend on a particular operating-system layout:

- `CORE_ROOT` contains installed, Core-managed program files, schemas, generic templates, and version metadata.
- `DEPLOYMENT_ROOT` contains deployment-owned configuration and canonical documentation.
- `STATE_ROOT` contains durable state generated and managed by Byte Core.
- `CACHE_ROOT` contains disposable data that Byte Core can rebuild.
- `LOG_ROOT` contains private local logs and diagnostics.
- `RUNTIME_ROOT` contains ephemeral process state.

These names describe roles. They are not environment-variable names or final filesystem paths.

Credentials remain under deployment control in an external credential provider. Byte Core configuration may contain an opaque reference to a credential, but it must not contain or manage the credential value.

## Ownership classes

### Core-managed

Core-managed content includes executable code, schemas, validators, generic templates, public documentation, and Core version metadata.

Byte Core updates may replace a Core-managed file only when the file is listed in the installed Core manifest and its current content matches the expected installed version. Unexpected local modification requires safe refusal or explicit reconciliation.

### Deployment-owned

Deployment-owned content includes configuration, identity, inventory, canonical documentation, credential references, and operator-authored extensions. The optional [inventory backend](inventory.md) stores explicit JSON observations and reviewed catalog snapshots outside Core; it does not add configuration keys, discover configuration layers, or change this resolver's schema.

Byte Core may create a deployment-owned file only through an explicit initialization, helper-setup, or future migration plan. Once created, the file remains deployment-owned. Routine installation and update operations must not overwrite it. Helper setup preserves the prepared TOML's comments and line endings, and its byte verification reports later customization as a change rather than rewriting it.

A newer Core template does not authorize replacement of a file previously created from an older template.

### Byte-generated state

Byte-generated durable state may record the installed Core version, the last successfully validated configuration-schema version, and the state needed to recover an interrupted Byte operation.

Generated state must not become an alternative source of deployment truth. It must not contain credentials or copies of deployment-owned documents.

### Private local artifacts

Caches, logs, diagnostics, reports, temporary plans, and test output are local artifacts. They must remain outside version control and have documented retention and removal behavior.

Ignore rules are defense-in-depth. An ignored location is not approved secret storage.

## Configuration layers

Configuration resolves in this order, from lowest to highest precedence:

1. Core defaults
2. Deployment configuration
3. Platform configuration
4. Host configuration

Tables merge recursively by schema-defined key. Scalars replace lower-precedence scalar values. Arrays replace lower-precedence arrays completely and are not concatenated implicitly.

A higher-precedence layer must not weaken a non-overridable safety invariant.

The current internal resolver accepts caller-supplied layer files and validates schema versions, known keys, and value types. It does not discover layers, connect to inventory, enforce a general safety-policy schema, or provide a public configuration command. Its initial keys cover deployment labels, platform/host selection labels, a workspace-path string, and cache-retention metadata; resolving those values does not perform the described operations.

Resolution is deterministic, records the source layer for every resolved value, and makes no file changes.

Unknown keys, duplicate keys, invalid types, malformed syntax, and unsupported schema versions are errors. Missing optional deployment facts remain unknown. Missing required values produce validation errors; Byte Core must not invent a value.

Configuration does not perform environment-variable interpolation, implicit home-directory expansion, command execution, network access, or credential resolution.

## Schema ownership and versioning

Byte Core owns the configuration schema. A deployment configuration set declares one positive integer `schema_version`, and every participating layer must use that version.

The Core release version and configuration schema version are independent.

A missing, malformed, non-positive, or unsupported future schema version fails safely without modifying files. Initial implementation supports only explicitly documented schema versions.

Any future schema migration must be an explicit version-to-version operation. Checking and planning must be read-only. Applying a migration requires an exact reviewed plan, recoverable backups, and post-migration validation.

Routine Core updates must not silently migrate deployment-owned configuration. No migration engine or migration command is implemented; current update descriptors must explicitly declare that no migration is required.

## Path semantics

The intended configuration path contract uses UTF-8 text and `/` as the logical separator, with relative paths resolved against `DEPLOYMENT_ROOT`.

The internal resolver validates `paths.workspace` in every participating layer, including values later overridden. It accepts a nonempty UTF-8 relative path using `/` separators, up to 4096 characters. Absolute/drive-qualified paths, parent traversal, empty or dot components, backslashes, control characters, home shorthand, and variable/command-expansion syntax are refused. Other helper-file path fields use their separately documented absolute-path schema.

The internal `resolve_workspace_path(configuration, deployment_root)` API resolves this value against an explicit existing absolute deployment directory. It refuses symlinked roots or path components, file components, and targets outside that root. Missing workspace directories are allowed but are not created. Resolving a value does not authorize an operation, prove the target's purpose, or lock its identity against concurrent changes; operational callers must revalidate before mutation. There is no automatic deployment-root selection or public layered-configuration command.

Before mutation, Byte Core resolves the exact filesystem target and verifies containment after accounting for symbolic links. A configured path does not prove that the target exists or establish facts about its contents.

Final operating-system-specific locations are not selected yet. The experimental lifecycle commands require explicit absolute roots and perform their own target and containment checks independently of the internal configuration resolver.

## Updates and preservation

An update may replace only verified Core-managed content.

Deployment configuration, inventory, canonical documentation, credential references, and operator-authored content remain byte-for-byte unchanged during an ordinary Core update.

If a Core-managed file differs from its recorded installed content, Byte Core refuses the update or requires explicit reconciliation. It does not silently discard the local change.

Every mutating operation identifies its exact targets, ownership class, backup, verification steps, and backout procedure before applying changes.

Durable generated state uses atomic replacement where the platform supports it. Interrupted operations retain enough state for deterministic recovery.

Rollback restores Core-managed and Byte-generated state. It does not roll deployment-authored truth backward unless an explicitly approved and backed-up schema migration included those files.

## Repository and installation boundary

The public source repository contains Core-managed source, schemas, generic templates, documentation, and deliberately fictional fixtures.

Repository-local development state belongs outside tracked content. The provisional `.byte-local/`, local configuration patterns, private diagnostics, local reports, logs, credentials, and secrets listed in `.gitignore` remain untracked defense-in-depth locations.

An installed deployment is not defined by the source checkout. Installation and platform-specific root selection belong to the lifecycle and support contracts.

## Privacy

Public files and fixtures must not contain real deployment identities, addresses, paths, services, credentials, inventory, transcripts, diagnostics, or observed state.

Examples use reserved documentation values and newly created fictional identities. Private source material must not be copied, adapted, reconstructed, or redacted into public examples.

Diagnostics and reports are built from an explicit minimal allowlist. Broad logs, environment variables, arbitrary files, and command output are not collected and redacted after the fact.

Unknown deployment facts remain unknown.
