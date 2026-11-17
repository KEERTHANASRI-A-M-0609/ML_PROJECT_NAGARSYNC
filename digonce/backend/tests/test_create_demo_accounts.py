from backend.app import create_demo_accounts, users


def test_create_demo_accounts_prints_working_credentials(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    monkeypatch.setattr(create_demo_accounts.secrets, "token_urlsafe", lambda _: "GeneratedPass2026!")

    assert create_demo_accounts.create_demo_accounts() == 0

    output = capsys.readouterr().out
    assert "municipal-admin@example.test / GeneratedPass2026!" in output
    assert "municipal-worker@example.test / GeneratedPass2026!" in output
    assert "demo-citizen@example.test / GeneratedPass2026!" in output
    assert users.login("municipal-admin@example.test", "GeneratedPass2026!")["user"]["role"] == "admin"
    assert users.login("municipal-worker@example.test", "GeneratedPass2026!")["user"]["role"] == "field_worker"
    assert users.login("demo-citizen@example.test", "GeneratedPass2026!")["user"]["role"] == "citizen"


def test_create_demo_accounts_preserves_existing_and_creates_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    users.create_managed_user(
        "municipal-admin@example.test",
        "ExistingDemoPassword2026!",
        "admin",
        "Existing Demo Administrator",
    )
    monkeypatch.setattr(create_demo_accounts.secrets, "token_urlsafe", lambda _: "GeneratedPass2026!")

    assert create_demo_accounts.create_demo_accounts() == 0

    output = capsys.readouterr().out
    assert "municipal-worker@example.test / GeneratedPass2026!" in output
    assert "demo-citizen@example.test / GeneratedPass2026!" in output
    assert "municipal-admin@example.test / GeneratedPass2026!" not in output
    assert users.login("municipal-admin@example.test", "ExistingDemoPassword2026!")["user"]["role"] == "admin"
    assert users.login("municipal-admin@example.test", "GeneratedPass2026!") == "Invalid email or password"


def test_reset_passwords_rotates_existing_demo_credentials(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    users.create_managed_user(
        "municipal-admin@example.test",
        "ExistingDemoPassword2026!",
        "admin",
        "Municipal Admin",
    )
    monkeypatch.setattr(create_demo_accounts.secrets, "token_urlsafe", lambda _: "NewDemoPassword2026!")

    assert create_demo_accounts.create_demo_accounts(reset_passwords=True) == 0

    output = capsys.readouterr().out
    assert "municipal-admin@example.test / NewDemoPassword2026!" in output
    assert users.login("municipal-admin@example.test", "NewDemoPassword2026!")["user"]["role"] == "admin"
    assert users.login("municipal-admin@example.test", "ExistingDemoPassword2026!") == "Invalid email or password"


def test_reset_passwords_can_target_one_role(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(users, "_STORE", tmp_path / "users.json")
    monkeypatch.setattr(users, "_col", lambda: None)
    users.create_managed_user(
        "municipal-admin@example.test",
        "ExistingAdminPassword2026!",
        "admin",
        "Municipal Admin",
    )
    users.create_managed_user(
        "municipal-worker@example.test",
        "ExistingWorkerPassword2026!",
        "field_worker",
        "Field Worker",
    )
    monkeypatch.setattr(create_demo_accounts.secrets, "token_urlsafe", lambda _: "NewAdminPassword2026!")

    assert create_demo_accounts.create_demo_accounts(reset_passwords=True, selected_role="admin") == 0

    output = capsys.readouterr().out
    assert "municipal-admin@example.test / NewAdminPassword2026!" in output
    assert "municipal-worker@example.test" not in output
    assert users.login("municipal-admin@example.test", "NewAdminPassword2026!")["user"]["role"] == "admin"
    assert users.login("municipal-worker@example.test", "ExistingWorkerPassword2026!")["user"]["role"] == "field_worker"
