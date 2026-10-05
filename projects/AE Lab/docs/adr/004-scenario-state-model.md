# ADR-004: Explicit scenario and learning states

Status: accepted for Phase 1.

**Context.** A learner must see failure and recovery distinctly, resume safely,
and avoid treating an assisted walkthrough as independent mastery.

**Decision.** Persist run evidence and legal transitions through READY,
BASELINE, FAULT_INJECTED, FAILED, DIAGNOSING, REMEDIATED, VERIFIED and MASTERED.
Keep the educational order orient → predict → run → observe → diagnose → fix →
verify → recall → connect. Successful recovery criteria establish VERIFIED;
successful diagnosis and narrow concept recall complete the local exercise label
MASTERED only when the run is not an automated demonstration.

**Alternatives.** Infer state from the last log; collapse execution and learning
into one success flag; update the existing trainer's canonical mastery registers.

**Tradeoffs.** Explicit states make a short exercise resumable but require legal
transition checks. The requested MASTERED label is constrained to one local
concept and retains assistance/exposure qualifications.

**Consequences.** State changes and submitted answers remain inspectable. An
automated demo remains assisted and cannot earn MASTERED after resumed recall.
Re-verification suspends old VERIFIED/MASTERED acceptance, records a reasoned
transition to REMEDIATED and requires new passing checks to restore VERIFIED.
The source fixture's SHA-256 pin prevents mutable answers from changing the oracle.
Structured answers cannot certify prose
reasoning, broad engineering competence or transfer; canonical trainer records
remain separate. Resetting practice retains previous evidence.
