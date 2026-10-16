# KRISONA AI AGENT — Dataset Resources

## 1. Existing evaluation dataset

File: `data/decision_evaluation_cases.json`

Purpose:
- Test rule-based recommendation behavior.
- Check constraint handling and clarification cases.
- Track regression behavior as the code changes.

Current limitation:
This is a small, curated evaluation set. It is not a training dataset
and does not establish real-world decision quality.

## 2. External dialogue datasets

### Schema-Guided Dialogue (SGD)

URL:
https://github.com/google-research-datasets/dstc8-schema-guided-dialogue

License: CC BY-SA 4.0 (review the included license and attribution terms).

Potential use:
Explore annotated intents, dialogue state, and task-oriented conversations.

Limitation:
The repository is archived and the dataset focuses on task-oriented
domains, not general personal-goal coaching.

### MultiWOZ

URL:
https://github.com/budzianowski/multiwoz

Potential use:
Study multi-domain dialogue and dialogue-state management.

Important:
Review the license and terms for the exact dataset version before use.

Limitation:
Its task-oriented conversations do not directly represent general life goals.

## 3. Dataset loading documentation

Hugging Face Datasets:
https://huggingface.co/docs/datasets/en/loading

Purpose:
Learn to load local or hosted JSON, CSV, and other supported data formats.

## 4. KRISONA data governance

- Review licenses and attribution requirements before importing external data.
- Keep private mission records and local SQLite databases out of public datasets.
- Keep training, validation, and test data separate.
- Record dataset versions and preprocessing steps.
- Do not treat benchmark results as proof of real-world reliability.
- Do not add an external dataset to production behavior without evaluation.

## 5. Planned next dataset

Create a KRISONA-specific evaluation set with reviewed examples of:
- Ambiguous goals requiring clarification.
- Goals with deadlines and measurable success criteria.
- User constraints such as budget and available time.
- Candidate actions with explicit trade-offs.
- Cases where the system should abstain instead of recommending.

## 6. AI assistant usage behavior dataset

File: `data/raw/daily_ai_assistant_usage_behavior.csv`

Observed structure:
- 300 records and 8 columns.
- Timestamp, device, usage category, prompt length, session
  duration, satisfaction rating, assistant model, and tokens used.
- Initial validation found no blank fields.

Potential use:
- Summarize session duration and token usage.
- Compare satisfaction ratings across usage categories and devices.
- Explore usage patterns for research and demonstrations.

Limitations:
- The data's provenance and license have not yet been verified.
- Observed associations do not establish causation.
- Do not treat usage behavior as evidence that a goal was achieved.

## 7. KRISONA 5,000-document project dataset

File: `data/raw/krisonaai_5000_docs.zip`

Observed structure:
- ZIP integrity check passed.
- 5,002 files: two structured data files and 5,000 phase documents.
- Structured files include `dataset.jsonl` and `projects_summary.csv`.
- Project documents use discovery, goal/scope, solution, build/pilot,
  and review phases.

Potential use:
- Explore project lifecycles and phase-level patterns.
- Develop retrieval and project-planning evaluations.
- Study how project goals and reviews are represented.

Limitations:
- Source, license, and redistribution rights remain unverified.
- Validate schemas and individual records before using them.
- Do not assume project examples generalize to personal goals.

## 8. KRISONA 50K demo workbook

File: `data/demo/krisonaai_50k_demo_dataset.xlsx`

Sheets:
- `README`
- `Summary`
- `Dataset`

Observed structure:
- The Dataset sheet contains 50,000 data rows and a header row.

Potential use:
- Inspect goal, problem, root-cause, severity, recommendation,
  action-guidance, and outcome fields.
- Build offline analysis and evaluation experiments after verifying
  the actual schema and target definitions.

Limitations:
- Treated as synthetic demo data pending source verification.
- Validate columns, value ranges, duplicate rows, and target definitions.
- Demo performance does not establish real-world decision quality.

## 9. Scientific models reference

File: `docs/references/famous_scientific_models.docx`

Purpose:
- Reference catalog of model families and example use cases.
- Support model-selection research for prediction, classification,
  clustering, natural-language processing, and decision support.

Limitations:
- This reference is not an implemented model or a verified benchmark.
- Confirm licensing before redistribution.
- Select models based on validated use cases and evaluation results.

## 10. Data handling policy for new resources

- Keep raw datasets separate from application code.
- Verify provenance, license, schema, and intended use before redistribution.
- Avoid exposing personal, confidential, or sensitive records.
- Do not use demo datasets as proof of production reliability.
- Record preprocessing, validation, and evaluation results.

## 11. Goal pattern analysis

Module: `src/krisona_ai/goal_pattern_analyzer.py`

Input:
- `data/demo/krisonaai_50k_demo_dataset.xlsx`
- The `Dataset` worksheet.

Run:
`python -m krisona_ai.goal_pattern_analyzer`

Report:
- `goal_pattern_report.json` (when shell output is redirected to this file).

Summaries:
- Overall goal outcomes and mean achievement.
- Outcome distributions by domain and severity.
- Mean planned time, actual time, and time variance.

Validation:
- Required fields and numeric values are checked.
- Achievement percentages must be between 0 and 100.
- Time variance must equal actual time minus planned time.

Limitations:
- The workbook is demo data; provenance and licensing must be verified.
- Severity-group differences are descriptive, not causal.
- Do not use these results to automatically change recommendations
  without separate evaluation on appropriate data.
