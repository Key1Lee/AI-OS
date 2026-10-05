"""Deterministic simulator. Free-text reasoning is reviewed by a human/AI tutor."""
import hashlib
import re
from pathlib import Path

from . import exercise
from .contracts import MASTERY, PHASES

STAGE_TASKS = {
    "frame": {"DISCOVERY"}, "requirements": {"DISCOVERY"},
    "design": {"SCOPED", "DESIGNING"}, "evaluate": {"EVALUATING"},
    "harden": {"HARDENING"}, "debug": {"HARDENING"},
    "measure": {"OPERATING", "MEASURING"}, "explain": {"MEASURING", "RETROSPECTIVE"},
}
RUBRICS = {
    "frame": "Identify stakeholder, workflow, pain, frequency, current workaround, and an evidence-backed problem. Separate facts from assumptions.",
    "requirements": "Cite customer-confirmed metric definition, measurable acceptance, freshness/latency, cost, security, ownership, and unresolved constraints. Do not invent thresholds.",
    "design": "Draw actors, boundaries, components, data/control flows, contracts, state, telemetry, failure/security boundaries. Explain choice, alternative, tradeoff, and when to reconsider. Identify the smallest experiment.",
    "evaluate": "Separate model, system, and business evaluation. Define dataset, expected behavior, metric, customer-approved threshold, regression check, and release decision. Cite executable evidence and remaining gaps.",
    "harden": "Explain authentication/authorization, secrets, timeouts, retry semantics, capacity, telemetry, support ownership, progressive rollout, rollback triggers, and adoption/support plan.",
    "debug": "State impact, timeline, observations, unknowns, hypotheses, disconfirming evidence, containment, causal mechanism, recovery, verification, and prevention.",
    "measure": "Compare observed pilot results with the customer-agreed baseline, metric and time window. Identify adoption, limitations, ownership, and whether the intervention improved the workflow.",
    "explain": "Explain what was solved, evidence, missed reasoning, one mental model, business impact, and what should remain customer-specific versus reusable. State what will reappear later.",
    "hypothesis": "Name the layer, cite observations, and propose the cheapest experiment that could disprove your hypothesis.",
    "answer": "Explain the causal mechanism in your own words and connect it to observed evidence.",
    "recall": "Apply the principle to the new situation. Explain state, failure boundary, and verification; naming a term is insufficient.",
}


class LabError(ValueError):
    pass


def match_score(question, keywords):
    """Bounded whole-word matching; deliberately no claim of natural language understanding."""
    normalized = " ".join(re.findall(r"[\w]+", question.lower()))
    scores = []
    for keyword in keywords:
        phrase = " ".join(re.findall(r"[\w]+", keyword.lower()))
        if phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized):
            scores.append(len(phrase.split()) * 10 + len(phrase))
    return max(scores, default=0)


class Engine:
    def __init__(self, scenario, state, directory):
        self.scenario, self.state, self.directory = scenario, state, Path(directory)

    def event(self, kind, **details):
        item = {"id": f"event-{len(self.state['events']) + 1:04d}", "kind": kind, **details}
        self.state["events"].append(item)
        return item["id"]

    def expose(self, concepts, evidence):
        for key in concepts:
            record = self.state["concepts"][key]
            if record["state"] == "UNSEEN":
                record["state"] = "EXPOSED"
            if evidence not in record["evidence"]:
                record["evidence"].append(evidence)

    def start(self):
        if self.state["phase"] == "NEW":
            self.state["phase"] = "DISCOVERY"
            self.event("started")
        return self.scenario["opening"]

    def next(self):
        if self.state["phase"] in {"NEW", "DISCOVERY"}:
            return self.start()
        return f"Northstar Retail — {self.state['phase']}\n{self.next_prompt()}"

    def next_prompt(self):
        return {
            "DISCOVERY": "What do you want to understand first, and why?",
            "SCOPED": "Design the system. Start with actors and boundaries; defend the smallest valid experiment.",
            "DESIGNING": "Trace one transaction through your design. What can fail, and how will you know?",
            "PROTOTYPING": "Implement your experiment with fde build, then fde test. Explain why it tests your hypothesis.",
            "EVALUATING": "What evidence would justify a release decision, and which kind of evaluation is it?",
            "HARDENING": "Use fde break to begin the incident. What do you know, and what hypothesis would you test first?",
            "DEPLOYING": "Defend your pilot boundary, stop criteria, rollback, and support ownership; fde deploy simulates that pilot.",
            "OPERATING": "Request pilot evidence and measure customer value against the agreed baseline.",
            "MEASURING": "Explain the result, limitations, and what belongs in a reusable capability.",
            "RETROSPECTIVE": "Reconstruct the architecture from memory. Use fde recall to test transfer in a different context.",
            "MASTERED": "Evidence-backed practice complete. Choose a fresh transfer task with your tutor.",
        }.get(self.state["phase"], "What do you want to understand first, and why?")

    def available(self, card):
        return set(card["requires"]) <= set(self.state["released"])

    def release(self, key):
        card = self.scenario["evidence"][key]
        if not self.available(card):
            raise LabError("That artifact is not available from what you have established. Ask its owner about the upstream workflow first.")
        if key not in self.state["released"]:
            self.state["released"].append(key)
            self.event("evidence_released", evidence=key)
            self.expose(card["concepts"], key)
        return f"[{key}] {card['title']}\n{card['text']}"

    def ask(self, role, question):
        people = self.scenario["stakeholders"]
        if role not in people:
            raise LabError("Unknown stakeholder. Use fde stakeholders to see interview contacts.")
        person = people[role]
        ranked = sorted(enumerate(person["topics"]),
                        key=lambda pair: (-match_score(question, pair[1]["keywords"]), pair[0]))
        candidates = [topic for _, topic in ranked if match_score(question, topic["keywords"])]
        self.event("question", stakeholder=role, question=question)
        if not candidates:
            return f"{person['name']} ({person['title']}): {person['opening']}\nI need a more specific question about my work or the evidence you want."
        topic = next((t for t in candidates if all(self.available(self.scenario['evidence'][key])
                     for key in t['reveals'])), None)
        if topic is None:
            return f"{person['name']}: I need the relevant workflow or source artifact established before I can answer that. What upstream evidence would you ask for?"
        self.expose(topic.get("concepts", []), self.state["events"][-1]["id"])
        released = [self.release(key) for key in topic["reveals"]]
        return f"{person['name']} ({person['title']}): {topic['text']}" + ("\n\n" + "\n\n".join(released) if released else "")

    def investigate(self, question):
        # Incident logs are separate and only accessible once the failure has been injected.
        if self.state["incident"] and match_score(question, ["incident", "retry", "delivery", "replay", "log"]):
            return self.incident_evidence()
        if self.state["phase"] in {"OPERATING", "MEASURING", "RETROSPECTIVE", "MASTERED"} and match_score(question, ["pilot", "adoption", "measurement", "business impact"]):
            return self.pilot_evidence()
        ranked = sorted(self.scenario["evidence"].items(),
                        key=lambda pair: (-match_score(question, pair[1]["keywords"]), pair[0]))
        candidates = [(key, card) for key, card in ranked if match_score(question, card["keywords"] + [key])]
        if not candidates:
            self.event("investigation", question=question, found=False)
            return "No matching artifact found. Name the observation, system, or contract you want to inspect; no evidence has been released."
        # Never substitute a lower-ranked topic for a locked requested artifact.
        key, card = candidates[0]
        result = self.release(key)
        self.event("investigation", question=question, evidence=key)
        return result + "\n\nWhat does this establish, and what would disprove your current hypothesis?"

    def evidence(self, key=None):
        if key:
            if key == "incident-logs" and key in self.state["released"]:
                return self.incident_evidence()
            if key == "pilot-results" and key in self.state["released"]:
                return self.pilot_evidence()
            if key not in self.state["released"]:
                raise LabError("That evidence has not been released. Ask a stakeholder or investigate a specific question.")
            return self.release(key)
        cards = self.state["released"]
        return "Released evidence:\n" + ("\n".join(f"- {key}" for key in cards) if cards else "None yet. Ask a stakeholder or investigate a specific question.")

    def diagram(self):
        self.event("diagram_requested")
        return self.scenario["architecture"] + "\n\nTrace one transaction. Which boundary would you open first?"

    def open(self, component):
        box = self.scenario["components"].get(component)
        if not box:
            raise LabError("Unknown component. Available: " + ", ".join(self.scenario["components"]))
        event = self.event("component_opened", component=component)
        self.expose(box["concepts"], event)
        return f"{box['label']}\n{box['diagram']}\n\n{box['internals']}\n\n{box['question']}"

    def submit(self, kind, text, citations=()):
        if kind in STAGE_TASKS and self.state["phase"] not in STAGE_TASKS[kind]:
            raise LabError(f"{kind} is not available during {self.state['phase']}. {self.next_prompt()}")
        if not text.strip():
            raise LabError("Record your reasoning, not just a task name.")
        unknown = set(citations) - set(self.state["released"]) - {e['id'] for e in self.state['events']}
        if unknown:
            raise LabError("Cite only released evidence or recorded experiment events: " + ", ".join(sorted(unknown)))
        if kind in STAGE_TASKS and not citations:
            raise LabError("Cite at least one released artifact or experiment event with --evidence.")
        if kind == "recall" and not self.state["pending_recall"]:
            raise LabError("Request fde recall before answering.")
        item = {"id": f"submission-{len(self.state['submissions']) + 1:04d}", "kind": kind,
                "text": text, "citations": list(citations), "phase": self.state["phase"]}
        if kind == "recall":
            item["prompt"] = self.state["pending_recall"]
            self.state["pending_recall"] = None
        self.state["submissions"].append(item)
        self.event("learner_submission", submission=item["id"])
        if kind == "design":
            self.state["phase"] = "DESIGNING"
        identified = f"Your {kind} reasoning has been saved as {item['id']}."
        missing = "A tutor must assess the causal reasoning; keyword matches do not establish understanding."
        return f"YOU IDENTIFIED:\n{identified}\n\nYOU'RE MISSING:\n{missing}\n\nWHY IT MATTERS:\n{RUBRICS[kind]}\n\nNEXT QUESTION:\n" + ("What evidence would falsify this?" if kind == "hypothesis" else "Explain the weakest assumption in your reasoning.")

    def current_reviews(self):
        latest = {}
        for review in self.state['reviews']:
            latest[review['submission']] = review
        return list(latest.values())

    def reviewed(self, kind):
        item = next((s for s in reversed(self.state['submissions']) if s['kind'] == kind), None)
        if not item:
            return False
        review = next((r for r in reversed(self.state['reviews']) if r['submission'] == item['id']), None)
        return bool(review and review['result'] == 'demonstrated')

    def refresh_learning(self):
        current = self.current_reviews()
        submissions = {s['id']: s for s in self.state['submissions']}
        for key, record in self.state['concepts'].items():
            relevant = [r for r in current if r.get('concept') == key]
            record['state'] = 'EXPOSED' if record['evidence'] else 'UNSEEN'
            if not relevant:
                continue
            # A regression stays visible until its actual answer is reassessed.
            if any(r['result'] == 'developing' for r in relevant):
                continue
            record['state'] = 'UNDERSTOOD'
            kinds = {submissions[r['submission']]['kind'] for r in relevant}
            applied = bool(kinds & {'design', 'evaluate'}) and bool(self.state['exercise'] and self.state['exercise']['passed'])
            debugged = 'debug' in kinds and self.state['incident_passed']
            if applied or debugged:
                record['state'] = 'DEBUGGED' if debugged else 'APPLIED'
            transfer_prompts = {submissions[r['submission']].get('prompt') for r in relevant
                                if submissions[r['submission']]['kind'] == 'recall'}
            transfers = {p['id'] for p in self.scenario['recall']
                         if p['id'] in transfer_prompts and p['transfer'] and p['concept'] == key}
            if transfers and (applied or debugged):
                record['state'] = 'TRANSFERRED'
            if len(transfers) >= 2 and debugged:
                record['state'] = 'MASTERED'
        for key, record in self.state['performance'].items():
            relevant = [r for r in current if r.get('dimension') == key]
            if not relevant:
                record['state'] = 'UNSEEN'
            elif any(r['result'] == 'developing' for r in relevant):
                record['state'] = 'DEVELOPING'
            else:
                record['state'] = 'CONSISTENT' if len(relevant) >= 3 else 'DEMONSTRATED'
        if self.state['phase'] == 'MASTERED' and sum(r['state'] == 'MASTERED' for r in self.state['concepts'].values()) < 2:
            self.state['phase'] = 'RETROSPECTIVE'

    def review(self, submission, result, note, concept=None, dimension=None, tutor=None):
        item = next((s for s in self.state['submissions'] if s['id'] == submission), None)
        if not item:
            raise LabError('Submission does not exist.')
        if result not in {'developing', 'demonstrated'}:
            raise LabError('Assessment must be developing or demonstrated.')
        if not tutor or not note.strip():
            raise LabError('Tutor review requires --tutor and an evidence-based --note; this is an explicit assessment, not automated grading.')
        if concept and concept not in self.state['concepts']:
            raise LabError('Unknown concept.')
        if dimension and dimension not in self.state['performance']:
            raise LabError('Unknown performance dimension.')
        if item['kind'] == 'recall' and concept:
            prompt = next(p for p in self.scenario['recall'] if p['id'] == item['prompt'])
            if prompt['concept'] != concept:
                raise LabError('Recall review concept must match the actual prompt.')
        if result == 'demonstrated' and item['kind'] in STAGE_TASKS and not item['citations']:
            raise LabError('Stage assessments must cite scenario evidence.')
        review = {'id': f"review-{len(self.state['reviews']) + 1:04d}", 'submission': submission,
                  'result': result, 'note': note, 'tutor': tutor, 'concept': concept, 'dimension': dimension}
        self.state['reviews'].append(review)
        self.event('tutor_review', review=review['id'])
        if dimension:
            self.state['performance'][dimension]['evidence'].append(review['id'])
        if concept:
            self.state['concepts'][concept]['evidence'].append(review['id'])
        self.refresh_learning()
        self.advance()
        return f"{review['id']}: {result}, assessed by {tutor}.\n{note}\nPhase: {self.state['phase']}\n{self.next_prompt()}"

    def advance(self):
        phase = self.state["phase"]
        if phase == "DISCOVERY" and self.reviewed("frame") and self.reviewed("requirements") and "semantic-contract" in self.state["released"]:
            self.state["phase"] = "SCOPED"
        elif phase == "DESIGNING" and self.reviewed("design"):
            self.state["phase"] = "PROTOTYPING"
        elif phase == "EVALUATING" and self.reviewed("evaluate") and self.state["exercise"] and self.state["exercise"]["passed"]:
            self.state["phase"] = "HARDENING"
        elif phase == "HARDENING" and self.reviewed("harden") and self.reviewed("debug") and self.state["incident_passed"]:
            self.state["phase"] = "DEPLOYING"
        elif phase == "OPERATING" and self.reviewed("measure"):
            self.state["phase"] = "MEASURING"
        elif phase == "MEASURING" and self.reviewed("explain"):
            self.state["phase"] = "RETROSPECTIVE"
        elif phase == "RETROSPECTIVE" and sum(r['state'] == 'MASTERED' for r in self.state['concepts'].values()) >= 2:
            self.state["phase"] = "MASTERED"

    def build(self):
        if self.state["phase"] not in {"PROTOTYPING", "EVALUATING", "HARDENING"}:
            raise LabError("First establish the problem and requirements, then submit a tutor-reviewed design.")
        if not all(self.reviewed(kind) for kind in ("frame", "requirements", "design")):
            raise LabError("The current framing, requirements, and design must each have a tutor review.")
        if "semantic-contract" not in self.state["released"]:
            raise LabError("Establish the customer metric contract before implementation.")
        workspace = self.directory / "workspace"
        workspace.mkdir(exist_ok=True)
        for name, content in (("revenue.sql", exercise.starter()), ("fixture.sql", exercise.public_fixture()), ("TASK.txt", exercise.task())):
            path = workspace / name
            if not path.exists():
                path.write_text(content)
        self.event("exercise_created")
        return exercise.task() + f"\n\nEdit {workspace / 'revenue.sql'}\nInspect {workspace / 'fixture.sql'}\nRun fde test; the lab does not write the repair for you."

    def test(self, path=None):
        if self.state['phase'] not in {'PROTOTYPING', 'EVALUATING', 'HARDENING', 'DEPLOYING'} or not (self.directory / 'workspace' / 'revenue.sql').exists():
            raise LabError("Use fde build after the design gate before executing an exercise.")
        source = Path(path).resolve() if path else Path(self.state.get("active_exercise", self.directory / "workspace" / "revenue.sql"))
        sql = source.read_text()
        result = exercise.check(sql, incident=self.state["incident"])
        event = self.event("exercise_tested", artifact_hash=result['artifact_hash'], passed=result['passed'], incident=self.state['incident'])
        self.state["exercise"] = result
        self.state["exercise_path"] = str(source)
        if self.state["incident"]:
            self.state["incident_passed"] = result["passed"]
        self.refresh_learning()
        if result["passed"] and self.state["phase"] == "PROTOTYPING":
            self.state["phase"] = "EVALUATING"
        self.advance()
        checks = "\n".join(f"{'PASS' if c['passed'] else 'FAIL'} {c['name']}: {c['detail']}" for c in result['checks'])
        return f"{event} | {'PASS' if result['passed'] else 'FAIL'}\n{checks}\n\nWhat principle explains the result, and what does this test leave unproven?"

    def break_system(self):
        if self.state["phase"] != "HARDENING":
            raise LabError("The failure is introduced after a passing prototype and reviewed evaluation.")
        if not self.state["incident"]:
            workspace = self.directory / "workspace"
            workspace.mkdir(exist_ok=True)
            branch = workspace / "incident.sql"
            if branch.exists():
                raise LabError("An incident branch already exists. Preserve or rename it before injecting this failure.")
            branch.write_text(exercise.incident_starter())
            self.state["active_exercise"] = str(branch)
            self.state["incident"] = True
            self.state["incident_passed"] = False
            self.event("incident_injected")
        return self.scenario["incident"]["opening"] + f"\n\nActive local branch: {self.state['active_exercise']}\nRun fde test to reproduce the failed check. Your original revenue.sql is preserved.\n\nWhat do you know, what do you not know, and what evidence would test your first hypothesis?"

    def incident_evidence(self):
        if not self.state["incident"]:
            raise LabError("There is no active simulated incident.")
        if "incident-logs" not in self.state["released"]:
            self.state["released"].append("incident-logs")
            self.event("incident_evidence_released")
        return "\n\n".join(f"[{card['id']}] {card['title']}\n{card['text']}" for card in self.scenario['incident']['evidence'])

    def deploy(self):
        if self.state['phase'] != 'DEPLOYING':
            raise LabError('Pilot gate requires reviewed hardening/debugging and a passing replay regression.')
        if not all(self.reviewed(kind) for kind in ('frame', 'requirements', 'design', 'evaluate', 'harden', 'debug')):
            raise LabError('Current learner artifacts require demonstrated tutor reviews before the pilot.')
        tested = self.state['exercise']
        source = Path(self.state.get('exercise_path', self.directory / 'workspace' / 'revenue.sql'))
        if not tested or not tested['passed'] or not self.state['incident_passed'] or not source.exists():
            raise LabError('The pilot needs an existing, passing replay-tested SQL artifact.')
        sql = source.read_text()
        if hashlib.sha256(sql.encode()).hexdigest() != tested['artifact_hash']:
            raise LabError('SQL changed after its replay check. Return to fde test before deploying.')
        # Re-execute the exact recorded artifact before moving the synthetic pilot.
        if not exercise.check(sql, incident=True)['passed']:
            raise LabError('The current artifact no longer passes the pilot regression.')
        self.state['phase'] = 'OPERATING'
        self.event('simulated_pilot_deployed', artifact_hash=tested['artifact_hash'])
        return 'SIMULATED PILOT: limited executive read-only access; no external service has been deployed.\nRequest pilot results. What would make you pause or roll back?'

    def pilot_evidence(self):
        if self.state['phase'] not in {'OPERATING', 'MEASURING', 'RETROSPECTIVE', 'MASTERED'}:
            raise LabError("Pilot observations are available only after the simulated rollout.")
        if "pilot-results" not in self.state['released']:
            self.state['released'].append('pilot-results')
            self.event('pilot_results_released')
        pilot = self.scenario['pilot']
        return f"[pilot-results] {pilot['title']}\n{pilot['text']}"

    def recall(self):
        prompts = self.scenario["recall"]
        if self.state["pending_recall"]:
            prompt = next(p for p in prompts if p['id'] == self.state['pending_recall'])
        else:
            # Give struggled concepts priority, then cycle through different contexts.
            cursor = self.state['recall_cursor']
            ordered = prompts[cursor % len(prompts):] + prompts[:cursor % len(prompts)]
            struggling = {r['concept'] for r in self.current_reviews() if r['result'] == 'developing' and r.get('concept')}
            recent = {s['prompt'] for s in self.state['submissions'][-3:] if s['kind'] == 'recall'}
            prompt = next((p for p in ordered if p['concept'] in struggling and p['id'] not in recent), ordered[0])
            self.state['pending_recall'] = prompt['id']
            self.state['recall_cursor'] = prompts.index(prompt) + 1
            self.event('recall_requested', prompt=prompt['id'])
            self.expose([prompt['concept']], self.state['events'][-1]['id'])
        return f"[{prompt['id']}] {prompt['prompt']}\n\nAnswer with fde answer --kind recall."

    def hint(self):
        self.state['hint_level'] = min(self.state['hint_level'] + 1, len(self.scenario['hints']))
        self.event('hint_requested', level=self.state['hint_level'])
        return f"Hint {self.state['hint_level']}: {self.scenario['hints'][self.state['hint_level'] - 1]}"

    def solution(self):
        self.event('solution_explicitly_requested')
        return self.scenario['solution'] + "\n\nNow use fde recall and apply the principle to a new context."

    def progress(self):
        lines = [f"Northstar Retail — {self.state['phase']}", f"Released artifacts: {len(self.state['released'])}",
                 "Concepts (each evidence reference is a saved artifact/event/review):"]
        for key, record in self.state['concepts'].items():
            lines.append(f"- {key}: {record['state']} | {', '.join(record['evidence']) or 'no evidence yet'}")
        lines.append("Performance:")
        for key, record in self.state['performance'].items():
            lines.append(f"- {key}: {record['state']} | {', '.join(record['evidence']) or 'no evidence yet'}")
        return "\n".join(lines)

    def graph(self):
        lines = ["FDE", "  Business: discovery → workflow → requirements → value", "  Systems: software / data / APIs / AI / security / reliability", "  Delivery: prototype → evaluate → deploy → operate → adopt → measure", "", "Concept connections:"]
        for key, concept in self.scenario['technical_concepts'].items():
            lines.append(f"{key} [{self.state['concepts'][key]['state']}] → " + ", ".join(concept['connections']))
        return "\n".join(lines)

    def log(self):
        # Only learner actions/released observations, never internal hidden scenario fields.
        import json
        return json.dumps({key: self.state[key] for key in ('events', 'submissions', 'reviews')}, indent=2)

    def end(self):
        demonstrated = [r for r in self.current_reviews() if r['result'] == 'demonstrated']
        developing = [r for r in self.current_reviews() if r['result'] == 'developing']
        solved = "Executable prototype passed its fixture checks." if self.state['exercise'] and self.state['exercise']['passed'] else "No verified executable fix yet."
        understood = "; ".join(r['note'] for r in demonstrated[-2:]) or "No tutor-reviewed understanding recorded yet."
        missed = "; ".join(r['note'] for r in developing[-2:]) or "No assessed gaps recorded; unassessed work remains unproven."
        return (f"WHAT YOU SOLVED\n{solved}\n\nWHAT YOU UNDERSTOOD\n{understood}\n\nWHAT YOU MISSED\n{missed}\n\n"
                "ONE IMPORTANT MENTAL MODEL\nTrace one observation through every boundary; test causal claims with evidence.\n\n"
                "WHAT WILL REAPPEAR LATER\nThe weakest assessed principle will return in a different workflow.\n\n" + self.recall())
