"""
off_topic_detection_service.py

Responsibilities
-----------------
1. Compare an interview question with a candidate's answer.
2. Identify relevant, partially relevant, and off-topic answers.
3. Detect empty and unclear answers separately.
4. Calculate a rule-based relevance score.
5. Preserve matched terms and evidence for recruiter review.
6. Return a structured semantic response.

Important
---------
This is a lightweight rule-based relevance detector.
It does not use an ML model or replace human recruiter review.
"""

import re
from typing import Any, Optional


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

INTENT = "OFF_TOPIC_DETECTION"

RESPONSE_STATUSES = {
    "ON_TOPIC",
    "PARTIALLY_RELEVANT",
    "OFF_TOPIC",
    "EMPTY_ANSWER",
    "UNCLEAR",
}

# Words that generally do not identify the subject of a question.
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "am",
    "do", "does", "did", "can","company", "could", "would", "will",
    "should", "have", "has", "had", "been", "being",
    "i", "me", "my", "mine", "we", "our", "you", "your",
    "he", "she", "they", "them", "their", "it", "its",
    "what", "when", "where", "which", "who", "whom",
    "why", "how", "tell", "explain", "describe",
    "please", "kindly", "about", "to", "of", "in", "on",
    "at", "for", "from", "with", "and", "or", "but",
    "as", "if", "than", "then", "this", "that", "these",
    "those", "there", "here", "any", "some", "much",
    "many", "more", "most", "yourselves",
    "me", "also", "just",
}

UNCLEAR_ANSWER_PATTERN = re.compile(
    r"^\s*(?:"
    r"yes|no|maybe|not sure|"
    r"i don't know|i do not know|"
    r"no idea|"
    r"cannot say|can't say|"
    r"not applicable|"
    r"same|nothing|"
    r"i am not sure|"
    r"i'm not sure"
    r")\s*[.!?]*\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------
# Related Concept Groups
# ---------------------------------------------------------
# Terms in the same group are treated as related.
# These are practical interview-domain vocabulary groups,
# not a complete semantic language model.

CONCEPT_GROUPS = [
    {
        "python", "django", "flask", "fastapi",
        "pandas", "numpy", "programming", "coding",
        "developer", "development", "software",
        "script", "scripting","application", "applications",
        "building", "built", "solving","problems",
    },
    {
        "experience", "experienced", "worked",
        "working", "employment", "job", "career",
        "internship", "intern", "fresher",
        "beginner", "professional", "years",
        "months",
    },
    
   {
    "skill", "skills", "strength", "strengths",
    "proficient", "proficiency", "knowledge",
    "ability", "abilities", "capability",
    "capabilities", "expertise",

    # Technical skill examples
    "python", "java", "javascript",
    "html", "css", "sql",
    "django", "flask", "fastapi",
    "react", "angular", "node",
    "pandas", "numpy",
    "mysql", "postgresql",
    "programming", "coding",
    },
    {
        "sql", "database", "databases", "mysql",
        "postgresql", "postgres", "sqlite",
        "queries", "query", "dbms",
    },
    {
        "html", "css", "javascript", "frontend",
        "backend", "web", "website", "application",
        "applications", "fullstack", "full",
        "stack", "api", "apis",
    },
    {
        "project", "projects", "built", "build",
        "created", "developed", "implemented",
        "designed", "application", "applications",
    },
    {
        "availability", "available", "joining",
        "join", "notice", "period", "immediately",
        "immediate", "days", "weeks", "months",
    },
    {
        "salary", "expected", "expectation",
        "compensation", "package", "ctc",
        "lpa", "lakhs", "lacs", "remuneration",
        "pay", "earning", "earnings",
        "negotiable", "flexible",
    },
    {
        "education", "degree", "btech", "bachelor",
        "graduate", "graduation", "college",
        "university", "qualification", "studied",
        "electronics", "engineering","educational",
    },
    {
        "team", "teamwork", "collaboration",
        "collaborate", "colleagues", "communication",
        "leadership", "cooperation",
    },
    {
        "problem", "problems", "solving",
        "solution", "solutions", "debugging",
        "debug", "troubleshooting", "issues",
        "challenge", "challenges",
    },
    {
        "motivation", "motivated", "interest",
        "interested", "passion", "passionate",
        "career", "goals", "goal", "learning",
        "learn", "growth",
    },
    {
        "strength", "strengths", "weakness",
        "weaknesses", "improve", "improvement",
        "adaptable", "adaptability", "organized",
        "organization", "communication",
    },
    {
        "hire", "hiring", "suitable", "suitability",
        "candidate", "value", "contribute",
        "contribution", "skills", "experience",
    },
    {
    "yourself", "introduction", "introduce",
    "background", "profile", "education",
    "career", "experience",
    },
]


# ---------------------------------------------------------
# Text Processing
# ---------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """
    Convert text into a set of meaningful lowercase tokens.
    """

    if not text:
        return set()

    tokens = re.findall(
        r"[a-zA-Z]+(?:'[a-zA-Z]+)?|\d+(?:\.\d+)?",
        text.lower(),
    )

    return {
        token
        for token in tokens
        if token not in STOP_WORDS and len(token) > 1
    }


def _expand_concepts(tokens: set[str]) -> set[str]:
    """
    Expand tokens using related interview-domain concepts.
    """

    expanded = set(tokens)

    for group in CONCEPT_GROUPS:
        if tokens.intersection(group):
            expanded.update(group)

    return expanded


# ---------------------------------------------------------
# Answer Validation
# ---------------------------------------------------------

def _is_empty_answer(answer_text: str) -> bool:
    return not answer_text or not answer_text.strip()


def _is_unclear_answer(answer_text: str) -> bool:
    if not answer_text:
        return False

    normalized = answer_text.strip()

    if UNCLEAR_ANSWER_PATTERN.fullmatch(normalized):
        return True

    tokens = _tokenize(normalized)

    # Very short non-informative answers.
    if len(tokens) <= 1:
        return True

    return False


# ---------------------------------------------------------
# Relevance Calculation
# ---------------------------------------------------------

def _calculate_relevance(
    question_text: str,
    answer_text: str,
) -> dict[str, Any]:
    """
    Calculate a heuristic relevance score.

    The score measures how many meaningful question concepts
    are represented in the candidate's answer.
    """

    question_tokens = _tokenize(question_text)
    answer_tokens = _tokenize(answer_text)

    expanded_question = _expand_concepts(question_tokens)
    expanded_answer = _expand_concepts(answer_tokens)

    matched_terms = sorted(
        expanded_question.intersection(expanded_answer)
    )

    if not question_tokens or not answer_tokens:
        score = 0.0
    else:
        # Count the question concepts represented in the answer.
        matched_question_tokens = set()

        for question_token in question_tokens:
            related_terms = _expand_concepts({question_token})

            if related_terms.intersection(answer_tokens):
                matched_question_tokens.add(question_token)

        score = (
            len(matched_question_tokens)
            / len(question_tokens)
        )

        score = min(score, 1.0)

    return {
        "score": round(score, 2),
        "question_keywords": sorted(question_tokens),
        "answer_keywords": sorted(answer_tokens),
        "matched_terms": matched_terms,
    }


# ---------------------------------------------------------
# Status Classification
# ---------------------------------------------------------

def _classify_status(
    relevance_score: float,
) -> str:
    """
    Classify a substantive answer using the relevance score.
    """

    if relevance_score >= 0.65:
        return "ON_TOPIC"

    if relevance_score >= 0.25:
        return "PARTIALLY_RELEVANT"

    return "OFF_TOPIC"


# ---------------------------------------------------------
# Main Service
# ---------------------------------------------------------

def detect_off_topic_response(
    question_text: str,
    answer_text: str,
) -> dict[str, Any]:
    """
    Detect whether a candidate's answer is relevant to
    the given interview question.

    Args:
        question_text: Interview question shown to candidate.
        answer_text: Candidate's spoken or written answer.

    Returns:
        Structured relevance classification.
    """

    question = (
        question_text.strip()
        if isinstance(question_text, str)
        else ""
    )

    answer = (
        answer_text.strip()
        if isinstance(answer_text, str)
        else ""
    )

    if not question:
        return {
            "intent": INTENT,
            "status": "UNCLEAR",
            "is_off_topic": False,
            "relevance_score": 0.0,
            "reason": "Interview question is missing.",
            "confidence": "LOW",
            "requires_review": True,
            "evidence": {
                "question": question,
                "answer": answer,
                "question_keywords": [],
                "answer_keywords": [],
                "matched_terms": [],
            },
        }

    if _is_empty_answer(answer):
        return {
            "intent": INTENT,
            "status": "EMPTY_ANSWER",
            "is_off_topic": False,
            "relevance_score": 0.0,
            "reason": "Candidate did not provide an answer.",
            "confidence": "HIGH",
            "requires_review": True,
            "evidence": {
                "question": question,
                "answer": answer,
                "question_keywords": sorted(_tokenize(question)),
                "answer_keywords": [],
                "matched_terms": [],
            },
        }

    if _is_unclear_answer(answer):
        return {
            "intent": INTENT,
            "status": "UNCLEAR",
            "is_off_topic": False,
            "relevance_score": 0.0,
            "reason": "Candidate's answer is too short or vague to assess.",
            "confidence": "LOW",
            "requires_review": True,
            "evidence": {
                "question": question,
                "answer": answer,
                "question_keywords": sorted(_tokenize(question)),
                "answer_keywords": sorted(_tokenize(answer)),
                "matched_terms": [],
            },
        }

    relevance = _calculate_relevance(
        question,
        answer,
    )

    status = _classify_status(
        relevance["score"]
    )

    if status == "ON_TOPIC":
        reason = "The answer addresses the interview question."
        confidence = "HIGH"
        requires_review = False

    elif status == "PARTIALLY_RELEVANT":
        reason = (
            "The answer contains some relevant information "
            "but may not fully address the question."
        )
        confidence = "MEDIUM"
        requires_review = True

    else:
        reason = (
            "The answer does not appear to address "
            "the interview question."
        )
        confidence = "HIGH"
        requires_review = True

    return {
        "intent": INTENT,
        "status": status,
        "is_off_topic": status == "OFF_TOPIC",
        "relevance_score": relevance["score"],
        "reason": reason,
        "confidence": confidence,
        "requires_review": requires_review,
        "evidence": {
            "question": question,
            "answer": answer,
            "question_keywords": relevance["question_keywords"],
            "answer_keywords": relevance["answer_keywords"],
            "matched_terms": relevance["matched_terms"],
        },
    }


# ---------------------------------------------------------
# Compatibility Alias
# ---------------------------------------------------------

def process_off_topic_detection(
    question_text: str,
    answer_text: str,
) -> dict[str, Any]:
    return detect_off_topic_response(
        question_text=question_text,
        answer_text=answer_text,
    )