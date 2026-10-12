# ZechPath ATS — Developer Guide

## 1. Prerequisites

The public repository is Python-based. Use the Python version supported by the current dependency lock/requirements file; the maintainer's current development context uses Python 3.12. The repository may specify a different supported range, so check `requirements.txt` and project metadata first.

Recommended tools:

- Git
- Python and `venv`
- pip
- pytest
- An editor with Python linting and formatting support

## 2. Clone and create a virtual environment

Windows PowerShell:

```powershell
git clone https://github.com/aswathimdnn97/zechpath_ai_recruitment.git
cd zechpath_ai_recruitment

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If Python 3.12 is not installed or the dependency list requires another version, use the version declared by the project.

macOS/Linux:

```bash
git clone https://github.com/aswathimdnn97/zechpath_ai_recruitment.git
cd zechpath_ai_recruitment

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure local data and secrets

1. Inspect the settings/configuration modules and search for `os.getenv`, `os.environ`, and configuration classes.
2. Create a local `.env` only if the application expects one; do not commit it.
3. Verify input paths for resumes and job descriptions.
4. Verify output paths for candidate profiles, scoring results, and logs.
5. Ensure test fixtures contain synthetic or anonymized candidate data.

Do not invent environment variable names: document only those actually read by the code.

## 4. Run the project

The repository contains both `api/` and a root `main.py`; determine which is the intended runtime entry point for your task.

For a FastAPI application, the common launch pattern is:

```bash
uvicorn api.main:app --reload
```

Use that command only if `api/main.py` exports an `app` object. Otherwise, launch the actual module and application object defined in the repository. For a script-driven pipeline, inspect the root `main.py` and its `if __name__ == "__main__":` block before running it; it may process files from configured local directories.

When running locally, check the terminal for startup logs and open the FastAPI docs page at `/docs` only if the server starts successfully and exposes OpenAPI documentation.

## 5. Run tests

Start with the complete test suite:

```bash
python -m pytest -q
```

Run a focused module while debugging:

```bash
python -m pytest tests/ -q
```

Narrow this to the relevant test file once you identify it, for example:

```bash
python -m pytest tests/scoring/test_ats_scoring_engine.py -q
```

The final example assumes that file exists in your checkout. Use the exact path present in the current repository.

When a test fails:

1. Read the first traceback from the bottom upward to identify the actual failing line.
2. Separate import/setup errors from assertion failures.
3. Fix one root cause at a time.
4. Add a regression test for the bug.
5. Re-run the focused test, then the full suite.
6. Compare extraction output as well as scores; a score can appear plausible even when fields were extracted incorrectly.

## 6. Where to make changes

| Task | Likely area |
|---|---|
| Add or adjust API behavior | `api/` |
| Change resume/JD extraction | `document_processing/`, `parsers/`, or the owning pipeline |
| Change orchestration order | `pipelines/` or the current entry point |
| Change schema fields | `schemas/` and the producer/consumer tests |
| Change semantic representation | `embeddings/` |
| Change matching behavior | `matching/` / `similarity/` |
| Change score formula | `scoring/` and scoring tests |
| Change ranking/shortlisting | Locate the corresponding module and ensure ranking consumes stored scores |
| Add extraction regression tests | `tests/` and fixture data |
| Add or update dictionaries | Appropriate data/configuration subfolder, not a hard-coded extractor branch |

Treat this table as a navigation aid; verify exact module ownership with imports and call sites before editing.

## 7. Safe change workflow

1. Create a feature branch.
2. Reproduce the issue with a small fixture.
3. Add a failing test before changing production code.
4. Trace the value from raw text through extraction, normalization, profile schema, scoring, and output.
5. Make the smallest change that fixes the issue.
6. Run focused tests, then the full suite.
7. Inspect the diff and generated artifacts.
8. Commit code, tests, and relevant documentation together.

Example:

```bash
git checkout -b fix/section-detection
python -m pytest tests/ -q
git diff --check
git status
```

## 8. Debugging extraction issues

Use a stage-by-stage trace rather than changing several extractors simultaneously:

1. Raw extracted text
2. Detected section headings and line ranges
3. Section blocks
4. Extractor output before normalization
5. Alias resolution output
6. Validation output and confidence
7. Final profile JSON
8. Scoring input and component scores

For a company-extraction bug, for example, inspect whether the company/location line was preserved by section detection, split correctly, and then validated. Do not fix a company extractor to compensate for a section splitter that discarded the line.

## 9. Performance and LLM guidance

- Profile the existing deterministic pipeline before optimizing.
- Keep deterministic rules for clear patterns and reserve LLM calls for ambiguous cases.
- Batch independent work only when ordering and shared state do not matter.
- Cache embeddings only with a key that includes the model and source text/version.
- Set request timeouts, output schemas, retry limits, and a fallback for external model calls.
- Benchmark accuracy and latency on the same fixed test corpus before and after a change.
- Never let an LLM invent extracted facts; validate its suggestions against source text.

## 10. Pull request checklist

- [ ] Focused regression tests added
- [ ] Existing tests pass, or failures are explained
- [ ] No secrets or real candidate data committed
- [ ] Error responses are safe and consistent
- [ ] Scoring and ranking responsibilities remain separate
- [ ] Documentation and schema examples updated
- [ ] Performance impact checked for extraction/embedding changes
- [ ] Logs do not expose raw resume text or personal information
