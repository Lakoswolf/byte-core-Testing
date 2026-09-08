# Codex integration boundary

Byte Core is independent and is not affiliated with or endorsed by OpenAI. Its v0.1 Codex integration uses documented repository-native surfaces and remains optional to Core lifecycle behavior.

## Supported surface map

| Surface | v0.1 status | Ownership and purpose |
| --- | --- | --- |
| Repository `AGENTS.md` | Supported | Public durable repository layout, validation, ownership, safety, and GitHub workflow guidance |
| Project `.codex/config.toml` | Configured; requires project and hook trust | Enables only the repository SessionStart hook |
| Project SessionStart hook | Advisory proof | Emits generic safety context; never blocks tools, mutates files, or collects private context |
| Byte skill | Deferred | Reusable workflows are carried by the CLI contracts and repository guidance; no separate skill is packaged |
| Plugin package | Deferred beyond repository-native MVP validation | No v0.1 plugin, marketplace, app, bundled credential, or auto-install behavior |
| MCP server or app connector | Not required | Core behavior remains local and useful without a connector |
| Codex memory or transcript | Unsupported authority | Never parsed or treated as deployment truth |

The repository does not select a model, reasoning level, provider, credential method, approval policy, sandbox mode, MCP server, or personal configuration. Those remain user or administrator choices.

The optional [inventory workflow](inventory.md) is carried by repository guidance and explicit CLI plans. Discovery findings and manufacturer catalog text are untrusted task data, never instructions or hook input. The assistant can explain plans, help review identity, and research public model documentation with its separately authorized tools. The backend does not grant network access to Codex or perform web research itself.

## Trust and degradation

Codex loads project `.codex/` configuration only for trusted projects. Current Codex also requires review and trust of the exact non-managed hook definition; a new or changed hook is skipped until trusted. See the official [configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic) and [hook trust rules](https://learn.chatgpt.com/docs/hooks). In an untrusted project, with an untrusted hook, or in a Codex version or surface that does not load the configuration, the Python CLI, validators, plans, tests, documentation, and shell assets continue to work unchanged.

The project configuration enables the `hooks` feature and registers one `SessionStart` command. It does not broaden filesystem or network access and does not bypass approvals.

## SessionStart hook

The hook reads one bounded JSON object from standard input. It checks only:

- `hook_event_name` equals `SessionStart`; and
- `source` is one of `startup`, `resume`, `clear`, or `compact`.

It deliberately ignores session IDs, working-directory values, model names, permission metadata, and `transcript_path`. It never opens the transcript or any deployment file. Valid input produces one generic repository-safety `systemMessage`.

Invalid JSON, oversized or excessively nested input, input read errors, unknown events, and missing or malformed sources exit successfully with a generic fallback message directing Codex to `AGENTS.md`. Source type is checked before membership, so arrays and objects cannot raise an unhandled type error. The hook writes no file, report, log, cache, or network request.

The hook retains the documented advisory `continue` and `systemMessage` output fields; it does not block a session or add tool authority. See the official [hook output contract](https://learn.chatgpt.com/docs/hooks). A hook failure never authorizes mutation, publication, or reporting; the repository guidance and CLI remain the fallback.

## Testing and compatibility

Tests parse project TOML, validate the configured hook path and event, run public fictional fixtures through the hook, prove the transcript path is ignored, and verify fallback for invalid JSON, oversized/nested input, wrong top-level and source types, future events, and input read errors. They do not prove behavior for every possible runtime or output-stream failure.

These tests exercise the hook directly. They do not prove that a particular Codex app or CLI version loaded it in a live session. That integration and the guided first-user behavior still require manual evidence. The configured command locates the hook through a Git checkout; an extracted candidate alone is not a verified Codex project-hook installation.

Hook schemas can evolve. Byte accepts only the small documented subset it needs and ignores extra keys. Changes to the hook event or output contract require a new reviewed integration slice. Core functionality must never depend on hook execution.

## Skills and plugins

The v0.1 workflows are expressed as exact CLI plans and repository guidance. The [GitHub workflow](github-workflow.md) now gives assistants reusable preparation, publication, merge verification, and cleanup instructions, with an explicit entry in `AGENTS.md`. It ships in candidate documentation and does not depend on personal memory or hook execution. It remains advisory: no new GitHub command, automatic enforcement, or live assistant acceptance evidence is provided.

A separate Byte skill remains deferred. This workflow has one maintained contract in Core documentation; packaging a skill or distributing instructions to other repositories would require a separately scoped integration change. Installing Core or creating a deployment does not automatically activate the guidance outside this checkout.

Plugin packaging is also deferred. A future plugin must be justified by repository-native MVP evidence, use a valid public manifest, preserve project trust and hook review, remain optional, and introduce no private connector dependency. The public repository will not imply installation, endorsement, or availability before that work is separately approved.
