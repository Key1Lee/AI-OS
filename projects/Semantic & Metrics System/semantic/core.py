from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATA = Path(__file__).parent / "data"
STATES = ("PROPOSED", "REVIEWED", "APPROVED", "ACTIVE", "DEPRECATED")
CONTRACT_FIELDS = {
    "contract_version", "metric_id", "name", "description", "business_definition", "purpose",
    "owner", "technical_owner", "entity", "grain", "measure", "aggregation", "formula",
    "time_dimension", "timezone", "calendar", "refund_attribution", "filters", "dimensions",
    "currency", "version", "status", "upstream_assets", "consumers", "dependencies", "tests",
    "effective_from", "approval", "previous_version", "change_note", "compatibility", "consumer_migration",
}
MEANING_FIELDS = CONTRACT_FIELDS - {"status", "approval", "technical_owner", "tests", "consumers", "consumer_migration"}
FORMULAS = {
    "gross_revenue": ("gross_order_value", "SUM", ["gross_order_value"]),
    "net_revenue": ("gross_order_value - refund_amount", "SUM", ["gross_order_value", "refund_amount"]),
    "orders": ("order_count", "SUM", ["order_count"]),
    "active_customers": ("distinct_customer_id", "COUNT_DISTINCT", ["order_count"]),
}
REQUEST_FIELDS = {"contract_version", "metric_id", "version", "consumer", "start", "end", "dimensions"}


class SemanticError(ValueError):
    pass


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def read_json(path: str | Path) -> dict:
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise SemanticError("Artifact exceeds 2 MB local bound")
    try:
        value = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SemanticError("Invalid JSON artifact") from exc
    if not isinstance(value, dict):
        raise SemanticError("Artifact must be a JSON object")
    return value


def load_catalog() -> dict:
    return read_json(DATA / "catalog.json")


def load_snapshot() -> dict:
    return read_json(DATA / "commerce.json")


def aware(value: str) -> datetime:
    if not isinstance(value, str):
        raise SemanticError("Timestamp must be a timezone-aware ISO string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SemanticError("Invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise SemanticError("Naive time is ambiguous; include timezone")
    return parsed


def calendar_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise SemanticError("Window dates must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SemanticError("Window dates must use canonical YYYY-MM-DD")
    return parsed


def meaningful(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_contract(contract: dict, catalog: dict) -> None:
    if not isinstance(contract, dict) or set(contract) != CONTRACT_FIELDS:
        raise SemanticError("Metric contract fields must match semantic-metric-v1 exactly")
    if contract["contract_version"] != "semantic-metric-v1":
        raise SemanticError("Unsupported metric contract version")
    for field in ("metric_id", "name", "description", "business_definition", "purpose", "owner", "technical_owner", "version", "effective_from"):
        if not meaningful(contract[field]):
            raise SemanticError(f"Explicit {field} is required")
    if contract["metric_id"] not in FORMULAS or contract["name"] != contract["metric_id"]:
        raise SemanticError("Phase 1 supports four named core metrics")
    parts = contract["version"].split(".")
    if len(parts) != 3 or any(not p.isdigit() for p in parts):
        raise SemanticError("Version must be major.minor.patch")
    aware(contract["effective_from"])
    if contract["entity"] not in catalog["entities"] or contract["grain"] != "order":
        raise SemanticError("Phase 1 evaluates order-grain facts only")
    if contract["entity"] != "Order":
        raise SemanticError("These four metrics evaluate the Order population; customer count has distinct identity semantics")
    if contract["status"] not in STATES:
        raise SemanticError("Unknown lifecycle status")
    if contract["time_dimension"] not in {"created_at", "paid_at", "fulfilled_at", "shipped_at"}:
        raise SemanticError("Explicit supported event-time basis required")
    try:
        ZoneInfo(contract["timezone"])
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise SemanticError("Unknown reporting timezone") from exc
    if contract["calendar"] != "gregorian":
        raise SemanticError("Phase 1 supports Gregorian dates; fiscal calendars need a separate contract")
    if contract["refund_attribution"] != "order_reporting_date_as_of_snapshot":
        raise SemanticError("Phase 1 requires explicit order-cohort refund attribution")
    filters = contract["filters"]
    if not isinstance(filters, dict) or set(filters) != {"status", "currency"}:
        raise SemanticError("Declare status and currency filters; no ad hoc consumer predicates")
    if not isinstance(filters["status"], list) or not filters["status"] or any(not isinstance(v, str) for v in filters["status"]) or len(filters["status"]) != len(set(filters["status"])):
        raise SemanticError("Status filter requires distinct states")
    if any(s not in {"fulfilled", "completed", "paid", "created", "canceled"} for s in filters["status"]):
        raise SemanticError("Unknown lifecycle state in filter")
    if filters["currency"] != "USD" or contract["currency"] != ("USD" if contract["metric_id"] in {"gross_revenue", "net_revenue"} else None):
        raise SemanticError("Phase 1 uses explicit USD population; monetary metrics must declare USD")
    formula, aggregation, measures = FORMULAS[contract["metric_id"]]
    if (contract["formula"], contract["aggregation"], contract["measure"]) != (formula, aggregation, measures):
        raise SemanticError("Declared formula, aggregation and measures disagree with bounded evaluator")
    dimensions = contract["dimensions"]
    if not isinstance(dimensions, list) or not dimensions or any(not isinstance(d, str) for d in dimensions) or len(dimensions) != len(set(dimensions)) or any(d not in catalog["dimensions"] for d in dimensions):
        raise SemanticError("Dimensions must be known and distinct")
    for field in ("upstream_assets", "consumers", "dependencies", "tests", "consumer_migration"):
        values = contract[field]
        if not isinstance(values, list) or any(not meaningful(v) for v in values) or len(values) != len(set(values)):
            raise SemanticError(f"Invalid {field}")
    if not contract["consumers"] or not contract["tests"]:
        raise SemanticError("Declare consumers and verification references")
    if contract["metric_id"] == "net_revenue" and not any(d.startswith("gross_revenue@") for d in contract["dependencies"]):
        raise SemanticError("Net revenue must trace its gross revenue metric dependency")
    expected_assets = {catalog["measures"][m]["source"] for m in measures}
    expected_assets |= {catalog["dimensions"][d]["source"] for d in dimensions}
    if contract["metric_id"] == "active_customers":
        expected_assets.add("dim_customers")
    if set(contract["upstream_assets"]) != expected_assets:
        raise SemanticError("Lineage must name every consumed modeled asset and no unexplained asset")
    if not set(contract["upstream_assets"]) <= set(catalog["assets"]):
        raise SemanticError("Metric references missing upstream lineage asset")
    if any(m not in catalog["measures"] or catalog["measures"][m]["grain"] != contract["grain"] for m in measures):
        raise SemanticError("Measure grain is incompatible")
    if contract["compatibility"] not in {"initial", "compatible", "breaking"}:
        raise SemanticError("Declare version compatibility")
    if contract["previous_version"] is None:
        if contract["compatibility"] != "initial":
            raise SemanticError("Initial definitions must use initial compatibility")
    elif not meaningful(contract["change_note"]) or not contract["consumer_migration"] or contract["compatibility"] == "initial":
        raise SemanticError("Revisions need change note, compatibility and consumer migration")
    approval = contract["approval"]
    if contract["status"] in {"APPROVED", "ACTIVE", "DEPRECATED"}:
        if not isinstance(approval, dict) or set(approval) != {"owner", "evidence", "scope", "approved_at", "meaning_fingerprint"}:
            raise SemanticError("Approved lifecycle requires accountable owner approval evidence")
        if approval["owner"] != contract["owner"] or not meaningful(approval["evidence"]):
            raise SemanticError("Business owner must approve the definition")
        if approval["scope"] != "synthetic_scenario":
            raise SemanticError("Local Phase 1 approvals are synthetic, never real business authority")
        aware(approval["approved_at"])
        if approval["meaning_fingerprint"] != meaning_fingerprint(contract):
            raise SemanticError("Approval does not cover this definition; obtain a new version and owner approval")
    elif approval is not None:
        raise SemanticError("Proposed/reviewed contracts may not claim approval")


def meaning_fingerprint(contract: dict) -> str:
    return fingerprint({key: contract[key] for key in sorted(MEANING_FIELDS)})


class Registry:
    def __init__(self, catalog: dict | None = None):
        self.catalog = copy.deepcopy(catalog if catalog is not None else load_catalog())
        self.validate()

    def validate(self) -> dict:
        catalog = self.catalog
        if catalog.get("contract_version") != "semantic-catalog-v1":
            raise SemanticError("Unsupported semantic catalog")
        if set(catalog.get("entities", {})) != {"Order", "Customer", "Product"} or set(catalog.get("dimensions", {})) != {"date", "channel", "region", "product_category"} or set(catalog.get("measures", {})) != {"gross_order_value", "refund_amount", "order_count"}:
            raise SemanticError("Phase 1 catalog must declare three entities, four dimensions and three measures")
        entity_bindings = {"Order": ("order_id", "fct_orders", "order"), "Customer": ("customer_id", "dim_customers", "customer"), "Product": ("product_id", "dim_products", "product")}
        for name, entity in catalog["entities"].items():
            if entity.get("name") != name or any(not meaningful(entity.get(f)) for f in ("description", "identifier", "identifier_type", "source", "grain", "owner", "identity_policy")):
                raise SemanticError("Entity identity/grain/ownership metadata is incomplete")
            if (entity["identifier"], entity["source"], entity["grain"]) != entity_bindings[name]:
                raise SemanticError("Entity binding disagrees with bounded identity evaluator")
        dimension_bindings = {"date": ("Order", "fct_orders", "event_time_in_metric_timezone"), "channel": ("Order", "fct_orders", "at_order_event"), "region": ("Customer", "dim_customers", "current_snapshot"), "product_category": ("Product", "dim_products", "current_snapshot")}
        for name, dimension in catalog["dimensions"].items():
            if dimension.get("entity") not in catalog["entities"] or any(not meaningful(dimension.get(f)) for f in ("type", "description", "source", "time_behavior", "owner", "relationship")):
                raise SemanticError("Dimension metadata is incomplete")
            if (dimension["entity"], dimension["source"], dimension["time_behavior"]) != dimension_bindings[name]:
                raise SemanticError("Dimension binding disagrees with bounded evaluator")
        measure_bindings = {"gross_order_value": ("fct_orders", "gross_order_value_cents", "SUM"), "refund_amount": ("fct_order_refunds", "refund_amount_cents", "SUM"), "order_count": ("fct_orders", "order_id", "COUNT")}
        for name, measure in catalog["measures"].items():
            if measure.get("grain") != "order" or any(not meaningful(measure.get(f)) for f in ("source", "field", "aggregation", "description", "owner")):
                raise SemanticError("Measure metadata is incomplete or not order-grain")
            if (measure["source"], measure["field"], measure["aggregation"]) != measure_bindings[name]:
                raise SemanticError("Measure binding disagrees with bounded evaluator")
        asset_visiting, asset_visited = set(), set()
        def check_asset(asset):
            if asset not in catalog["assets"]:
                raise SemanticError("Missing upstream lineage asset")
            if asset in asset_visiting:
                raise SemanticError("Asset lineage cycle")
            if asset in asset_visited:
                return
            asset_visiting.add(asset)
            for parent in catalog["assets"][asset]["parents"]:
                check_asset(parent)
            asset_visiting.remove(asset)
            asset_visited.add(asset)
        for asset in catalog["assets"]:
            check_asset(asset)
        keys = set()
        contracts = catalog["metrics"]
        for contract in contracts:
            validate_contract(contract, catalog)
            key = (contract["metric_id"], contract["version"])
            if key in keys:
                raise SemanticError("A metric/version must have one unambiguous contract")
            keys.add(key)
        indexed = {(c["metric_id"], c["version"]): c for c in contracts}
        edges = {}
        for contract in contracts:
            key = f"{contract['metric_id']}@{contract['version']}"
            edges[key] = contract["dependencies"]
            for dependency in contract["dependencies"]:
                parts = dependency.split("@")
                parent = indexed.get(tuple(parts)) if len(parts) == 2 else None
                if parent is None:
                    raise SemanticError("Missing metric dependency")
                for field in ("entity", "grain", "time_dimension", "timezone", "calendar", "filters", "refund_attribution"):
                    if parent[field] != contract[field]:
                        raise SemanticError(f"Metric dependency has incompatible {field}")
                if parent["currency"] != contract["currency"] or not set(contract["dimensions"]) <= set(parent["dimensions"]):
                    raise SemanticError("Metric dependency has incompatible currency/dimensions")
            previous = contract["previous_version"]
            if previous is not None:
                old = indexed.get((contract["metric_id"], previous))
                if old is None or tuple(map(int, contract["version"].split("."))) <= tuple(map(int, previous.split("."))):
                    raise SemanticError("Revision must reference an older existing version")
                if aware(contract["effective_from"]) <= aware(old["effective_from"]):
                    raise SemanticError("Revision effective date must follow prior definition")
                operational = ("formula", "time_dimension", "timezone", "filters", "grain", "dimensions", "refund_attribution", "currency")
                changed = any(contract[f] != old[f] for f in operational)
                if changed and (contract["compatibility"] != "breaking" or int(contract["version"].split(".")[0]) <= int(previous.split(".")[0])):
                    raise SemanticError("Breaking semantic revisions require a new major version")
        visited, active = set(), set()

        def walk(node: str):
            if node in active:
                raise SemanticError("Metric dependency cycle")
            if node in visited:
                return
            active.add(node)
            for parent in edges[node]:
                walk(parent)
            active.remove(node)
            visited.add(node)
        for node in edges:
            walk(node)
        return {"status": "PASS", "metrics": len(contracts), "scope": "synthetic_scenario", "contract_version": "semantic-validation-v1"}

    def get(self, metric_id: str, version: str | None = None, active: bool = True) -> dict:
        candidates = [c for c in self.catalog["metrics"] if c["metric_id"] == metric_id and (version is None or c["version"] == version) and (not active or c["status"] == "ACTIVE")]
        if len(candidates) != 1:
            raise SemanticError("Select one explicit active metric/version; unknown, inactive or ambiguous definition")
        return copy.deepcopy(candidates[0])

    def register(self, contract: dict):
        validate_contract(contract, self.catalog)
        for existing in self.catalog["metrics"]:
            if (existing["metric_id"], existing["version"]) == (contract["metric_id"], contract["version"]):
                if meaning_fingerprint(existing) != meaning_fingerprint(contract):
                    raise SemanticError("Cannot overwrite business meaning within an existing version")
                raise SemanticError("Version already exists; lifecycle transition must use transition()")
        if contract["status"] != "PROPOSED":
            raise SemanticError("New versions enter governance as PROPOSED; advance through owner review and approval")
        candidate = copy.deepcopy(self.catalog)
        candidate["metrics"].append(copy.deepcopy(contract))
        Registry(candidate)
        self.catalog = candidate

    def transition(self, metric_id: str, version: str, target: str, approval: dict | None = None):
        existing = self.get(metric_id, version, active=False)
        current = STATES.index(existing["status"])
        if current == len(STATES) - 1 or target != STATES[current + 1]:
            raise SemanticError("Lifecycle advances exactly one step; deprecated contracts cannot reactivate")
        existing["status"] = target
        if target == "APPROVED":
            existing["approval"] = copy.deepcopy(approval)
        candidate = copy.deepcopy(self.catalog)
        candidate["metrics"] = [existing if (c["metric_id"], c["version"]) == (metric_id, version) else c for c in candidate["metrics"]]
        Registry(candidate)
        self.catalog = candidate


def snapshot_tables(snapshot: dict) -> dict[str, list[dict]]:
    if snapshot.get("contract_version") != "modeled-semantic-snapshot-v1" or snapshot.get("scope") != "synthetic_scenario":
        raise SemanticError("Use an explicit synthetic modeled snapshot in Phase 1")
    aware(snapshot["as_of"])
    if snapshot.get("refund_policy") != "refunded_through_as_of_aggregated_per_order":
        raise SemanticError("Refund snapshot meaning is unknown")
    tables = snapshot.get("tables")
    expected = {"fct_orders": "order_id", "fct_order_refunds": "order_id", "dim_customers": "customer_id", "dim_products": "product_id"}
    if not isinstance(tables, dict) or set(tables) != set(expected):
        raise SemanticError("Snapshot must contain the four declared modeled assets")
    for name, key in expected.items():
        table = tables[name]
        if table.get("grain") != ("order" if name.startswith("fct_") else "customer" if name == "dim_customers" else "product"):
            raise SemanticError("Modeled asset grain disagrees with semantic contract")
        rows = table.get("rows")
        if not isinstance(rows, list) or len(rows) > 200:
            raise SemanticError("Bounded evaluator supports at most 200 rows per asset")
        keys = [r.get(key) for r in rows if isinstance(r, dict)]
        if len(keys) != len(rows) or any(not meaningful(k) for k in keys) or len(set(keys)) != len(keys):
            raise SemanticError(f"Unsafe grain: {name} must have one row per {key}; fanout is forbidden")
    return {name: table["rows"] for name, table in tables.items()}


def evaluate(registry: Registry, snapshot: dict, request: dict) -> dict:
    if set(request) != REQUEST_FIELDS or request.get("contract_version") != "semantic-query-v1":
        raise SemanticError("Query accepts only governed metric/version, consumer, date window and dimensions")
    registry.validate()
    contract = registry.get(request["metric_id"], request["version"])
    if request["consumer"] not in contract["consumers"]:
        raise SemanticError("Consumer is not declared for this metric")
    dimensions = request["dimensions"]
    if not isinstance(dimensions, list) or any(not isinstance(d, str) for d in dimensions) or len(set(dimensions)) != len(dimensions) or not set(dimensions) <= set(contract["dimensions"]):
        raise SemanticError("Requested dimension is incompatible with metric")
    start, end = calendar_date(request["start"]), calendar_date(request["end"])
    if start >= end:
        raise SemanticError("Reporting window is start-inclusive, end-exclusive")
    reporting_start = datetime.combine(start, time.min, tzinfo=ZoneInfo(contract["timezone"]))
    if aware(contract["effective_from"]) > reporting_start:
        raise SemanticError("Version is not effective for the requested reporting window")
    tables = snapshot_tables(snapshot)
    customers = {r["customer_id"]: r for r in tables["dim_customers"]}
    products = {r["product_id"]: r for r in tables["dim_products"]}
    refunds = {r["order_id"]: r for r in tables["fct_order_refunds"]}
    order_ids = {r["order_id"] for r in tables["fct_orders"]}
    if set(refunds) - order_ids:
        raise SemanticError("Refund aggregate references an unknown Order identity")
    tz = ZoneInfo(contract["timezone"])
    as_of = aware(snapshot["as_of"])
    groups = {}
    for row in tables["fct_orders"]:
        required = {"order_id", "customer_id", "product_id", "channel", "status", "currency", "gross_order_value_cents", "created_at", "paid_at", "fulfilled_at", "shipped_at"}
        if set(row) != required:
            raise SemanticError("Order projection must match modeled input contract")
        if row["customer_id"] not in customers or row["product_id"] not in products:
            raise SemanticError("Explicit Customer/Product identity mapping is required; never infer email identity")
        if type(row["gross_order_value_cents"]) is not int or row["gross_order_value_cents"] < 0:
            raise SemanticError("Money requires non-negative integer cents")
        if row["status"] not in contract["filters"]["status"] or row["currency"] != contract["filters"]["currency"]:
            continue
        event = row[contract["time_dimension"]]
        if event is None:
            raise SemanticError("Eligible order lacks its governed time field")
        moment = aware(event)
        if moment > as_of:
            raise SemanticError("Order event is later than the declared snapshot")
        report_day = moment.astimezone(tz).date()
        if not start <= report_day < end:
            continue
        attrs = {"date": report_day.isoformat(), "channel": row["channel"], "region": customers[row["customer_id"]].get("region"), "product_category": products[row["product_id"]].get("product_category")}
        for dim in dimensions:
            value = attrs[dim]
            definition = registry.catalog["dimensions"][dim]
            if not meaningful(value) or definition["allowed_values"] is not None and value not in definition["allowed_values"]:
                raise SemanticError("Slicing attribute is missing or outside its declared semantic domain")
        key = tuple(attrs[d] for d in dimensions)
        group = groups.setdefault(key, {"gross": 0, "refund": 0, "orders": 0, "customers": set()})
        refund = refunds.get(row["order_id"])
        amount = 0 if refund is None else refund.get("refund_amount_cents")
        if type(amount) is not int or amount < 0 or refund is not None and (refund.get("currency") != "USD" or refund.get("as_of") != snapshot["as_of"]):
            raise SemanticError("Refund aggregate requires exact USD cents and matching as-of evidence")
        group["gross"] += row["gross_order_value_cents"]
        group["refund"] += amount
        group["orders"] += 1
        group["customers"].add(row["customer_id"])
    if not dimensions and not groups:
        groups[()] = {"gross": 0, "refund": 0, "orders": 0, "customers": set()}
    values = []
    for key, group in sorted(groups.items()):
        value = {"gross_revenue": group["gross"], "net_revenue": group["gross"] - group["refund"], "orders": group["orders"], "active_customers": len(group["customers"])}[contract["metric_id"]]
        dollars, cents = divmod(abs(value), 100)
        formatted = ("-" if value < 0 else "") + f"{dollars}.{cents:02d}"
        values.append({**dict(zip(dimensions, key)), "value": formatted if contract["currency"] else str(value), "integer_value": value})
    return {"contract_version": "semantic-result-v1", "metric_id": contract["metric_id"], "version": contract["version"], "consumer": request["consumer"], "rows": values, "unit": "USD cents" if contract["currency"] else "count", "currency": contract["currency"], "grain": contract["grain"], "time_dimension": contract["time_dimension"], "timezone": contract["timezone"], "calendar": contract["calendar"], "start": request["start"], "end_exclusive": request["end"], "as_of": snapshot["as_of"], "definition_fingerprint": meaning_fingerprint(contract), "catalog_fingerprint": fingerprint(registry.catalog), "source_fingerprint": fingerprint(snapshot), "scope": "synthetic_scenario", "upstream_assets": contract["upstream_assets"], "owner": contract["owner"]}


def lineage(registry: Registry, metric_id: str, version: str | None = None) -> dict:
    contract = registry.get(metric_id, version)
    nodes, edges = set(), set()
    assets = registry.catalog["assets"]

    def asset_walk(asset: str):
        nodes.add(asset)
        for parent in assets.get(asset, {}).get("parents", []):
            nodes.add(parent)
            edges.add((parent, asset))
            asset_walk(parent)
    for asset in contract["upstream_assets"]:
        asset_walk(asset)
    metric_node = f"{metric_id}@{contract['version']}"
    nodes.add(metric_node)
    for measure in contract["measure"]:
        nodes.add(measure)
        edges.add((registry.catalog["measures"][measure]["source"], measure))
        edges.add((measure, metric_node))
    for asset in contract["upstream_assets"]:
        edges.add((asset, metric_node))
    for dependency in contract["dependencies"]:
        nodes.add(dependency)
        edges.add((dependency, metric_node))
    for consumer in contract["consumers"]:
        nodes.add(consumer)
        edges.add((metric_node, consumer))
    return {"contract_version": "semantic-lineage-v1", "nodes": sorted(nodes), "edges": [{"from": a, "to": b, "evidence": "declared_contract"} for a, b in sorted(edges)], "scope": "synthetic_scenario", "note": "Declared lineage; operational freshness and dependency failures remain Observability evidence"}


def explain(registry: Registry, metric_id: str, version: str | None = None) -> str:
    c = registry.get(metric_id, version)
    return f"{c['name'].upper()} @{c['version']}\n\nOWNER: {c['owner']} (synthetic scenario)\nTECHNICAL OWNER: {c['technical_owner']}\nENTITY: {c['entity']}\nGRAIN: One logical order\nWHY: {c['purpose']}\nBUSINESS DEFINITION: {c['business_definition']}\n\n{', '.join(c['upstream_assets'])}\n  |\n  v\n{c['formula']} [{c['aggregation']}]\n  |\n  v\nfilters: {json.dumps(c['filters'], sort_keys=True)}\n  |\n  v\n{c['time_dimension']} -> {c['timezone']} / {c['calendar']} reporting date\n  |\n  v\n{c['name']}@{c['version']} -> {', '.join(c['consumers'])}\n\nDIMENSIONS: {', '.join(c['dimensions'])}\nREFUNDS: {c['refund_attribution']}\nIDENTITY: canonical customer_id; email/account_id are not interchangeable\nCHECKS: {', '.join(c['tests'])}\n"
