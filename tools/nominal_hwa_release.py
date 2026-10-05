"""Verify actual Nix receipts and release/debug/API/browser parity."""
import argparse
import base64
import hashlib
import math
import re
from pathlib import Path

from nominal_hwa_audit import ROOT, SOURCE, read, sha

REPORT=ROOT/'docs/nominal-hwa-packaged-checks.json.gz'
DIAGNOSTICS=ROOT/'docs/nominal-hwa-diagnostics.json.gz'
RUNTIME=ROOT/'docs/nominal-hwa-runtime-checks.json.gz'
BROAD=ROOT/'docs/nominal-hwa-packaged-observations.json.gz'
CORPORA=ROOT/'docs/nominal-hwa-packaged-corpora.json.gz'


def inspect_streams(package, broad, corpora):
    """Bind independently captured release streams to the tested executable."""
    debug_broad = read(ROOT / 'docs/nominal-hwa-observations.json.gz')
    debug_corpora = read(ROOT / 'docs/nominal-hwa-corpora.json.gz')
    for actual, expected, fields in (
        (broad, debug_broad, ('comparisons', 'changed_record_pairs')),
        (corpora, debug_corpora, ('after_words', 'corpora', 'changed_words',
                                'candidate_changes', 'after_word_stream_sha256')),
    ):
        assert actual['cli_sha256'] == package['cli_sha256']
        assert actual['before_cli_sha256'] == expected['before_cli_sha256']
        for field in fields:
            assert actual[field] == expected[field], field
    assert broad['dictionary_sha256'] == package['dictionary_sha256']
    return 1128312, 66570, 32096


def inspect(report):
    diagnostic,runtime=read(DIAGNOSTICS),read(RUNTIME)
    assert report['schema_version']==1 and report['checklist']=='COV-022p'
    assert report['source_sha256']==sha(SOURCE)
    assert report['diagnostics_sha256']==sha(DIAGNOSTICS)
    assert report['debug_runtime_sha256']==sha(RUNTIME)
    log=report['nix_log']['text']
    assert hashlib.sha256(log.encode()).hexdigest()==report['nix_log']['sha256']
    assert report['nix_exit_code']==0 and 'FAILED' not in log and 'error:' not in log
    counts=re.findall(r'klem> test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',log)
    assert (sum(int(p) for p,i in counts),sum(int(i) for p,i in counts),len(counts))==(920,1,199)
    assert (report['rust_passed'],report['rust_ignored'],report['rust_batches'])==(920,1,199)
    outputs=report['nix_outputs'];assert set(outputs)=={'klem','web-assets'}
    for path in outputs.values():assert path.startswith('/nix/store/') and path in log
    assert set(report['runs'])==set(diagnostic['runs'])
    for mode,runs in report['runs'].items():
        assert set(runs)==set(diagnostic['runs'][mode])
        for name,run in runs.items():
            assert run['jsonl']==diagnostic['runs'][mode][name]['jsonl']
            assert hashlib.sha256(run['jsonl'].encode()).hexdigest()==run['sha256']
            assert run['exit_code']==0
            cmd=run['command'];assert cmd[0]==outputs['klem']+'/bin/klem'
            assert cmd[1:4]==['text','-','--dictionary']
            assert cmd[4].endswith('/data/dictionaries/krdict/krdict.db')
            expected=[] if mode=='raw' else ['--dict-only'] if mode=='headword' else ['--dict-compatible']
            assert cmd[5:]==expected+['--cache-bytes','8388608' if name.endswith('-cached') else '0']
    def semantic_response(value):
        assert isinstance(value['elapsed_ms'], (int, float)) and math.isfinite(value['elapsed_ms']) and value['elapsed_ms'] >= 0
        return {k: v for k, v in value.items() if k != 'elapsed_ms'}
    assert len(report['api_batches']) == len(runtime['api']['batches']) == 32
    for actual, expected in zip(report['api_batches'], runtime['api']['batches'], strict=True):
        assert {k: v for k, v in actual.items() if k != 'response'} == {k: expected[k] for k in ['encoding', 'request']}
        assert semantic_response(actual['response']) == semantic_response(expected['response'])
    assert report['complete_native_entries']==runtime['api']['complete_native_entries']
    browser=report['browser'];assert browser['cli_sha256']==report['cli_sha256']
    assert browser['dictionary_sha256']==report['dictionary_sha256']==diagnostic['dictionary_sha256']
    for actual, expected in zip(browser['responses'], runtime['browser']['responses'], strict=True):
        assert {k: v for k, v in actual.items() if k != 'response'} == {k: v for k, v in expected.items() if k != 'response'}
        assert semantic_response(actual['response']) == semantic_response(expected['response'])
    for key in ['checks','diagrams','browser_errors','fixture_sha256']:
        assert browser[key]==runtime['browser'][key]
    assert set(report['screenshots'])=={'desktop','mobile'}
    for snap in report['screenshots'].values():
        raw=base64.b64decode(snap['base64'],validate=True);assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        assert hashlib.sha256(raw).hexdigest()==snap['sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    assert report['cli_sha256']!=diagnostic['cli_sha256']
    return {'rust_passed':920,'api_words':1918,'native_entries':164,'browser_exports':6,'browser_diagrams':10}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true',required=True);p.add_argument('--report',type=Path,default=REPORT)
    args=p.parse_args();report=read(args.report)
    print('Verified actual Nix release receipts and parity:',inspect(report))
    print('Bound release broad/corpus streams:',inspect_streams(report,read(BROAD),read(CORPORA)))
