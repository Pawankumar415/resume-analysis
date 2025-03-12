from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import User
from database import get_db
from schemas import UserCreate, UserLogin  # Ensure UserLogin schema exists
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

router = APIRouter()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key and algorithm for JWT token
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

# Utility function to create JWT token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Register route
@router.post("/register", response_model=dict)
def register_user(
    user_data: UserCreate = Body(...),  # Added Body() for Swagger to recognize fields
    db: Session = Depends(get_db)
):
    if db.query(User).filter((User.email == user_data.email) | (User.username == user_data.username)).first():
        raise HTTPException(status_code=400, detail="Email or username already exists.")

    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_subscribed=False,
        remaining_attempts=2
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully."}

# Login route
@router.post("/login", response_model=dict)
def login_user(
    user_data: UserLogin = Body(...),  # Replaced OAuth2PasswordRequestForm with UserLogin schema
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.email == user_data.identifier) | 
        (User.username == user_data.identifier)
    ).first()

    if not user or not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    access_token = create_access_token({"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}

# Dependency for protected routes
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token.")

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found.")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate token.")
