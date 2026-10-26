"""Exercise the running gateway over HTTP and remove the temporary user."""

import argparse
import secrets
from uuid import uuid4

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--origin", default="http://localhost:5173")
    args = parser.parse_args()
    email = f"smoke-{uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24)
    with httpx.Client(
        base_url=args.url, headers={"Origin": args.origin}, timeout=15, trust_env=False
    ) as client:

        def call(method: str, path: str, expected: int, **kwargs):
            response = client.request(method, "/api/users" + path, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
            print(f"{method} {path}: {response.status_code}")
            return response

        def csrf():
            return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}

        call(
            "POST",
            "/auth/register",
            201,
            json={
                "email": email,
                "password": password,
                "name": "Smoke Test",
                "phone": "+79991234567",
            },
        )
        call("POST", "/auth/login", 200, json={"email": email, "password": password})
        call("GET", "/users/me", 200)
        call("PATCH", "/users/me", 200, json={"name": "Updated"}, headers=csrf())
        call("POST", "/auth/refresh", 200, headers=csrf())
        call("POST", "/auth/logout", 204, headers=csrf())
        call("GET", "/users/me", 401)
        call("POST", "/auth/login", 200, json={"email": email, "password": password})
        call("DELETE", "/users/me", 204, headers=csrf())
    print("HTTP authentication flow passed; temporary user removed.")


if __name__ == "__main__":
    main()
