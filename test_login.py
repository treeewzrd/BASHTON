from time import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def get_test_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db)
        engine.dispose()


@pytest.mark.parametrize(
    "username,password,expected",
    [
        ("alice", "example-password", 200),
        ("alice", "wrong-password", 401),
        ("unknown", "example-password", 401),
    ],
)
def test_login(client, username, password, expected):
    account = {"username": "alice", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    response = client.post("/login", json={"username": username, "password": password})

    assert response.status_code == expected
    if expected == 200:
        body = response.json()
        assert set(body) == {"access_token", "token_type"}
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str) and body["access_token"]
    else:
        assert response.json() == {"detail": "Invalid username or password"}


def test_me_requires_login_and_returns_owns_profile(client):
    denied = client.get("/me")
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"

    account = {"username": "alice", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    login = client.post("/login", json=account)
    assert login.status_code == 200

    token = login.json()["access_token"]
    profile = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json() == {"id": created.json()["id"], "username": "alice"}


@pytest.mark.parametrize("case", ["expired", "wrong_key"])
def test_me_rejects_invalid_token(client, monkeypatch, case):
    server_key = "test-server-signing-key-for-this-test-only"
    monkeypatch.setattr("main.JWT_SECRET_KEY", server_key)

    account = {"username": "alice", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    now = int(time())
    claims = {
        "sub": str(created.json()["id"]),
        "exp": now - 60 if case == "expired" else now + 900,
    }
    key = server_key if case == "expired" else "different-test-signing-key-for-this-test"
    token = jwt.encode(claims, key, algorithm="HS256")

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"