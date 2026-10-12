# ZechPath ATS — Technical Documentation

## 1. Purpose and scope

ZechPath AI Recruitment is a Python recruitment/Applicant Tracking System (ATS) project. Its ATS scope is to process job descriptions and resumes, normalize extracted candidate information, compare candidate profiles with job requirements, calculate match scores, and support ranking and shortlisting.

This document focuses on the ATS path. It does not claim that every optional subsystem or directory is active in production.

## 2. Core workflow

1. **Input** — a job description (JD) and candidate resume files are supplied.
2. **Document extraction** — text is extracted from supported document formats. Scanned PDFs may require OCR; verify the configured extractor and OCR fallback in the active pipeline.
3. **Section detection** — text is segmented into logical resume sections such as summary, skills, education, experience, projects, certifications, and achievements.
4. **Entity extraction** — structured fields are extracted, including personal information, skills, education, work history, projects, and certifications.
5. **Normalization and validation** — aliases, spelling variants, canonical skills, job titles, companies, institutions, and date/duration values are normalized and validated using project dictionaries and extraction rules.
6. **Profile construction** — extracted fields are represented in a candidate-profile structure.
7. **Bias mitigation / privacy handling** — where configured, personal attributes should be masked or excluded from scoring features. Keep identifiers required for workflow tracking separate from scoring features.
8. **Representation / embeddings** — JD and candidate profile text may be converted to embeddings for semantic comparison.
9. **Scoring** — component scores such as skills, experience, education, and semantic similarity are combined by the ATS scoring engine.
10. **Persistence** — profiles and scoring outputs are saved to the configured data locations.
11. **Ranking** — candidates are ordered using already-computed scores and any explicitly defined tie-breakers. Ranking should not silently recalculate ATS scores.
12. **Shortlisting** — scores are mapped to a decision category using configured thresholds, then returned to the caller or downstream workflow.

### Expected decision labels

The project workflow described by the maintainer uses these example thresholds:

| Score | Label |
|---|---|
| 80.0 and above | `SHORTLIST` |
| 60.0 to below 80.0 | `REVIEW` |
| Below 60.0 | `REJECT` |

Keep thresholds in configuration or a single policy module. Confirm the active implementation before relying on these values in a live workflow.

## 3. Logical responsibilities

| Area | Responsibility |
|---|---|
| `api/` | API application and route layer; inspect route modules for exact endpoints |
| `document_processing/` | Resume/JD text extraction, section detection, and entity extraction |
| `parsers/` | Parsing helpers and structured extraction logic |
| `pipelines/` | Orchestration of multi-step resume/JD processing |
| `schemas/` | Structured data contracts and validation models |
| `embeddings/` | Text representation / embedding generation |
| `similarity/` and `matching/` | Similarity and candidate-to-JD matching utilities |
| `scoring/` | Component and overall ATS scoring logic |
| `jobs/` and `workers/` | Job/task execution helpers; verify whether asynchronous processing is enabled |
| `data/` | Dictionaries, fixtures, inputs, and/or generated artifacts depending on subfolder |
| `tests/` | Automated tests |
| `utils/` | Shared helpers |
| `main.py` | Root entry point used for orchestration or local pipeline execution; confirm its current role in the checked-out branch |

## 4. Scoring model

The documented logical model separates component extraction/matching from final aggregation:

- **Skill score:** overlap between required/preferred JD skills and normalized candidate skills.
- **Experience score:** relevance and duration of candidate experience against the JD's requirements.
- **Education score:** degree/qualification relevance where applicable to the role.
- **Semantic score:** semantic similarity between a normalized JD representation and a candidate representation.

The exact weights, caps, missing-data behavior, and normalization formula must be read from the current scoring implementation. Avoid documenting a specific weighted formula unless it matches the code and tests.

### Scoring invariants

- Each component score should have a defined range, ideally `0–100`.
- Missing data must be handled explicitly; an empty JD must not accidentally produce a perfect candidate score.
- Missing candidate IDs and missing profiles should produce clear domain errors (for example, a not-found response), not an unexplained generic HTTP 500.
- Score generation should be deterministic for the same inputs and configuration, except where a model/provider introduces documented nondeterminism.
- Store component scores and a scoring-version identifier where feasible so results can be audited.
- Ranking should consume stored scores and preserve the single source of truth for score calculation.

## 5. Data contracts

Use a validated, versioned profile structure. The project’s resume schema has been described in this general shape:

```json
{
  "personal_information": {},
  "education": [],
  "experience": [],
  "projects": [],
  "certifications": [],
  "skills": [],
  "metadata": {
    "parser_version": "1.0"
  }
}
```

This is an illustrative contract, not a guarantee of every field currently returned. Consult the actual Pydantic/schema definitions before changing payloads.

Recommended conventions:

- Represent dates consistently (for example, ISO `YYYY-MM` where month precision is all that exists).
- Distinguish `null` (unknown/not extracted) from empty arrays (known to contain no items).
- Preserve source text or provenance for important extracted values when feasible.
- Keep canonical names and original matched text separate for debugging.
- Deduplicate normalized skills by canonical skill ID, not merely by raw string.
- Keep extraction confidence and match method where the implementation supports them.

## 6. Error handling and API behavior

Use consistent error envelopes and map domain failures to appropriate HTTP status codes.

| Condition | Recommended behavior |
|---|---|
| Missing upload filename | `400 Bad Request` |
| Unsupported file type | `415 Unsupported Media Type` or documented `400` |
| Invalid request payload | `422 Unprocessable Entity` |
| Candidate/profile not found | `404 Not Found` |
| Resume parsing failure | Domain-specific response with safe details |
| Scoring/ranking/shortlisting failure | Domain-specific response; log traceback server-side |
| Unexpected internal failure | `500 Internal Server Error` with no sensitive internals exposed |

Do not return stack traces, full resume text, secrets, or personal data in public error responses. Log a request/correlation ID and a concise exception context instead.

## 7. Quality, fairness, and privacy

- Use the minimum personal data needed for processing.
- Exclude protected or irrelevant personal attributes from scoring.
- Do not treat gaps in employment as a negative signal unless there is a transparent, job-related and validated policy; prefer measuring relevant evidence.
- Evaluate score behavior across resume layouts, career breaks, nontraditional education, and different writing styles.
- Provide human review for borderline or low-confidence extraction and scoring.
- Retain source documents and generated profile/scoring files only under a documented retention policy.
- Add tests that prove personal attributes do not change the score when job-related evidence is identical.

## 8. Observability

Log pipeline stage, candidate/job internal IDs, elapsed time, model/extractor version, and failure category. Avoid logging raw resume text or direct identifiers by default.

Suggested per-resume metrics:

- extraction success/failure rate
- section-detection accuracy on labelled fixtures
- field-level precision/recall for skills, education, company, title, dates, certifications
- end-to-end latency by document type
- scoring latency and missing-data frequency
- shortlist/review/reject distribution, monitored for unexpected shifts

## 9. Versioning and reproducibility

For every scoring result, aim to retain:

- scoring algorithm version
- parser version
- dictionary/alias data version
- embedding model and version
- JD/profile revision identifiers
- component scores and final score
- timestamp and configuration identifier

Recompute scores only through an explicit re-scoring operation. Ranking should not modify prior scoring records.

## 10. Known documentation gaps to close

Before release, confirm these details from the code:

1. Exact API routes, request/response examples, and authentication behavior.
2. Supported formats and OCR fallback behavior.
3. Exact scoring weights and edge-case rules.
4. Active persistence paths and file naming rules.
5. Whether `jobs/` and `workers/` are used by the running API.
6. Environment variables and secrets required to start the application.
7. Current test command and baseline test status.
999999999999999999999999999999999999999999999999999999999999999999999