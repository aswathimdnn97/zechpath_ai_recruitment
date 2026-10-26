from importlib import import_module
from pathlib import Path
import sys
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(proj_root))
mod = import_module('document_processing.resume.entity_extracter.education.school_degree_classifier')
print('Patterns:')
print(mod.HIGHER_SECONDARY_PATTERN.pattern)
print(mod.SECONDARY_PATTERN.pattern)

blocks = [
    [
        "2011-2012 All India Senior School Certificate Exam",
        "Kendriya Vidyalaya Kalpetta",
        "Central Board of Secondary Education",
    ],
    [
        "2000-2010 All India Secondary School Examination",
        "Kendriya Vidyalaya Kalpetta",
        "Central Board of Secondary Education",
    ],
]

for b in blocks:
    print('Block:', b)
    print('Text:', ' '.join(b))
    print('Higher match:', bool(mod.HIGHER_SECONDARY_PATTERN.search(' '.join(b))))
    print('Secondary match:', bool(mod.SECONDARY_PATTERN.search(' '.join(b))))
    print('classify_school_degree:', mod.classify_school_degree(b))
    import inspect
    print('\nFunction source:')
    print(inspect.getsource(mod.classify_school_degree))
