"""At most twelve measured complete Tier 8 circuit alternatives."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.tier08_extreme.screen import build, score
from submissions.team3.tier08.solution import count_modular_powers
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--selected', default=str(HERE/'scored_selected.json'))
    parser.add_argument('--label', default='scored_blocks')
    parser.add_argument('--mode', choices=('dirty','native'))
    parser.add_argument('--pivot', default='first', choices=('first','last'))
    parser.add_argument('--allocation', default='work_first', choices=('work_first','external_first'))
    args = parser.parse_args()
    out = HERE/'whole_candidates.json'
    data = json.loads(out.read_text()) if out.exists() else {'budget':12,'results':[]}
    if not data['results']:
        for name in ('first_whole','first_native_whole','first_last_whole'):
            prior = json.loads((HERE/(name+'.json')).read_text())
            data['results'].append({'label':name,'selected_file':'first_selected.json',**prior})
    selected = json.loads(Path(args.selected).read_text())
    modes = [{'mode':args.mode,'pivot':args.pivot,'allocation':args.allocation}] if args.mode else [
        {'mode':mode,'pivot':pivot,'allocation':allocation}
        for mode,pivot,allocation in itertools.product(('dirty','native'),('first','last'),('work_first','external_first'))
        if mode != 'native' or allocation == 'work_first']
    for emission in modes:
        if len(data['results']) >= data['budget']:
            raise RuntimeError('Complete circuit budget exhausted')
        label = args.label+'_'+emission['mode']+'_'+emission['pivot']+'_'+emission['allocation']
        if any(row['label']==label for row in data['results']):
            raise RuntimeError('Duplicate complete-circuit evaluation')
        circuit = build(selected, **emission)
        row = {'label':label,'selected_file':Path(args.selected).name,
               'source_operations_sha256':hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest(),
               'emission':emission,'whole':score(circuit),'powers':count_modular_powers(circuit)}
        data['results'].append(row)
        data['evaluated'] = len(data['results'])
        out.write_text(json.dumps(data,indent=2)+'\n')
        print(label,row['whole']['metrics'],flush=True)


if __name__ == '__main__':
    main()
