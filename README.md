# BASHTON

BASHTON is a REST API built with FastAPI and PostgreSQL. Users register with a username and password, sign in, and retrieve their profile. The API hashes passwords with Argon2id. A successful login returns a signed access token that expires after 15 minutes.

I built BASHTON to experiment with API security and understand what happens between signing in and requesting a protected resource. I wanted to see how an API stores passwords safely, how it identifies the user making a request, and how to test what happens when someone sends an expired token or one signed with the wrong key. My goal is to reuse BASHTON’s login flow and tests in future projects that need user accounts, then refine it as those projects introduce new access rules.

`POST /login` returns the same error for an unknown username and an incorrect password. `GET /me` requires a valid bearer token and returns the signed-in user’s ID and username. The other user-management routes currently allow unauthenticated access.

The test suite covers password hashing, successful and failed logins, and profile requests with missing, expired, or incorrectly signed tokens. The login and profile tests use temporary SQLite databases.