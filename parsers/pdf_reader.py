import pdfplumber


def read_pdf(file):

    text = ""

    with pdfplumber.open(file) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            print("\n========================================")
            print(f"PDF PAGE {page_number} DIAGNOSTIC")
            print("========================================")

            # -------------------------------------------------
            # Extract all words with coordinates
            # -------------------------------------------------
            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=2,
                keep_blank_chars=False,
                use_text_flow=False
            )
            
            print("\n========== WORDS BY VERTICAL POSITION ==========")

            for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
                print(
                    f"top={word['top']:7.1f} "
                    f"x0={word['x0']:7.1f} "
                    f"x1={word['x1']:7.1f} "
                    f"text={word['text']!r}"
                )

            print(f"Total words extracted: {len(words)}")

            # -------------------------------------------------
            # Print every extracted word
            # -------------------------------------------------
            for word in words:
                print(
                    f"text={word['text']!r} "
                    f"x0={word['x0']:.1f} "
                    f"x1={word['x1']:.1f} "
                    f"top={word['top']:.1f} "
                    f"bottom={word['bottom']:.1f}"
                )

            # -------------------------------------------------
            # Search specifically for Skills-related words
            # -------------------------------------------------
            print("\n========== SKILL KEYWORD SEARCH ==========")

            skill_keywords = {
                "skills",
                "skill",
                "java",
                "spring",
                "boot",
                "sql",
                "mysql",
                "html",
                "css",
                "git",
            }

            found = []

            for word in words:

                word_text = word["text"].strip().lower()

                if word_text in skill_keywords:
                    found.append(word)

            if found:
                print("FOUND SKILL-RELATED TEXT:")

                for word in found:
                    print(
                        f"{word['text']!r} "
                        f"x0={word['x0']:.1f} "
                        f"top={word['top']:.1f}"
                    )

            else:
                print("❌ No skill-related words found")

            # -------------------------------------------------
            # Existing normal extraction
            # -------------------------------------------------
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )

            if page_text:
                text += page_text + "\n"

    return text


