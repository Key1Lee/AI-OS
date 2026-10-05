"""Small explicit content contract; private fields never enter public projections."""
import json
from pathlib import Path

PHASES = ("NEW", "DISCOVERY", "SCOPED", "DESIGNING", "PROTOTYPING",
          "EVALUATING", "HARDENING", "DEPLOYING", "OPERATING", "MEASURING",
          "RETROSPECTIVE", "MASTERED")
MASTERY = ("UNSEEN", "EXPOSED", "UNDERSTOOD", "APPLIED", "DEBUGGED", "TRANSFERRED", "MASTERED")
DIMENSIONS = ("Discovery", "Curiosity", "Problem Framing", "Requirements", "System Design",
              "Software Engineering", "Data Systems", "Distributed Systems", "AI Systems",
              "Reliability", "Security", "Debugging", "Tradeoffs", "Delivery",
              "Communication", "Business Impact")
PRIVATE_FIELDS = {"hidden_realities", "expected_reasoning", "solution", "failure_modes",
                  "business_context", "constraints", "success_metrics"}


def load_scenario(path=None):
    source = Path(path) if path else Path(__file__).parent / "scenarios" / "northstar.json"
    data = json.loads(source.read_text())
    validate_scenario(data)
    return data


def validate_scenario(data):
    required = {"schema_version", "scenario_id", "industry", "customer", "difficulty",
                "stated_problem", "opening", "architecture", "components", "stakeholders",
                "evidence", "technical_concepts", "recall", "hints", "incident", "pilot"} | PRIVATE_FIELDS
    missing = required - data.keys()
    if missing or data.get("schema_version") != 1:
        raise ValueError(f"Invalid scenario contract: missing {sorted(missing)} or unsupported version")
    evidence = data["evidence"]
    concepts = data["technical_concepts"]
    for key, card in evidence.items():
        if not {"title", "keywords", "requires", "text", "concepts"} <= card.keys():
            raise ValueError(f"Incomplete evidence card: {key}")
        if set(card["requires"]) - evidence.keys() or key in card["requires"]:
            raise ValueError(f"Invalid evidence prerequisites: {key}")
    visited, visiting = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError("Evidence prerequisite cycle")
        if key in visited:
            return
        visiting.add(key)
        for parent in evidence[key]["requires"]:
            visit(parent)
        visiting.remove(key)
        visited.add(key)
    for key in evidence:
        visit(key)
    for role, stakeholder in data["stakeholders"].items():
        if not {"name", "title", "opening", "topics"} <= stakeholder.keys():
            raise ValueError(f"Incomplete stakeholder: {role}")
        for topic in stakeholder["topics"]:
            if not {"id", "keywords", "text", "reveals", "concepts"} <= topic.keys():
                raise ValueError(f"Incomplete interview topic: {role}")
            if set(topic["reveals"]) - evidence.keys():
                raise ValueError(f"Unknown evidence in stakeholder {role}")
            if set(topic["concepts"]) - concepts.keys():
                raise ValueError(f"Unknown concept in stakeholder {role}")
    for key, box in data["components"].items():
        if not {"label", "diagram", "internals", "question", "concepts"} <= box.keys():
            raise ValueError(f"Incomplete component: {key}")
    for key, concept in concepts.items():
        if not {"label", "prerequisites", "connections"} <= concept.keys():
            raise ValueError(f"Incomplete concept: {key}")
        if (set(concept['prerequisites']) | set(concept['connections'])) - concepts.keys():
            raise ValueError(f"Unknown concept graph reference: {key}")
    for container in list(evidence.values()) + list(data["components"].values()):
        if set(container.get("concepts", [])) - concepts.keys():
            raise ValueError("Unknown technical concept")
    for prompt in data["recall"]:
        if prompt["concept"] not in concepts:
            raise ValueError("Unknown recall concept")
    recall_ids = [p['id'] for p in data['recall']]
    if len(recall_ids) != len(set(recall_ids)):
        raise ValueError('Recall IDs must be unique')
    if not {"title", "text"} <= data['pilot'].keys():
        raise ValueError('Pilot observations require provenance/title and text')
    if "semantic-contract" not in evidence:
        raise ValueError("SQL exercise requires a semantic-contract card")
    return data
