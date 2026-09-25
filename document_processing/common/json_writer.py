import json
import os


def save_resume(text, original_pdf_path):

    # Create folder to save structured JD
    output_dir = "data/extracted/jd"
    os.makedirs(output_dir, exist_ok=True)

    # Get filename from original PDF
    # Example:
    # data/job_descriptions/PythonDeveloperFresher(2).pdf
    #          ↓
    # PythonDeveloperFresher(2)
    file_name = os.path.splitext(
        os.path.basename(original_pdf_path)
    )[0]

    # Create JSON filepath
    output_path = os.path.join(
        output_dir,
        file_name + ".json"
    )

    # Save structured JD data
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            text,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"Extracted JD JSON file saved: {output_path}")

    return output_path
