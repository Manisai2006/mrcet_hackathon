from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.analytics import ProgressDashboardResponse, TopicPerformanceResponse, RecommendationItem
from app.auth.dependencies import get_current_user
from app.services.analytics_service import get_student_overall_stats, generate_adaptive_recommendations

router = APIRouter(prefix="/api/progress", tags=["Student Progress & Adaptive Learning"])

@router.get("", response_model=ProgressDashboardResponse)
def get_student_progress_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stats = get_student_overall_stats(current_user, db)
    recommendations = generate_adaptive_recommendations(current_user, stats)

    return ProgressDashboardResponse(
        total_questions_asked=stats["total_questions_asked"],
        total_docs_uploaded=stats["total_docs_uploaded"],
        total_exams_completed=stats["total_exams_completed"],
        average_score_percentage=stats["average_score_percentage"],
        strong_topics=stats["strong_topics"],
        weak_topics=stats["weak_topics"],
        topic_performances=stats["topic_performances"],
        recommendations=recommendations
    )

@router.get("/topics", response_model=List[TopicPerformanceResponse])
def get_student_topic_performances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stats = get_student_overall_stats(current_user, db)
    return stats["topic_performances"]

@router.get("/recommendations", response_model=List[RecommendationItem])
def get_student_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stats = get_student_overall_stats(current_user, db)
    return generate_adaptive_recommendations(current_user, stats)
