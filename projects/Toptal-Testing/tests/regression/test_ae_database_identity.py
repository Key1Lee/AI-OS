import hashlib
import sqlite3

import pytest

from trainer.repositories.store import Store


def test_wrong_database_is_rejected_before_persistent_changes(tmp_path):
    path=tmp_path/'existing-assessment.db'
    connection=sqlite3.connect(path)
    connection.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, answer TEXT)')
    connection.execute("INSERT INTO sessions VALUES ('existing','preserve this work')")
    connection.commit();connection.close()
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='another application'):
        Store(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    connection=sqlite3.connect(path)
    assert connection.execute('SELECT answer FROM sessions').fetchone()[0]=='preserve this work'
    connection.close()
