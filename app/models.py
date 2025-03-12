from sqlalchemy import Column, Integer, String, Boolean,ForeignKey
from database import Base
from sqlalchemy.orm import relationship


class ResumeData(Base):
    __tablename__ = "resume_data"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)  
    overall_score = Column(Integer)
    relevance = Column(Integer)
    skills_fit = Column(Integer)
    experience_match = Column(Integer)
    cultural_fit = Column(Integer)
    strengths = Column(String(1000)) 
    weaknesses = Column(String(1000))
    missing_elements = Column(String(1000))
    recommendations = Column(String(1000))
    candidate_name = Column(String(100))  
    candidate_gmail = Column(String(100))
    candidate_phone = Column(String(20))







class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(100), nullable=False)

    # Relationship for better data querying
    user = relationship("User", back_populates="reports")

# Add this relationship in the `User` model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    is_subscribed = Column(Boolean, default=False)
    remaining_attempts = Column(Integer, default=2)

    # Relationship with InterviewReport
    reports = relationship("InterviewReport", back_populates="user")