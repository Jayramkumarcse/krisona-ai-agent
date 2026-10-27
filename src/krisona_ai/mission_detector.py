"""Rule-based mission detection for KRISONA AI AGENT v0.1."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4


DOMAIN_KEYWORDS = {
    "career": (
        "career", "job", "jobs", "resume", "cv", "interview",
        "interviews", "internship", "placement", "promotion", "salary", "naukri",
        "job search", "skill development", "नौकरी", "रोजगार",
    ),
    "education": (
        "education", "study", "studying", "exam", "exams", "test",
        "syllabus", "assignment", "learn", "learning", "course",
        "school", "college", "university", "padhai", "parhai",
        "पढ़ाई", "परीक्षा",
    ),
    "daily_life": (
        "daily life", "home", "household", "chores", "routine",
        "family", "cooking", "cleaning", "shopping", "ghar",
        "rozmarra", "ghar ke kaam", "घर", "परिवार", "रोजमर्रा",
    ),
    "productivity": (
        "productivity", "productive", "time management",
        "procrastinating", "procrastination", "focus",
        "distracted", "distraction", "task", "tasks",
        "schedule", "prioritization", "prioritisation", "prioritize",
        "prioritise", "deadline", "habit", "plan my day",
        "organize my day", "manage my time", "project", "projects",
        "planning", "समय प्रबंधन",
    ),
}


GOAL_PATTERNS = (
    r"\bmy goal is to\s+(.+?)\s*[.!?]*$",
    r"\b(?:i want to|i need to|i would like to|i'd like to|"
    r"i am trying to|i'm trying to)\s+(.+?)\s*[.!?]*$",
    r"\b(?:i want|i need|i would like)\s+(.+?)\s*[.!?]*$",
    r"\b(?:mera goal hai|mera lakshya hai)\s+(.+?)\s*[.!?]*$",
    r"\b(?:mujhe|mujhko)\s+(.+?)\s+(?:chahiye|chaahiye)\b",
    r"\b(?:mujhe|mujhko)\s+(.+?)\s+"
    r"(?:karna hai|karni hai|seekhna hai|seekhni hai)\b",
)


TIME_PATTERNS = (
    r"\bwithin\s+\d+\s+(?:days?|weeks?|months?|years?)\b",
    r"\bin\s+(?:the\s+next\s+)?\d+\s+"
    r"(?:days?|weeks?|months?|years?)\b",
    r"\b\d+\s+(?:din|days?|hafte|hafton|weeks?|mahine|months?)\b",
    r"\b(?:today|tomorrow|this week|next week|this month|next month)\b",
)


CONSTRAINT_CUES = (
    "budget", "money", "₹", "rupee", "rs ", "hour", "available time",
    "limited time", "only have", "cannot spend", "can't spend",
    "resources", "constraint",
)

SUCCESS_CUES = (
    "success criteria", "measure of success", "success means",
    "completion criteria", "finished when",
)


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match complete words/phrases, not accidental substrings."""
    pattern = r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)"
    return re.search(pattern, text.casefold()) is not None


def extract_goal(situation: str) -> str | None:
    """Extract an explicit goal and separate its time horizon."""
    text = situation.strip()

    for pattern in GOAL_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        goal = re.sub(r"\s+", " ", match.group(1)).strip(" \t\r\n.,!?;:")

        # Remove English deadline expressions from the goal.
        goal = re.sub(
            r"\s+\b(?:in|within|by)\s+(?:the\s+next\s+)?\d+\s+"
            r"(?:days?|weeks?|months?|years?)\b.*$",
            "",
            goal,
            flags=re.IGNORECASE,
        )

        # Remove Hinglish time phrases, e.g. "30 din mein".
        goal = re.sub(
            r"\b\d+\s+(?:din|days?|hafte|hafton|weeks?|mahine|months?)\s+"
            r"(?:mein|me|ke andar)\b\s*",
            "",
            goal,
            flags=re.IGNORECASE,
        )
        goal = re.sub(r"\s+", " ", goal).strip(" \t\r\n.,!?;:")

        if not goal:
            continue
        if goal.casefold().startswith(("help", "some help", "advice", "support")):
            continue
        return goal

    return None

def extract_time_horizon(situation: str) -> str | None:
    """Detect simple time expressions without inventing calendar dates."""
    for pattern in TIME_PATTERNS:
        match = re.search(pattern, situation, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None


def _classify_domain(
    situation: str,
) -> tuple[str, str, dict[str, list[str]]]:
    """Classify with whole-word keyword matches and explicit uncertainty."""
    text = situation.casefold()
    evidence = {
        domain: [word for word in keywords if _contains_phrase(text, word)]
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    scores = {domain: len(words) for domain, words in evidence.items()}
    best_score = max(scores.values(), default=0)

    if best_score == 0:
        return "other", "unclear", evidence

    leaders = [domain for domain, score in scores.items() if score == best_score]
    if len(leaders) != 1:
        return "other", "unclear", evidence

    domain = leaders[0]
    second_score = max(
        score for other_domain, score in scores.items() if other_domain != domain
    )
    margin = best_score - second_score

    if best_score >= 3 and margin >= 2:
        confidence = "high"
    elif best_score >= 2 and margin >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return domain, confidence, evidence

def detect_mission(situation: str) -> dict:
    """Convert a user's situation into an initial structured mission."""
    if not isinstance(situation, str):
        raise TypeError("situation must be a string")

    text = situation.strip()
    if not text:
        raise ValueError("Please describe your situation before continuing.")

    domain, domain_confidence, evidence = _classify_domain(text)
    goal = extract_goal(text)
    time_horizon = extract_time_horizon(text)

    missing_information = []
    if goal is None:
        missing_information.append("goal")
    if time_horizon is None:
        missing_information.append("time_horizon")
    if not any(_contains_phrase(text, cue) for cue in CONSTRAINT_CUES):
        missing_information.append("constraints")
    if not any(_contains_phrase(text, cue) for cue in SUCCESS_CUES):
        missing_information.append("success_criteria")

    questions = []
    if domain == "other":
        questions.append(
            "Is this mainly about career, education, daily life, or productivity?"
        )
    if goal is None:
        questions.append("What specific outcome would you like to achieve?")
    elif time_horizon is None:
        questions.append("By when would you like to achieve this?")

    assumptions = [
        "The primary domain is inferred from keyword matches and may be wrong."
    ]
    if goal is None:
        assumptions.append(
            "No supported explicit goal phrase was detected; the user may "
            "still have a goal."
        )
    if domain == "other":
        assumptions.append(
            "There is not enough clear evidence to assign an initial domain."
        )

    if goal is None or domain == "other":
        status = "clarifying"
        next_step = "Clarify the situation before creating a detailed plan."
    else:
        status = "identified"
        next_step = (
            "Confirm the goal, time horizon, and constraints before "
            "comparing feasible next actions."
        )

    now = datetime.now(timezone.utc).isoformat()

    return {
        "mission_id": str(uuid4()),
        "created_at": now,
        "updated_at": now,
        "situation": text,
        "domain": domain,
        "status": status,
        "goal": goal,
        "success_criteria": None,
        "deadline": None,
        "time_horizon": time_horizon,
        "context": {},
        "constraints": [],
        "resources": [],
        "priorities": [],
        "urgency": None,
        "missing_information": missing_information,
        "assumptions": assumptions,
        "options": [],
        "selected_decision": None,
        "plan": [],
        "outcomes": [],
        "feedback": [],
        "confidence": {
            "domain": domain_confidence,
            "goal": "explicit" if goal else "not_detected",
            "note": "Qualitative heuristic labels, not calibrated probabilities.",
        },
        "domain_evidence": evidence,
        "clarifying_questions": questions,
        "next_step": next_step,
    }


def main() -> None:
    """Provide a simple command-line demonstration."""
    try:
        situation = input("Describe your real-life situation: ")
        mission = detect_mission(situation)
    except (TypeError, ValueError) as error:
        print(f"Input error: {error}")
        raise SystemExit(2) from error

    print(json.dumps(mission, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
