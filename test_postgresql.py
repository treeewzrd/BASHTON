import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from database import Base
from main import app, get_db


@pytest.fixture
def postgres_client(monkeypatch):
    password = os.environ.get("POSTGRES_TEST_PASSWORD")
    if password is None:
        pytest.skip("POSTGRES_TEST_PASSWORD is not configured")

    url = URL.create(
        "postgresql+psycopg",
        username="secure_api_user",
        password=password,
        host="localhost",
        port=5432,
        database="bashton_integration_check",
    )

    engine = create_engine(url)
    monkeypatch.setattr(
        "main.JWT_SECRET_KEY",
        "postgres-integration-test-signing-key-only",
    )

    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                Base.metadata.create_all(connection)

                def get_test_db():
                    with Session(
                        bind=connection,
                        join_transaction_mode="create_savepoint",
                    ) as db:
                        yield db

                monkeypatch.setitem(
                    app.dependency_overrides, get_db, get_test_db
                )
                with TestClient(app) as client:
                    yield client
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_postgres_registration_and_login(postgres_client):
    account = {
        "username": "postgres-test-user",
        "password": "postgres-test-password",
    }
    created = postgres_client.post("/users", json=account)
    assert created.status_code == 201
    profile = created.json()
    assert set(profile) == {"id", "username"}
    assert profile["username"] == account["username"]

    login = postgres_client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()
    assert token["token_type"] == "bearer"

    response = postgres_client.get(
        "/me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json() == profile


def test_postgres_duplicate_registration_preserves_account(postgres_client):
    account = {
        "username": "postgres-conflict-user",
        "password": "postgres-original-password",
    }
    created = postgres_client.post("/users", json=account)
    assert created.status_code == 201

    duplicate = postgres_client.post(
        "/users",
        json={
            "username": account["username"],
            "password": "postgres-different-password",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Username already exists"}

    login = postgres_client.post("/login", json=account)
    assert login.status_code == 200
    token = login.json()["access_token"]
    profile = postgres_client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json() == created.json()
