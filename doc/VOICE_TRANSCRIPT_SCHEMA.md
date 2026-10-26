# Voice Transcript Schema

## 1. Purpose

The Voice Transcript Schema defines how candidate speech converted to text is represented, validated, normalized, stored, and reviewed during AI-based HR screening.

It supports the ZechPath AI Recruitment screening workflow and integrates transcripts with screening sessions, candidate responses, and evaluation.

## 2. Transcript Data Structure

The transcript schema uses the following logical field groups.

| Field | Purpose |
|---|---|
| `transcript_id` | Unique identifier for a transcript |
| `session_id` | Identifies the HR screening session |
| `candidate_id` | Identifies the candidate |
| `job_id` | Identifies the job associated with screening |
| `question_id` | Identifies the related screening question, when applicable |
| `response_id` | Links the transcript to a saved screening response, when applicable |
| `source` | Identifies the transcript source, such as speech-to-text |
| `language` | Language of the transcript: `en`, `ml`, or `hi` |
| `original_text` | Text received from the transcription process |
| `normalized_text` | Text after normalization |
| `corrected_text` | Text corrected during review, when applicable |
| `confidence` | Transcription confidence value between `0` and `1`, when available |
| `segments` | JSON structure for transcript segments |
| `normalization_version` | Version of the normalization rules applied |
| `status` | Transcript processing status |
| `review_status` | Human review status |
| `reviewer_id` | Identifier of the reviewer, when applicable |
| `recorded_at` | Time associated with recording |
| `transcribed_at` | Time associated with transcription |
| `created_at` | Record creation timestamp |
| `updated_at` | Last record update timestamp |

The exact field definitions and validation rules should remain aligned with `api/schemas/transcript_schema.py` and the persistence implementation.

## 3. Processing Status

Supported processing statuses:

- `PENDING` — transcript awaits processing.
- `PROCESSING` — transcript processing is underway.
- `PROCESSED` — transcript processing completed successfully.
- `FAILED` — transcript processing failed.

## 4. Review Status

Supported review statuses:

- `PENDING` — awaiting review.
- `APPROVED` — transcript approved by a reviewer.
- `CORRECTED` — transcript text corrected during review.

A processing status and a review status represent different concerns. For example, a transcript can be successfully processed but still require human review.

## 5. Transcript Segments and Timing

The `segments` field stores structured segment information as JSONB in the database.

A segment may represent a portion of recognized speech and may include text and timing information when supplied by the transcription process. Exact segment keys and timing constraints must follow the implemented schema.

## 6. Storage Structure

Transcript JSON files are stored using the established path pattern:

`data/hr_screening/transcripts/SCREEN_<session_id>/TRN_<transcript_id>.json`

This groups transcripts under their screening session.

## 7. Normalization Integration

The normalization service is implemented in:

`api/service/transcript_normalization_service.py`

The service uses normalization version `1.0`. The normalization process is described in the Metadata Standards and Transcript Normalization document.

## 8. Evaluation Integration

The transcript workflow integrates with screening evaluation. Approved or corrected linked transcript text is synchronized before evaluation. A pending linked transcript may block evaluation until the required review condition is satisfied.

This ensures that evaluation does not silently treat an unreviewed transcript as final when the workflow requires review.

## 9. Implementation References

- `api/schemas/transcript_schema.py`
- `api/service/transcript_normalization_service.py`
- `api/service/transcript_service.py`
- `api/service/hr_screening_evaluation_service.py`

## 10. Design Principle

The transcript schema separates the recognized text, normalized text, reviewer-corrected text, processing status, and review status. This supports traceability and helps prevent transcription processing from being confused with human approval.
