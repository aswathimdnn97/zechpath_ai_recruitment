# Screening Interaction Database Schema

## 1. Purpose

This document describes the PostgreSQL schema used for screening interactions in ZechPath AI Recruitment, based on the table definitions, constraints, indexes, and consistency checks inspected during the current review.

> **Scope:** This document records the observed schema. Recommendations are proposals only; this document does not mean any database migration has been applied.

## 2. Tables and responsibilities

| Table | Purpose |
|---|---|
| `screening_sessions` | Stores candidate screening sessions, job/role context, language, status, and timestamps. |
| `session_questions` | Records questions assigned to each session, their order, and mandatory status. |
| `screening_responses` | Stores candidate answers, selected options, answer data, status, and timestamps. |
| `transcripts` | Stores speech-to-text text, normalized/corrected text, segments, confidence, processing status, and review status. |
| `questions` | Stores the question bank, including role, category, language, text, type, active/mandatory flags, and metadata. |
| `evaluations` | Stores session-level evaluation versions, scores, result status, reports, and timestamps. |
| `evaluation_details` | Stores per-question evaluation scores, statuses, and feedback. |
| `recruiter_reviews` | Stores recruiter decisions and comments for a session and optionally an evaluation. |

Other tables observed in `public` include `candidates_demo` and `screening_sessions_demo`; their detailed definitions were not part of this review.

## 3. Relationships

```text
questions
   │ questions.question_pk
   ▼
session_questions
   │ session_questions.session_question_id
   ▼
screening_responses
   │ screening_responses.response_id (optional link)
   ▼
transcripts

screening_sessions
   ├── session_questions
   ├── screening_responses
   ├── transcripts
   ├── evaluations
   │      └── evaluation_details
   └── recruiter_reviews
```

The diagram is conceptual. The inspected foreign-key relationships are summarized below.

### 3.1 Sessions and assignments

- `session_questions.session_id` references `screening_sessions.session_id`.
- `session_questions.question_pk` references `questions.question_pk`.
- Unique `(session_id, question_id)` prevents the same question identifier being assigned twice in a session.
- Unique `(session_id, question_order)` prevents duplicate order positions within a session.
- `question_order` must be greater than zero.

### 3.2 Responses

- `screening_responses.session_id` references `screening_sessions.session_id` with `ON DELETE CASCADE`.
- `(session_id, session_question_id)` references the same pair in `session_questions` with `ON DELETE CASCADE`.
- `session_question_id` also references `session_questions.session_question_id` with `ON DELETE CASCADE`.
- Unique `session_question_id` enforces at most one response row per assigned question.
- The composite foreign key ensures that the response session and assignment belong together.

### 3.3 Transcripts

- `transcripts.session_id` references `screening_sessions.session_id` with `ON DELETE CASCADE`.
- Nullable `transcripts.response_id` references `screening_responses.response_id` with `ON DELETE SET NULL`.
- The transcript/session consistency query returned **0 rows**, so no existing mismatches were found by that query.
- The two separate foreign keys do not by themselves guarantee that a future transcript's `session_id` matches the session of its linked response. Consider stronger enforcement only after reviewing migration impact and application write paths.

### 3.4 Evaluations and details

- `evaluations.session_id` references `screening_sessions.session_id` with `ON DELETE CASCADE`.
- Unique `(session_id, evaluation_version)` allows one evaluation per version for a session.
- `(evaluation_details.session_id, evaluation_id)` references `(evaluations.session_id, evaluation_id)` with `ON DELETE CASCADE`.
- `evaluation_details.question_pk` references `questions.question_pk`.
- Unique `(evaluation_id, question_id)` prevents duplicate details for the same question identifier in one evaluation.
- The evaluation-question consistency query returned **0 rows**, so no mismatches were found among details matched by `question_pk`.
- Because both `question_id` and `question_pk` are stored, application or database enforcement may be needed to prevent future drift.

### 3.5 Recruiter reviews

- `recruiter_reviews.session_id` references `screening_sessions.session_id` with `ON DELETE CASCADE`.
- `(session_id, evaluation_id)` references `(evaluations.session_id, evaluation_id)`.
- `evaluation_id` is nullable, so a review can be recorded without an evaluation reference under the current nullable-FK behavior.
- `decision` is restricted to the values listed in Section 5.

## 4. Table columns

### 4.1 `screening_sessions`

| Column | Type | Null/default notes |
|---|---|---|
| `session_id` | `varchar` | NOT NULL; primary key |
| `candidate_id` | `varchar` | NOT NULL |
| `job_id` | `varchar` | NOT NULL |
| `role_id` | `varchar` | NOT NULL |
| `language` | `varchar` | NOT NULL |
| `status` | `varchar` | NOT NULL; default `CREATED` |
| `started_at` | `timestamptz` | Nullable |
| `submitted_at` | `timestamptz` | Nullable |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |

### 4.2 `session_questions`

| Column | Type | Null/default notes |
|---|---|---|
| `session_question_id` | `bigint` | NOT NULL; primary key |
| `session_id` | `varchar` | NOT NULL |
| `question_id` | `varchar` | NOT NULL |
| `question_order` | `integer` | NOT NULL |
| `is_mandatory` | `boolean` | NOT NULL; default `false` |
| `assigned_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `question_pk` | `bigint` | NOT NULL; references `questions.question_pk` |

### 4.3 `screening_responses`

| Column | Type | Null/default notes |
|---|---|---|
| `response_id` | `bigint` | NOT NULL; primary key |
| `session_question_id` | `bigint` | NOT NULL; unique; references an assignment |
| `session_id` | `varchar` | NOT NULL; references the session and composite assignment |
| `answer_text` | `text` | Nullable |
| `selected_option` | `jsonb` | Nullable |
| `answer_status` | `varchar` | NOT NULL; default `DRAFT` |
| `submitted_at` | `timestamptz` | Nullable |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `answer_data` | `jsonb` | Nullable |

### 4.4 `transcripts`

| Column | Type | Null/default notes |
|---|---|---|
| `transcript_id` | `varchar` | NOT NULL; primary key |
| `session_id` | `varchar` | NOT NULL; references a session |
| `response_id` | `bigint` | Nullable; references a response with `ON DELETE SET NULL` |
| `candidate_id` | `varchar` | NOT NULL |
| `job_id` | `varchar` | NOT NULL |
| `question_id` | `varchar` | Nullable |
| `source` | `varchar` | NOT NULL; default `SPEECH_TO_TEXT` |
| `language` | `varchar` | NOT NULL |
| `original_text` | `text` | Nullable |
| `normalized_text` | `text` | Nullable |
| `corrected_text` | `text` | Nullable |
| `confidence` | `numeric` | Nullable; must be between 0 and 1 when present |
| `segments` | `jsonb` | Nullable |
| `normalization_version` | `varchar` | Nullable |
| `status` | `varchar` | NOT NULL; default `PENDING` |
| `review_status` | `varchar` | NOT NULL; default `PENDING` |
| `reviewer_id` | `varchar` | Nullable |
| `recorded_at` | `timestamptz` | Nullable |
| `transcribed_at` | `timestamptz` | Nullable |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |

### 4.5 `questions`

| Column | Type | Null/default notes |
|---|---|---|
| `question_id` | `varchar` | NOT NULL |
| `role_id` | `varchar` | NOT NULL |
| `category` | `varchar` | NOT NULL |
| `language` | `varchar` | NOT NULL |
| `question_text` | `text` | NOT NULL |
| `question_type` | `varchar` | NOT NULL; default `TEXT` |
| `is_mandatory` | `boolean` | NOT NULL; default `false` |
| `is_active` | `boolean` | NOT NULL; default `true` |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `question_pk` | `bigint` | NOT NULL; referenced by assignments and evaluation details |
| `metadata` | `jsonb` | NOT NULL; default `{}` |

### 4.6 `evaluations`

| Column | Type | Null/default notes |
|---|---|---|
| `evaluation_id` | `varchar` | NOT NULL; primary key |
| `session_id` | `varchar` | NOT NULL; references a session |
| `evaluation_version` | `varchar` | NOT NULL |
| `overall_score` | `numeric` | Nullable; between 0 and 100 when present |
| `result_status` | `varchar` | NOT NULL; default `PENDING` |
| `report` | `jsonb` | Nullable |
| `evaluated_at` | `timestamptz` | Nullable |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |

### 4.7 `evaluation_details`

| Column | Type | Null/default notes |
|---|---|---|
| `detail_id` | `bigint` | NOT NULL; primary key |
| `evaluation_id` | `varchar` | NOT NULL; references an evaluation together with `session_id` |
| `session_id` | `varchar` | NOT NULL |
| `question_id` | `varchar` | NOT NULL |
| `score` | `numeric` | Nullable; non-negative and cannot exceed `max_score` when both are present |
| `max_score` | `numeric` | Nullable; default `100`; if present, greater than zero |
| `evaluation_status` | `varchar` | NOT NULL; default `PENDING` |
| `feedback` | `text` | Nullable |
| `evaluated_at` | `timestamptz` | Nullable |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `question_pk` | `bigint` | NOT NULL; references `questions.question_pk` |

### 4.8 `recruiter_reviews`

| Column | Type | Null/default notes |
|---|---|---|
| `review_id` | `bigint` | NOT NULL; primary key |
| `session_id` | `varchar` | NOT NULL; references a session |
| `evaluation_id` | `varchar` | Nullable; references an evaluation together with `session_id` |
| `reviewer_id` | `varchar` | NOT NULL |
| `decision` | `varchar` | NOT NULL |
| `comments` | `text` | Nullable |
| `reviewed_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |
| `created_at` | `timestamptz` | NOT NULL; default `CURRENT_TIMESTAMP` |

## 5. Check constraints and allowed values

| Table / column | Rule |
|---|---|
| `screening_sessions.language` | `en`, `ml`, `hi` |
| `screening_sessions.status` | `CREATED`, `IN_PROGRESS`, `SUBMITTED`, `EVALUATED`, `CANCELLED` |
| `session_questions.question_order` | Greater than `0` |
| `screening_responses.answer_status` | `DRAFT`, `SUBMITTED`, `REVIEW_REQUIRED` |
| `questions.language` | `en`, `ml`, `hi` |
| `transcripts.language` | `en`, `ml`, `hi` |
| `transcripts.confidence` | `NULL` or between `0` and `1` inclusive |
| `transcripts.status` | `PENDING`, `PROCESSING`, `PROCESSED`, `FAILED` |
| `transcripts.review_status` | `PENDING`, `APPROVED`, `CORRECTED` |
| `evaluations.overall_score` | `NULL` or between `0` and `100` inclusive |
| `evaluations.result_status` | `PENDING`, `PASSED`, `FAILED`, `REVIEW_REQUIRED`, `COMPLETED`, `NEEDS_REVIEW` |
| `evaluation_details.evaluation_status` | `PENDING`, `EVALUATED`, `REVIEW_REQUIRED`, `NOT_APPLICABLE`, `NEEDS_REVIEW`, `UNANSWERED` |
| `evaluation_details.max_score` | `NULL` or greater than `0` |
| `evaluation_details.score` | `NULL` or non-negative; when present, must not exceed a non-null `max_score` |
| `recruiter_reviews.decision` | `SHORTLIST`, `REJECT`, `HOLD`, `NEEDS_FURTHER_REVIEW` |

## 6. Keys, unique constraints, and indexes

### 6.1 Keys and uniqueness observed

| Table | Observed key/uniqueness |
|---|---|
| `screening_sessions` | Primary key on `session_id` |
| `session_questions` | Primary key on `session_question_id`; unique `(session_id, question_id)`, `(session_id, session_question_id)`, `(session_id, question_order)` |
| `screening_responses` | Primary key on `response_id`; unique `session_question_id` |
| `transcripts` | Primary key on `transcript_id` |
| `questions` | `question_pk` is referenced as a key; exact primary/unique definition should be confirmed in the catalog for a complete inventory |
| `evaluations` | Primary key on `evaluation_id`; unique `(session_id, evaluation_id)` and `(session_id, evaluation_version)` |
| `evaluation_details` | Primary key on `detail_id`; unique `(evaluation_id, question_id)` |
| `recruiter_reviews` | Primary key on `review_id` |

The unique `(session_id, session_question_id)` constraint on `session_questions` may appear redundant because `session_question_id` is already a primary key. It supports the composite foreign key from `screening_responses`; do not remove it without redesigning that relationship.

### 6.2 Indexes observed

- `screening_responses`: primary-key index on `response_id`; unique index on `session_question_id`. No index with `session_id` as the leading column was observed.
- `session_questions`: primary-key index and unique indexes on `(session_id, question_id)`, `(session_id, session_question_id)`, and `(session_id, question_order)`.
- `evaluations`: primary-key index and unique indexes on `(session_id, evaluation_id)` and `(session_id, evaluation_version)`.
- `evaluation_details`: primary-key index and unique index on `(evaluation_id, question_id)`.
- `recruiter_reviews`: only the primary-key index was observed.
- `transcripts`: only the primary-key index was observed.

PostgreSQL does not automatically create indexes on foreign-key referencing columns. Add indexes based on real query patterns and query plans, not by default.

## 7. Consistency checks performed

### 7.1 Transcript session vs. response session

```sql
SELECT
    t.transcript_id,
    t.session_id AS transcript_session_id,
    t.response_id,
    r.session_id AS response_session_id
FROM public.transcripts AS t
JOIN public.screening_responses AS r
    ON r.response_id = t.response_id
WHERE t.session_id <> r.session_id;
```

**Observed result:** 0 rows. No existing mismatches were found. Rows with a null `response_id` are not covered by this join.

### 7.2 Evaluation detail question ID vs. question primary key

```sql
SELECT
    ed.detail_id,
    ed.evaluation_id,
    ed.question_id AS detail_question_id,
    ed.question_pk,
    q.question_id AS referenced_question_id
FROM public.evaluation_details AS ed
JOIN public.questions AS q
    ON q.question_pk = ed.question_pk
WHERE ed.question_id <> q.question_id;
```

**Observed result:** 0 rows. No mismatches were found among evaluation details matched by `question_pk`. Because this is an inner join, it does not detect orphaned keys; the foreign key is expected to prevent those.

## 8. Recommendations (proposals only)

1. **Review indexes against query patterns.** If reviews are commonly fetched by session, evaluate an index on `recruiter_reviews(session_id)`. If transcripts are fetched by session or response, evaluate indexes on `transcripts(session_id)` and `transcripts(response_id)`.
2. **Consider response lookup performance.** If response queries frequently filter by session, evaluate an index on `screening_responses(session_id)`. An index whose leading column is `session_question_id` does not substitute for one leading with `session_id`.
3. **Enforce transcript/session consistency if required.** Current data is consistent in the tested rows, but the two foreign keys do not guarantee future consistency between a transcript and its linked response. Assess composite-key options and application write paths before a migration.
4. **Prevent question identifier drift.** Since `evaluation_details` stores both `question_id` and `question_pk`, determine whether service-level validation is sufficient or database enforcement is needed.
5. **Review status naming.** Both `REVIEW_REQUIRED` and `NEEDS_REVIEW` appear in evaluation-related checks. Inspect service enums and persisted values before standardizing; do not remove values without a migration plan.
6. **Validate transcript state transitions in services.** Check constraints validate individual values, not the sequence of allowed processing/review transitions.
7. **Complete question key inventory.** Inspect the exact primary/unique constraints on `questions.question_pk` and `questions.question_id` if a complete catalog-level schema report is required.

## 9. Conclusion

The inspected schema contains the main entities and relationships needed for screening interactions. Both targeted consistency checks returned zero rows. Complete the documentation first, then make only evidence-based schema changes after confirming application query patterns and service-level rules.
