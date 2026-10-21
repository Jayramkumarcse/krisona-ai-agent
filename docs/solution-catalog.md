# KRISONA Solution Catalog

## Purpose

The solution catalog is intended to hold candidate solutions supported by
documented sources. It separates source metadata from the rule-based advice
playbooks in `solution_advisor.py`.

## Required metadata

Every record must include:

- `solution_id`: unique stable identifier.
- `problem_type`: lowercase problem-category identifier.
- `title` and `description`: what the proposed solution involves.
- `source_name` and `source_url`: where the supporting material came from.
- `evidence_summary`: a concise description of what the source supports.
- `verified_on`: date the source and relevant claims were last checked,
  using YYYY-MM-DD.
- `evidence_type`: official guidance, systematic review, peer-reviewed
  study, expert guidance, or community experience.
- `cost` and `currency`: estimated cost and three-letter currency code,
  or null when the cost is unknown.
- `duration_days`: estimated duration in days, or null when unknown.
- `safety_rating`: assessed rating from 1 to 5, or null when unassessed.
- `limitations`: known caveats, applicability limits, or evidence gaps.
- `steps`: concrete steps describing how the solution may be tried.

## Trust and verification

The catalog validator checks record structure and metadata types. It does
not fetch URLs, authenticate sources, verify research claims, or certify
that a solution is safe or effective.

HTTPS alone does not establish that a source is credible.

Do not mark estimates as known when they are uncertain. Use null for
unknown cost, duration, or safety rating. A missing estimate must never
be interpreted as proof that a hard constraint is satisfied.

Evidence type describes the kind of source, not the strength of a claim
by itself. Record important caveats and avoid implying causation unless
the cited evidence supports it.

Test fixtures and example URLs are not real catalog entries.

## Loading a catalog

The local loader accepts a UTF-8 JSON file containing a list of records.
It validates each record and rejects duplicate identifiers. The catalog
is size-limited; no network access is performed by the loader.

This module is the validation layer only. Recommendations should not be
labelled evidence-backed until real entries have been researched, reviewed,
and checked against the user's constraints.
