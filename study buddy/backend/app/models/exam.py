import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    difficulty = Column(String, default="Medium")  # Easy, Medium, Hard, Mixed
    language = Column(String, default="English")
    total_questions = Column(Integer, default=5)
    time_limit_minutes = Column(Integer, default=0)  # 0 means untimed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.question_number")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = Column(Integer, nullable=False)
    question_type = Column(String, nullable=False)  # MCQ, True/False, Fill Blank, Short Answer, Long Answer, Numerical
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=True)  # JSON array string for MCQ options
    correct_answer = Column(Text, nullable=False)  # Kept strictly backend-only until submission
    explanation = Column(Text, nullable=True)
    difficulty = Column(String, default="Medium")
    topic = Column(String, default="General")

    exam = relationship("Exam", back_populates="questions")

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)
    feedback = Column(Text, nullable=True)

    exam = relationship("Exam", back_populates="attempts")
    user = relationship("User", back_populates="attempts")
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_answer_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, default=False)
    score_obtained = Column(Float, default=0.0)
    evaluation_feedback = Column(Text, nullable=True)

    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("Question")
