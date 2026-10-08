"""Bind actual release tests, packages, original-source runtime and launcher assets."""
import gzip
import re
from pathlib import Path

from literary_question_geona_runtime import ROOT, read, sha, inspect as verify_cli
from literary_question_geona_adapter_audit import inspect as verify_adapter
from literary_question_geona_browser_audit import inspect as verify_browser
from literary_question_geona_sources import inspect as verify_sources


def inspect(package, cli, adapter, runtime, browser):
    assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
    assert sha(package['producer']['text'].encode())==package['producer']['sha256']
    log = gzip.decompress((ROOT/'docs/literary-question-geona-package-nix.log.gz').read_bytes())
    assert sha(log)==package['log_sha256']
    rows = re.findall(r'^klem> test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',log.decode(), re.MULTILINE)
    tests = {k:sum(int(row[i]) for row in rows) for i,k in enumerate(['passed','failed','ignored'])}
    tests['batches'] = len(rows)
    assert tests=={'passed':1059,'failed':0,'ignored':1,'batches':227}
    rust = read(ROOT/'docs/literary-question-geona-main-full-rust.json.gz')
    assert rust['state']=='passed' and rust['exit_code']==0 and rust['inputs_unchanged'] is True
    rust_log=gzip.decompress((ROOT/'docs/literary-question-geona-main-full-rust.log.gz').read_bytes())
    assert sha(rust_log)==rust['log_sha256']
    rust_rows=re.findall(r'^test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',rust_log.decode(),re.MULTILINE)
    assert {**{k:sum(int(row[i]) for row in rust_rows) for i,k in enumerate(['passed','failed','ignored'])},'batches':len(rust_rows)}==tests
    assert package['snapshot']['files']==rust['snapshot_files']==runtime['snapshot_files']
    assert len(package['snapshot']['files'])==957
    historical = verify_sources(ROOT/'docs/literary-question-geona-historical-sources.json.gz')
    assert set(historical)==set(package['snapshot']['files'])
    assert len(set(package['outputs']))==len(package['outputs'])==3
    main = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    adapter_path = next(p for p in package['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))
    assets = next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0'))+'/share/klem-web'
    assert cli['cli']==main+'/bin/klem'
    assert cli['producer']['text']==(ROOT/'tools/literary_question_geona_replay.py').read_text()
    assert adapter['adapter']==adapter_path+'/bin/klem-corpus-adapter'
    for report in [cli,adapter,runtime]:
        assert report['package_sha256']==sha((ROOT/'docs/literary-question-geona-package-nix.json').read_bytes())
    cli_summary = verify_cli(cli)
    adapter_summary = verify_adapter(adapter,read(ROOT/'docs/literary-question-geona-prototype-corpora.json.gz'))
    browser_summary = verify_browser(runtime,browser,
        read(ROOT/'docs/literary-question-geona-complete-owner-preparation.json.gz'),
        browser_path=ROOT/'docs/literary-question-geona-packaged-browser.json.gz')
    assert runtime['producer']['text']==(ROOT/'tools/capture_literary_question_geona_web.py').read_text()
    assert runtime['cli']==cli['cli'] and runtime['cli_sha256']==cli['cli_sha256']
    assert runtime['server']==main+'/bin/klem-web' and runtime['assets']==assets
    assert runtime['package_sha256']==sha((ROOT/'docs/literary-question-geona-package-nix.json').read_bytes())
    assert runtime['frozen_inputs'][runtime['server']]==runtime['server_sha256']
    assert re.fullmatch(r'/nix/store/[a-z0-9]{32}-klem-web/bin/klem-web',runtime['launcher'])
    assert runtime['help_exit_code']==0
    assert sha(runtime['launcher_text'].encode())==runtime['launcher_sha256']
    assert runtime['frozen_inputs'][runtime['launcher']]==runtime['launcher_sha256']
    assert [line for line in runtime['launcher_text'].splitlines() if line.startswith('exec ')]==[
        f'exec {runtime["server"]} --assets {assets} "$@"']
    assert runtime['command']==[runtime['launcher'],'--port',runtime['url'].rsplit(':',1)[1],
                               '--dictionary',next(p for p in runtime['frozen_inputs'] if p.endswith('/krdict/krdict.db'))]
    assert runtime['index_sha256']==runtime['asset_snapshot']['index.html']
    assert len(runtime['asset_checks'])==2
    assert {Path(c['path']).suffix for c in runtime['asset_checks']}=={'.js','.css'}
    for row in runtime['asset_checks']:
        assert row['bytes']>0 and row['sha256']==runtime['asset_snapshot'][row['path'].lstrip('/')]
    node = next(p for p in runtime['frozen_inputs'] if p.endswith('.mjs'))
    assert browser['producer_sha256']==sha((ROOT/'web/tests/literary-question-geona.mjs').read_bytes())
    assert runtime['browser_command']==['node',node]
    return {'release_tests':tests,'compile_and_frontend_inputs':957,'cli':cli_summary,
            'adapter':adapter_summary,'browser':browser_summary,'launcher_assets':2,
            'owned_server_stopped':True,'precision_context_and_independent_review':'pending'}


def inputs():
    return [read(ROOT/'docs'/name) for name in [
        'literary-question-geona-package-nix.json','literary-question-geona-packaged-cli-replay.json',
        'literary-question-geona-packaged-adapter.json.gz','literary-question-geona-packaged-browser-runtime.json',
        'literary-question-geona-packaged-browser.json.gz']]


if __name__=='__main__':
    print(inspect(*inputs()))
