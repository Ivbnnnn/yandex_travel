"""Create a separate monolith configuration; existing configuration is preserved."""

import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / ".env.monolith"
    if destination.exists():
        print(".env.monolith already exists; nothing changed.")
        return
    template = (root / ".env.example").read_text(encoding="utf-8")
    for placeholder in (
        "replace-local-postgres-password",
        "replace-jwt-secret-with-32-random-characters",
        "replace-csrf-secret-with-32-random-characters",
        "replace-local-admin-password",
    ):
        template = template.replace(placeholder, secrets.token_urlsafe(32))
    destination.write_text(template, encoding="utf-8")
    destination.chmod(0o600)
    print("Created .env.monolith. Administrator credentials are in this file.")


if __name__ == "__main__":
    main()
