from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ExamGenerateRequest(BaseModel):
    subject: str = Field("Physics", description="Subject name")
    document_id: Optional[int] = Field(None, description="Optional PDF document ID")
    difficulty: str = Field("Medium", description="Easy, Medium, Hard, or Mixed")
    language: str = Field("English", description="English, Telugu, or Hindi")
    total_questions: int = Field(5, ge=1, le=20, description="Number of questions (1-20)")
    question_types: str = Field("MCQ", description="MCQ, True/False, Fill in the blank, Short Answer, Long Answer, Numerical")
    time_limit_minutes: int = Field(0, description="0 for untimed, or minutes")

class QuestionPublicResponse(BaseModel):
    id: int
    question_number: int
    question_type: str
    question_text: str
    options: Optional[str] = None  # JSON string array
    difficulty: str
    topic: str

    class Config:
        from_attributes = True

class ExamResponse(BaseModel):
    id: int
    user_id: int
    title: str
    subject: str
    difficulty: str
    language: str
    total_questions: int
    time_limit_minutes: int
    created_at: datetime

    class Config:
        from_attributes = True

class ExamDetailPublicResponse(ExamResponse):
    questions: List[QuestionPublicResponse] = []

class StudentAnswerInput(BaseModel):
    question_id: int
    student_answer_text: Optional[str] = ""

class ExamSubmitRequest(BaseModel):
    answers: List[StudentAnswerInput] = []

class StudentAnswerResult(BaseModel):
    question_id: int
    question_number: int
    question_text: str
    student_answer_text: Optional[str] = None
    correct_answer: str
    is_correct: bool
    score_obtained: float
    evaluation_feedback: Optional[str] = None
    explanation: Optional[str] = None
    topic: str

    class Config:
        from_attributes = True

class ExamResultResponse(BaseModel):
    attempt_id: int
    exam_id: int
    title: str
    score: float
    max_score: float
    percentage: float
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    feedback: str
    strong_topics: List[str] = []
    weak_topics: List[str] = []
    completed_at: datetime
    detailed_answers: List[StudentAnswerResult] = []

    class Config:
        from_attributes = True
