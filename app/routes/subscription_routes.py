from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User

router = APIRouter()

@router.post("/subscribe/{user_id}")
async def subscribe_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_subscribed:
        return {"message": "User is already subscribed."}

    user.is_subscribed = True
    user.remaining_attempts = None  # Unlimited attempts for subscribed users
    db.commit()
    db.refresh(user)

    return {"message": "Subscription activated successfully."}

@router.get("/status/{user_id}")
async def check_subscription_status(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "is_subscribed": user.is_subscribed,
        "remaining_attempts": "Unlimited" if user.is_subscribed else user.remaining_attempts
    }
