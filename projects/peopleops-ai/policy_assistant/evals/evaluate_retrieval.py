from app.identity import MockIdentityProvider
from app.mock_store import transaction
from app.rag_search import search
from evals.common import cases, outcome, ratio, summarize


def evaluate_retrieval(settings, ranking="tfidf"):
    identities = MockIdentityProvider(settings.fixture_root / "employees.json")
    principals = {entry["demo_token"]: principal for entry, (_, principal) in zip(identities.entries, identities.credential_entries(), strict=True)}
    rows, hits, relevant, retrieved, covered, mrr_sum, positives = [], 0, 0, 0, 0, 0, 0
    unauthorized = outdated = context_chars = returned_chunks = 0
    with transaction(settings.database_path) as conn:
        for case in cases("retrieval"):
            passages = search(conn, case["question"], principals["demo-" + case["actor"]], settings, ranking)
            context_chars += sum(len(p["body"]) for p in passages)
            returned_chunks += len(passages)
            ids = list(dict.fromkeys(p["document_id"] for p in passages))
            gold = set(case["expected_documents"])
            found = len(gold & set(ids))
            denied = len(set(ids) - set(case["allowed_documents"]))
            old = sum(p["metadata"]["status"] != "approved" or (p["document_id"] == "HR-PTO-US" and p["version"] != "2.1") for p in passages)
            unauthorized += denied
            outdated += old
            if gold:
                positives += 1
                relevant += len(gold)
                hits += found
                retrieved += len(ids)
                covered += bool(found)
                mrr_sum += next((1 / (i + 1) for i, doc in enumerate(ids) if doc in gold), 0)
            rows.append(outcome(case["id"], found == len(gold) and denied == 0 and old == 0, retrieved_ids=ids, relevant_hits=found, unauthorized=denied, outdated=old))
    report = summarize(rows)
    report.update({"recall_at_5": ratio(hits, relevant), "precision_at_5": ratio(hits, 5*positives), "returned_result_precision": ratio(hits, retrieved), "coverage": ratio(covered, positives),
                   "mrr": ratio(mrr_sum, positives), "unauthorized_exposure_count": unauthorized, "outdated_exposure_count": outdated,
                   "ranking": ranking, "chunk_chars": settings.chunk_chars,
                   "returned_chunks": returned_chunks, "mean_context_chars": ratio(context_chars, len(rows))})
    return report
