
from pprint import pprint

import sys
from pathlib import Path

# Project root: zechpath_ai_recruitment/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.service.indicconformer_speech_to_text_service import  (
    transcribe_malayalam,
)



def main():
    audio_file = "test_malayalam_16k.wav"

    print("Testing IndicConformer service...")

    result = transcribe_malayalam(
        audio_path=audio_file,
        decoding_method="rnnt",
    )

    pprint(result)


if __name__ == "__main__":
    main()
