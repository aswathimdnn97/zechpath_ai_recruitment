from api.service.hybrid_speech_to_text_service import (
    HybridSpeechToTextService,
)

service = HybridSpeechToTextService()

test_cases = [
    ("test_audio.wav", "en"),
    ("test_malayalam_16k.wav", "ml"),
]

for audio_path, language in test_cases:
    print(f"\nTesting {language}: {audio_path}")

    try:
        result = service.transcribe_file(
            audio_path,
            language=language,
        )

        print("Provider:", result["provider"])
        print("Status:", result["status"])
        print("Transcript:", result["original_text"])
        print("Duration:", result["duration_seconds"])
        print("Segments:", len(result["segments"]))

    except Exception as exc:
        print("FAILED:", exc)