
import json
from pathlib import Path


JOB_ID = "JOB_BF2FEFE4A4A3"

JD_PATH = Path("data/extracted/jd") / f"{JOB_ID}.json"
PROFILE_DIR = Path("data/candidates/candidate_profile")



def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    if not JD_PATH.exists():
        print(f"JD file not found: {JD_PATH}")
        return

    jd = load_json(JD_PATH)

    print("\n--- Parsed JD ---")
    print("job_id:", jd.get("job_id"))
    print("jd_id:", jd.get("jd_id"))
    print("required_skills:", jd.get("required_skills"))
    print("experience:", jd.get("experience"))
    print("education:", jd.get("education"))

    if not PROFILE_DIR.exists():
        print(f"\nProfile directory not found: {PROFILE_DIR}")
        return

    profiles = sorted(PROFILE_DIR.glob("*.json"))

    print("\n--- Candidate Profile Schema ---")

    if not profiles:
        print("No candidate profile JSON files found.")
        return

    # Inspect one profile first, without displaying its personal data.
    profile = load_json(profiles[0])
    masked = profile.get("masked_profile", profile)

    print("Example file:", profiles[0].name)
    print("Top-level keys:", list(profile.keys()))

    if isinstance(masked, dict):
        print("Profile keys:", list(masked.keys()))

        skills = masked.get("skills")
        experience = masked.get("experience")

        print("Skills type:", type(skills).__name__)
        print("Experience type:", type(experience).__name__)

        if isinstance(skills, dict):
            print("Skill category keys:", list(skills.keys()))

        if isinstance(experience, dict):
            print("Experience field keys:", list(experience.keys()))

    print("\nExpected JD job_id:", JOB_ID)
    print("Inspection complete. No files were modified.")
    
    
    print("\n--- Skill Entry Structure ---")

    if isinstance(skills, list) and skills:
        for index, skill in enumerate(skills[:3]):
            print(f"Skill {index} type:", type(skill).__name__)

            if isinstance(skill, dict):
                print("Skill keys:", list(skill.keys()))

    print("\n--- Experience Entry Structure ---")

    if isinstance(experience, list) and experience:
        for index, item in enumerate(experience[:3]):
            print(f"Experience {index} type:", type(item).__name__)

            if isinstance(item, dict):
                print("Experience keys:", list(item.keys()))
                print(
                    "Experience value types:",
                    {
                        key: type(value).__name__
                        for key, value in item.items()
                    },
                )
    else:
        print("No experience entries found.")

    education = masked.get("education")

    print("\n--- Education Structure ---")
    print("Education type:", type(education).__name__)

    if isinstance(education, list) and education:
        print("First education entry type:", type(education[0]).__name__)

        if isinstance(education[0], dict):
            print("Education keys:", list(education[0].keys()))

    
    print("\n--- Extracted Skill Names ---")

    if isinstance(skills, list):
        print([
            item.get("skill")
            for item in skills[:10]
            if isinstance(item, dict)
        ])

    print("\n--- Experience Duration Details ---")

    if isinstance(experience, list):
        for index, item in enumerate(experience[:3]):
            if not isinstance(item, dict):
                continue

            print(f"\nExperience entry {index + 1}")

            for field in ("duration", "total_experience"):
                value = item.get(field)

                print(f"{field} type:", type(value).__name__)

                if isinstance(value, dict):
                    # Inspect only relevant experience fields.
                    print(f"{field} keys:", list(value.keys()))
                    print(f"{field} values:", value)
                else:
                    print(f"{field} value:", value)



if __name__ == "__main__":
    main()
