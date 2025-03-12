from pydantic import BaseModel, EmailStr

# Schema for user registration
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# Schema for user login
class UserLogin(BaseModel):
    identifier: str  # Can be either email or username
    password: str
