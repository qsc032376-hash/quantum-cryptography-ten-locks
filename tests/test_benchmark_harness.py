"""Low-cost tests using synthetic data; never inspect challenge secrets."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmarks import circuit_benchmark as cb
from benchmarks import cross_seed_regression as cs
from benchmarks.common import resolve, run_worker, snapshot, write_json

BASE='868fb65e20c73a27bffc118f3617080df9cf2f8b'


class ParsingTests(unittest.TestCase):
    def test_cross_cli(self):
        args=cs.parser().parse_args(['--tiers','5','9','10','--seeds','11','23','--output','out.json'])
        self.assertEqual(args.tiers,[5,9,10]); self.assertEqual(args.seeds,[11,23])
    def test_comparison_cli(self):
        args=cb.parser().parse_args(['--baseline','a','--candidate','b','--tier','5','--output','out.json'])
        self.assertEqual(args.target,'two_qubit_gates'); self.assertFalse(args.official)
    def test_duplicate_seed_rejected(self):
        with self.assertRaises(SystemExit):
            cs.main(['--tiers','2','--seeds','1','1','--output','x'])


class CrossSeedStatusTests(unittest.TestCase):
    def example(self):
        return {'resource':{'state':'ok'},'hash_ok':True,'solve_seconds':1,'circuits_executed':2,
                'aer_circuits_observed':2,'aer_calls':1,'aer_timing':{'jobs_finished':1},
                'seed_metadata':{'requested_simulator_seed':11,'actual_forwarded_simulator_seeds':[11]}}
    def test_status_requires_observed_aer_and_hash(self):
        row=self.example(); self.assertEqual(cs.status(row),'PASS')
        row['aer_circuits_observed']=1; self.assertEqual(cs.status(row),'UNCONTROLLED')
        row=self.example(); row['seed_metadata']['actual_forwarded_simulator_seeds']=[]
        self.assertEqual(cs.status(row),'UNCONTROLLED')
        row=self.example(); row['hash_ok']=False; self.assertEqual(cs.status(row),'FAIL')
        row=self.example(); row['resource']['state']='timeout'; self.assertEqual(cs.status(row),'FAIL')


class ComparisonTests(unittest.TestCase):
    def item(self,n):
        m={'two_qubit_gates':n,'depth':3,'total_gates':4,'active_qubits':1}
        return {'metrics':m,'profile_hash_ok':True,'instrumentation_verified':True,
                'native_transpilation_calls':[{'seed_transpiler':12345,'optimization_level':1}],
                'application_rng_seed':None,'resource':{'state':'ok','peak_rss_bytes_sampled':1024},
                'official':{'status':'full','hash_ok':True,'flags':[],'metrics_status':'ok',
                            'metrics':dict(m),'resource':{'state':'ok','peak_rss_bytes_sampled':1024}}}
    def test_accept_only_with_all_conditions(self):
        a,b=self.item(10),self.item(9)
        self.assertEqual(cb.compare(a,b,rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'ACCEPT')
        self.assertEqual(cb.compare(a,b)['recommendation'],'INCONCLUSIVE')
        self.assertEqual(cb.compare(a,self.item(10),rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'REJECT')
        b['official']['hash_ok']=False
        self.assertEqual(cb.compare(a,b,rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'REJECT')
    def test_unknown_missing_and_flagged_are_not_accepted(self):
        a,b=self.item(10),self.item(9)
        b['official']['flags']=['review']; self.assertEqual(cb.compare(a,b,rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'INCONCLUSIVE')
        b=self.item(9); b['metrics']=None
        self.assertEqual(cb.compare(a,b,rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'INCONCLUSIVE')
        b=self.item(9); b['official']['resource']['state']='timeout'
        self.assertEqual(cb.compare(a,b,rules_reviewed=True,reliability=True,reliability_reviewed=True)['recommendation'],'INCONCLUSIVE')
    def test_regression_evidence_requires_actual_distinct_forwarded_seeds(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'r.json'
            data={'kind':'cross_seed_regression','commit':BASE,'runs':[
                {'tier':2,'seed':s,'status':'PASS','hash_ok':True,'seed_metadata':{'actual_forwarded_simulator_seeds':[s,s+1]}}
                for s in range(10,110,10)]}
            write_json(f,data); self.assertEqual(json.loads(f.read_text()),data)
            self.assertEqual(cb.cross_evidence(f,BASE,2),list(range(10,110,10)))
            data['runs'][1]['seed_metadata']['actual_forwarded_simulator_seeds']=[11,21]
            write_json(f,data); self.assertIsNone(cb.cross_evidence(f,BASE,2))


class IsolationTests(unittest.TestCase):
    def test_snapshot_from_git_not_dirty_worktree(self):
        self.assertEqual(resolve(BASE),BASE)
        with tempfile.TemporaryDirectory() as d:
            snapshot(BASE,d)
            self.assertTrue((Path(d)/'tools/check_submission.py').is_file())
            self.assertTrue((Path(d)/'submissions/team3/tier10/solution.py').is_file())
            self.assertFalse((Path(d)/'benchmarks').exists())
    def test_tiny_deadline_stops_worker(self):
        with tempfile.TemporaryDirectory() as d:
            snapshot(BASE,d)
            result=run_worker('cross',d,2,11,0.001,1024)
            self.assertEqual(result['resource']['state'],'timeout')

    def test_protected_config_fingerprint(self):
        self.assertEqual(cb.protected_tree(BASE),cb.protected_tree(BASE))


if __name__ == '__main__': unittest.main()
