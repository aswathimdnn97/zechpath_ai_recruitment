# Metadata Standards and Transcript Normalization Rules

## 1. Purpose

This document defines the metadata conventions and transcript normalization rules used by the ZechPath AI Recruitment HR screening workflow.

It covers candidate and job identifiers, question identifiers, timestamps, transcription confidence, language identifiers, and transcript text normalization.

## 2. Metadata Standards

### 2.1 Candidate ID

- Field: `candidate_id`
- Purpose: Identifies the candidate associated with the screening session or transcript.
- Standard: Use the candidate identifier maintained by the application.
- Validation: Validate the identifier against the relevant candidate or screening records where required.
- Privacy: Use identifiers instead of repeating personal information unnecessarily in transcript metadata.

### 2.2 Job ID

- Field: `job_id`
- Purpose: Identifies the job associated with the screening.
- Standard: Use the job identifier maintained by the application.
- Validation: Ensure that the job reference is valid for the relevant screening workflow.

### 2.3 Question ID

- Field: `question_id`
- Purpose: Identifies the screening question associated with a response or transcript.
- Standard: Use the configured question identifier.
- Validation: Confirm that the question is assigned to the relevant screening session when required.
- Note: The database also uses `question_pk` for relational integrity. The external question identifier and database primary key serve different purposes.

### 2.4 Timestamp

Relevant timestamp fields include:

- `recorded_at` — recording-related time.
- `transcribed_at` — transcription-related time.
- `created_at` — record creation time.
- `updated_at` — last record update time.
- `submitted_at` — submission time for relevant session or response records.
- `evaluated_at` — evaluation time.

Standards:

1. Use timestamps that represent the actual event.
2. Preserve consistent timestamp serialization across API and storage boundaries.
3. Prefer timezone-aware timestamps and a consistent UTC representation for cross-system exchange.
4. Do not replace a missing event timestamp with an invented time.
5. Keep recording, transcription, submission, and evaluation times semantically distinct.

The exact serialization format should follow the existing API and database configuration.

### 2.5 Confidence Level

- Field: `confidence`
- Purpose: Represents the transcription system's confidence value when available.
- Valid range: `0.0` to `1.0`.
- Interpretation: A higher value represents greater confidence according to the transcription provider's scoring method.
- Validation: Reject values outside the supported range.
- Missing values: Do not invent a confidence value when the transcription system does not provide one.

A confidence score is not a guarantee that the transcript is correct. Low-confidence or ambiguous transcription may require human review. Any thresholds for automatically flagging transcripts should be configured and documented separately.

### 2.6 Language

The screening workflow supports these language codes:

| Code | Language |
|---|---|
| `en` | English |
| `ml` | Malayalam |
| `hi` | Hindi |

Use the configured language code consistently across screening sessions and transcripts. Do not silently translate transcript text during normalization.

### 2.7 Identifiers

The project uses identifiers such as:

- `SCREEN_<identifier>` for screening sessions.
- `TRN_<identifier>` for transcript records.
- `CAN_<identifier>` for candidate records.
- `JOB_<identifier>` for job records.

Examples should be treated as demonstrations of the project's identifier conventions. Actual identifiers must be generated and validated by the relevant services.

## 3. Transcript Normalization Rules

The transcript normalization service is implemented in:

`api/service/transcript_normalization_service.py`

Normalization version: `1.0`.

### 3.1 Supported Rules

| Rule | Behavior |
|---|---|
| Unicode normalization | Apply Unicode NFC normalization |
| Newlines | Convert CRLF and CR line endings to LF |
| Tabs and repeated whitespace | Replace tabs and repeated whitespace with a single space |
| Leading and trailing whitespace | Trim surrounding whitespace |
| Punctuation | Preserve punctuation |
| Capitalization | Preserve letter capitalization |
| Numbers | Preserve numeric content |
| Negation | Preserve negation words such as “not” and “never” |
| Technical terms | Preserve technical terminology |
| Translation | Do not translate the transcript |
| Spelling correction | Do not automatically correct spelling |

### 3.2 Normalization Process

1. Receive the original transcript text.
2. Apply Unicode NFC normalization.
3. Normalize line endings.
4. Collapse tabs and repeated whitespace according to the implemented rules.
5. Trim surrounding whitespace.
6. Return the normalized text without changing the meaning of the answer.
7. Store the normalization version for traceability.

### 3.3 Example

Original transcript:

```text
  I know Python.   I do NOT know Django.	
```

Illustrative normalized result:

```text
I know Python. I do NOT know Django.
```

The example demonstrates whitespace cleanup. The technical terms, punctuation, capitalization, and negation remain unchanged.

### 3.4 Original and Normalized Text

Maintain a distinction between:

- `original_text`: text received from the transcription process.
- `normalized_text`: text after normalization.
- `corrected_text`: text corrected through the review process, when applicable.

Normalization must not overwrite the original text with a translated, paraphrased, or automatically spell-corrected version.

### 3.5 Versioning

The normalization service currently identifies its rules with version `1.0`.

If normalization behavior changes, update the version deliberately and ensure the stored `normalization_version` identifies the rules applied to each transcript.

## 4. Validation and Review

Metadata validation and transcript normalization do not replace the screening workflow's review requirements.

- Validate identifiers and relationships at the appropriate service or database boundary.
- Validate confidence values against the supported range.
- Validate supported language and status values.
- Keep processing status separate from review status.
- Preserve reviewer corrections separately from the original transcript.
- Apply transcript approval requirements before evaluation where required by the implemented workflow.

## 5. Implementation References

- `api/schemas/transcript_schema.py`
- `api/service/transcript_normalization_service.py`
- `api/service/transcript_service.py`
- `api/service/hr_screening_evaluation_service.py`
- `screening_interaction_database_schema.md`

## 6. Design Principle

Metadata provides reliable identification and traceability. Normalization improves textual consistency without changing the candidate's intended answer. Human review remains distinct from automated transcription and normalization.
