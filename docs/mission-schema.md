# KRISONA AI AGENT — Mission Schema

## 1. Purpose

This document defines the initial logical data model for a mission.
It is a design specification, not yet an enforced database schema.

The first implementation should use validated Python data models
and JSON-compatible input and output.

## 2. Mission Record

Each mission should represent one user objective or real-life problem.

### Required fields

- mission_id: Unique identifier for the mission.
- situation: User-provided description of the current situation.
- domain: Career, Education, Daily Life, Productivity, or Other.
- status: Current mission lifecycle status.
- created_at: Timestamp when the mission was created.
- updated_at: Timestamp when the mission was last updated.

### Optional fields

- title: Short, readable mission title.
- goal: Desired result.
- success_criteria: How achievement will be measured.
- deadline: Target completion date or time, if known.
- context: Relevant information about the situation.
- constraints: Limits that affect available choices.
- resources: Available assets and support.
- priorities: User-stated preferences and priorities.
- urgency: User-relevant urgency level.
- missing_information: Important unanswered questions.
- assumptions: Unverified assumptions made by the system.
- options: Candidate courses of action.
- selected_decision: Recommended or user-selected option.
- plan: Ordered actions for achieving the goal.
- outcomes: Reported or observed results.
- feedback: User feedback on recommendations or progress.
- confidence: Calibrated confidence or uncertainty information.

Optional fields must not be fabricated when information is unknown.

## 3. Domain Values

Initial supported domains:

- career
- education
- daily_life
- productivity
- other

A mission may involve multiple domains in future versions.
The initial version should select one primary domain and explain
uncertainty when classification is ambiguous.

## 4. Mission Status Values

Initial lifecycle states:

- identified
- clarifying
- planned
- in_progress
- blocked
- completed
- cancelled
- needs_review

Status changes should reflect available evidence. A mission must not
be marked completed merely because a plan was generated.

## 5. Goal Structure

A goal may contain:

- description: Desired outcome in plain language.
- success_criteria: Measurable evidence of achievement.
- target_date: Target date, if specified.
- priority: User-defined or explicitly agreed priority.
- measurement_method: How progress will be evaluated.

If the goal is unclear, the system should ask a useful question
rather than silently inventing a specific objective.

## 6. Constraint and Resource Structures

A constraint may contain:

- type: time, budget, skill, access, obligation, safety, or other.
- description: What the limitation means.
- severity: How strongly it limits available options.
- source: User-provided, observed, or inferred.

A resource may contain:

- type: time, knowledge, tool, budget, support, or other.
- description: The available resource.
- availability: Any relevant limits or conditions.
- source: User-provided, observed, or inferred.

Inferred values must be clearly distinguished from user-confirmed facts.

## 7. Option and Decision Structures

Each candidate option should contain:

- option_id: Identifier within the mission.
- description: Proposed course of action.
- expected_benefits: Anticipated advantages.
- estimated_cost: Known or estimated resource cost.
- estimated_time: Expected time requirement, if known.
- risks: Important potential downsides.
- assumptions: Conditions on which the option depends.
- feasibility: Assessment against known constraints.

A decision record should contain:

- selected_option_id: Chosen option, if one has been selected.
- rationale: Explanation of the recommendation.
- trade_offs: Important advantages and disadvantages.
- alternatives: Other viable options.
- uncertainty: Important unknowns.
- decision_owner: Agent recommendation or user decision.
- confirmation_required: Whether user confirmation is needed.

The agent should not represent estimates as certain facts.

## 8. Action Plan Structure

Each action should contain:

- action_id: Unique identifier within the mission.
- title: Short task description.
- details: Instructions for completing the task.
- status: pending, in_progress, completed, blocked, or skipped.
- priority: Relative importance.
- estimated_duration: Expected effort, if known.
- due_date: Deadline, if known.
- depends_on: Action identifiers that must be completed first.
- completion_criteria: Evidence that the action is finished.
- result: Reported or observed result, if available.

A plan should include a practical first action. Tasks and deadlines
must respect known constraints and available capacity.

## 9. Outcome and Feedback Structure

An outcome record may contain:

- action_id: Related action, when applicable.
- observed_result: What happened.
- evidence_source: User report or other authorized source.
- recorded_at: Time the result was recorded.
- goal_progress: Measured progress, if available.
- status: success, partial, failure, or unknown.

Feedback may contain:

- rating: Optional user rating.
- comments: User explanation or correction.
- helpfulness: Whether the recommendation was useful.
- reported_blockers: Obstacles encountered.
- suggested_changes: User-requested improvements.
- recorded_at: Time the feedback was recorded.

Feedback and reported outcomes should inform future recommendations.
A single result must not be treated as proof that a strategy always
works.

## 10. Uncertainty and Data Integrity

- Unknown values should be omitted or represented explicitly as unknown.
- User-provided facts must be distinguishable from system inferences.
- Dates, durations, costs, and confidence values need defined formats.
- Identifiers must remain stable when a mission is updated.
- Updates should preserve relevant history rather than silently
  rewriting past outcomes.
- Sensitive personal data should not be collected unless necessary.
- Users should be able to correct inaccurate information.

## 11. Initial Validation Rules

The first implementation should validate that:

1. Required mission fields are present.
2. Domain and status values belong to their allowed sets.
3. A completed action has appropriate completion evidence.
4. A completed mission meets its success criteria or records
   why completion could not be verified.
5. Action dependencies reference valid actions.
6. Deadlines and durations use consistent formats.
7. Unknown information is not invented to fill required fields.
8. Recommendations include a rationale and relevant uncertainty.
9. User feedback can be associated with the relevant mission or action.

## 12. Versioning

This is the initial schema specification, version 0.1.
Changes to field meanings or status values should be documented.
The implementation must validate incoming data before using it
for planning or decision-making.
