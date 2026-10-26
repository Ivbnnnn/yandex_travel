import asyncio
import os
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select
from user_service.db import User
from user_service.repositories import UserRepository

from .test_auth_flow import DATA, LOGIN, ME, REGISTER, csrf, register_login

pytestmark = pytest.mark.asyncio


async def test_email_update_conflict_rolls_back(stack):
    client, _, _, _ = stack
    await client.post(REGISTER, json={**DATA, "email": "bob@example.com"})
    await register_login(client)
    response = await client.patch(ME, json={"email": "bob@example.com"}, headers=csrf(client))
    assert response.status_code == 409
    assert (await client.get(ME)).json()["email"] == "alice@example.com"
    assert (
        await client.patch(ME, json={"name": "After rollback"}, headers=csrf(client))
    ).status_code == 200


@pytest.mark.parametrize(
    "claim,value",
    [
        ("aud", "another-api"),
        ("iss", "another-issuer"),
        ("sid", ""),
    ],
)
async def test_gateway_rejects_invalid_access_claims(stack, claim, value):
    client, app, _, _ = stack
    await register_login(client)
    claims = app.state.tokens.verify_access_token(client.cookies.get("access_token"))
    claims[claim] = value
    token = jwt.encode(claims, app.state.tokens.private_key, algorithm="RS256")
    response = await client.get(ME, headers={"Cookie": f"access_token={token}"})
    assert response.status_code == 401


async def test_refresh_rejects_missing_csrf_and_invalid_signature(stack):
    client, _, _, _ = stack
    await register_login(client)
    assert (await client.post("/api/users/auth/refresh")).status_code == 403
    token = client.cookies.get("refresh_token")
    # Change a signed payload character while preserving a decodable JWT shape.
    parts = token.split(".")
    parts[1] = parts[1][:-2] + "AA"
    token = ".".join(parts)
    response = await client.post(
        "/api/users/auth/refresh",
        headers={
            **csrf(client),
            "Cookie": f"refresh_token={token}; csrf_token={client.cookies.get('csrf_token')}",
        },
    )
    assert response.status_code == 401


async def test_secure_cookie_configuration(stack):
    client, app, _, _ = stack
    app.state.settings.COOKIE_SECURE = True
    await client.post(REGISTER, json=DATA)
    response = await client.post(LOGIN, json={"email": DATA["email"], "password": DATA["password"]})
    assert response.status_code == 200
    assert all("Secure" in cookie for cookie in response.headers.get_list("set-cookie"))


async def test_non_ascii_csrf_is_rejected(stack):
    client, _, _, _ = stack
    await register_login(client)
    response = await client.patch(
        ME,
        json={"name": "New"},
        headers=[(b"X-CSRF-Token", b"\xff")],
    )
    assert response.status_code == 403


async def test_unknown_errors_hide_internal_details(stack):
    client, app, _, _ = stack
    from shared.errors import unexpected_error_handler
    from starlette.requests import Request

    request = Request(
        {"type": "http", "method": "GET", "path": "/test", "headers": [], "query_string": b""}
    )
    response = await unexpected_error_handler(request, RuntimeError("secret database details"))
    assert response.status_code == 500
    assert b"secret database details" not in response.body


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL constraint race test",
)
async def test_registration_race_is_a_conflict_not_500(stack, monkeypatch):
    client, app, _, _ = stack
    original = UserRepository.get_user_by_email
    gate = asyncio.Event()
    entered = 0

    async def simultaneous_check(self, email):
        nonlocal entered
        user = await original(self, email)
        entered += 1
        if entered == 2:
            gate.set()
        await asyncio.wait_for(gate.wait(), timeout=10)
        return user

    monkeypatch.setattr(UserRepository, "get_user_by_email", simultaneous_check)
    email = f"race-{uuid4().hex}@example.com"
    results = await asyncio.gather(
        client.post(REGISTER, json={**DATA, "email": email}),
        client.post(REGISTER, json={**DATA, "email": email}),
    )
    assert sorted(response.status_code for response in results) == [201, 409]
    async with app.state.db.session_factory() as session:
        users = (await session.execute(select(User).where(User.email == email))).scalars().all()
        assert len(users) == 1
