"""Audit an extracted team directory against an immutable Git tree and search replay."""
import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from importlib.metadata import version

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

BASE = "0c043a40d3ae10b579be312c72a7adfe1e26e9a4"
RESEARCH = "d294a5a6f26b8abe96b1117928f8857e95750040"
FROZEN = "ca7290c7f6b35e37e4ef94f3d5f79110309f594f"
TEAM = "submissions/team3"
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args])


def blob(ref, path):
    return git("show", f"{ref}:{path}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def functions(source):
    return {node.name: ast.get_source_segment(source, node)
            for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def audit(tree, team, regenerated):
    prefix = TEAM + "/tier09/"
    changed = git("diff", "--name-only", BASE, tree, "--", TEAM).decode().splitlines()
    assert set(changed) == {prefix + p for p in ("solution.py","public_multiplier.py","public_operations.json")}
    paths = git("ls-tree", "-r", "--name-only", tree, TEAM).decode().splitlines()
    manifest = {}
    for path in paths:
        data = (team / path.removeprefix(TEAM + "/")).read_bytes()
        assert data == blob(tree, path), path
        manifest[path] = sha(data)
    assert set(team.rglob("*.json")) == {team / f"tier{t}/public_operations.json" for t in ("09","10")}
    assert manifest[TEAM + "/tier10/public_operations.json"] == "b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6"
    official = ["tools", "common", "hashes.txt", "requirements.txt", *(f"tier{i:02}" for i in range(1,11))]
    assert not git("diff", "--name-only", BASE, tree, "--", *official)
    assert blob(tree,prefix+"solution.py") == blob(BASE,prefix+"solution.py").replace(
        b"from .shared_controls import",b"from .public_multiplier import")
    research = blob(RESEARCH,"research/tier09_global/search.json")
    accepted = json.loads(research)
    ops = json.loads((team/"tier09/public_operations.json").read_bytes())
    assert ops == accepted["candidate"] == json.loads(regenerated.read_bytes())["candidate"]
    original = functions(blob(RESEARCH,"research/tier09_global/search.py").decode())
    imported = functions((team/"tier09/public_multiplier.py").read_text())
    assert all(original[k] == imported[k] for k in ("grouped","emit"))
    sys.path[:0] = [str(team.parent), str(team.parents[1])]
    module = importlib.import_module(team.name+".tier09.solution")
    q = module.build_circuit()
    assert module.count_modular_powers(q)["exponents"] == [1<<j for j in range(14)]
    assert q.num_qubits == 22 and q.num_clbits == 14
    assert set(ops) == {str(pow(2,1<<j,77)) for j in range(14)}
    errors = {}
    for d in sorted(map(int,ops)):
        u = module.build_controlled_multiplier(d,77,7)
        ideal = np.zeros((256,256),complex)
        for x in range(128):
            for c in (0,1):
                y = x*d%77 if c and x<77 else x
                ideal[2*y+c,2*x+c] = 1
        extended = QuantumCircuit(9)
        # Mark data/control live at HLS entry; only wire 8 starts clean.
        extended.h(range(8))
        extended.barrier()
        extended.compose(u,range(8),inplace=True)
        native = transpile(extended,basis_gates=["rz","sx","x","cx"],optimization_level=1,
                           seed_transpiler=12345,num_processes=1)
        probe = QuantumCircuit(9)
        probe.h(range(8))
        probe.compose(native,inplace=True)
        from qiskit_aer import AerSimulator
        probe.save_unitary()
        simulator = AerSimulator(method="unitary", max_parallel_threads=2)
        columns = np.asarray(simulator.run(probe).result().get_unitary())[:,:256]
        errors[str(d)] = {
            "forward":float(np.max(abs(Operator(u).data-ideal))),
            "inverse":float(np.max(abs(Operator(u.inverse()).data-ideal.conj().T))),
            "compiled_clean_output":float(np.max(abs(columns[:256]-ideal))),
            "compiled_scratch_leakage_amplitude":float(np.max(abs(columns[256:]))),
        }
        print(d, errors[str(d)], flush=True)
        assert max(errors[str(d)].values()) < 1e-9, errors[str(d)]
    deps = {}
    for line in blob(BASE,"requirements.txt").decode().splitlines():
        name,pin=line.split("==")
        deps[name]=version(name)
        assert deps[name]==pin
    assert sys.version_info[:2] == (3,12)
    return dict(team_tree=git("rev-parse",tree+":"+TEAM).decode().strip(),
                python=platform.python_version(),dependencies=deps,source_sha256=manifest,
                changed_sha256={p:manifest[p] for p in changed},operator_max_errors=errors,
                original_search_json_sha256=sha(research),replayed_seed=20261111,
                replayed_ordered_operations_match=True,verbatim_emitter=True,
                final_zip_sha256=sha(blob(FROZEN,"drafts/ten-locks-team3-final.zip")))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("ref")
    p.add_argument("team",type=Path)
    p.add_argument("regenerated",type=Path)
    a=p.parse_args()
    stats=audit(a.ref,a.team.resolve(),a.regenerated)
    (OUT/"source-audit.json").write_text(json.dumps(stats,indent=2)+"\n")
