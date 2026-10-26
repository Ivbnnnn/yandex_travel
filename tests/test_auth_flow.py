import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from shared.auth import InternalJWTError
from sqlalchemy import select
from user_service.db import RefreshSession, User

pytestmark = pytest.mark.asyncio
REGISTER = "/api/users/auth/register"
LOGIN = "/api/users/auth/login"
REFRESH = "/api/users/auth/refresh"
LOGOUT = "/api/users/auth/logout"
ME = "/api/users/users/me"
DATA = {
    "email": "Alice@Example.com",
    "password": "correct-password",
    "name": "Alice",
    "phone": "+79991234567",
}


async def register_login(client, email=DATA["email"]):
    data = {**DATA, "email": email}
    registered = await client.post(REGISTER, json=data)
    assert registered.status_code == 201, registered.text
    response = await client.post(LOGIN, json={"email": email, "password": data["password"]})
    assert response.status_code == 200, response.text
    return response


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


async def test_registration_persists_and_never_returns_hash(stack):
    client, app, _, _ = stack
    response = await client.post(REGISTER, json=DATA)
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"
    assert "password_hash" not in response.json() and "password" not in response.json()
    assert not response.headers.get_list("set-cookie")
    async with app.state.db.session_factory() as session:
        user = (await session.execute(select(User))).scalar_one()
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != DATA["password"]


async def test_duplicate_email_and_invalid_password(stack):
    client, _, _, _ = stack
    await register_login(client)
    duplicate = await client.post(REGISTER, json={**DATA, "email": "ALICE@EXAMPLE.COM"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "user_already_exists"
    for email in ("alice@example.com", "missing@example.com"):
        response = await client.post(LOGIN, json={"email": email, "password": "wrong-password"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


async def test_cookies_and_profile_headers(stack):
    client, _, _, received = stack
    login = await register_login(client)
    cookies = login.headers.get_list("set-cookie")
    assert len(cookies) == 3
    assert all("Path=/" in item and "SameSite=lax" in item for item in cookies)
    assert all("HttpOnly" in item for item in cookies if not item.startswith("csrf_token="))
    assert "HttpOnly" not in next(item for item in cookies if item.startswith("csrf_token="))
    profile = await client.get(ME, headers={"X-Internal-Token": "forged", "X-User-Id": "999"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"
    headers = received[-1]["headers"]
    assert headers.get("x-internal-token") != "forged"
    assert "cookie" not in headers and "x-user-id" not in headers


async def test_csrf_origin_and_access_required(stack):
    client, _, _, _ = stack
    assert (await client.get(ME)).status_code == 401
    await register_login(client)
    assert (await client.patch(ME, json={"name": "New"})).status_code == 403
    assert (
        await client.patch(
            ME, json={"name": "New"}, headers={**csrf(client), "Origin": "https://evil.example"}
        )
    ).status_code == 403
    response = await client.patch(ME, json={"name": "New"}, headers=csrf(client))
    assert response.status_code == 200
    assert (await client.get(ME)).json()["name"] == "New"
    assert (await client.get("/api/users/users/99999")).status_code == 403


async def test_refresh_rotation_rejects_replay_and_hashes_tokens(stack):
    client, app, _, _ = stack
    await register_login(client)
    old_refresh = client.cookies.get("refresh_token")
    old_csrf = client.cookies.get("csrf_token")
    claims = app.state.tokens.verify_refresh_token(old_refresh)
    sid = UUID(claims["sid"])
    assert (await client.post(REFRESH, headers=csrf(client))).status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert new_refresh != old_refresh
    async with app.state.db.session_factory() as session:
        stored = await session.get(RefreshSession, sid)
        assert stored.token_hash not in (old_refresh, new_refresh)
        assert len(stored.token_hash) == 64
    replay = await client.post(
        REFRESH,
        headers={
            "Cookie": f"refresh_token={old_refresh}; csrf_token={old_csrf}",
            "X-CSRF-Token": old_csrf,
        },
    )
    assert replay.status_code == 401
    assert (await client.post(REFRESH, headers=csrf(client))).status_code == 200


async def test_refresh_and_logout_without_access_token(stack):
    client, app, _, _ = stack
    await register_login(client)
    client.cookies.delete("access_token")
    assert (await client.post(REFRESH, headers=csrf(client))).status_code == 200
    claims = app.state.tokens.verify_refresh_token(client.cookies.get("refresh_token"))
    old_refresh, old_csrf = client.cookies.get("refresh_token"), client.cookies.get("csrf_token")
    client.cookies.delete("access_token")
    response = await client.post(LOGOUT, headers=csrf(client))
    assert response.status_code == 204
    assert not client.cookies
    async with app.state.db.session_factory() as session:
        stored = await session.get(RefreshSession, UUID(claims["sid"]))
        assert stored.revoked_at is not None
    response = await client.post(
        REFRESH,
        headers={
            "Cookie": f"refresh_token={old_refresh}; csrf_token={old_csrf}",
            "X-CSRF-Token": old_csrf,
        },
    )
    assert response.status_code == 401


async def test_wrong_token_type_and_expired_access(stack):
    client, app, _, _ = stack
    await register_login(client)
    refresh_token = client.cookies.get("refresh_token")
    response = await client.get(ME, headers={"Cookie": f"access_token={refresh_token}"})
    assert response.status_code == 401
    access = client.cookies.get("access_token")
    response = await client.post(
        REFRESH, headers={"Cookie": f"refresh_token={access}; csrf_token=x", "X-CSRF-Token": "x"}
    )
    assert response.status_code == 401
    claims = app.state.tokens.verify_access_token(access)
    expired = app.state.tokens._create_token(
        claims["sub"], claims["sid"], "access", timedelta(seconds=-1)
    )
    assert (await client.get(ME, headers={"Cookie": f"access_token={expired}"})).status_code == 401
    assert (await client.post(REFRESH, headers=csrf(client))).status_code == 200


async def test_direct_service_requires_valid_gateway_token(stack):
    client, app, gateway, _ = stack
    login = await register_login(client)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://user-service"
    ) as direct:
        assert (await direct.get("/users/me")).status_code == 401
        assert (
            await direct.get("/users/me", headers={"X-Internal-Token": "forged"})
        ).status_code == 401
        token = gateway.state.auth.internal_jwt.create_token(
            str(login.json()["id"]), "sid", audience="another-service"
        )
        assert (
            await direct.get("/users/me", headers={"X-Internal-Token": token})
        ).status_code == 401
        with pytest.raises(InternalJWTError):
            app.state.internal_jwt.verify_token(token, "user-service")


async def test_delete_cascades_sessions_and_clears_cookies(stack):
    client, app, _, _ = stack
    await register_login(client)
    response = await client.delete(ME, headers=csrf(client))
    assert response.status_code == 204
    assert not client.cookies
    async with app.state.db.session_factory() as session:
        assert (await session.execute(select(User))).scalars().all() == []
        assert (await session.execute(select(RefreshSession))).scalars().all() == []


async def test_reject_null_and_private_registration_fields(stack):
    client, _, _, _ = stack
    response = await client.post(REGISTER, json={**DATA, "password_hash": "attacker"})
    assert response.status_code == 422
    await register_login(client)
    response = await client.patch(ME, json={"email": None}, headers=csrf(client))
    assert response.status_code == 422
    assert (await client.get(ME)).status_code == 200


async def test_expired_db_session_cannot_refresh(stack):
    client, app, _, _ = stack
    await register_login(client)
    claims = app.state.tokens.verify_refresh_token(client.cookies.get("refresh_token"))
    async with app.state.db.session_factory.begin() as session:
        stored = await session.get(RefreshSession, UUID(claims["sid"]))
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await client.post(REFRESH, headers=csrf(client))).status_code == 401


async def test_concurrent_refresh_has_one_winner(stack):
    client, _, _, _ = stack
    await register_login(client)
    refresh_token = client.cookies.get("refresh_token")
    csrf_token = client.cookies.get("csrf_token")
    headers = {
        "Cookie": f"refresh_token={refresh_token}; csrf_token={csrf_token}",
        "X-CSRF-Token": csrf_token,
    }
    responses = await asyncio.gather(
        client.post(REFRESH, headers=headers), client.post(REFRESH, headers=headers)
    )
    assert sorted(item.status_code for item in responses) == [200, 401]


async def test_logout_does_not_revoke_existing_access_jwt(stack):
    client, _, _, _ = stack
    await register_login(client)
    access = client.cookies.get("access_token")
    assert (await client.post(LOGOUT, headers=csrf(client))).status_code == 204
    response = await client.get(ME, headers={"Cookie": f"access_token={access}"})
    assert response.status_code == 200
