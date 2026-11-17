"""Interactively reset a local NagarSync administrator password."""
from __future__ import annotations

from getpass import getpass

from backend.app import users


def recover_admin_password() -> int:
    admins = [
        user for user in users.list_users(limit=2000)
        if user.get("role") == "admin" and user.get("archived_at") is None
    ]
    if not admins:
        print("No active administrator found. Use the first-admin bootstrap flow instead.")
        return 1

    print("Select the administrator whose password you want to reset:")
    for index, admin in enumerate(admins, start=1):
        print(f"{index}. {admin['name']} <{admin['email']}>")

    selection = input("Administrator number (or blank to cancel): ").strip()
    if not selection:
        print("Password reset cancelled.")
        return 1
    if not selection.isdecimal() or not 1 <= int(selection) <= len(admins):
        print("Invalid administrator selection.")
        return 1

    password = getpass("New password (10-200 characters): ")
    if not 10 <= len(password) <= 200:
        print("Password must be between 10 and 200 characters.")
        return 1
    confirmation = getpass("Confirm new password: ")
    if password != confirmation:
        print("Passwords do not match.")
        return 1

    admin = admins[int(selection) - 1]
    updated = users.update_managed_user(admin["id"], password=password)
    if updated is None:
        print("Could not update the administrator password.")
        return 1

    print(f"Password updated for {admin['email']}. Existing sessions have been revoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(recover_admin_password())
