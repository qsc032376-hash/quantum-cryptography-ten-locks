"""Compare the pinned test wrapper and installed builder in one compiler environment."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from operators import T5, extract, load


def compare(root):
    sys.path.insert(0,str(root))
    from submissions.team3.tier05 import solution
    with TemporaryDirectory() as directory:
        path=Path(directory)/"search.py"
        extract(T5,"research/tier05_extreme/search.py",path)
        research=load("pinned_search",path)
        config=dict(fused=True,order=1,pivot_last=True,level=2,gf2=True)
        fields={}
        for label,circuit in (("pinned_builder",research.build_config(config)),
                              ("integrated_builder",solution.build_circuit())):
            scored,compiled=research.compile_actual(circuit,config)
            fields[label]=dict(metrics=scored["metrics"],execution_gate_counts=dict(compiled.count_ops()))
        assert fields["pinned_builder"]==fields["integrated_builder"]
        print(json.dumps(fields,indent=2))


if __name__=="__main__":
    compare(Path(sys.argv[1]).resolve())
