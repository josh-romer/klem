"""Recognize only the complete proven Sena child of the preserved Gena revision.

This guard validates captured source/build evidence. It explicitly uses captured
binary evidence and does not claim to execute or hash host executables in Nix.
Candidate/corpus verification remains in the separate full runtime/wide audits.
"""
import gzip
import json
import re
from pathlib import Path

import friendly_command_gena_revision as parent
import friendly_hortative_sena_browser_audit as browser_audit
import friendly_hortative_sena_runtime_audit as runtime

ROOT = runtime.ROOT
sha = runtime.sha
RUST_SHA = 'e0abbb317ca3adc88c72fc51f4a9c400e0d1b4aa841ab72103fab7cac963f0d2'
SELECTED_SHA = '30b7ef2ddade9bbf303cd305272a785800ad3990a2dd95beca7a2b0dd2b5c069'
WIDE_SHA = 'bb4cb1f2cfa778ba8eab65d02d398e26c89809b578e3c3ff268d74be9a5e4621'
WIDE_AUDIT_SHA = '6be97cef445f76c7d9e4a7174f41c987e974ac77057e5408cc16f567ca3bf3f9'


def artifacts(manifest, digest, names):
    raw = (ROOT/'docs'/manifest).read_bytes()
    assert sha(raw)==digest, 'immutable Sena revision manifest'
    catalog=json.loads(raw)['files']; values={}; hashes={}; originals={}
    assert set(names)<=set(catalog), 'all requested original Sena artifacts'
    for name in names:
        item=catalog[name];packed=(ROOT/'docs'/item['path']).read_bytes()
        assert sha(packed)==item['archive_sha256'], 'immutable packed Sena revision artifact'
        original=gzip.decompress(packed)
        assert sha(original)==item['source_sha256'], 'immutable original Sena revision artifact'
        originals[name]=original;hashes[name]=sha(original)
        values[name]=(json.loads(gzip.decompress(original) if name.endswith('.gz') else original)
                      if name.endswith(('.json','.json.gz')) else original)
    return values,hashes,originals


def inputs():
    proof,hashes,originals=runtime.archive('friendly-hortative-sena-browser-proof-archive.json',browser_audit.MANIFEST_SHA)
    corpus,_,_=runtime.archive('friendly-hortative-sena-corpus-regression-proof-archive.json',browser_audit.CORPUS_SHA)
    bound=runtime.inputs(binary_evidence='captured')
    browser=dict(runtime=bound,proof=proof,hashes=hashes,originals=originals,
                 corpus=corpus['friendly-hortative-sena-corpus-regression-retry.json.gz'],
                 labels=json.loads((ROOT/'web/src/grammar-labels.json').read_bytes()))
    rust,rust_hashes,rust_originals=artifacts('friendly-hortative-sena-full-rust-current-proof-archive.json',RUST_SHA,[
        'friendly-hortative-sena-full-rust-serial-retry.json','friendly-hortative-sena-full-rust-serial-retry.log',
        'run_friendly_hortative_sena_full_rust_serial_retry.py','friendly-hortative-sena-full-rust.json',
        'friendly-hortative-sena-full-rust-serial.json'])
    selected,selected_hashes,selected_originals=artifacts('friendly-hortative-sena-wide-selected-source-proof-archive.json',SELECTED_SHA,[
        'friendly-hortative-sena-wide-selected-source.json','friendly-hortative-sena-wide-selected-source.log',
        'preflight_friendly_hortative_sena_wide_selected_source.py'])
    wide,wide_hashes,wide_originals=artifacts('friendly-hortative-sena-wide-proof-archive.json',WIDE_SHA,[
        'friendly-hortative-sena-wide-comparisons.json','friendly-hortative-sena-wide-comparisons.log',
        'validate_friendly_hortative_sena_wide_comparisons.py'])
    audited,audited_hashes,audited_originals=artifacts('friendly-hortative-sena-wide-audit-proof-archive.json',WIDE_AUDIT_SHA,[
        'friendly-hortative-sena-wide-audit-validation.json','friendly-hortative-sena-wide-audit-validation.log',
        'validate_friendly_hortative_sena_wide_audit.py'])
    profiles=selected['friendly-hortative-sena-wide-selected-source.json']['profiles']
    current_profiles={name:{p:sha((ROOT/('web/' if name=='web-assets' else '')/p).read_bytes()) for p in value['files']}
                      for name,value in profiles.items()}
    return dict(parent=parent.inputs(),browser=browser,rust=rust,rust_hashes=rust_hashes,rust_originals=rust_originals,
                selected=selected,selected_hashes=selected_hashes,selected_originals=selected_originals,
                wide=wide,wide_hashes=wide_hashes,wide_originals=wide_originals,
                audited=audited,audited_hashes=audited_hashes,audited_originals=audited_originals,
                current_profiles=current_profiles)


def inspect(v):
    previous=parent.inspect(v['parent'],check_current=False)
    bound=v['browser']['runtime'];runtime.inspect_binding(bound)
    assert bound['binary_evidence']['mode']=='captured' and bound['binary_evidence']['live_executable_files_verified'] is False, 'explicit captured Sena source guard scope'
    production=bound['binding']['production_inputs']
    assert previous==bound['binding']['parent_production_inputs'], 'exact verified Gena parent production'
    assert {p for p in production if production[p]!=previous[p]}==runtime.CHANGES, 'only five proven Sena production changes'
    rust=v['rust']['friendly-hortative-sena-full-rust-serial-retry.json'];runtime.terminal(rust)
    assert rust['protected_binaries_unchanged'] and rust['production_inputs']==production, 'complete passing Rust Sena production'
    assert rust['runtime_binding_sha256']==bound['hashes']['friendly-hortative-sena-complete-runtime-binding.json'], 'actual Rust executable binding'
    assert rust['rust_totals']==dict(passed=1211,failed=0,ignored=1) and rust['rust_batches']==262, 'complete1211 Rust262 targets'
    results=rust['results'];targets=rust['all_targets']
    assert len(results)==266 and len(targets)==262 and all(r['exit_code']==0 for r in results), 'every actual Rust target and final check passed'
    assert [r['target'] for r in results if r['target'] is not None]==targets, 'every metadata target tested once in order'
    metadata=rust['cargo_metadata']
    assert sha(json.dumps(metadata,ensure_ascii=False,separators=(',',':')).encode()+b'\n')==rust['cargo_metadata_sha256'], 'original cargo metadata binding'
    package=next(p for p in metadata['packages'] if p['manifest_path']=='/home/josh/projects/klem/.direnv/friendly-hortative-sena/Cargo.toml')
    assert package['targets']==targets, 'complete original Cargo metadata targets'
    assert results[0]['command']==['cargo','fmt','--all','--','--check'] and results[-3]['command']==['cargo','clippy','--locked','--offline','--all-targets','--features','web','--','-D','warnings'], 'actual formatting and warning-denied Clippy'
    assert results[-2]['command']==['python3','tools/review_inventory.py','--verify'] and results[-1]['command']==['git','diff','--check'], 'actual queue and diff checks'
    batches=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',v['rust_originals']['friendly-hortative-sena-full-rust-serial-retry.log'].decode())
    assert len(batches)==262 and all(b[0]=='ok' for b in batches) and [sum(int(b[i]) for b in batches) for i in [1,2,3]]==[1211,0,1], 'complete original Rust log totals'
    assert rust['log_sha256']==v['rust_hashes']['friendly-hortative-sena-full-rust-serial-retry.log'], 'complete original Rust log binding'
    assert rust['producer']==dict(text=v['rust_originals']['run_friendly_hortative_sena_full_rust_serial_retry.py'].decode(),sha256=v['rust_hashes']['run_friendly_hortative_sena_full_rust_serial_retry.py']), 'original actual full Rust producer'
    assert all(v['rust'][n]['state']=='failed' for n in ['friendly-hortative-sena-full-rust.json','friendly-hortative-sena-full-rust-serial.json']), 'original compilation and cleanup failures retained'
    selected=v['selected']['friendly-hortative-sena-wide-selected-source.json'];runtime.terminal(selected)
    assert selected['controls']==139 and selected['parent_binding_unchanged'] and selected['production_inputs']==production and selected['parent_production_inputs']==previous, 'actual selected139 exact production closure'
    assert all(r['exit_code']==0 for r in selected['results']) and sum(r['controls'] for r in selected['results'])==139, 'every selected139 command passed'
    assert selected['log_sha256']==v['selected_hashes']['friendly-hortative-sena-wide-selected-source.log'], 'complete original selected139 log'
    assert selected['producer']==dict(text=v['selected_originals']['preflight_friendly_hortative_sena_wide_selected_source.py'].decode(),sha256=v['selected_hashes']['preflight_friendly_hortative_sena_wide_selected_source.py']), 'original actual selected139 producer'
    profiles=selected['profiles']
    assert {name:len(value['files']) for name,value in profiles.items()}=={'klem':1158,'corpus-adapter':1158,'web-assets':18}, 'all1158/1158/18 actual compile profiles'
    assert v['current_profiles']=={name:value['files'] for name,value in profiles.items()}, 'every current compiled Rust frontend byte'
    assert rust['head']==selected['head'] and rust['index_sha256']==selected['index_sha256'] and rust['frozen_inputs']==selected['frozen_inputs'], 'same complete passing Rust and selected revision'
    for name,profile in profiles.items():
        prefix='web/' if name=='web-assets' else ''
        assert all(rust['frozen_inputs'][prefix+p]==d for p,d in profile['files'].items()), 'every passing Rust compile input'
    wide=v['wide']['friendly-hortative-sena-wide-comparisons.json'];runtime.terminal(wide)
    assert wide['external_inputs_unchanged'] and wide['protected_current_binaries_unchanged'], 'actual wide external inputs retained'
    assert all(wide['frozen_inputs'][p]==d for p,d in production.items()), 'complete wide Sena production closure'
    assert len(wide['results'])==3 and all(r['exit_code']==0 for r in wide['results']), 'actual whole cohort gold broad comparisons passed'
    assert wide['log_sha256']==v['wide_hashes']['friendly-hortative-sena-wide-comparisons.log'] and wide['producer']==dict(text=v['wide_originals']['validate_friendly_hortative_sena_wide_comparisons.py'].decode(),sha256=v['wide_hashes']['validate_friendly_hortative_sena_wide_comparisons.py']), 'original whole comparison producer and log'
    audited=v['audited']['friendly-hortative-sena-wide-audit-validation.json'];runtime.terminal(audited)
    assert audited['controls']==34 and audited['external_inputs_unchanged'] and all(r['exit_code']==0 for r in audited['results']), 'actual independent34 wide controls'
    assert all(audited['frozen_inputs'][p]==d for p,d in production.items()), 'complete independent wide source closure'
    assert audited['log_sha256']==v['audited_hashes']['friendly-hortative-sena-wide-audit-validation.log'] and audited['producer']==dict(text=v['audited_originals']['validate_friendly_hortative_sena_wide_audit.py'].decode(),sha256=v['audited_hashes']['validate_friendly_hortative_sena_wide_audit.py']), 'original wide auditor producer and log'
    browser_audit.inspect(v['browser'])
    return production


def normalized(current):
    result={}
    for name,digest in current.items():
        path=Path(name)
        if path.is_absolute():
            try: path=path.relative_to('/tmp/klem-gentle-command')
            except ValueError: return None
        name=str(path)
        if name in result: return None
        result[name]=digest
    return result


def accepts_production(current):
    relative=normalized(current)
    if relative is None: return False
    v=inputs()
    expected=v['browser']['runtime']['binding']['production_inputs']
    if relative!=expected: return False
    return relative==inspect(v)


def accepts_frontend(current,historical):
    v=inputs()
    selected={p.removeprefix('web/'):d for p,d in v['browser']['runtime']['binding']['frontend_inputs'].items()}
    if current!=selected: return False
    production=inspect(v)
    label='src/grammar-labels.json';p=v['parent']['parent']
    labels={v['parent']['binding']['production_inputs']['web/'+label],
            p['binding']['production_inputs']['web/'+label],
            p['binding']['parent_production_inputs']['/tmp/klem-gentle-command/web/'+label]}
    assert selected[label]==production['web/'+label], 'Sena frontend belongs to exact named production'
    if set(historical)!=set(selected) or len(historical)!=18 or historical[label] not in labels: return False
    if any(d!=selected[n] for n,d in historical.items() if n!=label): return False
    return current==selected


if __name__=='__main__':
    values=inputs();production=inspect(values)
    print(dict(production_inputs=len(production),compile_inputs={n:len(r) for n,r in values['current_profiles'].items()},
               binary_evidence=values['browser']['runtime']['binary_evidence'],full_coverage_complete=False))
