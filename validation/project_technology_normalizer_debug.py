import inspect

from document_processing.resume.entity_extracter.skill.synonym_resolver import (
    resolve_synonyms
)

print(inspect.getfile(resolve_synonyms))

print("\n" + "=" * 70)
print("RESOLVE_SYNONYMS SOURCE")
print("=" * 70)

print(inspect.getsource(resolve_synonyms))

print("\nLIST INPUT:")
print(resolve_synonyms(["Python", "FastAPI", "PostgreSQL"]))

print("\nDICT INPUT:")
print(
    resolve_synonyms(
        [
            {"skill": "Python"},
            {"skill": "FastAPI"},
            {"skill": "PostgreSQL"},
        ]
    )
)