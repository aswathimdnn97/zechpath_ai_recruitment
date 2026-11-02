
"""
transcript_skill_workflow_service.py

Coordinates saved transcript retrieval and skill extraction.
Does not modify transcript creation or normalization.
"""

from typing import Any

from api.service.transcript_service import (
    get_transcript,
    TranscriptServiceError,
)
from api.service.transcript_skill_extraction_persistence_service import (
    process_and_save_transcript_skills,
    TranscriptSkillPersistenceError,
)


class TranscriptSkillWorkflowError(Exception):
    """Raised when the transcript-to-skill workflow fails."""


def process_saved_transcript_skills(
    session_id: str,
    transcript_id: str,
) -> dict[str, Any]:
    """
    Load a persisted transcript and save its extracted skills.
    """

    try:
        transcript_record = get_transcript(
            session_id=session_id,
            transcript_id=transcript_id,
        )

        # Convert the Pydantic record to the dictionary expected
        # by the persistence/orchestration service.
        transcript_data = transcript_record.model_dump(mode="json")

        result = process_and_save_transcript_skills(
            transcript=transcript_data,
        )

        return result

    except (
        TranscriptServiceError,
        TranscriptSkillPersistenceError,
    ) as exc:
        raise TranscriptSkillWorkflowError(
            "Unable to process skills for the saved transcript."
        ) from exc
