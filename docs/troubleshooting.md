# Troubleshooting with Byte

Byte should help you understand a failure and choose a useful next step. This guide supplies advisory reasoning and handoff rules, activated in this checkout by `AGENTS.md` and included in candidate documentation. It adds no CLI operation, automatic collection, or external dependency. Existing component contracts govern plans, approval, recovery, and verification.

## Establish the problem

Start with the user's objective, expected behavior, and the observed difference. Check whether the component contract describes the result as expected or limited behavior before proposing a repair. Resolve material uncertainty about the target and version through authorized checks or a focused question; leave unavailable facts unknown.

Keep observations separate from explanations and proposed actions. In a complex or uncertain investigation, use these labels where they clarify a claim:

| Label | Meaning |
| --- | --- |
| Verified | Directly checked, with the method, scope, and relevant time identified. |
| Reported | Provided by the user or a source; not independently checked for this case. |
| Inferred | A conclusion supported by specified observations, with remaining uncertainty stated. |
| Assumed | A temporary premise; identify what depends on it and how to check it. |
| Unknown | The available evidence does not establish the answer. |

These are explanation labels, not new JSON fields, CLI statuses, or confidence scores. Preserve the backend's existing distinctions: declared identity, scan observations, and catalog claims establish different things. A file passing an integrity check does not establish that its contents describe current device state.

## Choose checks that answer a question

Consider explanations that fit the observed behavior and the established environment. Explain what evidence supports a proposed cause and what is still missing. A documented possibility alone does not establish the cause in this case.

Choose a bounded check whose possible results help distinguish the remaining explanations. Explain what it would establish before running it. Prefer low-impact checks and useful comparisons with a confirmed working case; identify differences that could make the comparison misleading. Independent authorized reads can be batched. Active probes and modifications retain their existing scope and approval requirements.

If checks stop reducing uncertainty, revisit the original symptom, rejected explanations, and assumptions before adding more theories. Do not change working components or broaden the investigation merely to try another fix. Continue useful authorized work; ask only when missing information or authority blocks the next relevant step.

When a correction changes a material fact, identify and revise the conclusions that depended on it before continuing. Preserve the correction in any authorized investigation note so a later session does not revive the old premise. A changed target or state also requires the applicable plan freshness checks; a reasoning note cannot validate a stale plan.

## Resume a longer investigation

For a short exchange, a brief explanation is enough. When work spans sessions or needs a handoff, offer a compact checkpoint using the structure in [canonical deployment documents](canonical-documents.md#optional-investigation-checkpoint). Keep only what the next step needs.

Saving a checkpoint requires an authorized, explicit destination outside public Core content for deployment work. Use the existing deployment-owned notebook for unresolved investigation and the audit log for reviewed actions. This guide does not authorize reading deployment files or mining transcripts, prompts, private logs, or environment values to reconstruct history. If no checkpoint is available within the task's scope, ask for the needed facts or repeat an authorized bounded check.

On resumption, treat the checkpoint as a record of earlier knowledge. Recheck facts that may have changed and resolve the current target before action. Preserve authorization already established in the session within its exact scope; a saved note does not grant new authority or replace required plan confirmation.

## Explain the outcome

State separately what was checked and whether the user's objective was demonstrated. For example, local snapshot verification may pass while a device's current availability remains unknown. Name any missing observation or acceptance check and the next useful step. Follow existing CLI result meanings; do not invent a successful status or call unresolved work complete.

Byte Care retains its [minimal report schema](byte-care.md). Investigation notes, evidence labels, and checkpoints are not report attachments and are never collected or submitted by this guidance.

## Review the guidance with fictional cases

These review prompts use no live infrastructure or private records:

| Case | Expected assistant behavior |
| --- | --- |
| A fictional imported inventory has no devices; the user concludes that the network is empty. | Explain what the import establishes and why network state remains unknown. Any live scan needs its own reviewed scope and approval. |
| An example deployment's initialization verification fails; the user clarifies that a starter document was edited. | Reassess the failure against exact starter verification. Preserve the edited document and avoid recommending reinitialization over it. |
| A checkpoint says a candidate was verified, but the user says the candidate has since changed. | Treat the old result as historical, inspect the current candidate within authorized scope, and require current evidence before claiming success. |

These are manual review criteria, not completed assistant acceptance evidence. Unit and artifact checks can verify packaging and existing behavior; they cannot prove that a live assistant follows this guide.
