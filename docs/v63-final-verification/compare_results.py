"""Compare freshly executed official results and recheck every delivered byte."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--official-root',type=Path,required=True);a=p.parse_args()
    root=a.repository.resolve();out=root/'docs/v63-final-verification'
    archive=json.loads((out/'archive-verification.json').read_text())
    fresh=json.loads((out/'checker/report.json').read_text())
    reference=json.loads(subprocess.check_output(['git','-C',str(root),'show','ce75c0721622d363e77912191a52a02c34f92472:docs/v63-evidence/zip-checker/report.json']))
    execution=json.loads((out/'execution.json').read_text());delivery=json.loads((out/'download-verification.json').read_text())
    checks={};failures=[]
    if set(fresh['tiers'])!=set(map(str,range(1,11))):failures.append('exact ten tiers missing')
    for t in map(str,range(1,11)):
        v=fresh['tiers'].get(t,{});expected=reference['tiers'][t]
        checks[t]={'full':v.get('status')=='full','hash_match':v.get('hash_ok') is True,
                   'zero_flags':v.get('flags')==[],'actual_aer_execution':v.get('circuit_executed') is True,
                   'valid_metrics':v.get('metrics_status')=='ok','all_four_metrics_match':v.get('metrics')==expected['metrics'],
                   'metrics':v.get('metrics'),'expected_metrics':expected['metrics'],
                   'solve_seconds':v.get('solve_seconds'),'circuits_executed':v.get('circuits_executed'),
                   'unique_circuits':v.get('unique_circuits'),'oracle_calls':v.get('oracle_calls'),
                   'status':v.get('status'),'flags':v.get('flags')}
        for name in ('full','hash_match','zero_flags','actual_aer_execution','valid_metrics','all_four_metrics_match'):
            if not checks[t][name]:failures.append(f'tier {t}: {name}')
    totals={k:sum((v.get('metrics') or {}).get(k,0) for v in fresh['tiers'].values()) for k in ('two_qubit_gates','depth','total_gates')}
    if totals!={'two_qubit_gates':103166,'depth':217625,'total_gates':294982}:failures.append('totals differ')
    if execution['exit_code']!=0 or execution['resource_state']!='ok':failures.append('execution resource/exit failure')
    for key in ('config_sha256','hashes_sha256','qiskit','qiskit_aer'):
        if fresh[key]!=reference[key]:failures.append(key+' differs')
    extraction_unchanged=all(digest(a.official_root/'submissions'/entry['member'])==entry['sha256'] for entry in archive['members'])
    official_unchanged=all(digest(a.official_root/entry['path'])==entry['sha256'] for entry in archive['extraction']['protected_official_files'])
    zip_unchanged=digest(root/'drafts/ten-locks-team3-v6.3-rc.zip')==archive['expected_sha256']
    delivered_copy_unchanged=digest(Path(delivery['shareable_copy_location']))==archive['expected_sha256']
    for name,value in [('extraction_unchanged',extraction_unchanged),('official_unchanged',official_unchanged),('zip_unchanged',zip_unchanged),('delivered_copy_unchanged',delivered_copy_unchanged)]:
        if not value:failures.append(name)
    core_failures=[f for f in failures if f != 'totals differ' and not f.endswith(': all_four_metrics_match')]
    disposition='RELEASE_BLOCKED' if core_failures else 'INCONCLUSIVE' if failures else 'ZIP_VERIFIED'
    result={'approved_commit':archive['approved_commit'],'verified_zip_sha256':archive['actual_sha256'],'status':disposition,'archive_and_functional_checks_pass':not core_failures,'exact_reference_metrics_reproduced':not failures,'ready_for_submission_under_requested_criteria':not failures,'core_failures':core_failures,'checked_at':datetime.now(ZoneInfo('America/New_York')).isoformat(),
            'failures':failures,'tiers':checks,'totals':totals,'totals_note':'Depth is a sum of ten separate circuit depths, not one combined circuit depth; active qubits are per tier, not summed.',
            'full_count':sum(v['full'] for v in checks.values()),'hash_match_count':sum(v['hash_match'] for v in checks.values()),
            'actual_aer_tier_count':sum(v['actual_aer_execution'] for v in checks.values()),
            'flagged_tier_count':sum(not v['zero_flags'] for v in checks.values()),
            'timeout_count':sum(v.get('status')=='timeout' or 'timed out' in v.get('metrics_status','').lower() or any('timeout' in str(f).lower() for f in (v.get('flags') or [])) for v in fresh['tiers'].values()),
            'post_run_archive_unchanged':zip_unchanged,'post_run_extracted_members_unchanged':extraction_unchanged,
            'post_run_official_files_unchanged':official_unchanged,'post_run_download_copy_unchanged':delivered_copy_unchanged,
            'reference_report':'ce75c0721622d363e77912191a52a02c34f92472:docs/v63-evidence/zip-checker/report.json',
            'fresh_report_sha256':digest(out/'checker/report.json'),'checker_source_sha256':digest(a.official_root/'tools/check_submission.py'),
            'simulation_kind':'Classical Qiskit Aer execution of the submitted quantum circuits; not quantum hardware.',
            'form_submitted':False}
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','full_count','hash_match_count','actual_aer_tier_count','flagged_tier_count','timeout_count','totals','failures')}))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
