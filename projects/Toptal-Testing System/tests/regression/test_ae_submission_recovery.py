from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event, Lock

import pytest

from tests.ae.test_workflow import UnavailableRunner, start, submit
from trainer.config import Settings
from trainer.execution.sql import ExecutionUnavailable, SqlRunner
from trainer.repositories.models import AttemptRow
from trainer.schemas.models import SubmitRequest


def test_old_failed_request_cannot_reopen_completed_attempt(ae_factory):
    client, service = ae_factory(runner=UnavailableRunner(Settings()))
    attempt = start(client)
    assert submit(client, attempt, 'SELECT 1', 'old-failed-request').status_code == 503
    service.runner = SqlRunner(Settings())
    query = service.bank.exercises[attempt['exercise']['id']].reference_solution
    completed = submit(client, attempt, query, 'new-correct-request').json()
    before = client.get('/api/dashboard').json()['stats']

    assert submit(client, attempt, 'SELECT 1', 'old-failed-request').status_code == 409
    frozen = client.get('/api/attempts/' + attempt['id']).json()
    assert frozen['status'] == 'completed' and frozen['result'] == completed['result']
    assert frozen['pending_submission'] is None
    assert client.get('/api/dashboard').json()['stats'] == before


@pytest.mark.parametrize('status', ['paused', 'grading'])
def test_old_failed_request_obeys_attempt_transition_guards(ae_factory, status):
    client, service = ae_factory(runner=UnavailableRunner(Settings()))
    attempt = start(client)
    assert submit(client, attempt, 'SELECT 1', 'old-failed-request').status_code == 503
    with service.store.transaction(write=True) as session:
        session.get(AttemptRow, attempt['id']).status = status

    assert submit(client, attempt, 'SELECT 1', 'old-failed-request').status_code == 409
    assert client.get('/api/attempts/' + attempt['id']).json()['status'] == status


class DelayedFirstFailure(SqlRunner):
    def __init__(self):
        super().__init__(Settings())
        self.started, self.release, self.lock = Event(), Event(), Lock()
        self.calls = 0

    def grade(self, code, exercise):
        with self.lock:
            self.calls += 1
            call = self.calls
        if call == 1:
            self.started.set()
            if not self.release.wait(10):
                raise AssertionError('The test did not release its first worker')
            raise ExecutionUnavailable('A superseded worker failed late')
        return super().grade(code, exercise)


def test_late_worker_failure_cannot_reset_a_completed_lease_retry(ae_factory):
    current = [datetime.now(timezone.utc)]
    runner = DelayedFirstFailure()
    client, service = ae_factory(runner=runner, clock=lambda: current[0])
    attempt = start(client)
    query = service.bank.exercises[attempt['exercise']['id']].reference_solution
    payload = SubmitRequest(code=query, request_id='recover-expired-lease')

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(service.submit, attempt['id'], payload)
        try:
            assert runner.started.wait(5)
            current[0] += timedelta(seconds=runner.settings.suite_timeout + 21)
            completed = service.submit(attempt['id'], payload)
            assert completed['result']['outcome'] == 'Correct'
        finally:
            runner.release.set()
        with pytest.raises(ExecutionUnavailable):
            first.result(timeout=5)

    frozen = service.attempt(attempt['id'])
    assert frozen['status'] == 'completed' and frozen['result'] == completed['result']
    assert service.dashboard()['stats']['attempts'] == 1
    assert all(c['attempts'] <= 1 for c in service.dashboard()['competencies'])
