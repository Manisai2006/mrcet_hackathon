from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.user import User
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.models.exam import Exam, ExamAttempt
from app.models.analytics import StudentPerformance

def get_student_overall_stats(user: User, db: Session) -> Dict[str, Any]:
    """Calculates overall learning statistics for an authenticated student."""
    # 1. Total questions asked in chat
    total_questions_asked = db.query(Message).join(Conversation).filter(
        Conversation.user_id == user.id,
        Message.role == "student"
    ).count()

    # 2. Total documents uploaded (ready)
    total_docs_uploaded = db.query(Document).filter(
        Document.user_id == user.id,
        Document.status == "Ready"
    ).count()

    # 3. Total exams completed
    total_exams_completed = db.query(ExamAttempt).filter(ExamAttempt.user_id == user.id).count()

    # 4. Average exam score percentage
    avg_score_res = db.query(func.avg(ExamAttempt.percentage)).filter(
        ExamAttempt.user_id == user.id
    ).scalar()

    average_score = round(float(avg_score_res), 1) if avg_score_res is not None else 0.0

    # 5. Fetch Topic Performance records
    perf_records = db.query(StudentPerformance).filter(
        StudentPerformance.user_id == user.id
    ).all()

    strong_topics = [p.topic for p in perf_records if p.proficiency_percentage >= 70.0]
    weak_topics = [p.topic for p in perf_records if p.proficiency_percentage < 70.0]

    return {
        "total_questions_asked": total_questions_asked,
        "total_docs_uploaded": total_docs_uploaded,
        "total_exams_completed": total_exams_completed,
        "average_score_percentage": average_score,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "topic_performances": perf_records
    }

def generate_adaptive_recommendations(user: User, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates dynamic adaptive study recommendations based on weak topics and history."""
    recommendations = []
    weak_topics = stats.get("weak_topics", [])
    pref_lang = user.profile.preferred_language if user.profile else "English"

    if weak_topics:
        first_weak = weak_topics[0]
        recommendations.append({
            "id": 1,
            "title": f"🔥 Practice {first_weak}",
            "subtitle": f"You scored below 70% in {first_weak}. Try a 5-question targeted quiz.",
            "action_type": "exam",
            "target_url": f"exams.html?subject={first_weak}&difficulty=Medium",
            "icon_class": "fa-solid fa-fire text-warning"
        })
        recommendations.append({
            "id": 2,
            "title": f"💬 Ask Tutor About {first_weak}",
            "subtitle": f"Get a step-by-step Socratic explanation in {pref_lang}.",
            "action_type": "chat",
            "target_url": f"chat.html?prompt=Explain+{first_weak}+step+by+step",
            "icon_class": "fa-solid fa-comments text-primary"
        })
    else:
        recommendations.append({
            "id": 1,
            "title": "⚡ Take a Medium Physics Mock Exam",
            "subtitle": "Test your overall concepts with an AI-generated mock test.",
            "action_type": "exam",
            "target_url": "exams.html",
            "icon_class": "fa-solid fa-file-signature text-warning"
        })

    recommendations.append({
        "id": 3,
        "title": "📚 Upload Chapter Notes PDF",
        "subtitle": "Ask questions directly from your school textbook.",
        "action_type": "document",
        "target_url": "materials.html",
        "icon_class": "fa-solid fa-file-pdf text-info"
    })

    return recommendations
