"""Business exercise coordinator; native execution, validation, and evaluation.

No cloud connectors or sibling domain engines are implemented here. A pinned
fixture describes external conditions; each business transformation is real SQL.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .adapters.bridge import invoke
from .business_catalog import CATALOG, VERSION, public_case, fault_layer
from .contracts import Event, EventType
from .store import StateError, Store

OUTPUT_GRAINS = (
    "one sale per sale_id", "one latest invoice per invoice_id", "one current non-deleted SKU",
    "one delivery event per event_id", "one order per order_id", "one net-revenue sale per sale_id",
    "one valid normalized reading per reading_id", "one modeled scan estimate per requested report",
    "one customer feature row at the stated prediction cutoff", "one order in the committed published snapshot",
)

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def same_rows(left, right):
    return Counter(json.dumps(row,sort_keys=True) for row in left) == Counter(json.dumps(row,sort_keys=True) for row in right)

def business_view(record):
    step = record["learning_step"]
    item = CATALOG[record["scenario_id"]]
    result = {key:deepcopy(record[key]) for key in ("run_id","state","created_at","scenario_id","assistance","kind")}
    result.update(step=step,case=public_case(item,solutions=step>=5),evidence={},feedback={},verification=None)
    # Do not even ship recall/repair options before they become relevant.
    for stage, reveal in (("predict",1),("diagnose",4),("fix",5),("recall",7)):
        if step < reveal:
            result["case"].pop(stage,None)
    if step>=3:
        result["inputs"] = deepcopy(item["tables"])
        result["evidence"] = {name:{key:deepcopy(phase[key]) for key in (
            "rows","row_count","expected_count","value","expected_value","metric_label","model_status",
            "quality_status","publication","quarantine","sql","tests","checks","scope")}
            for name,phase in record["phases"].items()}
    for stage, answers in record["answers"].items():
        if answers and (stage!="predict" or step>=3):
            evaluation=answers[-1]["evaluation"]
            result["feedback"][stage]={key:evaluation[key] for key in ("outcome","score","feedback")}
    if step>=6:
        result["verification"]=deepcopy(record["verification"])
    return result

class BusinessLab:
    def __init__(self, store: Store):
        self.store=store

    def directory(self,record):
        return self.store.root / record["run_id"]

    def save(self,record):
        self.store.save(record)
        directory=self.directory(record)
        (directory/"evidence.json").write_text(json.dumps(record,indent=2)+"\n")
        (directory/"events.jsonl").write_text("".join(json.dumps(e)+"\n" for e in record["events"]))

    def event(self,record,kind,status,phase):
        number=len(record["events"])+1
        record["events"].append(Event(event_id=f"{record['run_id']}:{number}",
            timestamp=datetime.now(timezone.utc).isoformat(),run_id=record["run_id"],scenario_id=record["scenario_id"],
            system="lab",asset="business_output",event_type=kind,status=status,metadata={"phase":phase}).as_dict())

    def start(self,scenario_id):
        if scenario_id not in CATALOG:
            raise StateError("Unknown business exercise")
        item=CATALOG[scenario_id]
        record={"kind":VERSION,"run_id":str(uuid4()),"scenario_id":scenario_id,
            "definition_sha256":fingerprint(item),"created_at":datetime.now(timezone.utc).isoformat(),
            "state":"READY","learning_step":0,"phases":{},"answers":{},"verification":None,
            "events":[],"assistance":{"automated_demo":False,"exposure":"Guided structured choices; prose and independent mastery unassessed"}}
        directory=self.directory(record)
        directory.mkdir()
        (directory/"fixtures.json").write_text(json.dumps(item["tables"],indent=2)+"\n")
        record["fixture_sha256"]=fingerprint(item["tables"])
        for mode in ("healthy","failed","recovered"):
            lines=["flowchart LR"]
            for index,(name,label,_detail) in enumerate(item["layers"]):
                lines.append(f'  n{index}["{name}: {label}"]')
                if index:
                    lines.append(f"  n{index-1} --> n{index}")
            lines += ["  classDef failed fill:#fee2e2,stroke:#b91c1c", "  classDef impact fill:#fef3c7,stroke:#b45309", "  classDef healthy fill:#dcfce7,stroke:#166534", "  classDef recovered fill:#dbeafe,stroke:#1d4ed8"]
            for index in range(len(item["layers"])):
                style="failed" if mode=="failed" and index==fault_layer(item) else "impact" if mode=="failed" and index>fault_layer(item) else "healthy" if mode=="failed" else mode
                lines.append(f"  class n{index} {style}")
            (directory/f"{mode}.mmd").write_text("\n".join(lines)+"\n")
        self.event(record,EventType.RUN_STARTED,"RUNNING","orient")
        self.save(record)
        return record

    def definition(self,record):
        item=CATALOG[record["scenario_id"]]
        if record["definition_sha256"]!=fingerprint(item):
            raise StateError("This exercise definition changed. Keep its evidence and start a fresh exercise.")
        tables=json.loads((self.directory(record)/"fixtures.json").read_text())
        if fingerprint(tables)!=record["fixture_sha256"]:
            raise StateError("Pinned fixtures changed. Start a fresh exercise.")
        return item,tables

    def evaluate(self,record,stage,answer):
        item,_=self.definition(record)
        authored={"scenario_id":item["id"],"concept":item["concept"],"prompt":item[stage]["prompt"],
            "criteria":[["choice","Chosen answer follows this business scenario's authored requirement"]],
            "expected":{"choice":[item[stage]["correct"]]}}
        result=invoke("testing",{"stage":stage,"answer":answer,"authored":authored})
        record["answers"].setdefault(stage,[]).append({"answer":answer,"evaluation":result})
        self.save(record)
        return result

    def phase(self,record,name,policy):
        item,tables=self.definition(record)
        quarantine_sql="SELECT reading_id AS entity_id,text_value,unit,'invalid value or unit' AS reason FROM readings WHERE try_cast(text_value AS INTEGER) IS NULL OR unit NOT IN ('C','F')" if item["number"]==7 and policy=="recovery" else None
        modeled=invoke("modeling",{"tables":tables,"sql":item["sql"][policy],"quarantine_sql":quarantine_sql},worker="business_modeling.py")
        rows=modeled["rows"]
        columns=[{"name":"entity_id","data_type":"STRING","nullable":False}]
        for column in item["expected"][0]:
            if column!="entity_id":
                columns.append({"name":column,"data_type":"INTEGER","nullable":False})
        timestamp=datetime.now(timezone.utc).isoformat()
        contract={"id":"business_contract","dataset_id":"business_output","grain":OUTPUT_GRAINS[item["number"]-1],
            "primary_key":["entity_id"],"columns":columns,"owner":"AE Lab business scenarios",
            "semantic_meaning":item["story"],"rules":[{"id":"expected_volume","name":"Complete expected output",
                "description":"Scenario-specific authored expected record count","target":"business_output","dimension":"volume",
                "expectation":{"kind":"volume","minimum":len(item["expected"]),"maximum":len(item["expected"])}}]}
        quality=invoke("quality",{"contract":contract,"rows":rows,"timestamp":timestamp,"run_id":record["run_id"]},worker="business_quality.py")
        keys_ok=bool(modeled["tests"]) and all(t["status"]=="pass" for t in modeled["tests"])
        matched=same_rows(rows,item["expected"])
        quarantine_ok=(same_rows(modeled["quarantine"],[{"entity_id":"T2","text_value":"N/A","unit":"C","reason":"invalid value or unit"}])
                       if item["number"]==7 else not modeled["quarantine"])
        checks={"complete_business_rows":matched,"declared_key":keys_ok,"native_quality_gate":quality["status"]=="PASS",
                "quarantine_accounted":quarantine_ok}
        trusted=all(checks.values())
        measure=lambda values: len(values) if item["metric"][2]=="count" else sum(row[item["metric"][1]] for row in values)
        phase={"rows":rows,"row_count":len(rows),"expected_count":len(item["expected"]),
            "value":measure(rows),"expected_value":measure(item["expected"]),"metric_label":item["metric"][0],
            "model_status":"PASS" if matched and keys_ok else "FAIL","quality_status":quality["status"],
            "publication":"ELIGIBLE" if trusted else "BLOCKED","quarantine":modeled["quarantine"],
            "sql":item["sql"][policy],"tests":modeled["tests"],"checks":checks,"native_quality":quality,
            "provenance":modeled["provenance"],"scope":item["limits"]}
        # Materialize candidate evidence and release atomically only if trusted.
        with sqlite3.connect(self.directory(record)/"warehouse.sqlite") as db:
            db.execute("CREATE TABLE IF NOT EXISTS snapshots (phase TEXT PRIMARY KEY, output TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS publication (id INTEGER PRIMARY KEY CHECK(id=1), phase TEXT NOT NULL)")
            db.execute("INSERT INTO snapshots VALUES (?,?) ON CONFLICT(phase) DO UPDATE SET output=excluded.output",(name,json.dumps(rows)))
            if trusted:
                db.execute("INSERT INTO publication VALUES (1,?) ON CONFLICT(id) DO UPDATE SET phase=excluded.phase",(name,))
        record["phases"][name]=phase
        self.event(record,EventType.MODEL_COMPLETED,"PASS" if matched else "FAIL",name)
        self.event(record,EventType.QUALITY_CHECK_PASSED if quality["status"]=="PASS" else EventType.QUALITY_CHECK_FAILED,quality["status"],name)
        self.save(record)
        return phase

    def action(self,record,action,answer):
        item,_=self.definition(record)
        step=record["learning_step"]
        actions=["continue","predict","run","continue","diagnose","fix","verify","recall","continue"]
        if step>=9 or action!=actions[step]:
            raise StateError("This action belongs to a different exercise step.")
        if action in {"predict","diagnose","recall"}:
            evaluation=self.evaluate(record,action,answer)
            if action!="predict" and evaluation["outcome"]!="pass":
                return business_view(record)
        elif action=="run":
            # Repeating an interrupted operation replaces its same candidate snapshot.
            self.phase(record,"baseline","recovery")
            self.phase(record,"fault","fault")
            record["state"]="FAILED"
        elif action=="fix":
            if answer.get("choice")!=item["fix"]["correct"]:
                raise StateError("This repair does not address the observed architectural cause. Try another approach.")
            self.phase(record,"recovery","recovery")
            record["state"]="REMEDIATED"
        elif action=="verify":
            record["verification"]={"status":"RUNNING","checks":{}}
            self.save(record)
            before=deepcopy(record["phases"]["recovery"])
            fault=fingerprint(record["phases"]["fault"])
            rerun=self.phase(record,"rerun","recovery")
            with sqlite3.connect(self.directory(record)/"warehouse.sqlite") as db:
                release=db.execute("SELECT s.output FROM publication p JOIN snapshots s ON s.phase=p.phase WHERE p.id=1").fetchone()
            checks={**rerun["checks"],"repair_reconciled":all(before["checks"].values()),
                "deterministic_replay":same_rows(before["rows"],rerun["rows"]),
                "published_snapshot_matches":bool(release) and same_rows(json.loads(release[0]),item["expected"]),
                "fault_evidence_retained":fault==fingerprint(record["phases"]["fault"])}
            record["verification"]={"status":"PASS" if all(checks.values()) else "FAIL","checks":checks}
            self.save(record)
            if not all(checks.values()):
                raise StateError("Verification found a remaining problem.")
            record["state"]="VERIFIED"
        if action=="diagnose":
            record["state"]="DIAGNOSING"
        if step==8:
            # Structured guided success does not award canonical mastery.
            record["state"]="COMPLETED"
            self.event(record,EventType.RUN_COMPLETED,"VERIFIED","connect")
        record["learning_step"]=step+1
        self.save(record)
        return business_view(record)
