# pydantic base class for request validation
from pydantic import BaseModel, Field


# schema for incoming user creation requests
class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)


# Schema for user data returned by the API
class UserResponse(BaseModel):
    id: int
    username: str
    model_config = {"from_attributes": True}
