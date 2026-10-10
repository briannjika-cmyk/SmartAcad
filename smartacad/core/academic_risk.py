from functools import lru_cache
import json
from pathlib import Path

import joblib


MODEL_DIRECTORY = Path(__file__).resolve().parent / "model_artifacts"
MODEL_PATH = MODEL_DIRECTORY / "academic_risk_model.joblib"
METADATA_PATH = MODEL_DIRECTORY / "academic_risk_model.json"

NUMERIC_FEATURES = (
    "attendance_percentage",
    "gpa",
    "study_hours_per_day",
    "assignment_completion_percentage",
)

DIFFICULTY_FEATURES = {
    "difficulty_course_concepts": "Understanding course concepts",
    "difficulty_concentration": "Concentration",
    "difficulty_time_management": "Time management",
    "difficulty_language_barriers": "Language barriers",
    "difficulty_learning_resources": "Access to learning resources",
    "difficulty_exam_anxiety": "Exam or test anxiety",
    "difficulty_other": "Other",
}

HABIT_FEATURES = {
    "habit_daily_schedule": "Following a daily study schedule",
    "habit_weekly_revision": "Weekly revision",
    "habit_group_study": "Studying with a group",
    "habit_note_taking": "Taking notes",
    "habit_practice_questions": "Practising with questions",
    "habit_online_resources": "Using online learning resources",
    "habit_seeking_help": "Seeking help from a lecturer or tutor",
    "habit_other": "Other",
}

FEATURES = (
    *NUMERIC_FEATURES,
    *DIFFICULTY_FEATURES,
    *HABIT_FEATURES,
)

HIGH_RISK_THRESHOLD = 0.30


@lru_cache(maxsize=1)
def load_model():
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_model_metadata():
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def questionnaire_features(questionnaire):
    difficulties = set(questionnaire.learning_difficulties.splitlines())
    habits = set(questionnaire.study_habits.splitlines())
    values = [
        int(option in difficulties)
        for option in DIFFICULTY_FEATURES.values()
    ]
    values.extend(
        int(option in habits)
        for option in HABIT_FEATURES.values()
    )
    return values


def classify_risk(
    class_probabilities,
    high_risk_threshold=HIGH_RISK_THRESHOLD,
):
    if not 0 <= high_risk_threshold <= 1:
        raise ValueError("The High-risk threshold must be between 0 and 1.")
    if "High" not in class_probabilities:
        raise ValueError("The model did not return a High-risk score.")
    if class_probabilities["High"] >= high_risk_threshold:
        return "High"

    other_probabilities = {
        label: probability
        for label, probability in class_probabilities.items()
        if label != "High"
    }
    if not other_probabilities:
        raise ValueError("The model did not return a non-High risk score.")
    return max(other_probabilities, key=other_probabilities.get)


def intervention_recommendations(
    *,
    risk_level,
    attendance_percentage,
    gpa,
    study_hours,
    assignment_completion,
    questionnaire,
):
    recommendations = []

    if risk_level == "High":
        recommendations.append("Advisor check-in this week")
        recommendations.append("Review attendance and missed work")
        recommendations.append("Set a 2-week support plan")
    elif risk_level == "Medium":
        recommendations.append("Short check-in next week")
        recommendations.append("Set one academic goal")

    if attendance_percentage < 75:
        recommendations.append("Follow up on absences")
    if gpa < 2.5:
        recommendations.append("Arrange tutoring")
    if assignment_completion < 50:
        recommendations.append("Break work into small tasks")
    if study_hours < 2:
        recommendations.append("Create a study schedule")

    difficulties = set(questionnaire.learning_difficulties.splitlines())
    if "Exam or test anxiety" in difficulties:
        recommendations.append("Offer practice assessments")
    if "Understanding course concepts" in difficulties:
        recommendations.append("Targeted concept support")
    if "Concentration" in difficulties:
        recommendations.append("Improve study environment")

    if not recommendations:
        recommendations.append("Monitor progress")

    return recommendations[:3]


def recommendations_for_missing_data(missing_data):
    details = ", ".join(missing_data)
    if not details:
        details = "complete attendance and questionnaire information"
    return [
        f"Collect {details} before risk review."
    ]
