from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .adapters import contract_from_modeling, dbt_export, gx_design, observability_test
from .compatibility import CompatibilityRequest, compare_contracts
from .contracts import DataContract, QualityEvent, QualityRule, ValidateRequest, ValidationResult, ValidationBundle
from .engine import compile_contract, validate_bundle
from .scenarios import SCENARIO_ID, ScenarioRequest, data_contract, scenario_definition, scenario_input


def create_app(web_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Data Quality & Contracts System", version="0.1.0")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "data-quality-contracts-system"}

    @app.get("/api/contracts")
    def contracts():
        return {"data_contract": DataContract.model_json_schema(), "quality_rule": QualityRule.model_json_schema(),
                "validation_result": ValidationResult.model_json_schema(), "quality_event": QualityEvent.model_json_schema(),
                "validation_bundle": ValidationBundle.model_json_schema()}

    @app.get("/api/scenarios")
    def scenarios():
        return [{"id": SCENARIO_ID, "title": "Trust 10 current orders", "contract_version": "quality-scenario-v1"}]

    @app.get("/api/scenarios/{scenario_id}")
    def scenario(scenario_id: str):
        if scenario_id != SCENARIO_ID:
            raise HTTPException(404, "Unknown scenario")
        return scenario_definition()

    @app.post("/api/scenarios/{scenario_id}/validate", response_model=ValidationBundle)
    def scenario_validate(scenario_id: str, request: ScenarioRequest):
        if scenario_id != SCENARIO_ID:
            raise HTTPException(404, "Unknown scenario")
        try:
            return validate_bundle(scenario_input(request))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/scenarios/{scenario_id}/preview")
    def preview(scenario_id: str, request: ScenarioRequest):
        if scenario_id != SCENARIO_ID:
            raise HTTPException(404, "Unknown scenario")
        inputs = scenario_input(request)
        return {"datasets": {k: v.model_dump(mode="json") for k, v in inputs.datasets.items()}, "executed_at": inputs.executed_at}

    @app.post("/api/validate", response_model=ValidationBundle)
    def external_validate(request: ValidateRequest):
        try:
            return validate_bundle(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/compatibility")
    def compatibility(request: CompatibilityRequest):
        return compare_contracts(request)

    @app.post("/api/adapters/modeling")
    def modeling(payload: dict):
        try:
            return contract_from_modeling(payload)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/adapters/dbt")
    def dbt():
        return dbt_export(data_contract())

    @app.get("/api/adapters/gx")
    def gx():
        return [gx_design(r) for r in compile_contract(data_contract())]

    @app.post("/api/adapters/observability")
    def observability(event: QualityEvent):
        return observability_test(event, event.rule_id)

    if web_dir and (web_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app()
