"""Capture all conditional owner-mode additions against the actual previous CLI."""
import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from ostensible_reason_audit import ROOT, matches, read, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-cli',type=Path,required=True)
    parser.add_argument('--cli',type=Path,required=True)
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    fixture=ROOT/'tests/fixtures/ostensible-reason-mode-scope.json'
    matrix=read(fixture);assert len(matrix['cases'])==12
    paths=[args.before_cli,args.cli,args.dictionary,fixture,Path(__file__)]
    frozen={str(p):sha(p.read_bytes()) for p in paths}
    runs=[];observations=[];owners=set()
    for encoding in ['NFC','NFD']:
        text=unicodedata.normalize(encoding,' '.join(c['surface'] for c in matrix['cases']))
        for mode,flags in [('raw',[]),('headword',['--dict-only']),('compatible',['--dict-compatible'])]:
            commands=[[str(cli),'text','-','--dictionary',str(args.dictionary),*flags] for cli in [args.before_cli,args.cli]]
            outputs=[subprocess.run(command,cwd=ROOT,input=text.encode(),capture_output=True,check=True).stdout for command in commands]
            before,after=[list(map(json.loads,raw.splitlines())) for raw in outputs]
            assert len(before)==len(after)==23
            cursor=0
            for index,(old,new) in enumerate(zip(before,after,strict=True)):
                assert new['span']['start']==cursor
                assert text.encode()[cursor:new['span']['end']].decode()==new['surface'];cursor=new['span']['end']
                assert {k:v for k,v in old.items() if k not in ['analysis','dictionary']}=={k:v for k,v in new.items() if k not in ['analysis','dictionary']}
                if old.get('analysis') is None:assert old==new;continue
                old_paths,new_paths=old['analysis']['analyses'],new['analysis']['analyses']
                assert [a for a in new_paths if a in old_paths]==old_paths
                assert old['dictionary']['source']==new['dictionary']['source'] and old['dictionary']['fingerprint']==new['dictionary']['fingerprint']
                for analysis,assessment in zip(old_paths,old['dictionary']['readings'],strict=True):
                    assert new['dictionary']['readings'][new_paths.index(analysis)]==assessment
                assert all(match in new['dictionary']['lemmas'] for match in old['dictionary']['lemmas'])
                case=next(c for c in matrix['cases'] if c['surface']==new['analysis']['normalized'])
                for number,analysis in enumerate(new_paths):
                    if analysis in old_paths:continue
                    assert 'ending.ostensible_reason' in analysis['rules']
                    assessment=new['dictionary']['readings'][number]
                    owners.update(e['id'] for slot in assessment['lemmas'] for e in slot['entries'])
                    identity=sha(json.dumps([case['id'],encoding,mode,index,analysis],ensure_ascii=False,sort_keys=True).encode())[:24]
                    observations.append({'id':'ostensible-reason-mode-addition-'+identity,'case':case['id'],'encoding':encoding,'mode':mode,
                                         'frame_index':index,'surface':new['surface'],'span':new['span'],'analysis':analysis,'assessment':assessment,
                                         'matches_conditional_target':matches(analysis,case['expected']),
                                         'conditional_assertion_refs':[{'case':case['id'],'judgment':case['judgment_id']}],
                                         'structural_verdict':'unjudged','contextual_verdict':'unjudged','independent_review':'pending'})
            assert cursor==len(text.encode())
            runs.append({'encoding':encoding,'mode':mode,'input':text,'input_sha256':sha(text.encode()),'commands':commands,'exit_codes':[0,0],
                         'records':23,'before_jsonl':outputs[0].decode(),'before_sha256':sha(outputs[0]),
                         'after_jsonl':outputs[1].decode(),'after_sha256':sha(outputs[1])})
            print(encoding,mode,'all23 frames preserved;',len(observations),'new observations so far',flush=True)
    assert all(sha(Path(p).read_bytes())==h for p,h in frozen.items())
    report={'schema_version':1,'state':'passed','exit_code':0,'runs':runs,'individual_additions':observations,'matched_native_owner_ids':sorted(owners),
            'before_cli':str(args.before_cli),'before_cli_sha256':frozen[str(args.before_cli)],'cli':str(args.cli),'cli_sha256':frozen[str(args.cli)],
            'frozen_inputs':frozen,'inputs_unchanged':True,'producer':{'text':Path(__file__).read_text(),'sha256':frozen[str(Path(__file__))]},
            'scope':'All six actual before/after streams for twelve individually identified Native owner/mode cases. Every old candidate/order/assessment and flat entry survives. Every new path is individually unjudged; matching a conditional assertion tests presence/Native status, not structural precision or contextual suitability.',
            'contextual_verdict':'unjudged','independent_review':'pending'}
    args.output.write_bytes(gzip.compress((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
    print('Tracked',len(observations),'new unjudged paths;',len(owners),'matched Native owners.',flush=True)

if __name__=='__main__':main()
