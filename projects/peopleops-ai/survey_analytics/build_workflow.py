"""Generate an importable n8n workflow with readable stages and canvas notes."""

import json
from itertools import pairwise
from pathlib import Path

from .mock_account import DEMO_API_TOKEN

BASE = "http://survey-analytics:8812"


def http_node(name, position, method, route, body=None):
    """Create a bounded, retryable HTTP node; the receiving stages are idempotent."""
    params = {"method": method, "url": route, "options": {"timeout": 10000}}
    if "/mock-qualtrics/exports" in route:
        params.update(
            sendHeaders=True,
            headerParameters={
                "parameters": [{"name": "X-API-TOKEN", "value": DEMO_API_TOKEN}]
            },
        )
    if body is not None:
        params.update(sendBody=True, specifyBody="json", jsonBody=body)
    return {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": position,
        "parameters": params,
        "retryOnFail": True,
        "maxTries": 3,
        "waitBetweenTries": 1000,
    }


def build():
    """Wire the manual and webhook triggers into the same synthetic data pipeline."""
    nodes = [
        {
            "id": "manual",
            "name": "Run synthetic survey",
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [-1080, 0],
            "parameters": {},
        },
        {
            "id": "webhook",
            "name": "Test application webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2.1,
            "position": [-1080, 220],
            "webhookId": "qualtrics-gold-test",
            "parameters": {
                "httpMethod": "POST",
                "path": "qualtrics-gold-test",
                "responseMode": "responseNode",
                "options": {},
            },
        },
        http_node(
            "Start mock Qualtrics export",
            [-840, 80],
            "POST",
            BASE + "/mock-qualtrics/exports",
        ),
        http_node(
            "Check export ready",
            [-600, 80],
            "GET",
            "={{ '" + BASE + "/mock-qualtrics/exports/' + $json.export_id }}",
        ),
        http_node(
            "Download synthetic responses",
            [-360, 80],
            "GET",
            "={{ '" + BASE + "/mock-qualtrics/exports/' + $json.export_id + '/file' }}",
        ),
        http_node(
            "BRONZE - preserve raw export",
            [-120, 80],
            "POST",
            BASE + "/layers/bronze",
            "={{ JSON.stringify($json) }}",
        ),
        http_node(
            "SILVER - validate and deduplicate",
            [120, 80],
            "POST",
            BASE + "/layers/silver",
            "={{ JSON.stringify({batch_id: $json.batch_id}) }}",
        ),
        http_node(
            "GOLD - publish survey metrics",
            [360, 80],
            "POST",
            BASE + "/layers/gold",
            "={{ JSON.stringify({batch_id: $json.batch_id}) }}",
        ),
        {
            "id": "respond",
            "name": "Return metrics to test application",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.4,
            "position": [600, 80],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {},
            },
        },
    ]
    notes = [
        (
            "source-note",
            [-1110, -310],
            720,
            230,
            "## 1 · QUALTRICS TEST SOURCE\n**Synthetic local account + public FAKE API token. No live Qualtrics.**\nManual run or POST webhook → start export → check ready → download.\nAll three source requests send X-API-TOKEN. Local fixture is immediately ready; real adapter needs bounded polling and export parsing.\n**Closed cohort:** 20 invited; 15 raw deliveries including duplicate, revision and invalid score.",
        ),
        (
            "bronze-note",
            [-150, -310],
            260,
            230,
            "## 2 · BRONZE\nImmutable export + SHA-256 batch key.\n15 deliveries → **14 unique versions**.\n1 exact duplicate ignored.\nSQLite: bronze_batches + bronze_responses.\nReplay does not create new rows.",
        ),
        (
            "silver-note",
            [120, -310],
            260,
            230,
            "## 3 · SILVER\nLatest version per response ID, then validate types/ranges.\n**12 accepted · 1 quarantined · 1 superseded.**\n10 completed + 2 partial.\nInvalid newest version never revives an older answer.",
        ),
        (
            "gold-note",
            [390, -310],
            500,
            230,
            "## 4 · GOLD\n**7 metrics** with explicit denominators:\nResponse rate · completion rate · engagement mean · favorable % · CSAT · eNPS · median duration.\nVersioned, atomic SQLite aggregate snapshot.\nSmall department/question groups: all department slices withheld to prevent subtraction disclosure.",
        ),
        (
            "inspect-note",
            [-150, 340],
            1040,
            190,
            "## INSPECT THE DATA FLOW\nExecute workflow, then click each green HTTP node → Output → JSON.\nProduction webhook: POST http://127.0.0.1:5680/webhook/qualtrics-gold-test\nGold viewer: http://127.0.0.1:8812 · API: /layers · SQLite: survey_analytics/data/survey.sqlite3\nRetries: 3 attempts, 1-second wait, 10-second request timeout. Errors stop publication.\nOnly this synthetic workflow saves node outputs; HR chat execution settings are unchanged.",
        ),
    ]
    for name, pos, width, height, content in notes:
        nodes.append(
            {
                "id": name,
                "name": name,
                "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1,
                "position": pos,
                "parameters": {
                    "content": content,
                    "width": width,
                    "height": height,
                    "color": 4,
                },
            }
        )
    sequence = [n["name"] for n in nodes[2:9]]
    connections = {
        name: {"main": [[{"node": sequence[0], "type": "main", "index": 0}]]}
        for name in ("Run synthetic survey", "Test application webhook")
    }
    for source, target in pairwise(sequence):
        connections[source] = {"main": [[{"node": target, "type": "main", "index": 0}]]}
    return {
        "id": "qualtricsGold01",
        "name": "Qualtrics TEST → Bronze → Silver → Gold metrics",
        "active": False,
        "nodes": nodes,
        "connections": connections,
        "settings": {
            "executionOrder": "v1",
            "executionTimeout": 120,
            "saveExecutionProgress": False,
            "saveDataSuccessExecution": "all",
            "saveDataErrorExecution": "all",
            "saveManualExecutions": True,
            "timeSavedMode": "fixed",
            "timeSavedPerExecution": 10,
            "availableInMCP": True,
            "errorWorkflow": "qualtricsGoldError01",
        },
        "pinData": {},
        "tags": [],
    }


def build_cohort():
    """Collect the distinct 5,000-employee export and generate a dashboard after Gold commits."""
    workflow = build()
    workflow.update(
        id="samsaraSurvey5000",
        name="Samsara SYNTHETIC 5,000 employees → department visualization",
    )
    for node in workflow["nodes"]:
        if node["name"] == "Test application webhook":
            node["webhookId"] = "samsara-survey-5000"
            node["parameters"]["path"] = "samsara-survey-5000"
        elif node["name"] == "Start mock Qualtrics export":
            node["parameters"].update(
                sendBody=True,
                specifyBody="json",
                jsonBody='{"dataset":"employees5000"}',
            )
        elif node["name"] == "Return metrics to test application":
            node["position"] = [840, 80]
        elif node["id"] == "source-note":
            node["parameters"]["content"] = (
                "## 1 · SYNTHETIC SAMSARA COHORT\n5,000 UNIQUE fictional employees · 10 illustrative departments.\nFake local Qualtrics account and token. All responses are synthetic.\nStart export → check ready → download all 5,000 rows.\nSkipped questions retain nulls. No live Samsara data or staffing claim."
            )
        elif node["id"] == "bronze-note":
            node["parameters"]["content"] = (
                "## 2 · BRONZE\n5,000 responses, 5,000 unique employee IDs.\nExact source export + immutable content hashes.\nIndependent batch from the 15-row test fixture.\nReplay adds no duplicate rows."
            )
        elif node["id"] == "silver-note":
            node["parameters"]["content"] = (
                "## 3 · SILVER\nValidate scores, timestamps and departments.\n5,000 accepted complete responses.\nMissing individual questions excluded per metric.\nDistinct response grain, no employee-level rankings."
            )
        elif node["id"] == "gold-note":
            node["parameters"]["content"] = (
                "## 4 · GOLD → VISUALIZATION\nCompany + ten department aggregates.\nExperience 0–100 · CSAT favorable % · eNPS −100 to +100.\nQuestion-specific denominators; no invented answers.\nBuild portable HTML + CSV from committed Gold.\nOpen http://127.0.0.1:8812/dashboard"
            )
        elif node["id"] == "inspect-note":
            node["parameters"]["content"] = (
                "## INSPECT THIS WORKFLOW\nPOST /webhook/samsara-survey-5000 triggers source → Bronze → Silver → Gold → visualization.\nDashboard: http://127.0.0.1:8812/dashboard · Gold API: /analytics\nAll 5,000 people and the department mix are fictional. No external account or employee data.\nAn identical rerun reuses the committed batch. Downloads contain aggregates only."
            )
    node = http_node(
        "Build department visualization",
        [600, 80],
        "POST",
        BASE + "/analytics/publish",
        "={{ JSON.stringify({batch_id: $json.batch_id}) }}",
    )
    workflow["nodes"].append(node)
    workflow["connections"]["GOLD - publish survey metrics"] = {
        "main": [[{"node": node["name"], "type": "main", "index": 0}]]
    }
    workflow["connections"][node["name"]] = {
        "main": [
            [{"node": "Return metrics to test application", "type": "main", "index": 0}]
        ]
    }
    return workflow


def build_error_handler():
    """Route n8n failures to a local inbox using only allowlisted operational fields."""
    return {
        "id": "qualtricsGoldError01",
        "name": "Qualtrics TEST - local error notifications",
        "active": False,
        "nodes": [
            {
                "id": "error",
                "name": "Survey workflow failed",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [0, 0],
                "parameters": {},
            },
            http_node(
                "Notify local inbox",
                [300, 0],
                "POST",
                BASE + "/notifications/workflow-error",
                "={{ JSON.stringify({workflow_id: $json.workflow.id, execution_id: String($json.execution?.id || 'trigger'), last_node: $json.execution?.lastNodeExecuted || 'trigger'}) }}",
            ),
        ],
        "connections": {
            "Survey workflow failed": {
                "main": [[{"node": "Notify local inbox", "type": "main", "index": 0}]]
            }
        },
        "settings": {
            "executionOrder": "v1",
            "executionTimeout": 45,
            "availableInMCP": False,
            "saveDataSuccessExecution": "all",
            "saveDataErrorExecution": "all",
        },
        "pinData": {},
        "tags": [],
    }


def build_failure_probe():
    """Provide a synthetic failure probe so the error trigger can be tested end to end."""
    return {
        "id": "qualtricsGoldFailure01",
        "name": "Qualtrics TEST - intentional failure probe",
        "active": False,
        "nodes": [
            {
                "id": "failure-webhook",
                "name": "Failure test webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2.1,
                "position": [0, 0],
                "webhookId": "qualtrics-gold-failure-test",
                "parameters": {
                    "httpMethod": "POST",
                    "path": "qualtrics-gold-failure-test",
                    "responseMode": "onReceived",
                    "options": {},
                },
            },
            {
                "id": "intentional-failure",
                "name": "Intentional checklist failure",
                "type": "n8n-nodes-base.stopAndError",
                "typeVersion": 1,
                "position": [300, 0],
                "parameters": {
                    "errorType": "errorMessage",
                    "errorMessage": "Synthetic production-checklist failure probe",
                },
            },
        ],
        "connections": {
            "Failure test webhook": {
                "main": [
                    [
                        {
                            "node": "Intentional checklist failure",
                            "type": "main",
                            "index": 0,
                        }
                    ]
                ]
            }
        },
        "settings": {
            "executionOrder": "v1",
            "executionTimeout": 30,
            "errorWorkflow": "qualtricsGoldError01",
            "availableInMCP": False,
            "saveDataSuccessExecution": "none",
            "saveDataErrorExecution": "all",
        },
        "pinData": {},
        "tags": [],
    }


if __name__ == "__main__":
    for filename, factory in [
        ("samsara-5000.json", build_cohort),
        ("qualtrics-to-gold.json", build),
        ("qualtrics-error-handler.json", build_error_handler),
        ("qualtrics-failure-probe.json", build_failure_probe),
    ]:
        destination = Path(__file__).parent / filename
        destination.write_text(json.dumps(factory(), indent=2) + "\n")
        print(destination)
