"""Practical, rule-based advice for common real-life problems.

This is an initial local playbook system, not a general-purpose LLM.
Its suggestions are starting points and should be adapted to the user's
circumstances.
"""

from __future__ import annotations

import re
from math import isfinite
from typing import Any

from .solution_catalog import find_solutions


def _matches(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _daily_minutes(available: int, suggested: int = 20) -> int:
    """Keep a suggested daily task within the user's available time."""
    return min(available, suggested)



CONSTRAINT_FIELDS = {
    "max_cost": "cost",
    "max_duration_days": "duration_days",
    "min_safety": "safety",
}


def _validate_constraints(
    constraints: dict[str, Any] | None,
) -> dict[str, float]:
    'Validate user-provided hard limits.'
    if constraints is None:
        return {}

    if not isinstance(constraints, dict):
        raise TypeError("constraints must be a dictionary or None.")

    if any(not isinstance(key, str) for key in constraints):
        raise ValueError("Constraint names must be strings.")

    unknown = set(constraints) - set(CONSTRAINT_FIELDS)
    if unknown:
        raise ValueError(
            f"Unsupported constraints: {', '.join(sorted(unknown))}."
        )

    validated: dict[str, float] = {}

    for name, raw in constraints.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{name} must be a finite number.")

        try:
            value = float(raw)
        except (OverflowError, ValueError) as error:
            raise ValueError(f"{name} must be a finite number.") from error

        if not isfinite(value):
            raise ValueError(f"{name} must be a finite number.")

        if name == "min_safety":
            if not 1 <= value <= 5:
                raise ValueError("min_safety must be between 1 and 5.")
        elif value < 0:
            raise ValueError(f"{name} must be >= 0.")

        validated[name] = value

    return validated


def _assess_constraint_fit(
    options: list[dict[str, Any]],
    constraints: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
    'Exclude confirmed violations and expose unknown information.'
    if not constraints:
        return [dict(item) for item in options], [], "not_requested", []

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    unknown_constraints: set[str] = set()
    has_unknown = False

    for option in options:
        checks: dict[str, str] = {}
        violations: list[str] = []
        missing: list[str] = []

        for constraint, limit in constraints.items():
            field = CONSTRAINT_FIELDS[constraint]
            raw = option.get(field)

            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                checks[constraint] = "unknown"
                missing.append(constraint)
                continue

            try:
                value = float(raw)
            except (OverflowError, ValueError):
                checks[constraint] = "unknown"
                missing.append(constraint)
                continue

            if not isfinite(value):
                checks[constraint] = "unknown"
                missing.append(constraint)
                continue

            if constraint == "min_safety" and not 1 <= value <= 5:
                checks[constraint] = "unknown"
                missing.append(constraint)
                continue

            if constraint != "min_safety" and value < 0:
                checks[constraint] = "unknown"
                missing.append(constraint)
                continue

            passes = (
                value >= limit
                if constraint == "min_safety"
                else value <= limit
            )

            if passes:
                checks[constraint] = "within_limit"
            else:
                checks[constraint] = "exceeds_limit"
                violations.append(
                    f"{field}={value:g} violates {constraint}={limit:g}"
                )

        if violations:
            excluded.append({
                "name": option.get("name", "Unnamed option"),
                "violations": violations,
            })
            continue

        has_unknown = has_unknown or bool(missing)
        unknown_constraints.update(missing)

        assessed = dict(option)
        assessed["constraint_assessment"] = {
            "status": "needs_verification" if missing else "within_limits",
            "checks": checks,
        }
        eligible.append(assessed)

    if not eligible:
        status = "no_feasible_options"
    elif has_unknown and excluded:
        status = "partially_verified"
    elif has_unknown:
        status = "needs_verification"
    elif excluded:
        status = "within_limits_with_exclusions"
    else:
        status = "within_limits"

    notes: list[str] = []

    if unknown_constraints:
        names = ", ".join(sorted(unknown_constraints))
        notes.append(
            f"Feasibility is not verified for: {names}. "
            "Some options lack confirmed cost, duration, or safety metadata."
        )

    if excluded:
        notes.append(
            f"Excluded {len(excluded)} option(s) with confirmed violations "
            "of the supplied hard limits."
        )

    if not eligible:
        notes.append(
            "No listed option satisfies all supplied hard constraints "
            "based on the available metadata."
        )

    return eligible, excluded, status, notes


def generate_solution_advice(
    problem: str,
    *,
    goal: str | None = None,
    daily_capacity_minutes: int = 120,
    deadline: str | None = None,
    success_criteria: str | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate options and a practical first action for a described problem."""
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("Please describe the problem first.")

    if (
        isinstance(daily_capacity_minutes, bool)
        or not isinstance(daily_capacity_minutes, int)
        or not 1 <= daily_capacity_minutes <= 1440
    ):
        raise ValueError("Daily capacity must be a whole number from 1 to 1440.")

    limits = _validate_constraints(constraints)
    text = re.sub(r"\s+", " ", f"{problem} {goal or ''}".casefold()).strip()
    daily = _daily_minutes(daily_capacity_minutes)
    review = "Review after 7 days and adjust using your actual progress."

    if _matches(
        text, "spoken english", "speaking english", "english speaking",
        "conversation", "pronunciation", "communication skills",
        "speak english", "improve my english",
    ):
        category = "spoken_english"
        title = "Build speaking confidence through regular practice"
        recommendation = (
            "Start with short, frequent speaking practice and add feedback "
            "from another person at least once a week."
        )
        options = [
            {
                "name": "Daily voice practice",
                "benefit": "Low-cost practice that you can fit around your schedule.",
                "tradeoff": "Solo practice does not fully reproduce real conversation.",
                "first_step": "Record yourself speaking about one familiar topic for 2 minutes.",
            },
            {
                "name": "Conversation partner",
                "benefit": "Provides real speaking practice and opportunities to ask questions.",
                "tradeoff": "Finding a reliable partner may take coordination.",
                "first_step": "Arrange one 10- to 15-minute conversation this week.",
            },
            {
                "name": "Tutor or speaking group",
                "benefit": "May provide structured feedback on recurring mistakes.",
                "tradeoff": "Quality, schedule, and cost vary.",
                "first_step": "Try one available session before committing to a course.",
            },
        ]
        steps = [
            {"when": "Today", "task": f"Speak aloud or record a voice note for {min(10, daily)} minutes."},
            {"when": "This week", "task": "Complete three short speaking sessions and one conversation if possible."},
            {"when": "Day 7", "task": "Compare a new recording with the first one and note one improvement."},
        ]
        measure = (
            success_criteria
            or "Track completed practice sessions and whether you can hold a five-minute conversation."
        )

    elif _matches(
        text, "procrastinat", "time management", "can't focus",
        "cannot focus", "cant focus", "distract", "waste time",
        "too many tasks", "time management", "priorit",
        "productivity", "concentrat",
    ):
        category = "focus_and_time"
        title = "Reduce overload and start with one manageable task"
        recommendation = (
            "Choose one meaningful task, make its first step small, and protect "
            "a short focus period before adding more commitments."
        )
        options = [
            {
                "name": "Small-start method",
                "benefit": "Reduces the effort needed to begin.",
                "tradeoff": "A small start still needs follow-through.",
                "first_step": "Write down the next physical action and work on it for 10 minutes.",
            },
            {
                "name": "Time-blocking",
                "benefit": "Makes available time and priorities visible.",
                "tradeoff": "An overly rigid schedule can be difficult to maintain.",
                "first_step": "Reserve one realistic focus block in your calendar for tomorrow.",
            },
            {
                "name": "Distraction audit",
                "benefit": "Can identify avoidable interruptions.",
                "tradeoff": "Some interruptions are outside your control.",
                "first_step": "Notice and record the three biggest distractions today.",
            },
        ]
        steps = [
            {"when": "Today", "task": "List your tasks, choose one priority, and work on its first step."},
            {"when": "Days 2-6", "task": f"Use one focus block of up to {daily} minutes on your priority."},
            {"when": "Day 7", "task": "Review what you completed and change the schedule if it was unrealistic."},
        ]
        measure = success_criteria or "Track priority tasks completed and focus sessions finished."

    elif _matches(
        text, "exam", "study", "syllabus", "revision",
        "homework", "learn a subject", "learning", "test preparation",
    ):
        category = "study_and_exams"
        title = "Study with recall, practice, and regular review"
        recommendation = (
            "Use active recall and practice questions instead of relying only "
            "on rereading notes."
        )
        options = [
            {
                "name": "Active recall",
                "benefit": "Helps reveal what you can remember without looking at notes.",
                "tradeoff": "Can feel harder than rereading.",
                "first_step": "Study one small topic, close your notes, and write what you remember.",
            },
            {
                "name": "Spaced review",
                "benefit": "Revisits material over multiple sessions.",
                "tradeoff": "Needs a simple review schedule.",
                "first_step": "Schedule short reviews of one topic for later days.",
            },
            {
                "name": "Practice questions",
                "benefit": "Shows which skills or topics need more work.",
                "tradeoff": "Good questions or marking guidance may not always be available.",
                "first_step": "Complete a small set of questions and review each mistake.",
            },
        ]
        steps = [
            {"when": "Today", "task": f"Study one high-priority topic for up to {daily} minutes and test your recall."},
            {"when": "This week", "task": "Alternate practice questions with short reviews of weak areas."},
            {"when": "Day 7", "task": "Review errors and decide which topic needs the next study block."},
        ]
        measure = success_criteria or "Track practice accuracy and topics recalled without notes."

    elif _matches(
        text, "job search", "find a job", "career", "resume",
        "résumé", "cv ", "interview", "internship", "job application",
    ):
        category = "career_and_job_search"
        title = "Turn a broad career goal into targeted weekly actions"
        recommendation = (
            "Pick a target role first, then align your application materials "
            "and preparation with that role."
        )
        options = [
            {
                "name": "Targeted applications",
                "benefit": "Focuses effort on roles that fit your current skills.",
                "tradeoff": "Applications require tailoring and follow-up.",
                "first_step": "Choose one target role and review three relevant job descriptions.",
            },
            {
                "name": "Portfolio or skill evidence",
                "benefit": "Creates examples you can show employers.",
                "tradeoff": "A useful project needs time and a clear scope.",
                "first_step": "Choose one small project that demonstrates a required skill.",
            },
            {
                "name": "Interview practice",
                "benefit": "Builds familiarity with explaining experience and solving questions.",
                "tradeoff": "Practice should match the role you're pursuing.",
                "first_step": "Draft and rehearse answers to three common role-specific questions.",
            },
        ]
        steps = [
            {"when": "Today", "task": "Choose a target role and identify its most common requirements."},
            {"when": "This week", "task": "Improve one resume section and complete one focused practice task."},
            {"when": "Day 7", "task": "Review applications, feedback, and the next skill gap to address."},
        ]
        measure = success_criteria or "Track relevant applications, practice sessions, and evidence of skill development."

    elif _matches(
        text, "budget", "expenses", "expense", "save money",
        "saving money", "spending", "debt", "monthly costs",
    ):
        category = "personal_budgeting"
        title = "Make spending visible before changing the budget"
        recommendation = (
            "Start by recording actual spending, then make a realistic budget "
            "using your essential costs and income."
        )
        options = [
            {
                "name": "Seven-day spending log",
                "benefit": "Shows where money is actually going.",
                "tradeoff": "Requires consistent, honest recording.",
                "first_step": "Record today's purchases and bills in a note or spreadsheet.",
            },
            {
                "name": "Needs-first budget",
                "benefit": "Separates essential expenses from adjustable spending.",
                "tradeoff": "Some expenses cannot be reduced immediately.",
                "first_step": "List income, essential bills, and due dates before setting a savings target.",
            },
            {
                "name": "Review recurring costs",
                "benefit": "May reveal subscriptions or repeat charges worth reviewing.",
                "tradeoff": "Cancellation fees or essential services need consideration.",
                "first_step": "Review recurring payments and flag any you no longer need.",
            },
        ]
        steps = [
            {"when": "Today", "task": "Record spending and list upcoming essential bills."},
            {"when": "This week", "task": "Compare actual expenses with income and identify one realistic adjustment."},
            {"when": "Day 7", "task": "Review the figures and update the budget without assuming uncertain income."},
        ]
        measure = success_criteria or "Track spending, upcoming bills, and the difference between income and expenses."

    elif _matches(
        text, "stress", "stressed", "overwhelmed",
        "anxious", "anxiety", "burnout",
    ):
        category = "stress_management"
        title = "Address one manageable source of stress"
        recommendation = (
            "Identify what is contributing to the stress, choose one "
            "manageable action within your control, and consider using "
            "a structured self-help resource."
        )
        options = [
            {
                "name": "Structured self-help",
                "benefit": "Offers practical exercises to try at your own pace.",
                "tradeoff": "Self-help may not be sufficient for persistent or severe distress.",
                "first_step": "Review the WHO stress-management guide and choose an appropriate exercise.",
            },
            {
                "name": "Reduce one controllable pressure",
                "benefit": "Turns an overwhelming situation into a smaller action.",
                "tradeoff": "Some causes of stress are outside your control.",
                "first_step": "Write down one pressure and identify a small change you can make.",
            },
            {
                "name": "Seek appropriate support",
                "benefit": "A trusted person or qualified professional may offer additional help.",
                "tradeoff": "Finding suitable support can take time.",
                "first_step": "Identify someone trustworthy or a suitable local support service.",
            },
        ]
        steps = [
            {"when": "Today", "task": "Identify one source of stress and one manageable next step."},
            {"when": "This week", "task": "Try an appropriate coping exercise and notice how it feels."},
            {"when": "Day 7", "task": "Review what helped and whether more support is needed."},
        ]
        measure = (
            success_criteria
            or "Record which coping actions you tried and whether you found them useful."
        )

    else:
        category = "general_problem_solving"
        title = "Break the problem into a clear outcome and a small experiment"
        recommendation = (
            "Before choosing a large solution, define what needs to change, "
            "identify what you control, and test one low-risk next step."
        )
        options = [
            {
                "name": "Define the problem",
                "benefit": "Separates the observable problem from assumptions about its cause.",
                "tradeoff": "May reveal that more information is needed first.",
                "first_step": "Write what is happening, how it affects you, and what outcome you want.",
            },
            {
                "name": "Try one small change",
                "benefit": "Lets you learn without committing to a large plan.",
                "tradeoff": "One small experiment may not resolve a complex problem.",
                "first_step": "Choose one action you control that takes no more than 10 minutes.",
            },
            {
                "name": "Get relevant feedback",
                "benefit": "Another person's perspective may reveal blind spots or resources.",
                "tradeoff": "Choose someone trustworthy and suitably informed.",
                "first_step": "Describe the problem and ask one specific question of a trusted person.",
            },
        ]
        steps = [
            {"when": "Today", "task": "Write down the problem, desired outcome, and one constraint."},
            {"when": "This week", "task": f"Test one low-risk step for up to {daily} minutes per day, if appropriate."},
            {"when": "Day 7", "task": "Review what changed, what did not, and what information is still missing."},
        ]
        measure = success_criteria or "Choose one observable sign of improvement once the problem is defined."

    eligible_options, excluded_options, constraint_status, constraint_notes = (
        _assess_constraint_fit(options, limits)
    )

    if constraint_status == "no_feasible_options":
        recommendation = (
            "None of the listed options satisfies all supplied hard limits "
            "based on its available metadata. Review the limits or supply "
            "alternatives with verified cost, duration, and safety data."
        )
        steps = [{
            "when": "Next step",
            "task": (
                "Review the hard limits or identify an alternative with "
                "confirmed metadata before proceeding."
            ),
        }]

    catalog_solutions = find_solutions(category, constraints=limits)

    return {
        "status": (
            "no_feasible_options"
            if constraint_status == "no_feasible_options"
            else "advice_ready"
        ),
        "constraint_status": constraint_status,
        "constraint_notes": constraint_notes,
        "excluded_options": excluded_options,
        "problem_type": category,
        "catalog_solutions": catalog_solutions,
        "title": title,
        "problem": problem.strip(),
        "goal": goal,
        "deadline": deadline,
        "recommended_approach": recommendation,
        "options": eligible_options,
        "action_plan": steps,
        "success_measure": measure,
        "review": review,
        "limitations": (
            "These are rule-based starting suggestions, not guaranteed outcomes. "
            "For urgent danger or high-stakes medical, legal, or financial decisions, "
            "seek appropriate qualified help."
        ),
    }
