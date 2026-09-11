import json
import logging
from typing import List, Dict, Any, Tuple
from google.genai import types
from app.services.gemini_key_manager import key_manager

logger = logging.getLogger("ExamEvaluator")

def evaluate_subjective_answer(
    question_text: str,
    expected_answer: str,
    student_answer: str,
    language: str = "English"
) -> Tuple[bool, float, str]:
    """
    Evaluates a subjective student answer against expected answer using Gemini AI.
    Returns (is_correct, score_obtained [0.0 to 1.0], feedback_string).
    """
    if not student_answer or not student_answer.strip():
        return False, 0.0, "No answer provided."

    prompt = f"""You are an educational evaluator for school exams. Evaluate this student answer.

Question: {question_text}
Expected Answer: {expected_answer}
Student Answer: {student_answer}
Language: {language}

INSTRUCTIONS:
Evaluate for correctness, key concepts covered, and relevance.
Output strictly valid JSON with this schema:
{{
  "is_correct": true/false,
  "score": 1.0,
  "feedback": "Short constructive feedback in {language}"
}}
"""
    client, key_idx = key_manager.get_client()
    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=300
                )
            )
            if response and response.text:
                data = json.loads(response.text.strip())
                return (
                    bool(data.get("is_correct", False)),
                    float(data.get("score", 0.0)),
                    str(data.get("feedback", "Answer evaluated."))
                )
        except Exception as e:
            logger.error(f"Subjective evaluation error: {str(e)}")

    # Fallback string overlap heuristic for offline mode
    student_clean = student_answer.lower().strip()
    expected_clean = expected_answer.lower().strip()
    if student_clean in expected_clean or expected_clean in student_clean:
        return True, 1.0, "Good answer covering key concepts."
    return False, 0.0, "Answer needs more detail and key concept accuracy."

def generate_personalized_exam_feedback(
    subject: str,
    percentage: float,
    strong_topics: List[str],
    weak_topics: List[str],
    language: str = "English"
) -> str:
    """Generates personalized encouraging feedback and practice recommendations."""
    client, key_idx = key_manager.get_client()
    if client:
        try:
            prompt = f"""Generate short, encouraging personalized feedback for a school student who scored {percentage}% on a {subject} exam in {language}.
Strong topics: {', '.join(strong_topics) if strong_topics else 'General concepts'}
Weak topics: {', '.join(weak_topics) if weak_topics else 'None'}

Provide 2-3 specific action recommendations (e.g. revise chapter X, practice medium questions). Use Markdown."""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.5, max_output_tokens=400)
            )
            if response and response.text:
                return response.text.strip()
        except Exception:
            pass

    # Offline feedback templates
    if language == "Telugu":
        return f"""🎯 **పరీక్ష ఫలితం: {percentage}%**

మీరు బలంగా ఉన్న అంశాలు: {', '.join(strong_topics) if strong_topics else 'సాధారణ భావనలు'}
మరింత అభ్యాసం అవసరమైన అంశాలు: {', '.join(weak_topics) if weak_topics else 'ఏవీ లేవు'}

👉 **సూచనలు**:
1. బలహీనంగా ఉన్న అధ్యాయాలను మరొకసారి రివైజ్ చేయండి.
2. 5 మధ్యస్థాయి సాధన ప్రశ్నలను ప్రాక్టీస్ చేయండి."""
    elif language == "Hindi":
        return f"""🎯 **परीक्षा परिणाम: {percentage}%**

मजबूत विषय: {', '.join(strong_topics) if strong_topics else 'सामान्य अवधारणाएं'}
अभ्यास की आवश्यकता: {', '.join(weak_topics) if weak_topics else 'कोई नहीं'}

👉 **सिफारिशें**:
1. कमजोर विषयों का पुनरीक्षण करें।
2. 5 और प्रश्नों का अभ्यास करें।"""
    else:
        return f"""Great effort! 🎯 Score: {percentage}%

You performed strongly in: {', '.join(strong_topics) if strong_topics else 'General Topics'}
Needs more practice in: {', '.join(weak_topics) if weak_topics else 'None'}

👉 **Recommended Next Steps**:
1. Review notes on weaker topics.
2. Attempt a 5-question practice session."""
