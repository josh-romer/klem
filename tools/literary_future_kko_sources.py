"""Reconstruct every tested literary-future-kko package source without relying on current code."""
import argparse
import gzip
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from literary_question_go_sources import package_source_texts as previous_texts
from reported_dana_sources import nar_contents
from reported_deoni_complete_sources import source_store_path

ROOT=Path(__file__).resolve().parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()

def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

@lru_cache(maxsize=1)
def baseline_texts():
    return previous_texts(read(ROOT/'docs/literary-question-go-package-nix.json'))

def verify(proof,receipt,baseline):
    assert proof['state']==receipt['state']=='passed'
    assert receipt['exit_code']==0
    assert receipt['snapshot_unchanged'] is True
    assert proof['current_inputs_unchanged'] is True
    assert sha(proof['producer']['text'].encode())==proof['producer']['sha256']
    assert proof['snapshot_files']==receipt['snapshot']['files']
    assert len(proof['snapshot_files'])==947 and len(baseline)==939
    current=dict(baseline)
    assert len(proof['updates'])==15
    for name,update in proof['updates'].items():
        assert update['before_sha256']==(sha(baseline[name].encode()) if name in baseline else None)
        assert sha(update['after_text'].encode())==update['after_sha256']
        assert name not in baseline or update['after_sha256']!=update['before_sha256']
        current[name]=update['after_text']
    assert set(current)==set(proof['snapshot_files'])
    for name,text in current.items():
        record=proof['snapshot_files'][name]
        assert sha(text.encode())==record['sha256'] and len(text.encode())==record['bytes'],name
    assert set(proof['profiles'])=={'klem','web-assets','corpus-adapter'}
    mapped=set()
    for label,profile in proof['profiles'].items():
        expected_source=receipt['source_profiles'][label]
        assert profile['source']==expected_source
        outputs=receipt['outputs']
        assert profile['package'] in outputs
        expected_suffix={'klem':'-klem-0.1.0','web-assets':'-klem-web-assets-0.1.0','corpus-adapter':'-klem-corpus-adapter-0.1.0'}[label]
        assert profile['package'].endswith(expected_suffix)
        assert profile['actual_dump_verified'] is True
        raw=profile['derivation_json_text'];assert sha(raw.encode())==profile['derivation_json_sha256']
        drv=json.loads(raw);assert set(drv)=={profile['derivation']}
        assert drv[profile['derivation']]['env']['src']==profile['source']
        assert drv[profile['derivation']]['outputs']['out']['path']==profile['package']
        files=profile['files'];assert len(files)==(18 if label=='web-assets' else 930)
        texts={}
        for name,record in files.items():
            path='web/'+name if label=='web-assets' else name
            assert record['snapshot_path']==path and isinstance(record['executable'],bool)
            assert {k:v for k,v in record.items() if k not in ['snapshot_path','executable']}==proof['snapshot_files'][path]
            texts[name]=current[path];mapped.add(path)
        digest,count=nar_contents(files,profile['directories'],texts)
        assert (digest,count)==(profile['nar_sha256'],profile['nar_bytes'])
        assert source_store_path(digest)==profile['source']
        assert profile['nar_command']==['nix-store','--dump',profile['source']]
    assert mapped==set(current)
    main,adapter=proof['profiles']['klem'],proof['profiles']['corpus-adapter']
    assert main['source']==adapter['source'] and main['files']==adapter['files']
    assert main['nar_sha256']==adapter['nar_sha256'] and main['nar_bytes']==adapter['nar_bytes']
    return current

def inspect(proof_path):
    proof=read(proof_path)
    assert proof['receipt_sha256']==sha((ROOT/'docs/literary-future-kko-package-nix.json').read_bytes())
    assert proof['baseline']['proof']=='docs/literary-question-go-historical-sources.json.gz'
    assert proof['baseline']['proof_sha256']==sha((ROOT/proof['baseline']['proof']).read_bytes())
    return verify(proof,read(ROOT/'docs/literary-future-kko-package-nix.json'),baseline_texts())

@lru_cache(maxsize=1)
def package_source_texts_cached():
    return inspect(ROOT/'docs/literary-future-kko-historical-sources.json.gz')

def package_source_texts(package):
    assert package==read(ROOT/'docs/literary-future-kko-package-nix.json')
    return package_source_texts_cached()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--proof',type=Path,required=True);args=parser.parse_args()
    print('Verified all historical literary-future-kko source inputs:',len(inspect(args.proof)))
