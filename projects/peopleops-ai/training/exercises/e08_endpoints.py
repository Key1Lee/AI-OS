from fastapi import APIRouter, Depends
from lab.contracts import CandidateView, EmployeeView, JobView, PendingExercise


def build_router(get_principal, get_session) -> APIRouter:
    router = APIRouter()

    @router.get("/api/employees/{employee_id}", response_model=EmployeeView)
    def employee(employee_id: str, principal=Depends(get_principal), session=Depends(get_session)):
        """E08: check scope before existence disclosure; use E07 and SQLAlchemy."""
        raise PendingExercise("E08 employee endpoint")

    @router.get("/api/candidates/{candidate_id}", response_model=CandidateView)
    def candidate(candidate_id: str, principal=Depends(get_principal), session=Depends(get_session)):
        """E08: recruiter or HR only; candidate detail must not leak to other roles."""
        raise PendingExercise("E08 candidate endpoint")

    @router.get("/api/jobs", response_model=list[JobView])
    def jobs(principal=Depends(get_principal), session=Depends(get_session)):
        """E08: any authenticated role may read job openings; exclude candidates."""
        raise PendingExercise("E08 jobs endpoint")

    @router.get("/api/analytics/{metric}")
    def analytics(metric: str, principal=Depends(get_principal), session=Depends(get_session)):
        """E08: HR/analyst; allowlisted E03 named query and bound date parameters."""
        raise PendingExercise("E08 analytics endpoint")

    return router
