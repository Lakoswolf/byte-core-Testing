# Canonical deployment documents

Byte Core uses four deployment-owned Markdown documents as the canonical knowledge model for a self-managed environment. Core supplies generic starter templates and read-only validation; operators own every deployed copy and its contents.

> Byte Core owns behavior and structure; each deployment owns identity and truth.

## Document roles

- `manifest.md` records what is understood to exist now. It is authoritative for declared inventory and relationships, but it does not prove live state.
- `runbook.md` records reviewed operating and recovery procedures. It is authoritative for intended procedure, not for whether a procedure was performed.
- `audit-log.md` records what changed, when, why, and how the result was validated. It does not replace the current-state manifest.
- `notebook.md` records durable lessons, quirks, preferences, and questions that do not yet belong in another canonical source.

When documents disagree, use each document only for its stated authority. Resolve the disagreement through an explicit reviewed change; do not silently infer which deployment fact is correct.

## Machine-readable marker

The first line of each canonical document is exactly:

```text
<!-- byte-core-document: schema=1 role=ROLE -->
```

`ROLE` is one of `manifest`, `runbook`, `audit-log`, or `notebook`. All four documents in a set use the same supported positive schema version. Filenames and roles are unique and fixed for schema 1.

The marker describes document structure only. It must not contain a deployment name, host identity, address, path, credential, or observed state.

## Validation boundary

The internal validator is read-only. It checks required files, exact role markers, synchronized supported schema versions, unique roles, expected top-level headings, and relative Markdown links between files in the document root.

Schema 1 accepts links only among the four canonical documents, including heading fragments. External links, nested paths, and links to other files are rejected. The validator is an internal Python interface, not a standalone document-check CLI. Initialization `verify` also requires the exact original starter file set and hashes, so it is not a general verification command for edited deployment documents.

Validation does not execute commands, access the network, expand environment variables, follow symbolic links, inspect targets outside the document root, or establish that documented infrastructure facts are true.

## Ownership and updates

Starter templates under `templates/canonical/` are Core-managed examples. The experimental initialization flow copies them into a new deployment. The copied files immediately become deployment-owned and routine Core installation or update must never overwrite them.

Operators update the manifest when declared current state changes, the runbook when an approved procedure changes, the audit log after a reviewed action and its validation, and the notebook when durable context does not yet change an authoritative source.

For consequential work, an audit-log entry may include a governance basis: the
guidance standard and version, canonical digest or blob when available,
applicable addendum, controls applied, evidence classification, verification and
validation basis, freshness state, outcome status, and known limitations. Use
`verified`, `reported`, `inferred`, `assumed`, or `unknown` for evidence
classification. Use `confirmed`, `changed`, or `not observable` for freshness,
and do not claim a completed outcome when its status remains blocked or
unverified. This is traceability metadata, not a request for Byte Core to
retrieve or enforce an external standard. Missing governance metadata must not
be replaced with an invented claim of compliance.

Optional [guided inventory](inventory.md) produces separate deployment-owned JSON observations and reviewed device snapshots. These supplement the manifest; the backend never rewrites the four documents. The assistant may propose a reviewed manifest summary based on confirmed catalog entries. Schema-1 link rules remain unchanged, so reference a JSON filename as plain text rather than a Markdown link. New files or edited starter bytes intentionally invalidate the original initialization plan's exact verification; inventory has its own plan verification.

## Optional investigation checkpoint

For a longer investigation, the [troubleshooting guide](troubleshooting.md) recommends a short resumption note when useful. Place unresolved investigation under the notebook's existing `Notes` heading and reviewed actions under the audit log's existing `Entries` heading, only within authorized deployment-document work. No fifth canonical document, new marker, schema key, or automatic writer is introduced. Existing deployed files remain operator-owned; Core updates do not insert this structure.

Use a compact entry such as:

```text
Objective and scope:
Last checked state and when:
Evidence: verified / reported / inferred / assumed / unknown
Explanations rejected and why:
Open question and next useful check:
Actions taken and recovery state, if applicable:
Verification result and objective still to demonstrate:
Authorization still needed, if any:
```

Omit irrelevant fields. Keep only the minimum non-secret summary needed to continue; do not paste transcripts, raw logs, environment values, or broad command output. Real notes belong outside public repositories. Retain the distinction between an earlier observation and current state, and between a recorded decision and authorization for a new action. Corrections should identify which previous conclusion changed.

This optional prose does not change schema-1 heading or link rules. Mention evidence identifiers as plain text when they cannot be linked under those rules. Editing a starter document still makes the original initialization plan's exact verification fail; that result alone is not evidence of damaged deployment data.
