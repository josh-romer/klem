"""Preserve actual paired release timings and full-novel cache parity."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from ostensible_reason_audit import read, sha
from doeda_identity_performance import MODES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    package = read(args.package)
    prior_path = ROOT/'docs/additive-ppundeoreo-package-nix.json'
    prior = read(prior_path)
    for receipt in [prior, package]:
        assert receipt['state']=='passed' and receipt['exit_code']==0 and receipt['snapshot_unchanged'] is True
    binary = lambda receipt:Path(next(p for p in receipt['outputs'] if p.endswith('-klem-0.1.0')))/'bin/klem'
    before, after = binary(prior), binary(package)
    assert before!=after
    book = ROOT/'data/books/mujeong.txt'
    db = ROOT/'data/dictionaries/krdict/krdict.db'
    broad_path = ROOT/'docs/predicate-auxiliary-spacing-main-broad.json.gz'
    broad = read(broad_path)
    producer = Path(__file__)
    paths = [before, after, book, db, args.package, prior_path, broad_path, producer]
    frozen = {str(p):sha(p.read_bytes()) for p in paths}
    allowed = sorted(os.sched_getaffinity(0))
    cpu = allowed[-1]
    report = {'schema_version':1,'checklist':'COV-020t','state':'running',
              'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'before_cli':str(before),'cli':str(after),'before_cli_sha256':frozen[str(before)],
              'cli_sha256':frozen[str(after)],'input_source':'data/books/mujeong.txt',
              'input_bytes':book.stat().st_size,'input_sha256':frozen[str(book)],
              'dictionary_sha256':frozen[str(db)],'package_sha256':frozen[str(args.package)],
              'previous_package_sha256':frozen[str(prior_path)],'comparison_sha256':frozen[str(broad_path)],
              'allowed_cpus':allowed,'cpu_affinity':[cpu],'system':platform.platform(),
              'workloads':[],'cache_parity':[],'frozen_inputs':frozen,
              'producer':{'text':producer.read_text(),'sha256':frozen[str(producer)]},
              'scope':'Five interleaved fresh-process pairs for all eight complete novel workloads on one allowed CPU. Includes startup and serialization to /dev/null. Context samples are not evidence of isolation or constant clocks. No statistical equivalence or causality claim. Run only after own build, audit and browser jobs stop.'}
    def save():
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    def context():
        frequency = Path(f'/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq')
        return {'loadavg':Path('/proc/loadavg').read_text().strip(),
                'cpu_frequency_khz':int(frequency.read_text()) if frequency.exists() else None}
    def pin():
        os.sched_setaffinity(0,{cpu})
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='klem-predicate-auxiliary-spacing-timing-') as directory:
            stats = Path(directory)/'time.txt'
            for mode, cache in MODES:
                workload = {'mode':mode,'cache_bytes':cache,'samples':[]}
                report['workloads'].append(workload)
                for run in range(5):
                    versions = [('before',before),('after',after)]
                    if run%2:
                        versions.reverse()
                    for version, cli in versions:
                        command = [str(cli),'text',str(book),'--cache-bytes',str(cache)]
                        if mode!='novel-unannotated':
                            command += ['--dictionary',str(db)]
                        if mode not in ['novel-unannotated','novel-raw']:
                            command += ['--dict-compatible' if 'compatible' in mode else '--dict-only']
                        if 'spacing' in mode:
                            command += ['--suggest-spacing']
                        start_context = context()
                        start = time.perf_counter()
                        result = subprocess.run(['/run/current-system/sw/bin/time','-f','%U %S %e %M','-o',str(stats),*command],stdout=subprocess.DEVNULL,preexec_fn=pin,check=True)
                        elapsed = time.perf_counter()-start
                        user, system, gnu, rss = stats.read_text().split()
                        workload['samples'].append({'run':run+1,'version':version,'command':command,'seconds':elapsed,
                                                    'user_seconds':float(user),'system_seconds':float(system),
                                                    'gnu_elapsed_seconds':float(gnu),'peak_rss_kib':int(rss),
                                                    'start_context':start_context,'end_context':context(),'exit_code':result.returncode})
                        save()
                        print(mode,run+1,version,round(elapsed,4),flush=True)
                workload['summary'] = {v:{'median_seconds':statistics.median(r['seconds'] for r in workload['samples'] if r['version']==v),
                                          'median_user_seconds':statistics.median(r['user_seconds'] for r in workload['samples'] if r['version']==v),
                                          'min_seconds':min(r['seconds'] for r in workload['samples'] if r['version']==v),
                                          'max_seconds':max(r['seconds'] for r in workload['samples'] if r['version']==v)} for v in ['before','after']}
                save()
        for mode, flags in [('raw',[]),('headword',['--dict-only']),('compatible',['--dict-compatible']),('headword-spacing',['--dict-only','--suggest-spacing']),('compatible-spacing',['--dict-compatible','--suggest-spacing'])]:
            expected = next(r for r in broad['comparisons'] if r['mode']=='novel-'+mode)
            checks = []
            for cache in [0,8388608]:
                command = [str(after),'text',str(book),'--dictionary',str(db),*flags,'--cache-bytes',str(cache)]
                digest, records = hashlib.sha256(), 0
                job = subprocess.Popen(command,stdout=subprocess.PIPE)
                try:
                    for line in job.stdout:
                        digest.update(line)
                        records += 1
                    assert job.wait()==0
                finally:
                    if job.poll() is None:
                        job.terminate()
                        job.wait()
                assert digest.hexdigest()==expected['after_jsonl_sha256'] and records==expected['records']==179112
                checks.append({'command':command,'cache_bytes':cache,'sha256':digest.hexdigest(),'records':records,'exit_code':0})
                print('cache parity',mode,cache,records,flush=True)
            report['cache_parity'].append({'mode':mode,'checks':checks})
            save()
        assert all(sha(Path(p).read_bytes())==digest for p,digest in frozen.items())
        report.update(state='passed',exit_code=0,inputs_unchanged=True)
    except BaseException as error:
        report.update(state='failed',error=repr(error))
        raise
    finally:
        report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__=='__main__':
    main()
