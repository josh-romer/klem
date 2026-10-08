"""Bind actual release tests, packages, original-source runtime and launcher assets."""
import gzip
import re
from pathlib import Path

from literary_future_kko_runtime import ROOT, read, sha, inspect as verify_cli
from literary_future_kko_adapter_audit import inspect as verify_adapter
from literary_future_kko_browser_audit import inspect as verify_browser
from literary_future_kko_sources import inspect as verify_sources


def inspect(package, cli, adapter, runtime, browser):
    assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
    assert sha(package['producer']['text'].encode())==package['producer']['sha256']
    log = gzip.decompress((ROOT/'docs/literary-future-kko-package-nix.log.gz').read_bytes())
    assert sha(log)==package['log_sha256']
    rows = re.findall(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;',log.decode())
    tests = {k:sum(int(row[i]) for row in rows) for i,k in enumerate(['passed','failed','ignored'])}
    tests['batches'] = len(rows)
    assert tests=={'passed':1055,'failed':0,'ignored':1,'batches':224}
    rust = read(ROOT/'docs/literary-future-kko-main-full-rust.json.gz')
    assert rust['state']=='passed' and rust['inputs_unchanged'] is True and rust['tests']==tests
    assert package['snapshot']['files']==rust['snapshot_files']==runtime['source_snapshot']
    assert len(package['snapshot']['files'])==947
    historical = verify_sources(ROOT/'docs/literary-future-kko-historical-sources.json.gz')
    assert set(historical)==set(package['snapshot']['files'])
    assert len(set(package['outputs']))==len(package['outputs'])==3
    main = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    adapter_path = next(p for p in package['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))
    assets = next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0'))+'/share/klem-web'
    assert cli['cli']==main+'/bin/klem'
    assert cli['producer']['text']==(ROOT/'tools/literary_future_kko_replay.py').read_text()
    assert adapter['adapter']==adapter_path+'/bin/klem-corpus-adapter'
    cli_summary = verify_cli(cli)
    adapter_summary = verify_adapter(adapter,read(ROOT/'docs/literary-future-kko-prototype-corpora.json.gz'))
    browser_summary = verify_browser(runtime,browser,
        read(ROOT/'docs/literary-future-kko-spacing-owner-preparation.json.gz'),
        browser_path=ROOT/'docs/literary-future-kko-packaged-browser.json.gz')
    assert runtime['producer']['text']==(ROOT/'tools/capture_literary_future_kko_web.py').read_text()
    assert runtime['cli']==cli['cli'] and runtime['cli_sha256']==cli['cli_sha256']
    assert runtime['server']==main+'/bin/klem-web' and runtime['assets']==assets
    assert runtime['package_sha256']==sha((ROOT/'docs/literary-future-kko-package-nix.json').read_bytes())
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
    assert browser['producer_sha256']==sha((ROOT/'web/tests/literary-future-kko.mjs').read_bytes())
    assert runtime['browser_command']==['node',node]
    return {'release_tests':tests,'compile_and_frontend_inputs':947,'cli':cli_summary,
            'adapter':adapter_summary,'browser':browser_summary,'launcher_assets':2,
            'owned_server_stopped':True,'precision_context_and_independent_review':'pending'}


def inputs():
    return [read(ROOT/'docs'/name) for name in [
        'literary-future-kko-package-nix.json','literary-future-kko-packaged-cli-replay.json',
        'literary-future-kko-packaged-adapter.json.gz','literary-future-kko-packaged-browser-runtime.json',
        'literary-future-kko-packaged-browser.json.gz']]


if __name__=='__main__':
    print(inspect(*inputs()))
