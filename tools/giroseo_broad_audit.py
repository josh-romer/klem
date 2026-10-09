"""Bind all unchanged observed broad streams without treating them as coverage gold."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def inspect(report,prior,sources):
 assert report['state']=='draft-complete-broad-preservation-passed' and report['inputs_unchanged'] and report['full_coverage_complete'] is False,'terminal original broad replay'
 assert sha(report['producer']['text'].encode())==report['producer']['sha256'],'actual broad producer'
 assert len(report['comparisons'])==len(prior['comparisons'])==8,'complete original workloads'
 for run,previous in zip(report['comparisons'],prior['comparisons'],strict=True):
  assert all(run[k]==previous[k] for k in ['source','source_sha256','mode','records']),'complete original input'
  assert run['exit_codes']==[0,0] and run['original_bytes_conserved'],'actual complete stream execution'
  assert run['before_jsonl_sha256']==run['after_jsonl_sha256']==previous['after_jsonl_sha256'],'complete unchanged stream fingerprint'
  assert not run['changed_frames'],'no suppressed changed frames'
  text=sources['sources'][run['source']]['text'];assert sha(text.encode())==run['source_sha256'],'complete original source bytes'
  mode=run['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
  assert len(run['commands'])==2
  for c in run['commands']:assert c[1]=='text' and c[3]=='--dictionary' and c[5:]==flags+(['--suggest-spacing'] if 'spacing' in mode else []),'actual filter and spacing flags'
 assert sum(v['records'] for v in report['comparisons'])==1128312,'all original broad frames'
 assert report['individual_additions']==report['individual_spacing_additions']==[] and report['complete_native_entries']==report['independent_spacing_replay']=={},'complete zero-change accounting'
 return {'frames':1128312,'changed_paths':0,'changed_spacing':0,'contextual_and_independent_review':'pending'}
def inputs():return [read(ROOT/'docs'/n) for n in ['giroseo-broad.json.gz','reported-experience-broad.json.gz','reported-deoni-broad-inputs.json.gz']]
if __name__=='__main__':print(inspect(*inputs()))
