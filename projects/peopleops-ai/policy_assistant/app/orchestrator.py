"""Deterministic orchestration with measured stages and privacy-safe inspectors."""
import re
from time import perf_counter

from app.audit import write_audit
from app.diagnostics import ExecutionTrace
from app.intent_router import DeterministicRouter
from app.models import HRResponse, Intent, SourceAccess
from app.permissions import may_read_pto
from app.rag_search import authorized_chunks, search
from app.response_builder import policy_response, record_response, simple_response
from app.rules import default_rules
from app.security import suspicious_instruction
from app.workday_client import RecordError, validate_record


class Orchestrator:
    def __init__(self, settings, workday, retriever=search, router=None, rulebook=None):
        self.settings, self.workday, self.retriever = settings, workday, retriever
        self.rules = rulebook or default_rules()
        self.router = router or DeterministicRouter(self.rules)

    def handle(self, conn, principal, question, request_id):
        """Execute authorized source work and return measured, content-free decision metadata."""
        start = perf_counter()
        execution = ExecutionTrace()
        applied = [self.rules.match("SEC-INJECTION", "checked")]
        with execution.step("intent") as stage:
            route = self.router.route(question)
            if route.rule_id in self.rules.catalog:
                stage.rule_ids = [route.rule_id]
                applied.append(self.rules.match(route.rule_id, "matched"))
        intent = route.intent
        trace = ["enterprise_identity", "intent_router"]
        workflow, decision, source_status, attempts = "none", "not_required", "not_accessed", 0
        retrieval_ms = tool_ms = 0.0
        retrieved_count = 0
        sources = []
        requirements = ["HR-001", "HR-005", "HR-007", "HR-009"]
        injection = suspicious_instruction(question) or re.search(r"\b(call|invoke|execute)\b.{0,40}\b(tool|sql|shell|workday|delete)\b", question, re.I)
        if injection:
            with execution.step("authorization", ["SEC-INJECTION"]) as stage:
                stage.status, stage.failure_code = "denied", "untrusted_instruction"
                response = simple_response("refused", intent, "I cannot change permissions, reveal private instructions, or execute arbitrary tools.")
                response.failure_code = "untrusted_instruction"
                applied[0] = self.rules.match("SEC-INJECTION", "denied")
            decision = "denied"
            requirements.append("HR-015")
        elif intent in (Intent.PTO_BALANCE, Intent.EMPLOYEE_DATA_REQUEST):
            target = route.target_employee or principal.employee_id
            requirements += ["HR-002", "HR-004", "HR-010", "HR-011", "HR-014"]
            trace.append("resource_authorization")
            permission_rule = "SEC-PTO-SELF" if target == principal.employee_id else "SEC-PTO-DELEGATED"
            with execution.step("authorization", [permission_rule]) as stage:
                has_pto = bool(re.search(r"\b(pto|vacation|holiday|leave)\b", question, re.I))
                personal_handoff = not has_pto or (route.target_employee is None and intent == Intent.EMPLOYEE_DATA_REQUEST)
                allowed = not personal_handoff and may_read_pto(principal, target, security=self.rules.security)
                if not allowed:
                    stage.status = "handled" if personal_handoff else "denied"
                    stage.failure_code = "private_hr_review" if personal_handoff else "resource_denied"
            applied.append(self.rules.match(permission_rule, "allowed" if allowed else stage.status))
            if personal_handoff:
                response = simple_response("escalated", intent, "That personal HR information requires private People Operations support. No record was accessed.", "Use the authenticated HR case channel. No ticket has been created.")
                response.failure_code = "private_hr_review"
                applied.append(self.rules.match("BR-HANDOFF", "escalated"))
            elif not allowed:
                response = simple_response("denied", intent, "You are not authorized to access that HR resource.")
                response.failure_code, decision = "resource_denied", "denied"
            else:
                workflow, decision = "workday_pto", "allowed"
                trace.append("mock_workday")
                with execution.step("data_source"):
                    source = SourceAccess(system="mock_workday_database", access="accessed", operation="read_pto", duration_ms=0)
                source_start = perf_counter()
                try:
                    with execution.step("retrieval"):
                        record, attempts = self.workday.get_pto(principal, target)
                    with execution.step("validation", ["BR-PTO-EXACT", "BR-SOURCE-FRESH"]):
                        trace.append("record_validation")
                        record = validate_record(record, principal, target, self.settings, self.rules)
                    with execution.step("response"):
                        trace.append("deterministic_response")
                        response = record_response(record, intent, self_service=target == principal.employee_id)
                    source_status = "fresh"
                    source.returned_count, source.fields = 1, ["pto_balance", "unit", "as_of_date", "source_system"]
                except RecordError as error:
                    attempts, source_status = max(attempts, error.attempts), error.status
                    execution.stages[-1].failure_code = error.status
                    status = "denied" if error.status == "denied" else "abstained" if error.status in ("missing", "stale") else "unavailable"
                    response = simple_response(status, intent, "The authorized HR source cannot provide a current verified balance. Contact People Operations.")
                    response.failure_code = error.status
                tool_ms = (perf_counter()-source_start)*1000
                source.duration_ms, source.attempts, source.freshness = round(tool_ms, 4), attempts, source_status
                sources.append(source)
                applied += [self.rules.match("BR-PTO-EXACT", "validated" if response.status == "answered" else "no_facts_returned"),
                            self.rules.match("BR-SOURCE-FRESH", source_status)]
            if not allowed:
                sources.append(SourceAccess(system="mock_workday_database", access="blocked", operation="read_pto", duration_ms=0))
        elif route.personal_review:
            with execution.step("authorization", ["BR-HANDOFF"]) as stage:
                stage.status, stage.failure_code = "handled", "private_benefits_review"
                response = simple_response("escalated", intent, "Personal eligibility and plan coverage require a private benefits review. I cannot determine them from a general policy.", "Contact the benefits team through the authenticated HR portal.")
                response.failure_code = "private_benefits_review"
            applied.append(self.rules.match("BR-HANDOFF", "escalated"))
        elif intent in (Intent.POLICY_QUESTION, Intent.BENEFITS_QUESTION, Intent.PAYROLL_POLICY):
            workflow, decision = "policy_rag", "filtered"
            requirements += ["HR-003", "HR-004", "HR-006", "HR-008", "HR-011", "HR-015"]
            trace += ["current_policy_filter", "document_authorization", "local_search", "grounding_validation"]
            retrieval_start = perf_counter()
            with execution.step("authorization", ["SEC-DOC-ACL"]):
                candidates = authorized_chunks(conn, principal, self.settings.as_of_date, self.rules.security)
            with execution.step("data_source"):
                source = SourceAccess(system="hr_policy_index", access="accessed", operation="authorized_policy_search", duration_ms=0, attempts=1)
            with execution.step("retrieval"):
                passages = search(conn, question, principal, self.settings, candidates=candidates) if self.retriever is search else self.retriever(conn, question, principal, self.settings)
            retrieval_ms = (perf_counter()-retrieval_start)*1000
            retrieved_count = len(passages)
            source_status = "authorized_evidence" if passages else "no_evidence"
            source.duration_ms, source.returned_count, source.freshness = round(retrieval_ms, 4), len(passages), source_status
            source.fields = ["document_id", "title", "version", "section", "quote"] if passages else []
            sources.append(source)
            with execution.step("validation", ["BR-POLICY-EVIDENCE", "BR-CONFLICT"]) as stage:
                response = policy_response(question, passages, intent, self.rules.business.minimum_query_coverage)
                if response.status != "answered":
                    stage.status, stage.failure_code = "handled", response.failure_code
            applied += [self.rules.match("SEC-DOC-ACL", "filtered_before_ranking"),
                        self.rules.match("BR-POLICY-EVIDENCE", response.status),
                        self.rules.match("BR-CONFLICT", "conflict" if response.failure_code == "conflicting_evidence" else "checked")]
        elif intent == Intent.AMBIGUOUS_REQUEST:
            response = simple_response("clarify", intent, "Which HR topic do you need help with—for example a PTO balance, a leave policy, or benefits enrollment?")
            response.failure_code = "clarification_required"
        else:
            response = simple_response("abstained", intent, "I can help with the supported fictional HR workflows. I have no approved source for that request.")
            response.failure_code = "unsupported_topic"
        # The final typed serialization is real validation work for every workflow.
        if not any(row.stage == "response" for row in execution.stages):
            with execution.step("response"):
                response = HRResponse.model_validate(response.model_dump())
        response.request_id = request_id
        response.requirement_ids = sorted(set(requirements))
        response.trace = trace + ["redacted_audit", "response"]
        response.sources, response.applied_rules = sources, applied
        with execution.step("audit"):
            write_audit(conn, {"event": "request_completed", "request_id": request_id, "intent": intent.value,
                              "workflow": workflow, "decision": decision, "status": response.status,
                              "source_status": source_status, "attempts": attempts, "retrieval_ms": round(retrieval_ms, 3),
                              "tool_ms": round(tool_ms, 3), "retrieved_count": retrieved_count, "total_ms": round((perf_counter()-start)*1000, 3),
                              "failure_code": response.failure_code})
        response.execution_trace = execution.complete()
        return response
