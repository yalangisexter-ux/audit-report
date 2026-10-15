import sqlite3


def test_developer_mode_restores_customer_database_and_keeps_isolated_copy(
    tmp_path, monkeypatch
):
    import app

    database_path = tmp_path / "employee_audit.db"
    monkeypatch.setattr(app, "DB_PATH", database_path)
    monkeypatch.setattr(app, "BACKUP_DIR", tmp_path / "backups")

    database = app.Database()
    database.conn.execute("CREATE TABLE developer_mode_fixture(value TEXT NOT NULL)")
    database.conn.execute(
        "INSERT INTO developer_mode_fixture(value) VALUES('customer database')"
    )
    database.conn.commit()
    assert not database.verify_developer_mode_password("wrong-password")
    database.set_developer_mode(True)

    assert database.developer_mode_enabled is True
    assert database.github_sync.is_paused is True
    database.conn.execute(
        "INSERT INTO developer_mode_fixture(value) VALUES('developer edit')"
    )
    database.conn.commit()

    developer_copy = database.set_developer_mode(False)

    assert database.developer_mode_enabled is False
    assert database.github_sync.is_paused is False
    assert [row[0] for row in database.conn.execute(
        "SELECT value FROM developer_mode_fixture ORDER BY rowid"
    )] == ["customer database"]
    assert developer_copy.exists()

    copy = sqlite3.connect(developer_copy)
    try:
        assert [row[0] for row in copy.execute(
            "SELECT value FROM developer_mode_fixture ORDER BY rowid"
        )] == ["customer database", "developer edit"]
        settings = {row[0] for row in copy.execute("SELECT key FROM settings")}
        assert "github_sync_token_dpapi" not in settings
        assert "github_sync_install_id" not in settings
        assert "developer_mode_enabled" not in settings
        assert "developer_mode_password_hash" not in settings
        assert "developer_mode_password_salt" not in settings
    finally:
        copy.close()

    created = {}

    class FakeSync:
        def __init__(self, db_path, repository, installation_id, **kwargs):
            self.db_path = db_path
            self.repository = repository
            self.installation_id = installation_id
            self.kwargs = kwargs
            self.token = ""
            self.requests = []
            self.is_busy = False
            created["sync"] = self

        def set_token(self, token):
            self.token = token

        def request_sync(self, force=False):
            self.requests.append(force)

        def close(self, timeout=3):
            pass

    monkeypatch.setattr(app, "GitHubDatabaseSync", FakeSync)
    database.github_sync.set_token("test-token")
    try:
        developer_id = database.developer_sync_installation_id()
        sync = database.start_developer_database_sync()
        assert sync.db_path == developer_copy
        assert sync.repository == app.GITHUB_REPOSITORY
        assert sync.installation_id == developer_id
        assert sync.installation_id != database.github_sync_install_id
        assert sync.kwargs["remote_directory"] == "developer-data"
        assert sync.kwargs["auto_retry"] is False
        assert sync.kwargs["retry_conflicts"] is False
        assert sync.token == "test-token"
        assert sync.requests == [True]
        assert database.developer_sync_installation_id() == developer_id
    finally:
        database.close_github_sync()
        database.conn.close()
