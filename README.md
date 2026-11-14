# BASHTON

[![Tests](https://github.com/treeewzrd/BASHTON/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/treeewzrd/BASHTON/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

BASHTON is a user-account REST API built with Python, FastAPI, and PostgreSQL. Users can register, sign in, view their profile, change their username, and delete their account. Passwords are hashed with Argon2id, and protected requests use signed JWT access tokens.

## Why I built it

I built BASHTON to get a deeper understanding of something I use all the time. I wanted to build an API myself, work through the decisions and problems, and have something I could keep expanding or use as a starting point for other projects.

## Account access

Registration stores a salted password hash. Successful login returns an access token and its token type. An unknown username and an incorrect password return the same 401 error message.

Tokens are signed with HS256 and expire after 15 minutes. Protected routes verify the signature and expiry, require the account ID and expiration claims, and check that the account still exists.

A valid token identifies the caller. Ownership checks decide which account they can access. Account responses contain the ID and username, without exposing the password hash.

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/health` | Health response; no login required |
| POST | `/users` | Register an account |
| POST | `/login` | Verify credentials and return a bearer token |
| GET | `/me` | Retrieve the signed-in account |
| GET | `/users` | Return a list containing only the signed-in account |
| GET | `/users/{user_id}` | Retrieve the caller's own account |
| PUT | `/users/{user_id}` | Update the caller's username |
| PATCH | `/users/{user_id}` | Apply a partial username update |
| DELETE | `/users/{user_id}` | Delete the caller's account |

Except for health, registration, and login, these routes require:

```text
Authorization: Bearer <access_token>
```

Requests targeting another account return 403. Successful deletion returns 204 with no response body. The deleted account's existing token is rejected on subsequent authenticated requests.

### Validation

- Usernames must be 1–50 characters.
- Registration passwords must be 12–128 characters.
- Duplicate usernames return 409, with rollback of the failed database transaction.
- PUT accepts a username-only request.
- An empty PATCH body returns 400.
- An explicit null username in PATCH returns 422.
- Invalid username lengths return 422.

## Tools used

| Tool | Role in the project |
| --- | --- |
| [Python 3.12](https://www.python.org/) | Application and test code |
| [FastAPI](https://fastapi.tiangolo.com/) | API routes, dependencies, and interactive documentation |
| [Pydantic](https://docs.pydantic.dev/) | Request validation and response schemas |
| [SQLAlchemy](https://docs.sqlalchemy.org/) | Database models, sessions, and transactions |
| [PostgreSQL](https://www.postgresql.org/) and [Psycopg](https://www.psycopg.org/psycopg3/docs/) | Application database and Python driver |
| [pwdlib](https://frankie567.github.io/pwdlib/) with Argon2id | Password hashing and verification |
| [PyJWT](https://pyjwt.readthedocs.io/) | Token signing and validation |
| [pytest](https://docs.pytest.org/) and FastAPI TestClient | Automated testing |
| [GitHub Actions](https://github.com/treeewzrd/BASHTON/actions) | Automated dependency installation and test runs |
| [Git](https://git-scm.com/), [Bash](https://www.gnu.org/software/bash/), and [VS Code](https://code.visualstudio.com/) | Development and version control |

## Run locally

These instructions use Bash, Python 3.12, and a running PostgreSQL server.

### Get the project and install dependencies

```bash
git clone https://github.com/treeewzrd/BASHTON.git
cd BASHTON
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

[requirements.txt](requirements.txt) records the pinned Python dependencies.

### Configure PostgreSQL and the signing key

Create a PostgreSQL application role and development database. On a Linux installation with a `postgres` administrator account, for example:

```bash
sudo -u postgres createuser --pwprompt secure_api_user
sudo -u postgres createdb -O secure_api_user bashton
```

If that role already exists, use its existing credentials.

Set `DATABASE_URL` in your local `.env` to your connection details:

```text
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME
```

Replace the placeholders with your own values. Special characters in a connection URL's username or password must be URL-encoded.

Generate a signing secret:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Set `JWT_SECRET_KEY` in `.env` to the generated value. Keep actual credentials and `.env` out of Git.

### Create tables and start the API

```bash
python -c 'from database import Base, engine; import models; Base.metadata.create_all(engine)'
uvicorn main:app --reload
```

Table creation initializes the database; it does not provide schema migrations.

Open [the local interactive API documentation](http://127.0.0.1:8000/docs). Register an account through `POST /users`, then log in through `POST /login`. Use the returned access token with the **Authorize** control to try protected routes.

## Tests and verification

The full suite has passed **40 tests locally and on GitHub Actions**. The [public workflow](https://github.com/treeewzrd/BASHTON/actions/workflows/tests.yml) installs dependencies, checks their compatibility, starts PostgreSQL 16, and runs pytest using Python 3.12.

### SQLite and password-security tests

With the virtual environment active:

```bash
DATABASE_URL='sqlite:///:memory:' \
JWT_SECRET_KEY='local-test-only-signing-key-not-for-deployment' \
python -m pytest -q
```

Without `POSTGRES_TEST_PASSWORD`, the expected result is **38 passed, 2 skipped**. The skipped cases require PostgreSQL.

Coverage includes hashing and password verification, login failures, missing and invalid tokens, account ownership, username validation, conflicts, and deletion. Rejection tests also check that accounts remain unchanged.

### PostgreSQL integration tests

The integration fixture uses a dedicated database at `localhost:5432`, owned by `secure_api_user`:

```bash
sudo -u postgres createdb -O secure_api_user bashton_integration_check
```

Create it once. Supply that role's password privately and run the full suite:

```bash
read -r -s -p "PostgreSQL password: " POSTGRES_TEST_PASSWORD
```

```bash
POSTGRES_TEST_PASSWORD="$POSTGRES_TEST_PASSWORD" \
DATABASE_URL='sqlite:///:memory:' \
JWT_SECRET_KEY='local-test-only-signing-key-not-for-deployment' \
python -m pytest -q
```

```bash
unset POSTGRES_TEST_PASSWORD
```

Expected result: **40 passed**.

The two PostgreSQL tests verify registration, login, authenticated profile retrieval, and duplicate-registration handling while preserving the original account. The fixture overrides the API's database dependency and rolls back its test changes afterward.

### Verification scope

Dependency installation and the full suite were verified in a fresh Python environment on the development machine. GitHub Actions also passed using a separate runner and PostgreSQL service.

The remaining API scenarios are tested against SQLite. The complete manual PostgreSQL setup above has not yet been repeated from start to finish on a fresh machine. These results do not establish public deployment readiness.

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Routes, authentication, and ownership checks |
| `schemas.py` | Request and response schemas |
| `models.py` | User database model |
| `database.py` | Database engine and session configuration |
| `security.py` | Password hashing and token creation |
| `test_security.py` | Password hashing tests |
| `test_login.py` | SQLite API tests |
| `test_postgresql.py` | PostgreSQL integration tests |
| `.github/workflows/tests.yml` | Public automated test workflow |

## Development notes

To be added — compiling notes.