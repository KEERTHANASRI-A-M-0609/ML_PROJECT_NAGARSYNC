from backend.app import recover_admin


def test_recover_admin_password_updates_selected_account(monkeypatch, capsys):
    admins = [
        {"id": "admin-1", "email": "admin@example.test", "name": "Admin", "role": "admin"},
        {"id": "worker-1", "email": "worker@example.test", "name": "Worker", "role": "field_worker"},
    ]
    updates = []
    monkeypatch.setattr(recover_admin.users, "list_users", lambda limit: admins)
    monkeypatch.setattr(recover_admin.users, "update_managed_user", lambda user_id, password: updates.append((user_id, password)) or {"id": user_id})
    monkeypatch.setattr("builtins.input", lambda _: "1")
    passwords = iter(("LocalPassword2026!", "LocalPassword2026!"))
    monkeypatch.setattr(recover_admin, "getpass", lambda _: next(passwords))

    assert recover_admin.recover_admin_password() == 0
    assert updates == [("admin-1", "LocalPassword2026!")]
    assert "Existing sessions have been revoked." in capsys.readouterr().out


def test_recover_admin_password_rejects_mismatch(monkeypatch):
    updates = []
    monkeypatch.setattr(
        recover_admin.users,
        "list_users",
        lambda limit: [{"id": "admin-1", "email": "admin@example.test", "name": "Admin", "role": "admin"}],
    )
    monkeypatch.setattr(recover_admin.users, "update_managed_user", lambda *args, **kwargs: updates.append(args))
    monkeypatch.setattr("builtins.input", lambda _: "1")
    passwords = iter(("LocalPassword2026!", "DifferentPassword2026!"))
    monkeypatch.setattr(recover_admin, "getpass", lambda _: next(passwords))

    assert recover_admin.recover_admin_password() == 1
    assert updates == []
