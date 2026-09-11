from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class TopicPerformanceResponse(BaseModel):
    id: int
    subject: str
    topic: str
    total_questions_attempted: int
    correct_count: int
    proficiency_percentage: float
    status: str
    last_practiced_at: datetime

    class Config:
        from_attributes = True

class RecommendationItem(BaseModel):
    id: int
    title: str
    subtitle: str
    action_type: str
    target_url: str
    icon_class: str

class ProgressDashboardResponse(BaseModel):
    total_questions_asked: int
    total_docs_uploaded: int
    total_exams_completed: int
    average_score_percentage: float
    strong_topics: List[str] = []
    weak_topics: List[str] = []
    topic_performances: List[TopicPerformanceResponse] = []
    recommendations: List[RecommendationItem] = []
