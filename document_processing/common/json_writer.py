import json
import os


def save_resume(text, original_pdf_path):

    # Create folder to save structured resume
    output_dir = "data/extracted"
    os.makedirs(output_dir, exist_ok=True)

    # Get filename from original PDF
    # Example:
    # data/resumes/Arjun_Menon_Resume.pdf
    #          ↓
    # Arjun_Menon_Resume
    file_name = os.path.splitext(
        os.path.basename(original_pdf_path)
    )[0]

    # Create JSON filepath
    output_path = os.path.join(
        output_dir,
        file_name + ".json"
    )

    # Resume data
    resume_data = {
        "resume_text": text
    }

    # Save JSON
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(resume_data, file, indent=4, ensure_ascii=False)

    print(f"Extracted jsonfile saved: {output_path}")

    return output_path