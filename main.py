# Standard library
from typing import Annotated

# FastAPI
from fastapi import Depends, FastAPI, HTTPException, Response

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
from schemas import UserCreate, UserResponse, UserUpdate

app = FastAPI(title="Secure API")


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
    db_user = User(username=user.username)
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
