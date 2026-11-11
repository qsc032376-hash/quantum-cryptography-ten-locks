import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import numpy as np
from research.hyperoptimizer.ir.model import Gate,Semantics,certify
from research.hyperoptimizer.synthesis.windows import compose,exact_window
from research.hyperoptimizer.synthesis.permutations import network,block
from research.hyperoptimizer.verification.operators import verify_block
class Tests(unittest.TestCase):
 def test_phase_gatekeeping(self):
  with self.assertRaises(ValueError):certify(Gate('mcx',(2,),((0,1),(1,0))),'boolean')
  with self.assertRaises(ValueError):certify(Gate('ccx',(2,),semantics=Semantics.RELATIVE),'operator')
 def test_affine_controlled_padding(self):
  table=[(2*x)%5 if x<5 else x for x in range(8)]
  ops=network(table,3,[2,0,1],5,True,True,[(0,1),(1,2)])
  verify_block({'ops':ops,'affine':[(0,1),(1,2)]},table,3)
 def test_smt_mixed_multi_target(self):
  perm=[x^6 if x&1==0 else x for x in range(8)];g=(perm,[0]*8)
  result=exact_window(g,[g],max_depth=1);self.assertEqual(result['indices'],[0])
 def test_smt_phase_sensitive(self):
  phase=(list(range(4)),[0,1,0,1]);twice=compose([phase,phase],4)
  result=exact_window(twice,[phase,twice],max_depth=2);self.assertEqual(result['indices'],[1])
  for gate in (phase,twice):
   matrix=np.zeros((4,4),complex)
   for x in range(4):matrix[gate[0][x],x]=np.exp(1j*np.pi/4*gate[1][x])
   self.assertTrue(np.allclose(matrix.conj().T@matrix,np.eye(4)))
if __name__=='__main__':unittest.main()
