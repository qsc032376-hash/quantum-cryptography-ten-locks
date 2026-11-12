"""Aggregate uncensored audit evidence; never change or rebuild the approved ZIP."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--evidence',type=Path);p.add_argument('--remove-private-copies',action='store_true');a=p.parse_args()
    root=a.repository.resolve();out=(a.evidence or root/'docs/v63-metrics-reconciliation').resolve();private=a.private_root.resolve()
    rounds=json.loads((out/'three-runs.json').read_text());actual=json.loads((out/'actual-circuits.json').read_text())
    archive=json.loads((root/'docs/v63-final-verification/archive-verification.json').read_text())
    reference=json.loads(subprocess.check_output(['git','-C',str(root),'show','ce75c0721622d363e77912191a52a02c34f92472:docs/v63-evidence/zip-checker/report.json']))
    packages={k:importlib.metadata.version(k) for k in rounds['fixed_environment']['packages']}
    same_environment=(packages==rounds['fixed_environment']['packages'] and platform.python_version()==rounds['fixed_environment']['python'] and digest(Path(sys.executable).resolve())==rounds['fixed_environment']['python_executable_sha256'])
    preservation=[]
    for run in rounds['runs']:
        fresh=private/f"official-{run['run']}"
        preservation.append({'run':run['run'],
            'all_37_runtime_members_unchanged':all(digest(fresh/'submissions'/m['member'])==m['sha256'] for m in archive['members']),
            'all_protected_official_files_unchanged':all(digest(fresh/f['path'])==f['sha256'] for f in archive['extraction']['protected_official_files'])})
    metrics_by_run=[{t:v['metrics'] for t,v in run['tiers'].items()} for run in rounds['runs']]
    same_metrics=len(metrics_by_run)==3 and all(m==metrics_by_run[0] for m in metrics_by_run)
    required=(rounds.get('completed_runs')==3 and all(r['all_required_checks_pass'] and r['resource_state']=='ok' and r['exit_code']==0 for r in rounds['runs']))
    zip_same=digest(root/'drafts/ten-locks-team3-v6.3-rc.zip')==rounds['zip_sha256']
    retained_capture_complete=all(set(r['captured_tiers'])=={'5','6','7'} and all(v['worker_python_hash_seed']=='0' and not v['worker_isolated_flag_present'] for v in r['captured_tiers'].values()) for r in rounds['runs'])
    differences=[]
    for t in map(str,range(1,11)):
        for k,new in metrics_by_run[0][t].items():
            old=reference['tiers'][t]['metrics'][k]
            if old!=new:differences.append({'tier':int(t),'metric':k,'historical':old,'three_runs_each':new,'delta':new-old})
    safe=(required and same_environment and same_metrics and zip_same and retained_capture_complete and actual['all_official_winners_reproduced'] and actual['all_selected_winners_exact_native_sequence_equal'] and all(x['all_37_runtime_members_unchanged'] and x['all_protected_official_files_unchanged'] for x in preservation))
    stages=[]
    for tier in (5,6,7):
        solve=json.loads((out/f'tier{tier:02d}-solve-profile.json').read_text())
        score=json.loads((out/f'tier{tier:02d}-score-profile.json').read_text())
        bridge=solve['bridge_to_primary_checker']
        expected=metrics_by_run[0][str(tier)]
        stages.append({'tier':tier,
            'solve_hash_matches':solve['outcome']['hash_ok'],
            'solve_error_absent':not solve['outcome']['error_present'],
            'trace_complete':solve['trace_complete'] and score['trace_complete'],
            'raw_aer_and_recording_match_both_directions':solve['every_aer_input_matches_official_recording_native_exact'] and solve['every_official_recording_matches_aer_input_native_exact'],
            'bridge_to_primary_run_native_exact':bridge['unique_count_equal'] and bool(bridge['native_exact_by_record_index']) and all(bridge['native_exact_by_record_index']),
            'scored_metrics_match_diagnostic_and_primary_reports':score['selected_metrics_equal_official_worker_output'] and score['selected_scoring_output']['metrics']==expected})
    stage_checks=all(all(value for key,value in row.items() if key!='tier') for row in stages)
    structure_checks=[]
    for tier in (5,6,7):
        rows=[row for row in actual['results'] if row['tier']==tier]
        for stage in ('stage3_actual_recorded_input','stage4_scoring_replay_output'):
            digests=[[c[stage]['structural_digest'] for c in row['circuits']] for row in rows]
            structure_checks.append({'tier':tier,'stage':stage,'all_three_ordered_digest_lists_equal':len(digests)==3 and all(x==digests[0] for x in digests)})
    safe=safe and stage_checks and all(x['all_three_ordered_digest_lists_equal'] for x in structure_checks)
    verdict='SAFE_WITH_VARIANCE' if safe and differences else 'METRICS_RECONCILED' if safe else 'RELEASE_BLOCKED'
    report={'verdict':verdict,'completed_at':datetime.now(ZoneInfo('America/New_York')).isoformat(),
        'approved_commit':rounds['approved_commit'],'approved_zip_sha256':rounds['zip_sha256'],
        'approved_zip_unchanged':zip_same,'three_scheduled_runs_completed':rounds.get('completed_runs'),
        'new_full_results':sum(sum(v['status']=='full' for v in r['tiers'].values()) for r in rounds['runs']),
        'new_hash_matches':sum(sum(v['hash_ok'] for v in r['tiers'].values()) for r in rounds['runs']),
        'new_flagged_tiers':sum(sum(bool(v['flags']) for v in r['tiers'].values()) for r in rounds['runs']),
        'required_execution_checks_pass':required,'all_ten_per_tier_metrics_identical_across_three_runs':same_metrics,
        'end_dependency_versions_and_python_binary_match_start':same_environment,
        'actual_scoring_input_capture_complete':retained_capture_complete,
        'all_actual_winner_inputs_exact_native_sequence_and_global_phase_equal':actual['all_selected_winners_exact_native_sequence_equal'],
        'actual_scoring_replay_matches_original_official_reports':actual['all_official_winners_reproduced'],
        'historical_exact_metrics_reproduced':not differences,'historical_differences':differences,
        'same_environment_totals_each_run':[r['totals'] for r in rounds['runs']],
        'preservation_checks':preservation,
        'four_stage_checks':stages,'three_run_structural_fingerprints':structure_checks,
        'four_stage_diagnostics_all_checks_pass':stage_checks,
        'cross_historical_environment_root_cause_fully_isolated':False,
        'historical_native_circuit_identity_proven':False,
        'acceptance_basis':'Unchanged approved bytes, three uncensored functional/metric passes, actual executed/scored-circuit provenance, stable local native circuits, and official rules scoring valid actual measurements; historical exact gate counts are not a compliance requirement.',
        'score_impact_source':'../v63-metrics-reconciliation/scoring-impact.json',
        'ranking_invariance_claimed':False,'formal_cross_historical_unitary_equivalence_claimed':False,
        'previous_strict_reference_audit_preserved':True,
        'no_new_optimization_or_release_or_form_submission':True,
        'private_circuit_payloads_committed':False,'private_copies_removed':False}
    if a.remove_private_copies:
        assert safe and private.parent==Path('/workspace/scratch') and private.name=='v63-variance-private'
        shutil.rmtree(private);report['private_copies_removed']=True
    (out/'investigation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('verdict','new_full_results','new_hash_matches','new_flagged_tiers','all_ten_per_tier_metrics_identical_across_three_runs','private_copies_removed')}))
    if not safe:raise SystemExit(1)

if __name__=='__main__':main()
