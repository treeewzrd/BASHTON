# fastapi dependencies and application
from fastapi import FastAPI, Depends, HTTPException
# sqlalchemy database session type
from sqlalchemy.orm import Session
# database session factory
from database import SessionLocal
# sqlalchemy models
from models import User
# import pydantic schema used to validate incoming user creation requestss
from schemas import UserCreate, UserResponse
# Handles database integrity violations, including unique constraint violations
from sqlalchemy.exc import IntegrityError

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
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


# Validate incoming user data, create the database record, and return it
@app.post("/users", response_model=UserResponse, status_code=201)
def post_users(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username)
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")

    return db_user
