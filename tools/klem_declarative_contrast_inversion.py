"""An exact prior split final-ending/particle reading must license each addition."""
import copy
FORMS={'다만':('다','만',['krdict:80322']),'다마는':('다','마는',['krdict:80321']),'는다만':('는다','만',['krdict:80324','krdict:80326']),'는다마는':('는다','마는',['krdict:80323','krdict:80325'])}
def split_parent(candidate):
 assert 'ending.declarative_contrast' in candidate['rules']
 inverse=copy.deepcopy(candidate); positions=[]; morphemes=[]; sources=[]
 for i,m in enumerate(inverse['morphemes']):
  if m['kind']=='ending' and m['form'] in FORMS:
   ending,particle,entries=FORMS[m['form']];positions.append(i);sources.extend(entries)
   morphemes.extend([dict(m,form=ending),{'form':particle,'kind':'particle'}])
  else:morphemes.append(m)
 assert positions
 inverse['morphemes']=morphemes
 inverse['rules']=sorted(set(r for r in inverse['rules'] if r!='ending.declarative_contrast')|{'particle','particle.concessive'})
 for p in inverse.get('spelling_paths',[]):
  for recovery in p:recovery['morpheme_index']+=sum(i<recovery['morpheme_index'] for i in positions)
 return inverse,sorted(set(sources))
