"""Typed semantics contracts; Boolean evidence alone never certifies phase."""
from dataclasses import dataclass
from enum import Enum
from typing import Literal
class Semantics(str,Enum):
 EXACT='exact_unitary'
 RELATIVE='relative_phase_unitary'
 BOOLEAN='classical_action_only'
@dataclass(frozen=True)
class Ancilla:
 wire:int
 state:Literal['clean_zero','dirty']
 restored:bool=True
@dataclass(frozen=True)
class Gate:
 kind:Literal['x','cx','ccx','mcx','phase','affine','controlled_permutation']
 targets:tuple[int,...]
 controls:tuple[tuple[int,int],...]=()
 phase_pi_over_4:int=0
 linear_cnot:tuple[tuple[int,int],...]=()
 permutation:tuple[int,...]=()
 semantics:Semantics=Semantics.EXACT
 phase_sensitive:bool=True
 ancillas:tuple[Ancilla,...]=()
 def __post_init__(self):
  assert len(set(self.targets))==len(self.targets)
  assert all(value in (0,1) for _,value in self.controls)
  assert not set(self.targets)&{w for w,_ in self.controls}
  assert all(a.restored for a in self.ancillas)
def certify(gate,evidence):
 if gate.phase_sensitive and evidence=='boolean':raise ValueError('phase evidence required')
 if gate.semantics!=Semantics.EXACT:raise ValueError('requires contextual phase-cancellation proof')
 return True
