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
