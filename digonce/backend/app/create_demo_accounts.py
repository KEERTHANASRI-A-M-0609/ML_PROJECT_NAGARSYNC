"""Create local demo accounts and print their randomly generated credentials once."""
from __future__ import annotations

import argparse
import secrets

from backend.app import users

DEMO_ACCOUNTS = (
    ("municipal-admin@example.test", "Municipal Demo Administrator", "admin"),
    ("municipal-worker@example.test", "Municipal Demo Field Worker", "field_worker"),
    ("demo-citizen@example.test", "Demo Citizen", "citizen"),
)


def create_demo_accounts(reset_passwords: bool = False, selected_role: str | None = None) -> int:
    created_accounts: list[tuple[str, str, str]] = []
    existing_accounts: list[str] = []
    accounts = tuple(
        account for account in DEMO_ACCOUNTS
        if selected_role is None or account[2] == selected_role
    )
    for email, name, role in accounts:
        existing = users.get_user_by_email(email)
        if existing and not reset_passwords:
            existing_accounts.append(email)
            continue
        password = secrets.token_urlsafe(24)
        if existing:
            result = users.update_managed_user(existing["id"], password=password)
            if result is None:
                print(f"Could not reset password for {email}")
                if created_accounts:
                    _print_credentials(created_accounts)
                return 1
        else:
            result = users.create_managed_user(email, password, role, name)
        if isinstance(result, str):
            print(f"Could not create {role} account: {result}")
            if created_accounts:
                _print_credentials(created_accounts)
            return 1
        created_accounts.append((email, password, role))

    if created_accounts:
        _print_credentials(created_accounts)
    else:
        print("All demo accounts already exist. No accounts were changed.")
    if existing_accounts:
        print(f"Already present and unchanged: {', '.join(existing_accounts)}")
    return 0


def _print_credentials(accounts: list[tuple[str, str, str]]) -> None:
    print("Save these generated credentials now; they will not be shown again.")
    for email, password, role in accounts:
        print(f"{role}: {email} / {password}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision local NagarSync demonstration accounts.")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="Set fresh random passwords for existing demo accounts and print them once.",
    )
    parser.add_argument(
        "--role",
        choices=("admin", "field_worker", "citizen"),
        help="Limit provisioning or password reset to one demo role.",
    )
    args = parser.parse_args()
    raise SystemExit(create_demo_accounts(reset_passwords=args.reset_passwords, selected_role=args.role))
