# sqlalchemy column types
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

# shared declarative base form database configuration
from database import Base


# user table definition
class User(Base):
    __tablename__ = "users"

    # primary key: uniquely identifies each user
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # username: self explanatory
    username: Mapped[str] = mapped_column(String(50), unique=True)
