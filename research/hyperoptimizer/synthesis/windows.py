"""Bounded SMT on <=3-wire exact monomial windows, including Z8 phases.

A gate is (basis permutation, phase exponents modulo eight). This supports
X/CX/Toffoli/mixed-control/multi-target gates and diagonal pi/4-phase gates.
No Boolean-only certificate is accepted: phases are solver constraints too.
"""
import z3

def compose(gates,size):
 perm=list(range(size));phase=[0]*size
 for gp,gf in gates:
  phase=[(phase[x]+gf[perm[x]])%8 for x in range(size)];perm=[gp[y] for y in perm]
 return perm,phase

def exact_window(target,library,max_depth=3,timeout_ms=1000):
 size=len(target[0]);assert size in (2,4,8) and max_depth<=4 and timeout_ms<=5000
 assert all(sorted(g[0])==list(range(size)) and len(g[1])==size for g in [target,*library])
 attempts=[]
 def lookup(values,index):
  expr=z3.IntVal(values[-1])
  for j in reversed(range(len(values)-1)):expr=z3.If(index==j,values[j],expr)
  return expr
 for depth in range(max_depth+1):
  solver=z3.Solver();solver.set(timeout=timeout_ms);choices=[z3.Int(f'g{i}') for i in range(depth)]
  for g in choices:solver.add(g>=0,g<len(library))
  for x in range(size):
   state=z3.IntVal(x);phase=z3.IntVal(0)
   for choice in choices:
    ns=state;np=phase
    for i,(gp,gf) in enumerate(library):
     ns=z3.If(choice==i,lookup(gp,state),ns);np=z3.If(choice==i,(phase+lookup(gf,state))%8,np)
    state,phase=ns,np
   solver.add(state==target[0][x],phase%8==target[1][x]%8)
  status=solver.check();attempts.append({'depth':depth,'status':str(status)})
  if status==z3.sat:
   ids=[solver.model().eval(c).as_long() for c in choices];assert compose([library[i] for i in ids],size)==target
   return {'indices':ids,'attempts':attempts,'optimal_in_library':all(a['status']=='unsat' for a in attempts[:-1])}
  if status==z3.unknown:break
 return {'indices':None,'attempts':attempts,'optimal_in_library':False}
