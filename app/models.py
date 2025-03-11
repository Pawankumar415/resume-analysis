from sqlalchemy import Column, Integer, String
from database import Base

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
