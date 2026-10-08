"""Exercise the actual Nix web launcher, packaged assets and complete browser suite."""
import argparse
import datetime
import os
import re
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from literary_question_geona_runtime import ROOT, read, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    output = Path(str(args.prefix)+'-runtime.json')
    assert not output.exists()
    package = read(args.package)
    assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
    main_output = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    cli, server = Path(main_output+'/bin/klem'), Path(main_output+'/bin/klem-web')
    assets = Path(next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0')))/'share/klem-web'
    database = ROOT/'data/dictionaries/krdict/krdict.db'
    browser = ROOT/'web/tests/literary-question-geona.mjs'
    integration = ROOT/'docs/literary-question-geona-main-binaries.json.gz'
    snapshot = read(integration)['snapshot_files']
    assert snapshot==package['snapshot']['files'] and len(snapshot)==957
    assert all(sha((ROOT/name).read_bytes())==row['sha256'] for name,row in snapshot.items())
    frozen = {str(p):sha(p.read_bytes()) for p in
              [args.package,args.launcher,cli,server,database,browser,integration,Path(__file__)]}
    asset_snapshot = {str(p.relative_to(assets)):sha(p.read_bytes()) for p in assets.rglob('*') if p.is_file()}
    body = args.launcher.read_text()
    assert [line for line in body.splitlines() if line.startswith('exec ')]==[
        f'exec {server} --assets {assets} "$@"']
    help_result = subprocess.run([str(args.launcher),'--help'],cwd=ROOT,capture_output=True,check=True)
    assert b'Usage: klem-web' in help_result.stdout
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    command = [str(args.launcher),'--port',str(port),'--dictionary',str(database)]
    report = {'schema_version':1,'state':'running',
              'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'package_sha256':frozen[str(args.package)],'launcher':str(args.launcher),
              'launcher_text':body,'launcher_sha256':frozen[str(args.launcher)],
              'cli':str(cli),'cli_sha256':frozen[str(cli)],'server':str(server),
              'server_sha256':frozen[str(server)],'assets':str(assets),
              'command':command,'url':url,'help_exit_code':help_result.returncode,
              'help_stdout_sha256':sha(help_result.stdout),'frozen_inputs':frozen,
              'snapshot_files':snapshot,'asset_snapshot':asset_snapshot,
              'producer':{'text':Path(__file__).read_text(),'sha256':frozen[str(Path(__file__))]},
              'scope':'Actual immutable current-flake web launcher, CLI/server and SolidJS assets. '
                      'Complete source APIs, finite original diagrams and filter checks, Native endpoints '
                      'and source panes run in Chromium; served asset bytes are compared independently. '
                      'Unknown, contextual and sense-level candidates remain unjudged.'}
    import json
    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    save()
    job = None
    server_log = Path(str(args.prefix)+'-server.log')
    try:
        with server_log.open('xb') as stream:
            job = subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            report['server_pid'] = job.pid
            deadline = time.monotonic()+30
            while True:
                assert job.poll() is None, 'Owned packaged server exited during startup'
                try:
                    with urllib.request.urlopen(url,timeout=2) as response:
                        html = response.read()
                    break
                except OSError:
                    assert time.monotonic()<deadline, 'Packaged server startup timed out'
                    time.sleep(.1)
            assert html==(assets/'index.html').read_bytes()
            report['index_sha256'] = sha(html)
            checks = []
            for path in re.findall(r'(?:src|href)="(/assets/[^"?#]+\.(?:js|css))"',html.decode()):
                with urllib.request.urlopen(url+path,timeout=20) as response:
                    raw = response.read()
                assert raw==(assets/path.lstrip('/')).read_bytes()
                checks.append({'path':path,'bytes':len(raw),'sha256':sha(raw)})
            assert len(checks)==2
            report['asset_checks'] = checks
            env = dict(os.environ,KLEM_ROOT=str(ROOT),KLEM_WEB_URL=url,KLEM_BIN=str(cli),
                       KLEM_CAPTURE_PREFIX=str(args.prefix),
                       CHROMIUM_PATH='/nix/store/g0yvxs8p2ijrvmxpd5mim1ni0fyk9bnh-chromium-154.0.8037.57/bin/chromium')
            report['browser_command'] = ['node',str(browser)]
            subprocess.run(report['browser_command'],cwd=ROOT,env=env,check=True)
            report['browser_sha256'] = sha(Path(str(args.prefix)+'-browser.json').read_bytes())
            report.update(state='passed',exit_code=0)
    except BaseException as error:
        report.update(state='failed',exit_code=1,error=repr(error))
        raise
    finally:
        if job is not None:
            if job.poll() is None:
                job.send_signal(signal.SIGINT)
            report['server_exit_code'] = job.wait(timeout=20)
            report['server_stopped'] = True
        report['inputs_unchanged'] = (
            all(sha(Path(p).read_bytes())==digest for p,digest in frozen.items())
            and all(sha((ROOT/name).read_bytes())==row['sha256'] for name,row in snapshot.items())
            and all(sha((assets/name).read_bytes())==digest for name,digest in asset_snapshot.items()))
        report['server_log_sha256'] = sha(server_log.read_bytes())
        report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    assert report['inputs_unchanged'] and report['server_stopped'] and report['server_exit_code'] in [-2,130]
    print('Actual packaged launcher, complete browser and served asset bytes pass; owned server stopped.',flush=True)


if __name__=='__main__':
    main()
