"""Prove a new command ending against its exact retained adnominal parent."""
import copy


def parent_for(path, before):
    assert path['rules'].count('ending.friendly_command.n') == 1
    assert path['lemmas'][-1]['kind'] in {'predicate', 'auxiliary'}
    assert path['lemmas'][-1]['text'].endswith('오다')
    parent = copy.deepcopy(path)
    parent['rules'].remove('ending.friendly_command.n')
    ending = next(m for m in reversed(parent['morphemes']) if m['kind'] == 'ending')
    assert ending['form'] == 'ㄴ'
    ending['form'] = '은'
    assert parent in before, path
    return parent
