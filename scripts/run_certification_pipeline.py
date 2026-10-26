from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

# Load pipeline
pipe_path = proj_root / 'document_processing' / 'resume' / 'entity_extracter' / 'certifications' / 'certification_pipeline.py'
spec = spec_from_file_location('cert_pipe', str(pipe_path))
mod = module_from_spec(spec)
spec.loader.exec_module(mod)
certification_pipeline = mod.certification_pipeline

# Load splitter
split_path = proj_root / 'document_processing' / 'resume' / 'entity_extracter' / 'certifications' / 'certification_block_splitter.py'
spec2 = spec_from_file_location('cert_split', str(split_path))
mod2 = module_from_spec(spec2)
spec2.loader.exec_module(mod2)
split_certification_blocks = mod2.split_certification_blocks

sample = [['Microsoft Certified: Azure Developer Associate — Microsoft (2024)', 'Microsoft Certified: Azure AI Fundamentals — Microsoft (2023)', 'Google Cloud Professional Data Engineer — Google Cloud (2023)', 'Machine Learning Specialization — Coursera / Deep Learning.AI (2022)', 'TensorFlow Developer Certificate — TensorFlow (2022)', 'Python for Data Science — IBM (2021)']]

print('Split blocks:')
blocks = split_certification_blocks(sample)
for b in blocks:
    print(b)

print('\nPipeline output:')
print(certification_pipeline(sample))
