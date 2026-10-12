# ATS Scoring Logic

## 1. Overview

The Applicant Tracking System (ATS) scoring engine evaluates how well a candidate's resume matches a job description. It uses structured candidate profile data and job requirements to calculate a final ATS score.

The scoring pipeline consists of:

1. Resume parsing
2. Candidate profile generation
3. Bias mitigation
4. Skill score calculation
5. Experience score calculation
6. Education score calculation
7. Semantic similarity calculation
8. Final ATS score generation
9. Scoring result storage

## 2. Input Data

### Candidate Profile

The candidate profile may contain:

- Technical and soft skills
- Work experience and duration
- Education and qualifications
- Projects and certifications
- Other extracted resume information

### Job Description

The parsed job description may contain:

- Required skills
- Preferred skills
- Minimum experience requirements
- Educational requirements
- Job responsibilities and other relevant information

The scoring engine should use the actual output schema produced by the JD parsing pipeline.

## 3. Scoring Components

### 3.1 Skill Score

The skill score measures the match between candidate skills and job requirements.

It should consider required and preferred skills according to the project's configured scoring rules.

The implementation should document:

- Required skill matching
- Preferred skill matching
- Skill normalization and aliases
- Missing skills
- Skill score weighting

### 3.2 Experience Score

The experience score evaluates the candidate's relevant professional experience against the job's experience requirements.

It should consider:

- Total experience
- Relevant experience, where supported
- Minimum and maximum experience requirements
- Missing or invalid experience data

Experience calculations must handle missing values safely and must not compare lists or strings directly with numeric values.

### 3.3 Education Score

The education score compares the candidate's educational qualifications with the requirements specified in the job description.

It should handle missing education data and distinguish between unavailable information and a confirmed mismatch.

### 3.4 Semantic Similarity Score

The semantic score evaluates the similarity between the candidate's profile and the job description using the project's configured semantic matching or embedding approach.

The documentation should specify the embedding model, input text construction, similarity metric, and score normalization actually used by the implementation.

### 3.5 Final ATS Score

The final ATS score combines the component scores according to the configured weights.

For a weighted-average implementation:

**Final ATS Score =**

`(Skill Score × Skill Weight) + (Experience Score × Experience Weight) + (Education Score × Education Weight) + (Semantic Score × Semantic Weight)`

The weights must be represented as fractions that sum to 1.0, or percentages that sum to 100%, depending on the implementation.

Each component score should be normalized to a consistent scale before aggregation.

The formula above is illustrative. The production documentation must reflect the actual formula and weights in the scoring engine.

## 4. Scoring Result

The scoring result should contain the fields supported by the project's output schema, such as:

- Candidate ID
- Job description ID
- Component scores
- Final ATS score
- Scoring status
- Relevant metadata

The scoring result should be saved only after successful score calculation and validation.

## 5. Ranking and Shortlisting

Ranking and shortlisting consume the stored ATS scores.

- **SHORTLIST:** Score is at least 80.
- **REVIEW:** Score is at least 60 but below 80.
- **REJECT:** Score is below 60.

These thresholds should be configurable or documented as project constants.

Ranking should order candidates using their existing ATS scores. It should not recalculate the scores.

## 6. Validation and Error Handling

The scoring engine should validate:

- Candidate ID exists.
- Candidate profile exists and is readable.
- Job description exists and is valid.
- Component scores are numeric and within the permitted range.
- Scoring weights are valid.
- Final score is finite and within the expected range.

Expected failures should produce meaningful application errors rather than generic HTTP 500 responses.

## 7. Testing

Tests should cover:

- Complete candidate and job description data
- Missing candidate profile
- Unknown candidate ID
- Missing or empty job description
- Empty candidate skills
- Missing experience or education
- Invalid component scores
- Invalid scoring weights
- Final score calculation
- Score persistence
- Ranking without score recalculation
- Shortlisting threshold boundaries
