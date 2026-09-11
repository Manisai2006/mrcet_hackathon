import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class StudentPerformance(Base):
    __tablename__ = "student_performances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    total_questions_attempted = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    proficiency_percentage = Column(Float, default=0.0)
    status = Column(String, default="Needs Practice")  # "Strong", "Needs Practice"
    last_practiced_at = Column(DateTime, default=datetime.datetime.utcnow)
