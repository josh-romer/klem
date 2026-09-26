# Annotated corpus excerpts

`krdict.json` is separately licensed **CC BY-SA 2.0 KR** dictionary text from the
National Institute of Korean Language (국립국어원), Korean Basic Dictionary
(한국어기초사전). It is an adapted slice of the September 2026 official LMF JSON
export, `1_5000_20260919.json`, whose SHA-256 is
`0c03a895b00f9182d413381b3da727e5cc855a0c484716d7e9f827f2e9188d7c`.
It includes 13 word/idiom entries associated with parent IDs 27733, 72337, 78406,
65200, 27500 and 28764. Changes: retained only the first sense and its English
equivalent for each entry, removed global export metadata, and reformatted JSON.
Other entry fields retain the source's singleton/array representation. Audio
URLs are references only; no audio files are distributed or imported.
See [source downloads](https://krdict.korean.go.kr/download/downloadPopup),
[copyright policy](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo),
and [license terms](https://creativecommons.org/licenses/by-sa/2.0/kr/legalcode).
These are dictionary-source integration fixtures, not independently annotated
gold sentence analyses. Synthetic edge cases in `dictionary.rs` remain under
the code license. The full dictionary is never downloaded during tests.

`krdict-breakdown.json` is a further adapted excerpt of the same September 2026
KRDict export, by the National Institute of Korean Language (국립국어원), under
CC BY-SA 2.0 KR. It contains IDs 23394, 26910, 27932, 44506, 74906, 83396, 85764,
85851, 85853, 86355, and 86571 for offline sentence-breakdown integration tests,
including plural suffix regression coverage. Changes: retain the
first sense and English equivalents, omit WordForm/RelatedForm and export
metadata, and reformat JSON. Source and license links are above. These test
entries verify source integration; they are not gold sentence annotations.

`krdict-particles.json` contains 20 additional primary word entries from the same
September 2026 KRDict export, by the National Institute of Korean Language,
under CC BY-SA 2.0 KR. IDs: 17199, 29739, 29742, 31952, 31953, 44878, 57305,
58272, 62251, 62818, 68853, 71128, 73012, 73276, 84991, 86094, 86111, 86116,
86258, 86264. Changes: retain the first sense and its English equivalent,
omit WordForm/RelatedForm and export metadata, exclude idiom subentries, and
reformat JSON. Source/license links are above. Used for offline particle,
pronoun, POS-compatibility, and browser integration regressions.

`krdict-derivation.json` contains 10 additional primary word entries from that
same September 2026 KRDict export (National Institute of Korean Language,
CC BY-SA 2.0 KR). IDs: 21353, 21645, 21652, 31670, 65114, 75947, 86232, 88852,
88966, 92145. Changes: retain all senses/attachment notes for the three suffixes,
the first sense for other entries, and English equivalents only. Retain WordForm
for 정답다 to test source conjugations; omit other WordForm, RelatedForm, and
global metadata, exclude idiom subentries, and reformat JSON. Source/license
links are above. These are offline integration fixtures, not sentence gold.

`krdict-hada.json` contains 10 primary word entries from the same September 2026
KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
IDs: 15400, 24991, 49056, 60323, 60999, 66376, 78410, 78612, 80286, 85911.
Changes: retain the first sense and English equivalents, omit WordForm,
RelatedForm and global metadata, exclude idiom subentries, and reformat JSON.
Source/license links are above. Used for offline dictionary/CLI/browser checks
of shortened 하다; the spelling judgments themselves are in the separate ledger.

`krdict-adverbs.json` contains 17 primary entries from the same September 2026
KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
IDs: 16281, 16288, 26799, 26824, 28387, 45290, 48746, 52143, 62076, 64523,
68755, 70801, 80952, 88924, 88927, 89917, 89918. Changes: retain the first sense
and English equivalents, omit WordForm/RelatedForm and global metadata, exclude
idiom subentries, and reformat JSON. Source/license links are above. Used for
offline adverb/base preservation and homonymous suffix/ending lookup tests.

`optimization.json` contains complete-output SHA-256 fingerprints for 30 manually
chosen words, initially captured before replacing the auxiliary chart.
These project-licensed compatibility snapshots protect grouping, morphemes, rule
provenance and ordering; they are not independently annotated linguistic gold.
Intentional grammar changes require reviewing any resulting fingerprint changes.
The P1 particle expansion changed 12 of these snapshots: two words gained polite
요 paths, and ten gained contracted ㄴ/ㄹ hypotheses (including a copular case).
Comparison against the initial committed Nix binary preserved every previous
analysis and supporting rule. Affected entries retain `previous_sha256` and a
change note. Additional dictionary-free lexical hypotheses are not certified
valid words by these fingerprints; candidate judgments remain separate.
The COV-011 하다 extension changed nine further snapshots. Each was compared
against the preceding COV-010 Nix binary: all prior analyses and supporting rules
remain, and the additions all carry `deletion.ha`. These include unknown whole
하다 stems after stop-final strings and auxiliary groups headed by 먹하다.
The snapshots document API additions, not certification of these lexical roots.
Each retains its previous hash and change note; no corpus baseline was replaced.

`validity.json` is a separate, agent-authored candidate-judgment ledger under the
project's MIT OR Apache-2.0 license, not an excerpt from the corpora below. It
contains short illustrative forms and source-backed rationales, with independent
Korean-language review still pending. See the [evaluation workflow](../../docs/evaluation.md#candidate-judgment-ledger-and-review-queue).

These are unmodified first-four-sentence excerpts from the **development**
partitions of Universal Dependencies 2.15. They are deliberately small offline
adapter/regression fixtures, not a representative accuracy benchmark.

* `kaist.conllu`: [UD Korean KAIST](https://github.com/UniversalDependencies/UD_Korean-Kaist/tree/888f855c7bcf1e39291246744f4e98f6bda6742e), sentences M2TA_069-s1 through M2TA_069-s4.
* `gsd.conllu`: [UD Korean GSD](https://github.com/UniversalDependencies/UD_Korean-GSD/tree/60ffc4f2f0cbf0bf816f0d44a7339512f5ce9c25), sentences dev-s1 through dev-s4.

`kaist-adverbs.conllu` is a further unmodified excerpt of the same pinned KAIST
development partition, containing complete sentences M2TA_069-s19, M2TA_089-s68,
and MH2_0069-s41. The COV-012 regression checks their 같이/없이/달리 token IDs;
it does not assert all readings of every token in those sentences are correct.
The corpus license and attribution below also apply to this excerpt.

Both datasets specify **CC BY-SA 4.0**, separately from klem's code license.
See [LICENSE.txt](LICENSE.txt) and the upstream READMEs. GSD's README distinguishes
the annotation license from rights in the underlying source texts.

Attribution: Jayeol Chun, Na-Rae Han, Jena D. Hwang, and Jinho D. Choi,
*Building Universal Dependency Treebanks in Korean*, LREC 2018; the KAIST corpus
contributors, including Key-Sun Choi; and the GSD contributors, including Ryan
McDonald, Joakim Nivre, and Daniel Zeman. GSD also requests citation of
McDonald et al., *Universal Dependency Annotation for Multilingual Parsing*,
ACL 2013. Full upstream notices are downloaded alongside each corpus.

`krdict-comparative.json` contains three primary entries (61190, 80280, 80282)
from the same September 2026 KRDict export (National Institute of Korean
Language, CC BY-SA 2.0 KR). Changes: retain the first sense and English
equivalents, omit WordForm/RelatedForm and global metadata, exclude idiom
subentries, and reformat JSON. Source/license links above apply. This fixture
covers lexical 보다 and the distinct -듯/-듯이 ending entries.

`kaist-comparative.conllu` preserves two complete sentences, MH2_0069-s60 and
MH2_0069-s183, byte-for-byte from the same pinned KAIST development partition
linked above. The offline regression checks token 2 (보듯이 → 보다) in both
sentences. The KAIST attribution and CC BY-SA 4.0 license above apply; the test
does not certify all analyses of all tokens in the excerpts.

`krdict-conditional.json` contains six primary entries (66956, 68738, 68841,
68881, 69579, 73277) from the same September 2026 KRDict export (National
Institute of Korean Language, CC BY-SA 2.0 KR). Changes: retain the first sense
and English equivalents, omit WordForm/RelatedForm and global metadata, exclude
idiom subentries, and reformat JSON. Source/license links above apply. It covers
하다/살다 and the conditional endings alongside their quoted-expression homonyms.

`kaist-conditional.conllu` contains complete sentences MH2_0069-s53 and
MH2_0149-s14; `gsd-conditional.conllu` contains complete sentence dev-s153.
All are byte-identical excerpts from the pinned development partitions linked
above, under the same CC BY-SA 4.0 corpus license. Selected stable tokens test
한다면, 않는다면, and 들리신다면; the GSD annotation is secondary evidence,
not an independent manual judgment. Other candidates in those sentences are
not automatically labeled correct.

`krdict-adnominal.json` contains four primary entries (62171, 83896, 86688,
86717) from the same September 2026 KRDict export (National Institute of Korean
Language, CC BY-SA 2.0 KR). Changes: retain all senses for the three expressions,
the first sense for auxiliary 보다, and English equivalents only; omit
WordForm/RelatedForm and global metadata, exclude idiom subentries, and reformat
JSON. Source/license links above apply. Original 문법‧표현 / 품사 없음 fields
are retained to test the narrow grammar-expression lookup exception.

`kaist-adnominal.conllu` contains complete sentences M2TA_089-s4, MH2_0069-s151,
and MH2_0169-s111, byte-identical excerpts from the pinned KAIST development
partition linked above under the same CC BY-SA 4.0 corpus license. Selected
stable tokens protect 배우자는, 절약하려는, and the 바꿔보자는 auxiliary group;
other candidate readings in these sentences are not automatically certified.

`krdict-daga.json` contains three primary entries (57304, 85740, 86099) from
the same September 2026 KRDict export (National Institute of Korean Language,
CC BY-SA 2.0 KR). Changes: retain all senses for the endings, the first sense
for 부르다, and English equivalents only; omit WordForm/RelatedForm and global
metadata, exclude idiom subentries, and reformat JSON. Source/license links
above apply. It preserves the distinct -다가/-어다가 entries and notes.

`kaist-daga.conllu` contains complete sentences MH2_0169-s159, MH2_0169-s444,
and MH2_0169-s718; `gsd-daga.conllu` contains complete sentence dev-s616. These
are byte-identical excerpts from the pinned development partitions linked above,
under their CC BY-SA 4.0 corpus license. Three selected positive tokens protect
불렀다가, 침략했다가, and 갔다가. The additional KAIST sentence preserves the
살겠다가 quoted-subject annotation; it is not labeled a -다가 success. The GSD
annotation is secondary evidence and the fixtures do not certify all candidates.

`krdict-quoted-questions.json` contains three primary entries (86030, 86031,
26878) from the same September 2026 KRDict export (National Institute of Korean
Language, CC BY-SA 2.0 KR). Changes: retain the first sense and English
equivalents, omit WordForm/RelatedForm and global metadata, exclude idiom
subentries, and reformat JSON. Source/license links above apply. The fixture
preserves the quoted-question expressions and lexical 아니다.

`kaist-quoted-questions.conllu` contains complete sentences MH2_0069-s250 and
MH2_0169-s383, byte-identical excerpts of the pinned KAIST development partition
linked above. The KAIST attribution and CC BY-SA 4.0 license apply. Selected
stable tokens protect 아니냐는 and 했느냐는; the fixture does not certify all
analyses of these sentences.
