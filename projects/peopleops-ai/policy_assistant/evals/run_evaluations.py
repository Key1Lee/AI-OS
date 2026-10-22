import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
from time import perf_counter

from fastapi.testclient import TestClient

from app.audit import percentile
from app.main import create_app
from app.settings import HRSettings
from app.workday_client import MockWorkdayClient
from evals.common import ROOT, cases
from evals.evaluate_grounding import evaluate_grounding
from evals.evaluate_retrieval import evaluate_retrieval
from evals.evaluate_routing import evaluate_routing
from evals.evaluate_security import evaluate_security
from evals.traceability import traceability_report
from evals.provenance import fingerprint, test_evidence


def reliability(client, settings):
    """Measure actual local HTTP latency and concurrent request success separately from business SLO proposals."""
    client.app.state.orchestrator.workday = MockWorkdayClient(settings)
    def request(index):
        start=perf_counter()
        response=client.post("/ask",headers={"Authorization":"Bearer demo-employee-us"},json={"question":"What is my PTO balance?" if index % 2 else "What is the parental leave policy?"})
        return (perf_counter()-start)*1000, response.status_code == 200 and response.json()["status"]=="answered"
    measurements=[request(i) for i in range(40)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent=list(pool.map(request,range(16)))
    times=[elapsed for elapsed,_ in measurements]
    return {"samples":len(times),"p50_ms":percentile(times,.5),"p95_ms":percentile(times,.95),"p99_ms":percentile(times,.99),
            "successful":sum(ok for _,ok in measurements),"concurrent_successful":sum(ok for _,ok in concurrent),"concurrent_total":len(concurrent),
            "scope":"in-process HTTP, SQLite and synthetic HTTP mock transport on this machine; no production SLA claim"}


def evaluate_all(output, coverage_path=None, optional_judge=False, test_evidence_path=None):
    """Run independent evaluation layers, ranking experiments and explicit release gates."""
    output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="peopleops-evals-") as temporary:
        settings=HRSettings.configured().model_copy(update={"database_path":Path(temporary)/"evaluation.sqlite3","max_requests_per_minute":10000})
        with TestClient(create_app(settings)) as client:
            report={"business_date":settings.as_of_date.isoformat(),"runtime":platform.python_version(),"routing":evaluate_routing(),
                    "retrieval":evaluate_retrieval(settings),"grounding":evaluate_grounding(client,settings),"security":evaluate_security(client,settings),
                    "reliability":reliability(client,settings),"traceability":traceability_report()}
            if optional_judge:
                from evals.judges import LocalQwenJudge
                case=next(c for c in cases("grounding") if "expected_documents" in c)
                result=client.post("/ask",headers={"Authorization":"Bearer demo-"+case["actor"]},json={"question":case["question"]}).json()
                try:
                    judgment=LocalQwenJudge().judge(case["question"],result["answer"],[c["quote"] for c in result["citations"]])
                    report["optional_llm_judge"]={"status":"executed","result":judgment.model_dump(),"release_gate":False}
                except Exception as error:
                    report["optional_llm_judge"]={"status":"unavailable","error_class":type(error).__name__,"release_gate":False}
            else:
                report["optional_llm_judge"]={"status":"not_requested","release_gate":False}
        experiments=[]
        from ingestion.run_pipeline import run_pipeline
        for chunk_size,ranking in [(120,"tfidf"),(600,"tfidf"),(120,"overlap"),(600,"overlap")]:
            experiment=settings.model_copy(update={"database_path":Path(temporary)/f"experiment-{chunk_size}-{ranking}.sqlite3","chunk_chars":chunk_size})
            run_pipeline(experiment)
            measured=evaluate_retrieval(experiment,ranking)
            experiments.append({k:measured[k] for k in ("chunk_chars","ranking","recall_at_5","precision_at_5","returned_result_precision","mrr","coverage","unauthorized_exposure_count","outdated_exposure_count","returned_chunks","mean_context_chars")})
        report["retrieval_experiments"]=experiments
        coverage=json.loads(coverage_path.read_text())["totals"]["percent_covered"] if coverage_path and coverage_path.is_file() else None
        targets=settings.evaluation_gates
        evidence=test_evidence(test_evidence_path or ROOT/"reports/test-run.json", report["traceability"]["tests"].keys())
        gates={
            "routing_accuracy":report["routing"]["accuracy"]["value"] >= targets["routing_accuracy"],
            "recall_at_5":report["retrieval"]["recall_at_5"]["value"] >= targets["recall_at_5"],
            "citation_validity":report["grounding"]["citation_validity"]["value"] >= targets["citation_validity"],
            "extractive_support":report["grounding"]["extractive_support"]["value"] >= targets["extractive_support"],
            "pto_exactness":report["grounding"]["pto_exactness"]["value"] >= targets["pto_exactness"],
            "security":report["security"]["pass_rate"]["value"] >= targets["security_pass_rate"],
            "zero_exposure":report["retrieval"]["unauthorized_exposure_count"]==0 and report["retrieval"]["outdated_exposure_count"]==0,
            "all_answer_cases":report["grounding"]["passed"]==report["grounding"]["total"],
            "mock_p95":report["reliability"]["p95_ms"] < targets["mock_p95_ms"],
            "concurrent_success":report["reliability"]["concurrent_successful"]==report["reliability"]["concurrent_total"],
            "coverage":coverage is not None and coverage>=targets["coverage_percent"],
            "traceability":report["traceability"]["passed"],
            "current_test_evidence":evidence["passed"],
        }
        report["coverage_percent"]=coverage
        report["test_evidence"]=evidence
        report["source_fingerprint"]=fingerprint()
        report["demonstration_targets"]=targets
        report["release"]={"passed":all(gates.values()),"gates":gates,"failed_gates":[k for k,v in gates.items() if not v],"scope":"fictional local reference only; no production release approval"}
    (output/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"release.json").write_text(json.dumps(report["release"],indent=2)+"\n")
    (output/"traceability.json").write_text(json.dumps(report["traceability"],indent=2)+"\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"reports")
    parser.add_argument("--coverage",type=Path,default=ROOT/"reports/coverage.json")
    parser.add_argument("--judge-qwen",action="store_true")
    parser.add_argument("--test-evidence",type=Path,default=ROOT/"reports/test-run.json")
    args=parser.parse_args()
    result=evaluate_all(args.output,args.coverage,args.judge_qwen,args.test_evidence)
    print(json.dumps({"layers":{key:{k:result[key][k] for k in ("passed","total","failed_case_ids")} for key in ("routing","retrieval","grounding","security")},"release":result["release"],"report":str(args.output/"evaluation.json")},indent=2))
    raise SystemExit(0 if result["release"]["passed"] else 1)
