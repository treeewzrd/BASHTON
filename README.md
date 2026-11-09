# BASHTON

BASHTON is a REST API built with FastAPI and PostgreSQL. Users register with a username and password, sign in, and retrieve their profile. The API hashes passwords with Argon2id. A successful login returns a signed access token that expires after 15 minutes.

I built BASHTON so I could put my own security decisions to the test. Writing the API gave me control over both sides of the exercise. I could decide how a route should handle a request, then try to break it and see where my assumptions held up. I also wanted a codebase I could reuse, so the next time a project needed user accounts, I’d have a login flow and a set of tests I understood well enough to adapt.

`POST /login` returns the same error for an unknown username and an incorrect password. `GET /me` requires a valid bearer token and returns the signed-in user’s ID and username. `PATCH /users/{user_id}` requires a valid bearer token and allows the signed-in user to rename only their own account.

The test suite covers password hashing, successful and failed logins, and profile requests with missing, expired, or incorrectly signed tokens. The login and profile tests use temporary SQLite databases.