from time import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db
from models import User

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
        ("Sanitar", "example-password", 200),
        ("Sanitar", "wrong-password", 401),
        ("unknown", "example-password", 401),
    ],
)
def test_login(client, username, password, expected):
    account = {"username": "Sanitar", "password": "example-password"}
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

    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    login = client.post("/login", json=account)
    assert login.status_code == 200

    token = login.json()["access_token"]
    profile = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json() == {"id": created.json()["id"], "username": "Sanitar"}


@pytest.mark.parametrize("case", ["expired", "wrong_key"])
def test_me_rejects_invalid_token(client, monkeypatch, case):
    server_key = "test-server-signing-key-for-this-test-only"
    monkeypatch.setattr("main.JWT_SECRET_KEY", server_key)

    account = {"username": "Sanitar", "password": "example-password"}
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


def test_user_cannot_rename_another_user(client):
    sanitar = {"username": "Sanitar", "password": "example-password"}
    reshalla = {"username": "Reshalla", "password": "another-password"}

    assert client.post("/users", json=sanitar).status_code == 201
    created = client.post("/users", json=reshalla)
    assert created.status_code == 201
    reshalla_id = created.json()["id"]

    login = client.post("/login", json=sanitar)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.patch(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "renamed-by-sanitar"},
    )

    assert response.status_code == 403
    owner_login = client.post("/login", json=reshalla)
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]

    profile = client.get(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Reshalla"


def test_user_can_rename_own_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.patch(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "Sanitar-renamed"},
    )
    assert response.status_code == 200

    profile = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Sanitar-renamed"


def test_rename_requires_login(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    response = client.patch(f"/users/{user_id}", json={"username": "changed"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    profile = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Sanitar"


def test_put_cannot_rename_another_user(client):
    sanitar = {"username": "Sanitar", "password": "example-password"}
    reshalla = {"username": "Reshalla", "password": "another-password"}

    assert client.post("/users", json=sanitar).status_code == 201
    created = client.post("/users", json=reshalla)
    assert created.status_code == 201
    reshalla_id = created.json()["id"]

    login = client.post("/login", json=sanitar)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.put(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "renamed-by-sanitar", "password": "example-password"},
    )

    assert response.status_code == 403
    owner_login = client.post("/login", json=reshalla)
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]

    profile = client.get(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Reshalla" 


def test_put_can_rename_own_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "Sanitar-renamed"},
    )
    assert response.status_code == 200, response.json()

    profile = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Sanitar-renamed"


def test_put_requires_login(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    response = client.put(
        f"/users/{user_id}",
        json={"username": "changed", "password": account["password"]},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    profile = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Sanitar"


def test_delete_cannot_remove_another_user(client):
    sanitar = {"username": "Sanitar", "password": "example-password"}
    reshalla = {"username": "Reshalla", "password": "another-password"}

    assert client.post("/users", json=sanitar).status_code == 201
    created = client.post("/users", json=reshalla)
    assert created.status_code == 201
    reshalla_id = created.json()["id"]

    login = client.post("/login", json=sanitar)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.delete(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    owner_login = client.post("/login", json=reshalla)
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]

    profile = client.get(
        f"/users/{reshalla_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "Reshalla"


def test_delete_can_remove_own_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.delete(
       f"/users/{user_id}",
       headers={"Authorization": f"Bearer {token}"}, 
    )
    assert response.status_code == 204
    assert response.content == b""

    for db in app.dependency_overrides[get_db]():
        assert db.get(User, user_id) is None
    # D3leted acocunt must no longer authenticate with existing token
    denied = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert denied.status_code == 401


def test_delete_requires(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    # Confirm the rejected deletion left the account intact
    login = client.post("/login", json=account)
    assert login.status_code == 200


@pytest.mark.parametrize("method", ["put", "patch"])
def test_duplicate_username_returns_conflict(client, method):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201
    user_id = created.json()["id"]

    other = client.post(
        "users/",
        json={"username": "Reshalla", "password": "another-password"},
    )
    assert other.status_code == 201

    login = client.post("/login", json=account)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = getattr(client, method)(
        f"/users/{user_id}",
        headers=headers,
        json={"username": "Reshalla"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}

    profile = client.get("/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["username"] == "Sanitar"


@pytest.mark.parametrize("token", ["feet", "y.u.p", ""])
def test_me_rejects_malformed_tokens(client, token):
    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("missing_claim", ["sub", "exp"])
def test_me_rejects_missing_token_claims(client, monkeypatch, missing_claim):
    signing_key = "test-only-signing-key-at-least-32-characters"
    monkeypatch.setattr("main.JWT_SECRET_KEY", signing_key)

    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    claims = {
        "sub": str(created.json()["id"]),
        "exp": int(time()) + 900,
    }
    del claims[missing_claim]
    token = jwt.encode(claims, signing_key, algorithm="HS256")

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/users", "/users/1"])
def test_user_reads_require_login(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_user_list_returns_only_own_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    other = client.post(
        "/users",
        json={"username": "Reshalla", "password": "another-password"},
    )
    assert other.status_code == 201

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {"id": created.json()["id"], "username": "Sanitar"}
    ]


def test_user_cannot_read_another_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    other = client.post(
        "/users",
        json={"username": "Reshalla", "password": "another-password"},
    )
    assert other.status_code == 201
    other_id = other.json()["id"]

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        f"/users/{other_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Cannot view another user"}


def test_duplicate_registration_preserves_original_account(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    duplicate = client.post(
        "/users",
        json={"username": "Sanitar", "password": "different-password"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Username already exists"}

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]

    profile = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json() == created.json()


def test_patch_rejects_empty_update(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/users/{created.json()["id"]}",
        headers=headers,
        json={},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "No fields provided"}

    profile = client.get("/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json() == created.json()


def test_patch_rejects_null_username(client):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/users/{created.json()["id"]}",
        headers=headers,
        json={"username": None},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Fields cannot be null"}

    profile = client.get("/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json() == created.json()


@pytest.mark.parametrize("username", ["", "x" * 51])
def test_registration_rejects_invalid_username_length(client, username):
    response = client.post(
        "/users",
        json={"username": username, "password": "example-password"},
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "username"] for error in errors)


@pytest.mark.parametrize("method", ["put", "patch"])
@pytest.mark.parametrize("username", ["", "x" * 51])
def test_updates_reject_invalid_username_length(client, method, username):
    account = {"username": "Sanitar", "password": "example-password"}
    created = client.post("/users", json=account)
    assert created.status_code == 201

    login = client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = getattr(client, method)(
        f"/users/{created.json()['id']}",
        headers=headers,
        json={"username": username},
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"] == ["body", "username"] for error in errors)

    profile = client.get("/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json() == created.json()