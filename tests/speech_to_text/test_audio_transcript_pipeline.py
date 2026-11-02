
from pprint import pprint

from api.service.audio_transcript_pipeline_service import (
    transcribe_and_store_audio,
)


def main():
    result = transcribe_and_store_audio(
        audio_path="test_malayalam_16k.wav",

        # Replace these with IDs from an existing screening session.
        session_id="SCREEN_0B4F4DA9183D",
        candidate_id="CAN_B3B39704E1FF",
        job_id="JOB_BF2FEFE4A4A3",
        question_id="PYF_INTRO_001",

        language="ml",
        decoding_method="rnnt",
    )

    print("Pipeline completed.")
    pprint(result)


if __name__ == "__main__":
    main()
