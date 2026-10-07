"""Invert only the new sourced ending into its existing 으리라 companion."""
import copy


def inverse(word, analysis):
    rules = [r for r in analysis['rules'] if r in {
        'ending.degree_rimankeum', 'ending.counterfactual_ryeon'}]
    assert len(rules) == 1
    marker = rules[0]
    if marker == 'ending.degree_rimankeum':
        assert '만큼' in word
        companion = '라'.join(word.rsplit('만큼', 1))
        forms = {'으리만큼'}
        sources = ['krdict:87692', 'krdict:86608']
    else:
        suffix = '련마는' if '련마는' in word else '련만'
        assert suffix in word
        companion = '리라'.join(word.rsplit(suffix, 1))
        forms = {'으련마는'} if suffix == '련마는' else {'으련만'}
        sources = ['krdict:86545', 'krdict:86602'] if suffix == '련마는' else ['krdict:86546', 'krdict:86603']
    parent = copy.deepcopy(analysis)
    parent['rules'].remove(marker)
    endings = [m for m in parent['morphemes'] if m['kind'] == 'ending' and m['form'] in forms]
    assert len(endings) == 1
    endings[0]['form'] = '으리라'
    return companion, parent, sources
