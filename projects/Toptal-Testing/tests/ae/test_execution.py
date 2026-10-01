import json
import subprocess
import sys
from pathlib import Path

import pytest

from trainer.config import Settings
from trainer.execution.sql import SqlRunner


@pytest.mark.parametrize('exercise_id',[
    'sql-order-reconciliation','sql-customer-latest','sql-inventory-current','sql-settlement-days',
    'sql-export-activation','sql-price-levels','sql-calendar-window','sql-day-seven-retention',
    'sql-historical-owner','sql-device-islands','sql-click-sessions','sql-missing-invoices',
])
def test_reference_solution_executes_all_cases(bank,exercise_id):
    exercise=bank.exercises[exercise_id]
    result=SqlRunner(Settings()).grade(exercise.reference_solution,exercise)
    assert result['outcome']=='Correct',result


@pytest.mark.parametrize('sql',[
    'DROP TABLE orders',
    'SELECT 1; DELETE FROM orders',
    "ATTACH '/tmp/app.db' AS app",
    "COPY orders TO '/tmp/escaped.csv'",
    "SET enable_external_access=true",
    "INSTALL httpfs",
    "SELECT * FROM read_text('/etc/passwd')",
    "SELECT * FROM read_csv('https://example.com/data.csv')",
])
def test_untrusted_sql_cannot_write_read_files_or_network(bank,sql):
    result=SqlRunner(Settings()).execute(sql,bank.exercises['sql-order-reconciliation'].visible_case)
    assert result['ok'] is False


def test_os_sandbox_denies_files_outside_worker_directory(tmp_path):
    secret=tmp_path/'secret.txt';secret.write_text('outside-runtime-sentinel')
    allowed=tmp_path/'allowed';allowed.mkdir()
    runner=SqlRunner(Settings())
    profile=allowed/'worker.sb';profile.write_text(runner._profile(allowed))
    result=subprocess.run(['/usr/bin/sandbox-exec','-f',str(profile),sys.executable,'-I','-c',f'open({str(secret)!r}).read()'],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin'},cwd=allowed)
    assert result.returncode!=0
    assert 'outside-runtime-sentinel' not in result.stdout
    assert 'PermissionError' in result.stderr


def test_os_sandbox_denies_network(tmp_path):
    runner=SqlRunner(Settings())
    profile=tmp_path/'worker.sb';profile.write_text(runner._profile(tmp_path))
    result=subprocess.run(['/usr/bin/sandbox-exec','-f',str(profile),sys.executable,'-I','-c',"import socket;socket.create_connection(('127.0.0.1',9),timeout=1)"],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin'},cwd=tmp_path)
    assert result.returncode!=0 and 'Operation not permitted' in result.stderr


def test_timeout_and_output_limits_preserve_control(bank):
    case=bank.exercises['sql-order-reconciliation'].visible_case
    result=SqlRunner(Settings(execution_timeout=.001)).execute('SELECT * FROM orders',case)
    assert result['kind']=='timeout'
    result=SqlRunner(Settings()).execute('SELECT i FROM range(1001) AS r(i)',case)
    assert result['kind']=='limit'
