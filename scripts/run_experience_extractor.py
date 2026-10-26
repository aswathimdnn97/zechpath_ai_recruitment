import sys
from pathlib import Path
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import json

# Load the pipeline module directly to avoid package import issues
proj_root = Path(__file__).resolve().parents[1]
pipeline_path = proj_root / "document_processing" / "resume" / "entity_extracter" / "experience" / "experinece_pipeline.py"

spec = spec_from_file_location("experince_pipeline", str(pipeline_path))
mod = module_from_spec(spec)
spec.loader.exec_module(mod)

experience_extractor = mod.experience_extractor

# Also load company_extractor for debugging
company_path = proj_root / "document_processing" / "resume" / "entity_extracter" / "experience" / "company_extractor.py"
spec2 = spec_from_file_location("company_extractor", str(company_path))
mod2 = module_from_spec(spec2)
spec2.loader.exec_module(mod2)

extract_companies = mod2.extract_companies

sample = [['Senior Python Developer — Tech Nova Solutions Pvt. Ltd.', 'Bengaluru, India | Jan 2023 – Present', 'Designed and maintained Fast API and Django REST services supporting internal business applications and customer-facing workflows.', 'Built React-based dashboards for operational reporting, reducing manual reporting effort by approximately 35 .', 'Optimized PostgreSQL queries and backend APIs, improving average response time for key endpoints by about 30 .', 'Implemented Docker-based development and deployment workflows and integrated automated testing into CI/CD pipelines.', 'Worked with Azure services for application hosting, storage, monitoring, and secure configuration management.', 'Python Developer — Data Bridge Analytics', 'Kochi, Kerala, India | Jul 2020 – Dec 2022', 'Developed Python applications for data ingestion, validation, transformation, and automated reporting.', 'Created REST APIs using Django REST Framework and integrated PostgreSQL and MongoDB data sources.', 'Built data processing pipelines using Pandas and Num Py and supported machine learning model preparation.', 'Developed reusable modules, unit tests, logging, and error-handling utilities for production applications.', 'Collaborated with analysts and business teams to convert reporting requirements into maintainable software features.', 'Junior Software Developer — Code Craft Technologies', 'Thiruvananthapuram, Kerala, India | Jun 2018 – Jun 2020', 'Developed Python and JavaScript modules for web applications and internal automation tools.', 'Implemented frontend components using HTML, CSS, Bootstrap, and JavaScript.', 'Worked with SQL databases, Git-based source control, debugging, and application support.']]

result = experience_extractor(sample)
print(json.dumps(result, indent=2, ensure_ascii=False))
from importlib.util import spec_from_file_location, module_from_spec
block_splitter_path = proj_root / "document_processing" / "resume" / "entity_extracter" / "experience" / "experince_block_splitter.py"
spec3 = spec_from_file_location("block_splitter", str(block_splitter_path))
mod3 = module_from_spec(spec3)
spec3.loader.exec_module(mod3)

split_experience_blocks = mod3.split_experience_blocks

blocks = split_experience_blocks(sample)
print('\nBlocks and candidate companies:')
for i, b in enumerate(blocks, 1):
	print(f'\nBlock {i}:')
	for line in b:
		print('  ', line)
	candidates = extract_companies(b)
	print('  Candidates:', candidates)

	# Debug suffixes and a quick check on first block
	if i == 1:
		try:
			suffixes = mod2.load_suffixes()
			print('\n  Loaded suffixes:', suffixes)
			lower = b[0].lower()
			print('  First line lower:', lower)
			for s in suffixes:
				print('   contains', s, '?', s.lower() in lower)
		except Exception as e:
			print('  Failed loading suffixes:', e)
	# Detailed diagnostics per line
	for line in b:
		l = line.strip()
		low = l.lower()
		print('\n    Line:', l)
		print('      is_date?', mod2.is_date(l) if hasattr(mod2, 'is_date') else 'no is_date')
		import re
		pattern = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|present|\d{4}"
		m = re.search(pattern, low)
		print('      re.search match:', repr(m.group(0)) if m else None)
		# title lookup
		try:
			titles = {item['name'].lower() for item in mod2.load_job_titles()}
			print('      exact_title?', low in titles)
		except Exception:
			print('      failed title load')
		words = l.split()
		print('      words_len:', len(words))
		print('      any_action_word?', any(w in low for w in mod2.ACTION_WORDS))
		tech_count = sum(word in low for word in mod2.TECH_WORDS)
		print('      tech_count:', tech_count)
		print('      any_suffix?', any(s.lower() in low for s in suffixes))
