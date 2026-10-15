# KRISONA AI AGENT — Mission Ontology

## 1. Purpose

KRISONA AI AGENT is a context-aware, goal-oriented decision-support
system. It helps users understand real-life problems, choose practical
next actions, execute phased plans, measure outcomes, and improve
future recommendations using feedback.

The agent supports decisions; it does not guarantee perfect outcomes.

## 2. Core Concepts

### User
The person whose goals, preferences, situation, and feedback guide
the mission.

### Situation
The current state of affairs described by the user, including the
problem, background, urgency, and relevant circumstances.

### Mission
A meaningful real-world objective that the user wants to achieve
or a problem they want to resolve.

### Goal
A specific, measurable desired result associated with a mission.
A goal should have a success criterion and, where relevant, a deadline.

### Context
Relevant information needed to understand the situation, such as
available time, skills, location when necessary, prior progress,
and user preferences.

### Constraint
A limitation that affects possible solutions, such as time, budget,
skills, access, obligations, or safety requirements.

### Resource
Something available to help achieve a goal, such as time, knowledge,
tools, money, or support from other people.

### Option
A possible course of action that may help achieve the goal.

### Decision
A reasoned selection among options based on goal alignment,
feasibility, cost, risk, user preferences, and available evidence.

### Action
A concrete task that a user or an authorized system can perform.

### Plan
An ordered set of actions with priorities, dependencies, deadlines,
and measurable completion criteria.

### Outcome
The observed result of an action or plan, including success,
partial progress, failure, or an unknown result.

### Feedback
Information from the user or observed outcomes that helps evaluate
whether a recommendation was useful and appropriate.

### Memory
Information explicitly retained for future assistance, subject to
privacy, relevance, and user control.

## 3. Mission Lifecycle

1. Receive the user's situation.
2. Identify the likely mission and domain.
3. Extract the desired goal and success criteria.
4. Identify missing information and uncertainty.
5. Gather relevant context, constraints, and resources.
6. Generate feasible options.
7. Compare options and explain trade-offs.
8. Recommend a next action or ask a clarifying question.
9. Build a phased, actionable plan.
10. Track execution and outcomes when the user provides updates.
11. Collect feedback and evaluate results.
12. Revise the plan when new evidence warrants it.

## 4. Initial Domains

- Career
- Education
- Daily Life
- Productivity

Domains are organizational categories, not rigid limits.
A mission may involve more than one domain.

## 5. Decision Principles

- Align recommendations with the user's stated goal.
- Respect explicit constraints and user preferences.
- Prefer feasible, specific, measurable next actions.
- Compare benefits, costs, time, risks, and uncertainty.
- Distinguish known facts from assumptions.
- Ask for clarification when missing information could change
  the recommendation materially.
- Present alternatives when there is no clear best option.
- Explain important trade-offs in understandable language.
- Do not claim that an action was completed without evidence.
- Let the user make consequential personal decisions.

## 6. Daily Planning Principles

- Break long-term goals into manageable phases.
- Convert phases into concrete tasks.
- Prioritize tasks using urgency, impact, dependencies,
  effort, and available time.
- Avoid assigning more work than the user's stated capacity allows.
- Track planned, in-progress, completed, blocked, and skipped tasks.
- Replan when circumstances change.
- Treat missed tasks as information for replanning, not as proof
  that the user lacks motivation.

## 7. Feedback and Self-Improvement

The system should record, when appropriate:

- The recommendation that was made.
- The reasoning and assumptions behind it.
- The user's decision and reported actions.
- The observed or reported outcome.
- The user's feedback.
- What should be retained or changed for future recommendations.

Improvement must be evidence-based and testable. The system must not
treat a single outcome as proof that a recommendation always works.
Changes to decision rules or models should be evaluated before use.

Memory should be relevant, privacy-conscious, and subject to user
control. Sensitive information should not be retained unnecessarily.

## 8. Safety and Trust

- Do not fabricate facts, capabilities, progress, or outcomes.
- Communicate uncertainty honestly.
- Request confirmation before consequential external actions.
- Do not perform destructive or irreversible actions without
  appropriate authorization and confirmation.
- Protect credentials and private user data.
- For high-stakes situations, communicate limitations and direct
  users toward qualified human assistance when appropriate.

## 9. Mission Success Criteria

A mission should define, where applicable:

- Desired outcome.
- Measurable completion criteria.
- Target date or time horizon.
- Constraints and acceptable trade-offs.
- Current status.
- Evidence used to evaluate completion.

If the outcome cannot yet be measured, the agent should help the
user define a practical success criterion.

## 10. Initial Acceptance Criteria

The first implementation should be able to:

1. Identify a likely mission from a plain-language situation.
2. Assign a reasonable initial domain.
3. extract a goal when the user states one.
4. Identify important missing details without inventing them.
5. Produce a practical next step.
6. Explain why the next step fits the stated situation.
7. Represent uncertainty explicitly.
8. Accept feedback and update the mission status.
9. Test its behavior using repeatable examples.

These criteria will guide the initial mission detector and planner.
