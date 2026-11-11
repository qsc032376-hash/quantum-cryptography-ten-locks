import json
from pathlib import Path
from unittest.mock import patch
from submissions.team3.tier08 import solution
from research.hyperoptimizer.synthesis.permutations import block
ROOT=Path(__file__).resolve().parents[3]
def builder(selected):
 def replacement(d,p,w):
  if p!=35 or w!=6:raise ValueError('cache restricted to validated public instance')
  return block(selected[str(d)],w,borrowed=solution.dirty_qubit_count(w))
 with patch.object(solution,'build_controlled_multiplier',replacement):return solution.build_circuit()
def selected_builder():
 return builder(json.loads((ROOT/'research/hyperoptimizer/results/tier08-candidate.json').read_text())['blocks'])
