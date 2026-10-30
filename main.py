# Standard library
from typing import Annotated

# FastAPI
from fastapi import Depends, FastAPI, HTTPException

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
from schemas import UserCreate, UserResponse

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
