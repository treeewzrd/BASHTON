# BASHTON

BASHTON is a REST API built with FastAPI and PostgreSQL. Users register with a username and password, sign in, and retrieve their profile. The API hashes passwords with Argon2id. A successful login returns a signed access token that expires after 15 minutes.

I built BASHTON so I could put my own security decisions to the test. Writing the API gave me control over both sides of the exercise. I could decide how a route should handle a request, then try to break it and see where my assumptions held up. I also wanted a codebase I could reuse, so the next time a project needed user accounts, I’d have a login flow and a set of tests I understood well enough to adapt.

`POST /login` returns the same error for an unknown username and an incorrect password. `GET /me` requires a valid bearer token and returns the signed-in user’s ID and username. `PATCH /users/{user_id}` and `PUT /users/{user_id}` both require a valid bearer token and allow the signed-in user to rename only their own account.

DELETE /users/{user_id} requires a valid bearer token and allows users to delete only their own account. Successful deletion returns 204 with no response body. Once deleted, the account can no longer authenticate using its existing access token.

PostgreSQL integration and installation in a fresh environment have not yet been verified. Passing the SQLite-based tests does not establish public deployment readiness.

The test suite covers password hashing, successful and failed logins, and profile requests with missing, expired, or incorrectly signed tokens. The login and profile tests use temporary SQLite databases.

## Local setup

Requires Python 3.12 and PostgreSQL.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Create a PostgreSQL database and application user. Update `.env` with their connection details.

Generate a signing secret:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Use the generated value for `JWT_SECRET_KEY` in `.env`. Never commit `.env`.

Initialize tables in the configured development database:

```bash
python -c 'from database import Base, engine; import models; Base.metadata.create_all(engine)'
```

Start the API:

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

Run the tests:

```bash
python -m pytest -q
```