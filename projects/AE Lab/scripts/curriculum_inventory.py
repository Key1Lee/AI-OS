"""Regenerate the authored availability matrix without reading learner state."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.curriculum import CONCEPTS
from lab.problems import PROBLEMS

matrix={'contract_version':'ae-coverage-v1','scope':'authored_availability_baseline; zero learner observations, not live progress',
 'live_progress':'uv run lab-learn coverage --output .lab/coverage-matrix.json',
 'concepts':[{'concept':identity,'domain':meta['domain'],
   'difficulty':sorted({p['difficulty']['level'] for p in PROBLEMS if identity in p['mastery_tags']}),
   'problems_available':[p['problem_id'] for p in PROBLEMS if identity in p['mastery_tags']],
   'problems_attempted':0,'correct_attempts':0,'failed_attempts':0,'last_tested':None,
   'mastery_state':'UNSEEN','transfer_demonstrated':False} for identity,meta in CONCEPTS.items()]}
path=ROOT/'curriculum/coverage-matrix.json'
path.write_text(json.dumps(matrix,indent=2)+'\n')
print(f'{len(matrix["concepts"])} concepts; authored availability matrix written to {path}')
