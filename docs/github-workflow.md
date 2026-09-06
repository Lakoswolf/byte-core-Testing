# Working with GitHub through Byte

Byte should help you finish repository work in a state you can understand and maintain. Preparing a change includes its documentation and validation; completing an authorized merge includes checking the result and cleaning up integrated work branches.

This is reusable, Core-owned guidance for an assistant working with Git and GitHub. The Byte Core checkout activates it through `AGENTS.md`, and the candidate builder includes this guide. It is advisory: there is no `byte` command, background service, or hook that publishes changes or enforces this workflow. It does not require a Byte plugin or connector.

## Start with the user's task

You can ask Byte to prepare a change for review, publish a reviewed change, merge a ready pull request, or tidy integrated branches. Byte should establish the current state and carry the requested work through its authorized endpoint, explaining results in plain language.

| Request | Expected endpoint |
| --- | --- |
| Prepare a change | Scoped edits, current documentation, relevant checks, and a reviewable diff; state what remains local. |
| Publish a reviewed change | Verify the destination and outgoing content, push the intended branch, create or update the authorized PR, and report its URL and checks. |
| Merge a ready PR | Check the current reviewed commit, required CI and review rules, merge within the user's authority, verify integration, and clean up eligible branches. |
| Clean up branches | Separate active work from integrated leftovers, preserve recovery information, remove only verified targets, and report what remains. |

Respect authorization already given in the session; do not ask the user to approve the same action repeatedly. Preparation alone does not authorize publication, and publication alone does not authorize a merge, release, or repository-setting change. When authorization is missing, finish the independent preparation first and ask about the concrete result. If access, a repository rule, or an approval system blocks progress, identify that specific action and reason without claiming it succeeded.

## Establish the repository and preserve work

Before mutation, resolve the intended repository, push destination, default branch, current branch and commit, working-tree changes, linked worktrees, and relevant open PRs. Do not assume a remote named `origin` points to the intended project, that the default branch is named `main`, or that a local tracking ref is current. Refresh relevant refs when access allows; stale or unavailable remote evidence cannot justify publication, merge, or deletion.

Preserve unrelated edits and active branches. Use a focused branch or isolated worktree when needed; do not reset, overwrite, silently stash, or carry unrelated work into a commit. Name the exact scope, checks, and backout before applying changes. Check repository-specific contribution and ownership rules rather than applying Byte Core's Python test commands to every project.

Use existing authorized GitHub access when available. Never print credential-bearing remote URLs, tokens, environment values, or broad authentication diagnostics. Missing access is a limitation to explain, not permission to install a connector or change personal settings.

## Prepare a reviewable change

Keep implementation and affected documentation together. Describe what works now, what is still experimental, and which evidence is missing. Run the relevant checks, inspect the complete intended diff, and review the actual files and commits that will leave the machine. Stage only intended paths. Recheck the staged result before committing and the outgoing commits before pushing.

For public material, follow the destination's privacy rules and Byte Core's ownership boundary. Use fresh fictional examples. Do not publish deployment content, transcripts, private diagnostics, credentials, or private repository history; a privacy scanner passing does not replace that review. Keep recovery records outside version-controlled Core content and never use ignored files as secret storage.

Write PR titles and descriptions for a reviewer who has not seen the conversation. Lead with the concrete problem and resulting behavior, then include useful validation, documentation impact, remaining limits, and backout. Update the description when the scope changes. Use a structured body argument or a reviewed body file so newlines and literal text survive correctly; never interpolate untrusted prose into shell commands.

## Publish and merge the reviewed result

Push only the intended branch to the verified destination. Check for an existing matching PR before creating another. A draft can make authorized publication reviewable while work remains; a draft or a successful push is not evidence that the change is ready to merge.

Before merging, recheck the PR's repository, base, current head commit, review requirements, and CI results for that head. Pending, failed, absent, or stale required checks are not passing evidence. Follow the repository's merge method and queue rules; do not bypass protections to finish. If the head changes after review or testing, reassess the new work and its checks.

Bind the merge to the reviewed head when the tool supports it. For example, the [GitHub CLI merge command](https://cli.github.com/manual/gh_pr_merge) provides `--match-head-commit`. A merge queued for later is still pending: report that state until the server confirms completion. Verify the resulting commit is integrated into the intended base before claiming the merge is done. Only synchronize a local base when doing so preserves its work; do not reset local divergence or switch a dirty worktree for convenience.

## Finish with branch cleanup

Cleanup follows an authorized merge without another approval for the same integrated work. It does not include abandoning unmerged work or removing unrelated branches. Treat a separate cleanup request as authorization to inspect and remove verified integrated leftovers within its scope.

1. Refresh branch and PR state. Identify explicit candidates; protect the default branch, designated long-lived branches, active work, and branches needed by other open PRs or worktrees. Branch age, a missing upstream, or a closed PR is not proof of integration.
2. Record each candidate's exact tip. If it is an ancestor of the intended base, its history is integrated. For a squash or rebase merge, check that the tip matches the reviewed PR head and the merged changes are present. Identical trees at the branch tip and an integrated merge commit are sufficient evidence in the simple case; otherwise review the changes and any conflict resolutions. Preserve uncertain work and report why it remains.
3. Keep recoverable branch names and commit IDs before deletion. When original commits are not reachable from the base, preserve and verify a local recovery bundle. Explain where recovery material is kept and its retention limits; temporary storage is not a permanent backup.
4. Recheck that the candidate has not advanced and guard remote deletion against the recorded tip. Git supports an explicit expected value through [`--force-with-lease=<refname>:<expect>`](https://git-scm.com/docs/git-push). Here the guard protects deletion from a concurrent update; it does not authorize rewriting shared history. Stop and reassess if the guard fails.
5. Remove eligible local branches only when no worktree uses them and their local tips are also verified as integrated. If normal local deletion refuses, investigate the reason rather than automatically forcing it. Preserve a branch that now holds new work, even if its former remote branch was deleted. Prune stale remote-tracking refs.
6. Verify the remaining remote and local branches and confirm the user's working files are preserved. Report deferred cleanup, active work, and recovery information.

For a batch, an [atomic push](https://git-scm.com/docs/git-push) can make guarded ref changes succeed or fail together when the server supports it. If an operation partially completes, inspect actual state before retrying; do not replay an old deletion list blindly.

GitHub's [automatic deletion of merged PR branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches) is enabled for Byte Core. It handles eligible remote PR branches; protection rules can prevent deletion. Local cleanup still needs verification. For another repository, propose this setting when useful and change it only within the user's authorized scope.

## Leave a clear handoff

Finish with the outcome, relevant PR or commit, checks actually completed, publication or merge state, remaining active work, and any recovery or manual follow-up. If something remains local, pending, or blocked, say so. Do not describe an uncommitted rule as already available to GitHub users or a passing automated check as completed manual testing.

Reusable improvements belong in Core-owned guidance and, when needed, tested behavior with matching documentation. Express them as generic rules grounded in public requirements; do not reconstruct a conversation, import private operating knowledge, or depend on personal assistant memory. Repository identity, credentials, policies, and observed state remain owned by the user and must be resolved afresh for each task.

## Use outside the Byte Core checkout

An operator can explicitly ask an assistant to follow this guide for another repository, or adopt a reference in that repository's own guidance after review. Keep its project-specific instructions and authorization boundaries in force. Installing Core or initializing a deployment does not install these instructions into other repositories, modify their settings, or grant GitHub access.

The [Codex integration contract](codex-integration.md) describes how this checkout carries advisory guidance. The [contribution guide](../CONTRIBUTING.md) and [repository rules](../AGENTS.md) define Byte Core's own validation and safety requirements. Byte Care's separate [reviewed diagnostic transport](byte-care.md) does not authorize source publication or repository maintenance.
