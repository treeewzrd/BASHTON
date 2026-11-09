import os

# Standard library
from typing import Annotated

import jwt

# FastAPI
from fastapi import Depends, FastAPI, HTTPException, Response

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# SQLAlchemy
# Handles database integrity violations, including unique constraint violations
from sqlalchemy.exc import IntegrityError

# SQLAlchemy database session type
from sqlalchemy.orm import Session

# Project modules
# Database session factory
from database import SessionLocal

# SQLAlchemy models
from models import User

# Pydantic schemas for validating and returning user data
from schemas import TokenResponse, UserCreate, UserLogin, UserResponse, UserUpdate

# import password hashing function for secure password storage
from security import create_access_token, hash_password, verify_password

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]

app = FastAPI(title="Secure API")
bearer_scheme = HTTPBearer(auto_error=False)


# provides database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # close session after request
        db.close()


# health check endpoint: confirms api running
@app.get("/health")
def health_check():
    return {"status": "ok"}

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
    profile = client.get("/me", headers={"Authorization": f"Bearer{token}"})
    assert profile.status_code == 200
    assert profile.json() == {"id": created.json()["id"], "username": "alice"}
    
# retrieve all users from the database
@app.get("/users", response_model=list[UserResponse])
def get_users(db: Annotated[Session, Depends(get_db)]):
    return db.query(User).all()

# Retrieve a single user by database ID
@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Find a user by ID, return 404 if missing, otherwise delete and commit the record
@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return Response(status_code=204)

# Validate incoming user data, create the database record, and return it
@app.post("/users", response_model=UserResponse, status_code=201)
def post_users(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    db_user = User(
        username=user.username,
        hashed_password=hash_password(user.password))
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")

    return db_user

# Update an existing user's username by ID
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserCreate,
    db: Annotated[Session, Depends(get_db)]
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    db.commit()
    return db_user

# Partially update an existing user's information by ID
@app.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    user: UserUpdate,
    db: Annotated[Session, Depends(get_db)]
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")
    if any(value is None for value in update_data.values()):
        raise HTTPException(status_code=422, detail="Fields cannot be null")
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    return db_user


@app.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.username == credentials.username).first()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user.id, JWT_SECRET_KEY)
    return TokenResponse(access_token=token, token_type="bearer")


@app.get("/me", response_model=UserResponse)
def get_me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
