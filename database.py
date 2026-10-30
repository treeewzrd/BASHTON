# standard library
import os

# 3rd party
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# load environment variable from .env
load_dotenv()

# retrieve database connection string
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


# create databse engine and enable connection health checks
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# create database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# base class for sqlalchemy ORM models
class Base(DeclarativeBase):
    pass
