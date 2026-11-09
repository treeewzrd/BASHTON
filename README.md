# BASHTON

BASHTON is a REST API built with FastAPI and PostgreSQL. Users register with a username and password, sign in, and retrieve their profile. The API hashes passwords with Argon2id. A successful login returns a signed access token that expires after 15 minutes.

`POST /login` returns the same error for an unknown username and an incorrect password. `GET /me` requires a valid bearer token and returns the signed-in user’s ID and username. The other user-management routes currently allow unauthenticated access.

The test suite covers password hashing, successful and failed logins, and profile requests with missing, expired, or incorrectly signed tokens. The login and profile tests use temporary SQLite databases.