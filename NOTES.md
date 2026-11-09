# Secure API - Development Notes

## 1. Python and Project Structure

### Code Formatting
- PEP 8 is the standard Python style guide.
- Four spaces per indentation level.
- Two blank lines between top-level classes and functions.
- One blank line between logical sections.
- Comments should explain purpose, security decisions, and non-obvious behavior.

## 2. FastAPI

### Dependencies
- `Depends()` injects dependencies into endpoint functions.
- `get_db()` provides a database session for each request.
- `yield` provides the session to the endpoint.
- `finally` ensures the session closes after request processing.

### Request Bodies and Validation
- Parameters typed with a Pydantic model define the expected JSON request body.
- FastAPI uses Pydantic to validate incoming data.
- Invalid request data is rejected before endpoint execution.
- HTTP 422 indicates request validation failure.
- Validated data is accessible through Python object attributes.

### Response Models and HTTP Exceptions
- `response_model` defines the structure of an endpoint response.
- Pydantic can serialize SQLAlchemy objects using `from_attributes=True`.
- `HTTPException` returns a controlled HTTP error response.
- HTTP 409 Conflict indicates a conflict with existing resource state.
- HTTP 201 Created indicates successful resource creation.

## 3. PostgreSQL and SQLAlchemy

### Database Engine
- `create_engine()` establishes SQLAlchemy's database engine.
- `pool_pre_ping=True` checks connection health before using pooled connections.
- `SessionLocal` creates database sessions.

### Database Exceptions
- SQLAlchemy's `IntegrityError` represents database integrity violations.
- Unique constraints prevent duplicate values.
- Database exceptions should be handled deliberately.
- Rollback is necessary after a failed transaction.

### ORM
- ORM means Object Relational Mapping.
- `DeclarativeBase` provides the foundation for ORM models.
- `Mapped[]` declares mapped Python types.
- `mapped_column()` configures database columns.
- `primary_key=True` uniquely identifies records.
- `unique=True` prevents duplicate values in a column.

### Creating ORM Objects
- SQLAlchemy model classes represent database tables.
- Instantiating a model creates a Python object.
- Assigning model attributes provides values for database columns.
- Creating an object does not automatically persist it to the database.

### Database Permissions
- PostgreSQL roles control database access.
- `GRANT` assigns privileges to roles.
- `REVOKE` removes privileges.
- Database permissions should follow the principle of least privilege.

### Transactions
- `db.add()` stages an ORM object in the session.
- `db.commit()` commits the transaction and persists changes.
- `db.rollback()` cancels an uncommitted transaction.
- A failed transaction must be rolled back before the session can be reused.

## 4. Pydantic

### BaseModel
- `BaseModel` provides Pydantic's validation framework.
- Custom schemas inherit from `BaseModel`.
- Schemas define the expected structure of incoming API data.

### Field()
- `Field()` defines validation constraints.
- `min_length` establishes minimum string length.
- `max_length` establishes maximum string length.
- Field constraints help reject invalid input.

### UserCreate Schema
- `UserCreate` defines the expected data for creating a user.
- `username: str` requires a string.
- `Field(min_length=1, max_length=50)` restricts username length to 1–50 characters.

### Important Distinction
- Pydantic validates incoming API data.
- SQLAlchemy defines and interacts with database structures.
- PostgreSQL enforces database constraints.
- API validation and database constraints are separate layers.


## 5. Login Verification

- Correct username and password returned 200 with only the user's ID and username.
- Correct username with a wrong password returned 401 ("Invalid username or password").
- Unknown username returned the same 401 and message, so the response did not reveal whether the account exists.
-Login tests: 3 passed 1 warning


## 6. Authentication

- Planned: after password verification, `/login` will issue a signed bearer token valid for 15 minutes.
- The `sub` claim will identify the user by database ID. The `exp` claim will set the expiry time.
- `GET /me` will verify the token before loading the current user's profile.
- Verified that `create_access_token` signs the user ID and a 15-minute expiry with HS256.

## 7. Expiring Access Tokens

- Verified that valid login credentials return a bearer token and that both failed login cases return the same 401 response.
- After password verification, `/login` will issue a signed bearer token valid for 15 minutes.
- Verified that GET /me returns the signed-in user's ID and username with a valid login token and returns 401 when the token is missing.
- Verified that GET /me returns 401 for an expired token and for a token signed with the wrong key, even when each token names an existing user.
- Test result: all 6 login and bearer-token cases passed using temporary SQLite databases.
