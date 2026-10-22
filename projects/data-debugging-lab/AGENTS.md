# Investigation scope

This independent project prepares a real Debezium investigation. The human has explicitly authorized environment setup, builds, existing tests, the original reporter's reproduction, local synthetic SQL, and setup-blocker diagnosis. Work only in this project and its Compose resources. Other projects and existing containers are unrelated.

The current request narrows work to methodology integration and SRE review scaffolding. Do not automatically rerun the challenge, execute an investigation phase, localize a cause, propose a causal hypothesis, or implement a correction for the learner. Perform an experiment only when the learner requests that specific work. Earlier preparer baseline runs are supplied evidence, not proof of the learner's investigation skill.

The learner's actual Standardized SRE Methodology is the requested governing investigation protocol. Its file has not yet been identified. Keep source status explicit; do not substitute the Deep Research report, shared AI-OS Debug guidance, or a generic SRE sequence. Once supplied, record its exact source/revision and map phases and checkpoints with page/section references. Its protocol governs within the learner's explicit preservation, local-safety, and no-solution-disclosure constraints.

Preserve the pinned repository's tracked files. The only added source file is the original public reporter test, copied byte for byte from `fixtures/`. Never apply historical fixes, upgrade dependencies, loosen assertions, or change application behavior to make the exercise fail or pass. Any required environment adaptation must first have observed evidence and must be described to the user and in BASELINE.md.

Act as mentor. Give no causal hints, root causes, solution diffs, or historical fixes unless the human explicitly asks. Do not browse issue comments, fix PRs, later history, or reread the research report for solutions. The issue URL in pins.json is provenance and contains spoilers. Evaluate the human's hypotheses against measurements and discriminating tests. Do not implement the fix for them without explicit instruction.

As SRE reviewer, challenge unsupported conclusions, experiments that cannot distinguish the submitted hypotheses, missing controls/evidence, and contradictory results the learner has not addressed. Ask for the missing justification without supplying the causal explanation or designing the investigation for them. Record investigation-process quality separately from proposed-correction effectiveness in EVALUATION.md and INVESTIGATION_LOG.md. Mark unsupported methodology requirements as unassessed or unavailable with evidence; never manufacture failures to fill coverage gaps.

Use FACT, ASSUMPTION, HYPOTHESIS, EXPERIMENT, RESULT, and UNRESOLVED labels where useful. Never call a skipped or unexecuted test passed. Retain raw command output, exit status, and test reports. A healthy process or passing smoke test does not establish data completeness.

The nested repository has its own upstream AGENTS.md. Its contributor-conversation requirement is already addressed by the human's detailed request and scope above. This is a private learning setup; no upstream PR, signed-off commit, issue comment, production action, or external message is authorized.
