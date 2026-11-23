import os
from uuid import uuid4

import httpx
import pytest


@pytest.fixture
def client():
    base_url = os.environ.get("TEST_API_URL", "http://127.0.0.1:8000")
    with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as api:
        yield api


def test_health_checks_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_guest_can_search_demo_catalog(client):
    response = client.get("/api/v1/hotels", params={"city": "Москва", "limit": 1})
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["total"] >= 1
    assert len(catalog["items"]) == 1
    assert catalog["items"][0]["city"] == "Москва"


def test_profile_requires_login(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_registration_login_and_profile(client):
    credentials = {"email": f"ci-{uuid4().hex}@example.com", "password": "Ci-only-password-123!"}
    origin = {"Origin": str(client.base_url).rstrip("/")}

    registration = client.post(
        "/api/v1/auth/register", json={**credentials, "name": "CI user"}, headers=origin
    )
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json=credentials, headers=origin)
    assert login.status_code == 200
    assert "access_token" in client.cookies

    profile = client.get("/api/v1/users/me")
    assert profile.status_code == 200
    assert profile.json()["email"] == credentials["email"]
