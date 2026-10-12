
import cProfile
import pstats
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout


RESUME_DIR = PROJECT_ROOT / "data" / "resumes"

TARGET_RESUMES = [
    "RES_E094FDE23598.pdf",
    "RES_AA41C629DB06.pdf",
]


def profile_resume(filename):
    resume_path = RESUME_DIR / filename

    if not resume_path.exists():
        print(f"Resume not found: {resume_path}")
        return

    raw_text = extract_raw_text(resume_path)
    cleaned_text = clean_text(raw_text)

    # Warm up before profiling.
    fix_layout(cleaned_text)

    profiler = cProfile.Profile()
    profiler.enable()

    result = fix_layout(cleaned_text)

    profiler.disable()

    print("\n" + "=" * 90)
    print(f"FIX_LAYOUT PROFILE: {filename}")
    print(f"Input characters: {len(cleaned_text)}")
    print(f"Output characters: {len(result)}")
    print("=" * 90)

    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(25)


def main():
    for filename in TARGET_RESUMES:
        profile_resume(filename)


if __name__ == "__main__":
    main()