# ATS Scoring Troubleshooting Guide

## 1. Purpose

This guide helps developers identify and resolve common issues in the ATS scoring pipeline.

## 2. Common Issues

### Issue 1: HTTP 500 during scoring

**Symptoms**

The scoring endpoint returns `INTERNAL_SERVER_ERROR`.

**Possible causes**

- Unhandled exception in a scoring component
- Missing or malformed candidate profile
- Invalid job description structure
- Incorrect score aggregation
- File reading or serialization errors

**Troubleshooting**

1. Check the application logs for the original exception and traceback.
2. Confirm that the candidate profile and job description files exist.
3. Validate the input JSON structure.
4. Test each scoring component independently.
5. Confirm that expected application exceptions are handled by the registered exception handlers.

**Expected behavior**

Return a meaningful application error for expected failures. Reserve HTTP 500 for unexpected server-side errors.

### Issue 2: Candidate ID does not exist

**Symptoms**

The scoring endpoint fails when an unknown candidate ID is supplied.

**Possible causes**

- Candidate ID does not exist in the candidate store.
- Candidate profile file is missing.
- The lookup uses a different identifier format.

**Troubleshooting**

1. Validate the candidate ID before scoring.
2. Check whether the candidate profile exists at the expected location.
3. Distinguish an unknown candidate from a missing file for a known candidate.
4. Return a consistent, documented error response.

**Expected behavior**

An unknown candidate should produce a clear not-found response, typically HTTP 404, rather than a generic HTTP 500.

### Issue 3: Incorrect experience score

**Symptoms**

The experience score is incorrect or the calculation raises a `TypeError`.

**Possible causes**

- Experience is stored as a list or string rather than a numeric value.
- Missing experience data is not handled.
- Experience parsing produces an unexpected structure.
- Required experience is extracted incorrectly from the job description.

**Troubleshooting**

1. Inspect the candidate profile's experience fields.
2. Inspect the normalized experience values passed to the scoring function.
3. Confirm that numeric comparisons use numeric values.
4. Handle missing or invalid data explicitly.
5. Test candidates with zero, partial, and complete experience data.

**Example of an unsafe expression**

`(roles or skills or cy) > 0`

This can fail when `roles` or `skills` is a list.

**Safer approach**

Validate and calculate a numeric experience value separately before comparing it with a threshold. Do not use list truthiness as a substitute for numeric experience.

### Issue 4: Circular import in education scoring

**Symptoms**

The application fails to import the education scoring module.

**Possible cause**

The module imports its own function from itself, for example:

`from scoring.education_score import calculate_education_score`

inside `scoring/education_score.py`.

**Troubleshooting**

1. Remove the self-import.
2. Define `calculate_education_score()` in its intended module.
3. Review imports for circular dependencies.
4. Run the education scoring unit tests before running the complete pipeline.

### Issue 5: Unexpected final ATS score

**Symptoms**

The final score is outside the expected range or differs from the component scores.

**Possible causes**

- Incorrect weights
- Weights do not sum to the expected total
- Component scores use different scales
- A component is counted more than once
- Incorrect rounding or normalization

**Troubleshooting**

1. Log each component score.
2. Log the configured weights.
3. Verify the aggregation formula.
4. Check that all components use a consistent scale.
5. Compare the calculated result against a manually calculated test case.

### Issue 6: Empty skills produce an unexpectedly high score

**Symptoms**

A candidate receives a high skill score despite having no extracted skills.

**Possible causes**

- Empty input is treated as a perfect match.
- Missing required skills are not penalized.
- The implementation treats the absence of requirements as a complete match.

**Troubleshooting**

1. Inspect the candidate's extracted skills.
2. Inspect the job description's required and preferred skills.
3. Check the behavior when either collection is empty.
4. Define separate outcomes for missing input and a genuine complete match.
5. Add regression tests for empty skills and empty job requirements.

An empty job description should not automatically be treated as a perfect match unless that behavior is explicitly intended and documented.

### Issue 7: Scoring result is not saved

**Symptoms**

The score is calculated but unavailable to ranking or shortlisting.

**Possible causes**

- The persistence function is not called.
- The output path is incorrect.
- JSON serialization fails.
- The save operation fails silently.

**Troubleshooting**

1. Confirm that the score calculation completed successfully.
2. Verify the configured scoring-results directory.
3. Check file permissions and serialization errors.
4. Confirm that the saved record contains the expected candidate ID and job description ID.
5. Verify that ranking reads the same storage location and schema.

### Issue 8: Ranking changes the ATS score

**Symptoms**

A candidate's score changes when ranking is executed.

**Possible cause**

Ranking recalculates or modifies the original score.

**Troubleshooting**

1. Inspect the ranking service.
2. Confirm that it reads stored scoring results.
3. Ensure ranking only orders existing scores.
4. Keep score calculation inside the scoring pipeline.
5. Add a regression test confirming that ranking does not change stored ATS scores.

### Issue 9: Incorrect shortlist decision

**Symptoms**

Candidates receive an unexpected SHORTLIST, REVIEW, or REJECT status.

**Troubleshooting**

Check the configured thresholds and test boundary values.

| ATS score | Expected status |
|---:|---|
| 80.0 | SHORTLIST |
| 79.99 | REVIEW |
| 60.0 | REVIEW |
| 59.99 | REJECT |

These examples assume the configured rules are `score >= 80`, `score >= 60`, and otherwise REJECT.

## 3. Recommended Debugging Sequence

1. Validate the API request.
2. Verify the candidate profile and job description.
3. Test skill scoring independently.
4. Test experience scoring independently.
5. Test education scoring independently.
6. Test semantic scoring independently.
7. Verify the final score calculation.
8. Verify score persistence.
9. Verify ranking and shortlisting independently.

## 4. Logging Recommendations

Record useful diagnostic information, including:

- Request or correlation ID
- Candidate ID and job description ID
- Scoring stage
- Component scores and configured weights
- Error category and traceback for unexpected failures
- Persistence outcome

Do not log complete resumes, unnecessary personal information, credentials, or other sensitive candidate data.

## 5. Regression Testing

After fixing a scoring issue:

1. Add a test reproducing the original failure.
2. Verify the corrected behavior.
3. Run the relevant component tests.
4. Run the full scoring test suite.
5. Run integration tests for scoring, persistence, ranking, and shortlisting.

A fix should not be considered complete until the regression test passes.
