"""Exercise the actual Nix web launcher, packaged assets, and browser UI."""
import argparse
import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from ostensible_reason_audit import ROOT, read, sha
from ostensible_reason_runtime import without_elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    output = Path(str(args.prefix)+'-web-launcher.json')
    assert not output.exists()
    package_path = ROOT/'docs/literary-question-go-package-nix.json'
    package = read(package_path)
    assert package['state']=='passed' and package['snapshot_unchanged'] is True
    main_output = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    cli, server = Path(main_output+'/bin/klem'), Path(main_output+'/bin/klem-web')
    assets = Path(next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0')))/'share/klem-web'
    dictionary = ROOT/'data/dictionaries/krdict/krdict.db'
    browser_producer = ROOT/'web/tests/literary-question-go.mjs'
    producer_path = Path(__file__)
    frozen = {str(p):sha(p.read_bytes()) for p in
              [package_path,args.launcher,cli,server,dictionary,browser_producer,producer_path]}
    body = args.launcher.read_text()
    assert [line for line in body.splitlines() if line.startswith('exec ')]==[
        f'exec {server} --assets {assets} "$@"']
    help_result = subprocess.run([str(args.launcher),'--help'],cwd=ROOT,capture_output=True,check=True)
    assert b'Usage: klem-web' in help_result.stdout
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    command = [str(args.launcher),'--port',str(port),'--dictionary',str(dictionary)]
    receipt = {'schema_version':1,'state':'running','package_sha256':frozen[str(package_path)],
               'launcher':str(args.launcher),'launcher_text':body,'launcher_sha256':frozen[str(args.launcher)],
               'cli':str(cli),'cli_sha256':frozen[str(cli)],'server':str(server),'server_sha256':frozen[str(server)],
               'assets':str(assets),'command':command,'url':url,'help_exit_code':help_result.returncode,
               'help_stdout_sha256':sha(help_result.stdout),'frozen_inputs':frozen,
               'producer':{'text':producer_path.read_text(),'sha256':frozen[str(producer_path)]},
               'scope':'Actual immutable Nix launcher, CLI, server and frontend asset outputs. Full browser suite runs against this owned server; served index/JS/CSS bytes and original-source APIs are checked independently. Unknown and contextual candidates remain unjudged.'}
    output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    server_log = Path(str(args.prefix)+'-server.log')
    try:
        with server_log.open('xb') as stream:
            job = subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            receipt['server_pid'] = job.pid
            try:
                deadline = time.monotonic()+30
                while True:
                    assert job.poll() is None, 'Owned packaged server exited during startup'
                    try:
                        with urllib.request.urlopen(url,timeout=2) as response:
                            html = response.read()
                        break
                    except (OSError,urllib.error.URLError):
                        assert time.monotonic()<deadline, 'Packaged server startup timed out'
                        time.sleep(.1)
                assert html==(assets/'index.html').read_bytes()
                receipt['index_sha256'] = sha(html)
                checks = []
                for path in re.findall(r'(?:src|href)="(/assets/[^"?#]+\.(?:js|css))"',html.decode()):
                    with urllib.request.urlopen(url+path,timeout=20) as response:
                        raw = response.read()
                    assert raw==(assets/path.lstrip('/')).read_bytes()
                    checks.append({'path':path,'bytes':len(raw),'sha256':sha(raw)})
                assert len(checks)==2
                receipt['asset_checks'] = checks
                env = dict(os.environ,KLEM_ROOT=str(ROOT),KLEM_WEB_URL=url,KLEM_BIN=str(cli),
                           KLEM_FRONTEND=package['source_profiles']['web-assets'],KLEM_PROTOTYPE=str(ROOT),KLEM_CAPTURE_PREFIX=str(args.prefix),CHROMIUM_PATH='/nix/store/g0yvxs8p2ijrvmxpd5mim1ni0fyk9bnh-chromium-154.0.8037.57/bin/chromium')
                browser_command = ['node',str(browser_producer)]
                subprocess.run(browser_command,cwd=ROOT,env=env,check=True)
                browser_path = Path(str(args.prefix)+'-browser.json')
                browser = read(browser_path)
                receipt['browser_command'] = browser_command
                receipt['browser_sha256'] = sha(browser_path.read_bytes())
                responses = []
                for baseline in browser['responses']:
                    request = urllib.request.Request(url+'/api/analyze',data=json.dumps(baseline['request']).encode(),
                                                     headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=20) as response:
                        actual = json.load(response)
                    assert without_elapsed(actual)==without_elapsed(baseline['after'])
                    responses.append({'encoding':baseline['encoding'],'request':baseline['request'],'after':actual})
                receipt['responses'] = responses
            finally:
                if job.poll() is None:
                    job.send_signal(signal.SIGINT)
                receipt['server_exit_code'] = job.wait(timeout=20)
                receipt['server_stopped'] = True
        assert receipt['server_exit_code'] in [-signal.SIGINT,130]
        assert all(sha(Path(path).read_bytes())==digest for path,digest in frozen.items())
        receipt.update(state='passed',exit_code=0,inputs_unchanged=True)
    except Exception as error:
        receipt.update(state='failed',exit_code=1,error=repr(error))
        raise
    finally:
        receipt['server_log_sha256'] = sha(server_log.read_bytes())
        output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print('Actual packaged launcher/browser and static asset/API checks passed; owned server stopped.',flush=True)


if __name__=='__main__':
    main()
