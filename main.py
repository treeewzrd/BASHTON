# fastapi dependencies and application
from fastapi import Depends, FastAPI
# sqlalchemy database session type
from sqlalchemy.orm import Session
# database session factory
from database import SessionLocal
# sqlalchemy models
from models import User

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
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()