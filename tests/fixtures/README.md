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

`krdict-quoted-questions.json` contains seven primary entries (86030, 86031,
86032, 26878, 72146, 71306, 79033) from the same September 2026 KRDict export (National Institute of Korean
Language, CC BY-SA 2.0 KR). Changes: retain the first sense and English
equivalents, omit WordForm/RelatedForm and global metadata, exclude idiom
subentries, and reformat JSON. Source/license links above apply. The fixture
preserves the quoted-question expressions and lexical 아니다.

`kaist-quoted-questions.conllu` contains complete sentences MH2_0069-s250 and
MH2_0169-s383, byte-identical excerpts of the pinned KAIST development partition
linked above. The KAIST attribution and CC BY-SA 4.0 license apply. Selected
stable tokens protect 아니냐는 and 했느냐는; the fixture does not certify all
analyses of these sentences.

`krdict-post-ending-particles.json` contains four primary entries (86552,
86554, 86555, 68797) from the same September 2026 KRDict export (National
Institute of Korean Language, CC BY-SA 2.0 KR). Changes: retain the first sense
and English equivalents, omit WordForm/RelatedForm and global metadata, exclude
idiom subentries, and reformat JSON. It preserves the two 만 particle homonyms,
마는, and adjective 있다. Source/license links above apply.

`kaist-post-ending-particles.conllu` preserves four complete sentences
M2TA_089-s15, MH2_0069-s174, MH2_0159-s132, and MH2_0169-s548;
`gsd-post-ending-particles.conllu` preserves complete sentence dev-s320.
These are byte-identical excerpts from the pinned development partitions linked
above, under their CC BY-SA 4.0 license. Stable tokens check 빼고는, 통해서만,
있습니다만, 대주고는, and 하면서도. These annotation matches do not certify
all candidates in the excerpted sentences.

COV-018a updates only the 학교에서만은 compatibility fingerprint, retaining
its old hash. Four new 어/어서 + 만 + 은 paths have unknown predicate roots;
all prior analyses and provenance remain. This is an API compatibility review,
not a judgment that those roots are valid vocabulary.

`krdict-particle-chains.json` contains nineteen primary entries from the same
September 2026 KRDict export (National Institute of Korean Language,
CC BY-SA 2.0 KR): 78504, 78508, 89214, 89218, 86139, 70334, 70340, 70339,
70337, 70074, 70075, 86366, 86353, 60319, 58621, 61172, 15672, 69698, 70055.
Changes: keep all particle senses and the first lexical sense, retain English
equivalents only, omit WordForm/RelatedForm and global metadata, exclude idiom
subentries, and reformat JSON. Source/license links above apply. The fixture
retains particle homonyms and the final-ending licenses in later senses of 나.

`kaist-particle-chains.conllu` preserves complete sentences M2TA_089-s52,
MH2_0069-s295, and MH2_0169-s490; `gsd-particle-chains.conllu` preserves
complete sentence dev-s471. They are byte-identical excerpts of the pinned
development partitions linked above, under their CC BY-SA 4.0 license. Stable
tokens check 어디까지나, 이제부터라도, 사회주의라고, and 넣기라도; other
analyses in those sentences are not automatically judged correct.

`krdict-auxiliary-inventory.json` contains all 54 primary entries tagged 보조 동사
or 보조 형용사 in the September 2026 KRDict export, plus ending -을 (69058).
The National Institute of Korean Language attribution and CC BY-SA 2.0 KR
license above apply. Changes: retain the first sense, its first example and
English equivalents; omit WordForm/RelatedForm and global metadata, exclude
shared-ID idiom/proverb subentries, and reformat JSON. The complete entry IDs,
headwords, URLs, and attachment notes from every sense are preserved separately
in [the source inventory](../../docs/auxiliary-inventory.json), under the same
license. The browser fixture merge keeps existing primary entries where this
inventory overlaps richer fixtures; shared-ID idioms remain distinct entries.

`kaist-auxiliary-inventory.conllu` preserves complete sentences M2TA_069-s25,
MH2_0069-s198, MH2_0069-s422, and MH2_0169-s332;
`gsd-auxiliary-inventory.conllu` preserves complete sentence dev-s112. These are
byte-identical excerpts from the pinned development partitions linked above,
under their CC BY-SA 4.0 license. Selected tokens protect 착하다보니, 늘어났다,
번져나갔다, 해달라고, and 먹을만한. These annotations do not certify every
compound split or other candidate generated from those sentences.

COV-019a updates only the 먹게하고있다 compatibility fingerprint and retains
its previous hash. Two additional 어 + 하다 + 고 + 있다 paths hypothesize
unknown 먹게다/먹겋다 stems; every prior analysis and provenance item remains.
This records output compatibility, not a judgment of lexical validity.

`krdict-nominal-copulas.json` contains primary ending entries -기 (72222) and
-음 (78528) from the same September 2026 KRDict export (National Institute of
Korean Language, CC BY-SA 2.0 KR). Changes: retain the first sense and its first
example, keep only English equivalents, omit WordForm/RelatedForm and global
metadata, exclude idiom subentries, and reformat JSON. Source/license links
above apply. Copula 86232 and suffix -답다 are already in the derivation fixture.

`kaist-nominal-copulas.conllu` contains complete sentence MH2_0169-s271,
a byte-identical excerpt of the pinned KAIST development partition under its
CC BY-SA 4.0 license. Token 6, 떠먹이기다, protects the ordered 떠먹이다 + 이다
group through nominalization and copula omission. The other sentence candidates
are not automatically certified. All current compatibility fingerprints remain
unchanged by COV-020a.

`krdict-negative-contractions.json` contains nine primary entries (62051, 61178,
15807, 58695, 84451, 50338, 60097, 86756, 86757) from the same September 2026
KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
Changes: retain the first sense, its first example, and English equivalents;
omit WordForm/RelatedForm and global metadata, exclude idiom subentries, and
reformat JSON. Source/license links above apply. It preserves lexicalized words
alongside base predicates, and the distinct 품사 없음 confirmation expressions.
Auxiliary 않다 and 싶다 are provided by the auxiliary-inventory fixture.

`kaist-negative-contractions.conllu` contains complete sentence MH2_0159-s86,
a byte-identical excerpt of the pinned KAIST development partition under its
CC BY-SA 4.0 license. Token 12, 적잖은, protects the grouped 적다 + 않다 path.
The remaining candidates in this sentence are not automatically certified.

`krdict-adverb-expansion.json` contains fourteen primary entries (88504, 14970,
26788, 75797, 58167, 40533, 40536, 16218, 29025, 61076, 60323, 62493, 62494,
84452) from the September 2026 KRDict export (National Institute of Korean
Language, CC BY-SA 2.0 KR). Changes: retain the first sense, its first example,
and English equivalents; omit WordForm/RelatedForm and global metadata, exclude
idiom subentries, and reformat JSON. Source/license links above apply. The fixture
preserves the noun/adverb homonyms of 가까이, lexical adverbs, related predicates,
and the adverb-forming 히 suffix. The browser merge retains existing richer
primary entries when supplemental inventories overlap.

`kaist-adverb-expansion.conllu` contains complete sentences MH2_0159-s128,
MH2_0159-s341, MH2_0159-s358, and MH2_0159-s53, byte-identical excerpts from the
pinned KAIST development partition under CC BY-SA 4.0. Four selected tokens
protect 다분히, 가벼이, 적잖이, and 상당히. These grouped-lemma annotations do
not certify every candidate or a literal 하 segment in the adverb's surface.

`krdict-negative-auxiliaries.json` contains primary entries 80682 (-어라),
50193 (lexical 마), and 69296 (lexical 말다) from the September 2026 KRDict
export, National Institute of Korean Language, CC BY-SA 2.0 KR. Changes: retain
English equivalents and the first example per sense; omit WordForm/RelatedForm
and global metadata, exclude idiom subentries, and reformat JSON. Source/license
links above apply. The auxiliary-inventory fixture supplies the negative
auxiliaries; the separate lexical entries protect ambiguity and broad POS lookup.

`gsd-negative-auxiliaries.conllu` is complete sentence dev-s312, a byte-identical
excerpt of the pinned GSD development partition (CC BY-SA 4.0). Token 4, 마라,
protects 말다 recovery. Internal-particle and mood cases are source-backed
synthetic regressions, not additional corpus gold.

`krdict-auxiliary-classes.json` retains the attributed primary 없다 entry
(89917) from `krdict-adverbs.json`, ultimately the September 2026 KRDict export
(National Institute of Korean Language, CC BY-SA 2.0 KR). The existing trimmed
sense/example and English-equivalent selection is unchanged; source/license
links above apply. The auxiliary-inventory fixture supplies all 54 auxiliary
entries for the class tests.

`gsd-auxiliary-classes.conllu` contains complete sentences dev-s112, dev-s388,
dev-s572, and dev-s791 from the pinned GSD development partition (CC BY-SA 4.0).
Each sentence is a byte-identical excerpt. Four selected tokens protect 먹을만한,
참을만한데, 보고싶다, and 보고싶습니다. These are preserved gold recoveries,
not new gains or annotations of every alternative analysis. Rejected class
combinations are tracked separately by source-backed synthetic judgments.

`krdict-grammar-labels.json` contains 273 primary entries from the September
2026 KRDict export, National Institute of Korean Language, CC BY-SA 2.0 KR.
272 support the teaching-label catalog; 68883 supplies the alternate propositive
boundary. Changes: retain English equivalents and the first example per sense,
omit WordForm/RelatedForm and global metadata, exclude idiom/proverb subentries,
and reformat JSON. Source/license links above apply. The catalog records every
label's source IDs, headwords, and original POS; these are common-function hints,
not contextual sense selections or morphological attachment licenses.

`kaist-propositive.conllu` is the complete KAIST development sentence
MH2_0159-s160, a byte-identical excerpt under CC BY-SA 4.0. Token 11, 봅시다,
preserves 보다 recovery while the engine's canonical ending changes from the
legacy 습시다 to 읍시다. It is not a newly recovered corpus token; boundary and
irregularity judgments have separate synthetic regressions.

`kaist-foreign-nominals.conllu` and `gsd-foreign-nominals.conllu` contain complete,
byte-identical sentences from the pinned development partitions, CC BY-SA 4.0.
`foreign-nominal-gold.json` indexes 17 KAIST and 22 GSD tokens newly recovered by
conditional non-Hangul nominal boundaries, retaining the source spelling and
expected lemma groups. These annotations verify lexical recovery, not the
pronunciation assumption or normative spelling of each source token. In
particular Bilbe is retained as annotated rather than corrected to another word.
The selection and source hashes are in `docs/foreign-nominal-evaluation.json`.
Existing attributed grammar fixtures supply particles and copulas for browser
and dictionary tests; no artificial foreign-name dictionary entries are added.

`kaist-intention-endings.conllu` and `gsd-intention-endings.conllu` contain ten
KAIST and one GSD complete development sentences, byte-identical excerpts under
CC BY-SA 4.0. The eleven new intention/expectation/concession recoveries are
indexed in `docs/intention-ending-evaluation.json` and asserted by stable corpus
IDs in `tests/corpus.rs`. These gold groups do not annotate every reading or
certify contextual sense choice. The grammar-label fixture additionally includes
primary KRDict entries 85920/85922 (-으리라고/-리라고), 77049/77051
(-을지라도/-ㄹ지라도), and 80338/80339 (both -자면 homonyms), using the
same attribution and trimming policy documented above.

`krdict-emphatic-particles.json` contains 21 primary lexical entries for twelve
headwords used in COV-018c/017i dictionary/browser regressions, from the September
2026 KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
Changes: retain English equivalents and the first example per sense; omit
WordForm/RelatedForm and global metadata, exclude idiom/proverb subentries, and
reformat JSON. Source/license links above apply. The grammar-label fixture adds
ten entries: 70309, 70312, 70315, 70316, 70317, 80164, 80167, 86102, 86103, and
86168; every previously included entry is unchanged. It already contains both
서 particle homonyms, including locative 86712.

`kaist-emphatic-particles.conllu` and `gsd-emphatic-particles.conllu` contain twelve
KAIST and two GSD complete development sentences as byte-identical CC BY-SA 4.0
excerpts. Tests explicitly protect thirteen new grouped recoveries. GSD dev-s934
is retained for segmentation review: 확약서 is tagged 확약/NNG + 서/JKB in a
sentence about submitting a written pledge. Its numerical recovery is not made
into a required linguistic judgment. The source IDs, hashes, and fourteen total
numerical gains are recorded in `docs/emphatic-particle-evaluation.json`.

`kaist-quoted-definitions.conllu` and `gsd-quoted-definitions.conllu` contain 24
KAIST and two GSD complete development sentences as byte-identical CC BY-SA 4.0
excerpts. `quoted-definition-gold.json` indexes the 26 newly recovered groups.
The KAIST token MH2_0069-s370/6 is explicit standalone 이란 after a quoted noun
phrase; a separate role test requires its Copula-kind candidate without joining
tokens. Remaining 라는 representation differences are recorded in
`docs/quoted-definition-evaluation.json`, not promoted into required particles.

The grammar-label fixture adds primary KRDict entries 85858, 85859, 86297,
89676, 86606, and 52612 with the same source/license and trimming policy above;
all earlier entries remain unchanged. Existing `krdict-emphatic-particles.json`
lexical entries and the attributed 이다 entry in `krdict-derivation.json` supply
dictionary regressions, combined without their duplicate 학생 entry.

`kaist-copula-fragments.conllu` contains two complete, byte-identical KAIST
Universal Dependencies development sentences, MH2_0209-s39 and MH2_0209-s122,
under the same KAIST attribution/license above. COV-020b tests token 4 in each:
standalone 라는 has the annotated lemma 이 (normalized to 이다 by the existing
adapter). The corpus's `OrigLemma=이+란` is preserved; the program's canonical
ending remains 라는. See `docs/copula-fragment-evaluation.json` for comparison
hashes, source, stable IDs and the explicit preceding-quotation condition.

`kaist-obligation.conllu` and `gsd-obligation.conllu` contain two and three
complete development sentences, respectively, under the corpus attribution and
licenses listed above. They are byte-identical excerpts. The exact tested IDs,
file hashes and original expected lemma groups appear in
`docs/obligation-evaluation.json`. GSD's implicit 하다 in 와야겠다 and
세척해야겠지요 is preserved as an annotation difference. KRDict source entries
86238, 86239 and 86240 are included in the grammar-label fixture for the bundled
-아/어/여야겠- expression; previous entries remain unchanged.

`kaist-prefinal-licenses.conllu` is the complete byte-identical KAIST test sentence
MH2_0110-s324 under the KAIST attribution and CC BY-SA 4.0 license above. Token 14,
못하더라는, protects the original gold 못하다 after removal of the incorrect
더 + 으라는 command analysis. The valid replacement uses the sourced 더라는
bundle; this is a preserved recovery, not a new corpus gain. The grammar-label
fixture adds KRDict entry 86347 with the same trimming policy, source, and license
as its other entries. All 258 earlier entries remain unchanged. Dictionary tests
reuse the attributed lexical fixtures described above. Individual paths, hashes,
and the single reviewed optimization-snapshot change are recorded in
`docs/prefinal-license-evaluation.json`.

`kaist-omitted-copulas.conllu` and `gsd-omitted-copulas.conllu` contain four and
five complete byte-identical development sentences from the pinned corpora,
under their attribution and licenses above. All nine newly recovered groups are
identified by stable IDs in `docs/omitted-copula-evaluation.json`. Original short
거 versus full 것 annotations are preserved rather than normalized in the
adapter.

`krdict-colloquial-copulas.json` contains fifteen primary KRDict entries from the
same September 2026 snapshot: 62331, 62835, 71128, 44878, 62251, 31953, 29739,
31952, 86232, 73276, 20256, 20530, 58272, 62171, and 71581. Source/license links
above apply (National Institute of Korean Language, CC BY-SA 2.0 KR). Changes:
keep English equivalents and the first example per sense; remove WordForm,
RelatedForm, global metadata, and idiom/proverb subentries; reformat JSON. This
fixture supplies noun/pronoun alternatives, the copula, and the tested auxiliary
and whole-word homonyms. The grammar-label fixture additionally includes the
short ending allomorph sources 79397, 79401, 80259, and 85132; all 259 previous
entries remain unchanged.

`krdict-adverb-roots.json` contains 52 primary KRDict entries from the September
2026 export. `docs/adverb-root-inventory.json` records every source ID, base,
whole-word entry and grammatical role. National Institute of Korean Language,
CC BY-SA 2.0 KR; source/license links above apply. Changes: keep English
translations and the first example per sense, remove WordForm/RelatedForm and
global metadata, exclude idiom/proverb subentries, and reformat JSON. Missing
base entries are recorded rather than synthesized.

`kaist-adverb-roots.conllu` and `gsd-adverb-roots.conllu` contain three and one
complete byte-identical development sentences under the corpus attribution and
licenses above. The tested lexical adverbs are 더욱이, 일일이, 익히, and 특히;
the source gold keeps each whole word. Tests preserve these existing recoveries
alongside optional decompositions and do not relabel the corpus as derivational
gold. File hashes and unchanged development recall appear in
`docs/adverb-root-evaluation.json`.

`krdict-hada-ki.json` contains four primary entries from the same September 2026
KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR), IDs
17503, 48285, 58171 and 75325. Changes: retain the first sense, its English
equivalents and first example; omit WordForm/RelatedForm, global metadata and
idiom subentries; reformat JSON. Source/license links are above. These entries
support shortened 하다 nominalization dictionary and browser checks.

`kaist-hada-ki.conllu` and `gsd-hada-ki.conllu` preserve the complete, byte-identical
UD 2.15 development sentences MH2_0209-s34 and dev-s629 from the pinned sources
above. They verify 강구키 and 조성키로. Attribution and CC BY-SA 4.0 licensing
follow the other KAIST/GSD excerpts. GSD's separate 이시가키와 annotation anomaly
is recorded in `docs/hada-ki-evaluation.json`, not promoted to linguistic gold.

`krdict-reporting.json` contains eleven primary entries from the same September
2026 KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR),
IDs 15722, 17203, 24079, 31670, 46165, 58272, 64524, 69471, 69473, 69579 and
79033. Changes: retain English equivalents and first example per sense; omit
WordForm/RelatedForm, global metadata and idiom subentries; reformat JSON.
Source/license links are above. Nine additional reporting-grammar entries
(76427, 81377, 81389, 81393, 81412, 86633, 86635, 86636, 86638) are in the
grammar-label fixture with the same adaptations and all attachment notes.

`kaist-reporting.conllu` preserves complete UD 2.15 development sentences
M2TA_069-s20 and M2TA_069-s27; `gsd-reporting.conllu` preserves dev-s287 and
dev-s650. Both are byte-identical excerpts from the pinned corpora above,
under their CC BY-SA 4.0 licenses. They verify the grouped lemma recoveries for
넘었답니다, 묻었답니다, 물어본답니다 and 좋았답니다; they do not judge every
unannotated candidate or choose between informative and reported-speech senses.

`krdict-copula-yo.json` contains four primary entries from the same September
2026 KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR),
IDs 14023, 66841, 67746 and 73689. Changes: retain English equivalents and first
example per sense; omit WordForm/RelatedForm, global metadata and idiom
subentries; reformat JSON. Source/license links above apply. Entry 86117 (-요)
is added to the grammar-label fixture with the same adaptations.

`kaist-copula-yo.conllu` preserves five complete byte-identical UD 2.15
KAIST development sentences: MH2_0069-s406, MH2_0109-s3, MH2_0159-s181,
MH2_0159-s263 and MH2_0159-s354, under the pinned corpus's CC BY-SA 4.0 license.
They protect the connective -요 reading. Two separate sentence-final annotation
cases are documented in `docs/copula-yo-evaluation.json`, not promoted to gold
for the connective. COV-020d changes two stress fingerprints by adding an
unknown nominal + omitted copula reading; old hashes and all prior candidates
remain. The report records each addition rather than certifying those nominals.

`krdict-causal.json` contains nine primary entries (15983, 24079, 26878, 26962,
27804, 31670, 50557, 69579, 86232) from the same September 2026 KRDict export,
National Institute of Korean Language, under CC BY-SA 2.0 KR. Changes: retain
English equivalents and the first example group per sense; omit WordForm,
RelatedForm and export metadata; exclude idiom subentries and reformat JSON.
The two ending sources 73011 and 84811 are added to `krdict-grammar-labels.json`
with the same adaptation. All earlier source entries are retained. Source and
license links are above. These are dictionary integration fixtures, not
independent sentence judgments.

`gsd-causal.conllu` preserves complete, byte-identical UD Korean GSD 2.15
**development** sentences dev-s485 and dev-s836 under the dataset's CC BY-SA 4.0
license. They contain the saved 추천하길래 and 뽑길래 misses. The original
lemma/XPOS fields and sentence context remain; GSD's automatic annotation is
secondary evidence and does not label every valid alternative. See the existing
GSD source/license links above and `docs/causal-evaluation.json` for hashes.

COV-019d extends entry 62888 in `krdict-auxiliary-inventory.json` with its
expressive -어 하다 sense 9. It retains the source attachment note, Korean
definition, English equivalent and first example group; the existing causative
sense 1 and every other entry are unchanged. This is adapted from the same
September 2026 National Institute of Korean Language KRDict export under
CC BY-SA 2.0 KR, with the source/license links above. It validates dictionary
source integration, not an independently annotated candidate precision score.

`krdict-quoted-alternatives.json` contains nine primary lexical entries (15983,
17203, 24037, 30750, 31670, 49222, 69579, 86232, 89858) from the September 2026
National Institute of Korean Language KRDict export, under CC BY-SA 2.0 KR.
Ten grammar-expression entries (82118, 82119, 82121, 82122, 83892, 86053, 86055,
86056, 86057, 86332) are added to `krdict-grammar-labels.json`. Adaptation:
retain English equivalents and the first example group per sense, omit
WordForm/RelatedForm and global export metadata, exclude idiom subentries, and
reformat JSON. Earlier entries are unchanged. Source/license links above apply.
The source's 문법‧표현 / 품사 없음 classification is retained.

`kaist-quoted-alternatives.conllu` preserves complete development sentences
MH2_0159-s14 and MH2_0159-s161; `gsd-quoted-alternatives.conllu` preserves
complete dev-s330. They are byte-identical excerpts from the pinned UD 2.15
sources linked above under CC BY-SA 4.0. Four stable token IDs protect reported
alternative recovery; no annotation is rewritten or promoted into a judgment of
all candidates. GSD's automatic annotation remains secondary evidence.

`krdict-enumerative-particles.json` contains ten lexical entries (15983, 26344,
31670, 57305, 62171, 62683, 65114, 68755, 73276, 86232) from the September 2026
National Institute of Korean Language KRDict export, under CC BY-SA 2.0 KR.
Grammar entries 70330, 82342, 85861, 86046 and 86518 are added to the grammar-label
fixture. Adaptation: retain English equivalents and the first example group per
sense, omit WordForm/RelatedForm and global metadata, exclude idiom subentries,
and reformat JSON. All previous grammar entries are unchanged. Source/license
links above apply. NIKL's related-form tables supplement two dictionary gaps;
the catalog links existing source entries and does not fabricate missing entries.
The sources and representation boundaries are documented in COV-018e/017p.

`kaist-enumerative-particles.conllu` preserves complete, byte-identical UD Korean
KAIST 2.15 **training** sentences MH2_0014-s474, MH2_0024-s81 and MH2_0024-s173,
under the pinned corpus's CC BY-SA 4.0 license. The examples 것이라든가,
않든가 and 취미라든가 had missing gold groups before COV-018e/017p. Their
original lemma/XPOS fields remain unchanged. These three selected cases are
regressions, not a held-out recall estimate or evidence for every alternative.

`krdict-destination-particles.json` contains twenty lexical entries (15983, 17608,
17863, 25004, 29742, 30203, 31670, 60319, 60931, 61310, 62171, 62258, 62589,
62907, 69792, 71218, 73276, 86232, 89849, 91328) from the September 2026 National
Institute of Korean Language KRDict export, under CC BY-SA 2.0 KR. Grammar
entries 41693, 41695, 70037, 70051, 73013, 73014, 80293, 83879, 83880, 86550,
86573 and 86577 are added to the grammar-label fixture. Adaptation: retain English
equivalents and first example group per sense, omit WordForm/RelatedForm and
global metadata, exclude idiom subentries, and reformat JSON. All prior grammar
entries remain unchanged. Source/license links above apply. The seven deictic
entries supply location/direction senses; their homonyms are not interchangeable.

`kaist-destination-particles.conllu` preserves complete development sentences
MH2_0149-s138 and MH2_0169-s706; `gsd-destination-particles.conllu` preserves
complete dev-s127. These are byte-identical excerpts from the pinned UD 2.15
sources under CC BY-SA 4.0, with their original lemma/XPOS annotations. They
protect 강에다, 노동자보고 and 거기에다 recovery, without judging every
alternative or choosing contextual senses. GSD's automatic annotations remain
secondary evidence; source/license links above apply.


`krdict-enumerative-da.json` contains fifteen lexical entries (15983, 17608,
20195, 26805, 29542, 29555, 30159, 31670, 36978, 37057, 58809, 64611, 71218,
73276, 86232) from the September 2026 NIKL KRDict export under CC BY-SA 2.0 KR.
Grammar entries 85738 and 86118 are added to `krdict-grammar-labels.json`.
Adaptation: retain English equivalents and the first example group per sense,
omit WordForm/RelatedForm and global metadata, exclude idiom subentries, and
reformat JSON. Every previous grammar fixture entry is retained unchanged.
Source and license links above apply. Enumerative and emphatic 다 have separate
sources, and particle 이다 does not replace the copula homonym.

`gsd-enumerative-da.conllu` is the complete byte-identical UD Korean GSD 2.15
training sentence train-s1156 under CC BY-SA 4.0. Its 옷이다 token retains its
copular lemma/XPOS annotation. It protects an existing alternative, not a new
enumerative gold recovery or held-out score. Source/license links above apply.


`krdict-omitted-connectives.json` contains nineteen lexical entries (15983, 20256,
24079, 24562, 31670, 47976, 60319, 60321, 61468, 62171, 62331, 62657, 62835,
62907, 71875, 73276, 82525, 83170, 86232) from the September 2026 NIKL KRDict
export under CC BY-SA 2.0 KR. Entry 80139 is added to the grammar fixture; 80144
was already present. Adaptation: retain English equivalents and the first example
group per sense, omit WordForm/RelatedForm and global metadata, exclude idiom
subentries, and reformat JSON. Prior grammar entries remain unchanged. Source and
license links above apply. No entry is fabricated for the missing 엘리트주의.

`kaist-omitted-connectives.conllu` retains complete UD Korean KAIST 2.15 development
sentences M2TA_089-s65, MH2_0159-s200, MH2_0169-s179, MH2_0169-s615,
MH2_0169-s650 and MH2_0169-s698. `gsd-omitted-connectives.conllu` retains complete
GSD development sentences dev-s461, dev-s570 and dev-s842. All are byte-identical
excerpts with original annotations, under CC BY-SA 4.0. dev-s570 uses the place
name 테르니; matching its existing 테르 + 이 + 니 annotation is incidental,
not a claimed linguistic improvement. Source/license links above apply.


`krdict-honorific-copulas.json` contains fourteen lexical entries (15983, 17203,
20256, 24079, 31670, 58204, 59251, 62050, 62171, 62657, 62948, 69579, 71875,
86232) from the September 2026 NIKL KRDict export under CC BY-SA 2.0 KR.
Grammar entries 80329 and 86558 are added to the grammar-label fixture, retaining
all earlier entries unchanged. Adaptation: retain English equivalents and the
first example group per sense, omit WordForm/RelatedForm and global metadata,
exclude idiom subentries, and reformat JSON. Source and license links above apply.

`kaist-honorific-copulas.conllu` retains complete UD Korean KAIST 2.15 development
sentence MH2_0209-s66. `gsd-honorific-copulas.conllu` retains complete GSD development
sentences dev-s236 and dev-s932. They are byte-identical excerpts with original
annotations, under CC BY-SA 4.0. Their 마셨다, 주셨습니다 and 주셨어요 tokens
protect existing lexical readings as new copula hypotheses are introduced. They
are not relabeled or presented as new copula gold. Source/license links above apply.


`krdict-seo-connectives.json` is an attributed CC BY-SA 2.0 KR slice of the
September 2026 NIKL Korean Basic Dictionary export for COV-017q/018i. It retains
46 matching noun, predicate, auxiliary and particle entries for the tested
headwords, preserving homonyms and every sense, English equivalents and the
first example group per sense. Global export metadata, WordForm and RelatedForm
are omitted. The four new grammar sources 78584, 86567, 86569 and 86584 are added
to `krdict-grammar-labels.json` with the same selection policy. Other grammar
entries remain unchanged. Sources, source IDs and attachment notes are preserved
in `docs/seo-connective-evaluation.json`; these are dictionary integration
fixtures, not independent gold annotations.

`kaist-seo-connectives.conllu` preserves nine complete, byte-identical UD 2.15
KAIST development sentences whose annotated groups are newly recovered by
COV-017q/018i. The original annotations and corpus license remain unchanged;
case IDs and input hashes are recorded in the evaluation. No GSD recovery is
claimed by this batch.


`krdict-prefinal-copulas.json` is an attributed selection of 29 lexical entries
from the National Institute of Korean Language's Korean Basic Dictionary,
September 2026 export, under CC BY-SA 2.0 KR. It retains all senses, English
equivalents and the first example group per sense; WordForm, RelatedForm and
export metadata are omitted. Lexical homonyms remain distinct. Idiom entries
with reused numeric IDs are excluded, so 누구 is the pronoun, not an idiom.
The existing grammar fixture/catalog supplies modal/retrospective source entries.
See `docs/prefinal-copula-evaluation.json` for their complete attachment review.

`kaist-prefinal-copulas.conllu` and `gsd-prefinal-copulas.conllu` preserve one
and two complete UD 2.15 development sentences byte for byte. They protect
마찬가지겠지만, 최고더군요 and 어디더라 with their original grouped copula
annotations. Existing corpus licensing and attribution above apply; hashes and
case IDs are recorded in the comparison. Historical baselines are unchanged.


`kaist-retrospective-licenses.conllu` and `gsd-retrospective-licenses.conllu`
each preserve two complete UD 2.15 development sentences byte for byte. They
protect 않더라도, 맞더니, 가져가시더니 and 시켜주더군요 while retrospective
following-ending constraints remove other candidates. Existing UD corpus
licensing and attribution above apply. The source catalog, grammar fixture and
`krdict-prefinal-copulas.json` are reused unchanged for dictionary/CLI/browser
regressions. `docs/retrospective-license-evaluation.json` records source notes,
case IDs, fixture hashes and every targeted candidate removal; no historical
corpus baseline or stress fingerprint is regenerated.


`kaist-retrospective-connectives.conllu` and `gsd-retrospective-connectives.conllu`
each preserve two complete UD 2.15 development sentences byte for byte, covering
장손이기, 제한적이었음을, 먹게 and 먹기. Existing corpus attribution and licensing
above apply. `krdict-grammar-labels.json` adds short 며/면서/므로 entries
80253/80266/80268 with English translations and the first example group of each
sense, preserving every prior entry. The existing `krdict-prefinal-copulas.json`
lexical fixture is reused. `docs/retrospective-connective-evaluation.json` retains
source notes, hashes and every targeted candidate removal; no historical corpus
baseline or stress fingerprint is regenerated.


`kaist-retrospective-adnominals.conllu` and `gsd-retrospective-adnominals.conllu`
each preserve two complete UD 2.15 development sentences byte for byte, covering
정도였던가, 아니었던가요, 먹던 and 별로였던. Existing corpus attribution and
licensing above apply. `krdict-grammar-labels.json` adds eleven short-allomorph
and retrospective-bundle entries with English equivalents and the first example
group of each sense; every earlier entry remains. The dictionary regression
merges existing prefinal-copula and auxiliary-inventory fixtures by entry ID,
so shared entries are imported once. The comparison in
`docs/retrospective-adnominal-evaluation.json` records sources, fixture hashes,
and every targeted added/removed path without regenerating historical baselines.


`kaist-question-copulas.conllu` and `gsd-question-copulas.conllu` each preserve
two complete UD 2.15 development sentences byte for byte. GSD gains 뭔지/뭔가;
KAIST preserves 무엇일까/일부인지. Existing corpus licensing and attribution
above apply. `krdict-question-copulas.json` contains 39 lexical entries, retaining
all homonyms and senses for its selected heads, English equivalents and the
first example group per sense. `krdict-grammar-labels.json` adds short ㄹ까요
(entry 82350), preserving every earlier entry. These dictionary subsets use the
same KRDict attribution and CC BY-SA 2.0 KR license as the other fixtures.
`docs/question-copula-evaluation.json` records sources, fixture hashes, targeted
additions and the individually inspected stress change. The stress history is
retained; historical corpus baselines are unchanged.

`krdict-noh-contraction.json` contains 26 primary word entries from the September
2026 KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
IDs: 15983, 26847, 28325, 28326, 31670, 48279, 58272, 59468, 61013, 61190,
62051, 62171, 62249, 62601, 65570, 67470, 70060, 71234, 72578, 77243,
79033, 83636, 86118, 86232, 89534, 92457. All homonyms and senses are retained,
with English equivalents and the first example group per sense; WordForm,
RelatedForm, idiom subentries and global metadata are omitted. Source/license
links are above. Used for offline CLI/dictionary/browser contraction tests;
these entries are not annotated sentence gold.

`kaist-noh-contraction.conllu` preserves two complete byte-identical sentences
from the pinned UD Korean KAIST development file, with its existing source and
license attribution above. M2TA_069-s13/4 (놨었지요) newly recovers 놓다;
MH2_0169-s453/6 (내놓아야) protects the full compound spelling. Original gold
and historical baselines are unchanged; [the report](../../docs/noh-contraction-evaluation.json)
records input and fixture hashes.

`krdict-report-ne.json` contains 45 primary word entries from the September 2026
KRDict export (National Institute of Korean Language, CC BY-SA 2.0 KR).
IDs: 15983, 16488, 17186, 17203, 20256, 24079, 24396, 26847, 26878, 27500,
28764, 31670, 50557, 58272, 61190, 62171, 62249, 62394, 62395, 62595, 62657,
65172, 65173, 68796, 68797, 69579, 70060, 71285, 71311, 71581, 71583, 71875,
72578, 73276, 74104, 77243, 77245, 79033, 82136, 84412, 84413, 86118, 86232,
89534, 92457. All homonyms and senses are retained, with English equivalents and
the first example group per sense. WordForm, RelatedForm, idiom subentries and
global metadata are omitted. These integration fixtures are not sentence gold.

COV-017v adds 16 sources to `krdict-grammar-labels.json` with the same attribution,
license and adaptations: 69096, 69108, 75148, 75175, 75191, 75476, 82253, 82255,
82257, 82259, 86175, 86176, 86177, 86356, 86598, 89635. All 326 previous entries
remain; ten new canonical labels bring the catalog to 270 forms, 341 distinct
source IDs and 342 fixture entries. Ending and expression homonyms retain their
source POS and senses; the command label excludes the factual-only 라네 homonym.

`kaist-report-ne.conllu` and `gsd-report-ne.conllu` contain three and two complete
byte-identical sentences from the pinned UD development files, under their
existing source/license attribution above. They preserve the original gold for
대부분이라는데, 풍속이었다네, 있다는데, 판매한다네요 and 단골집이라는데.
[The report](../../docs/report-ne-evaluation.json) records the exact input and
fixture hashes; no historical corpus baseline is rewritten.

`krdict-doe.json` contains 38 primary word entries from the September 2026 KRDict
export (National Institute of Korean Language, CC BY-SA 2.0 KR). IDs: 15983,
17186, 17203, 20256, 24079, 24826, 26847, 26878, 28130, 31670, 36304, 50557,
57277, 57315, 58272, 61190, 62171, 62249, 62595, 62642, 62657, 68796, 68797,
69579, 70060, 70811, 71306, 71581, 71583, 71691, 71875, 74104, 77243, 79033,
86118, 86232, 89917, 92457. All homonyms/senses are retained, with English
equivalents and the first example group per sense. WordForm, RelatedForm,
idiom subentries and global metadata are omitted. These are integration fixtures,
not sentence gold. Source/license links are above.

COV-017w adds 80289 and 80291 to `krdict-grammar-labels.json` under the same
attribution, license and adaptations, preserving all 342 previous entries.
Canonical 으되 links both spellings; the catalog now has 271 forms, 343 distinct
source IDs and 344 grammar fixture entries.

`kaist-doe.conllu` and `gsd-doe.conllu` preserve complete byte-identical sentences
MH2_0149-s40 and dev-s267 from the pinned development files, under their existing
source/license attribution above. The original gold records 치렀으되 → 치르다
and 그리되 → 그리다. [The report](../../docs/doe-evaluation.json) includes hashes;
historical baselines and original annotations remain unchanged.


`krdict-chigo.json` contains 29 primary word entries from the September 2026
KRDict export, with every lexical homonym and sense for its selected headwords.
It retains English equivalents and the first example group per sense, omitting
WordForm/RelatedForm and export metadata. Attribution: National Institute of
Korean Language, Korean Basic Dictionary, [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The absent 교수님 headword is tested as a dictionary gap, not fabricated.
Three grammar entries (73015/83882/73016) extend `krdict-grammar-labels.json`
under the same attribution and adaptations; all previous entries remain.
The catalog now has 274 forms, 346 source IDs and 347 grammar fixture entries.

`gsd-chigo.conllu` preserves the complete byte-identical UD 2.15 GSD development
sentence `dev-s33`, under the GSD attribution/license above. Its regression
requires only the reviewed `id:dev-s33/5` 아파트치고 → 아파트 group; it does
not certify all candidates in that sentence. [The report](../../docs/chigo-evaluation.json)
records the corpus/fixture hashes and exact candidate comparisons.


`krdict-range-case.json` contains 37 primary word entries from the September
2026 KRDict export, with every lexical homonym and sense for selected heads.
It retains English equivalents and the first example group per sense, omitting
WordForm/RelatedForm and export metadata. Attribution: National Institute of
Korean Language, Korean Basic Dictionary, [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
No entries are invented for the raw 6세/ABC hypotheses. The grammar catalog and
its fixture are unchanged. [The comparison](../../docs/range-case-evaluation.json)
additionally retains explicitly selected dictionary example groups as evidence
for the five particle pairs, under the same attribution/license.

`kaist-range-case.conllu` preserves complete byte-identical UD 2.15 KAIST
development sentences `MH2_0149-s122` and `MH2_0159-s285`, under the KAIST
attribution/license above. The regression requires the reviewed
`id:MH2_0149-s122/6` 역사까지를 → 역사 group. The second sentence records
`id:MH2_0159-s285/15` 편마다에도 as an unresolved observation; its morphology
is neither required nor forbidden. The report records source/fixture hashes.


`krdict-extent.json` contains 73 primary word entries from the September 2026
KRDict export, retaining every homonym and sense for its selected headwords.
English equivalents and the first example group per sense remain; WordForm,
RelatedForm and export metadata are omitted. Attribution: National Institute of
Korean Language, Korean Basic Dictionary, [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Three particle entries (86121/80341/80343) extend `krdict-grammar-labels.json`
under the same attribution/adaptations; every earlier entry is retained. The
catalog now has 277 canonical forms, 349 source IDs and 350 grammar fixture
entries. Homonymous bound-noun/adverb entries remain lexical alternatives and
are excluded from particle lookup. The report retains two explicitly selected
있어서만치/만큼 example groups under the same attribution/license.

`kaist-extent.conllu` preserves complete byte-identical UD 2.15 KAIST development
sentences `MH2_0159-s121` and `M2TA_089-s30`, under the KAIST attribution/license
above. The tests require 필생토록 → 필생 and preserve lexical 그토록 gold;
they do not certify every candidate of every token in those sentences.
[The comparison](../../docs/extent-evaluation.json) records source/fixture hashes.


`krdict-approximation.json` contains 44 primary word entries from the September
2026 KRDict export, retaining all lexical homonyms/senses for selected heads.
English equivalents and the first example group per sense remain; WordForm,
RelatedForm and export metadata are omitted. Attribution: National Institute of
Korean Language, Korean Basic Dictionary, [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Suffix entry 88691 extends `krdict-grammar-labels.json` under the same
attribution/adaptations, preserving every earlier entry. The catalog now has
278 canonical forms, 350 source IDs and 351 grammar fixture entries.
[The review](../../docs/approximation-evaluation.json) retains selected example
groups from entries 88691/36231/68020/25578 under the same attribution/license.

`kaist-approximation.conllu` preserves the complete byte-identical UD 2.15 KAIST
development sentence `MH2_0159-s86`, under the KAIST attribution/license above.
The regression requires `id:MH2_0159-s86/17` 번쯤 → 번. The original jxc tag is
unchanged; the engine follows KRDict's suffix role. Neither annotation verifies
every candidate of the sentence. Source/fixture hashes are in the review.


`krdict-report-myeo.json` contains 44 primary word entries from the September
2026 KRDict export. Every selected lexical homonym/sense is retained, with
English equivalents and the first example group per sense; WordForm,
RelatedForm and export metadata are omitted. Attribution: National Institute of
Korean Language, Korean Basic Dictionary, [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Thirty-four source entries extend `krdict-grammar-labels.json` under the same
attribution/adaptations. Eighteen canonical labels bring the catalog to 296
forms, 384 source IDs and 385 grammar fixture entries, preserving every prior
entry. The [review](../../docs/report-myeo-evaluation.json) records source hashes
and selected stative/outer-particle examples under the same attribution/license.

`kaist-report-myeo.conllu` preserves complete byte-identical UD 2.15 development
sentences MH2_0169-s260, MH2_0169-s40 and MH2_0169-s516; `gsd-report-myeo.conllu`
preserves dev-s737, dev-s750 and dev-s926. They retain the KAIST/GSD source
attribution/licenses above. Six stable annotated groups cover 지원한다며,
필요하다면서, 모자란다면서도, 줄이라며, 현실이라며 and 극복하겠다며. No
sentence text, annotation or historical corpus baseline is rewritten.

`krdict-stative-report.json` retains 40 primary entries (all selected homonyms
and senses) from the September 2026 KRDict export by the National Institute
of Korean Language, under CC BY-SA 2.0 KR. It supports COV-019g auxiliary
reporting and dictionary/CLI/browser regressions. Changes: English equivalents
only, the first example group per sense, no WordForm/RelatedForm or export
metadata, and reformatted JSON. These are integration fixtures, not annotated
sentence gold. Source and license links are above.

`krdict-present-licenses.json` retains 39 primary entries and all selected
homonyms/senses from the September 2026 KRDict export by the National Institute
of Korean Language, under CC BY-SA 2.0 KR. It supports COV-017y / COV-019h
present-declarative class and prefinal tests. Nine further source entries extend
`krdict-grammar-labels.json` for ㄴ다/ㄴ다고/ㄴ다는/ㄴ다면 and the 는다면
expression homonym. Changes: English equivalents only, first example group per
sense, no WordForm/RelatedForm or export metadata, and reformatted JSON. Source
and license links are above. The catalog now has 296 canonical forms, 393 source
IDs and 394 grammar fixture entries. These fixtures verify source integration,
not independently annotated sentence analyses.

`gsd-present-licenses.conllu` retains two complete, byte-identical sentences
(dev-s153 and dev-s301) from the pinned GSD development corpus under the corpus
license described above. It preserves the annotated verbal groups while
rejecting omitted-copula present-declarative paths. The visit-context 들리다
spelling and the corpus POS tags are not corrected or certified as normative.
All six 들리다 dictionary entries, including the source redirect to 들르다,
remain in the corresponding lexical fixture; contextual spelling repair is
outside this change.


`krdict-report-ni.json` retains 53 primary entries and every selected homonym/sense
from the September 2026 KRDict export by the National Institute of Korean
Language, under CC BY-SA 2.0 KR. It supports COV-017z surprise and quoted -니
regressions. `krdict-grammar-labels.json` gains 24 grammar entries for the eight
new canonical components; the catalog now has 304 forms, 417 source IDs and 418
fixture entries. Changes: English equivalents only, first example group per
sense, no WordForm/RelatedForm or global metadata, exclude idiom subentries, and
reformat JSON. Source and license links are above. These are source-integration
fixtures, not independently annotated sentence gold.

`kaist-report-ni.conllu` retains complete, byte-identical development sentences
MH2_0169-s206 and MH2_0169-s628; `gsd-report-ni.conllu` retains dev-s74 from the
pinned corpora, under their respective corpus licenses described above. These
protect 따라가자니, 상대하자니 and 하신다니 without rewriting source spelling,
segmentation or POS labels. Their gold groups do not enumerate all alternatives.


`krdict-short-clauses.json` retains four additional lexical entries (내리다,
노력하다, 누구, 많다) and the unrelated suffix -단 (73350) as a negative source
control for COV-017ab; the tests reuse the 53-entry
`krdict-report-ni.json` fixture for the other selected lexical homonyms.
`krdict-grammar-labels.json` gains ten ending/expression entries for
단/는단/잔/냔/느냔/으냔/다간/다가는, excluding noun suffix 73350.
These excerpts are adapted from the September 2026 KRDict export by the National
Institute of Korean Language under CC BY-SA 2.0 KR. Changes: every selected
homonym/sense, English equivalents only, first example group per sense, omit
WordForm/RelatedForm/global metadata and idiom subentries, and reformat JSON.
Source/license links are above. The catalog now has 325 forms, 461 source IDs
and 462 grammar fixture entries; these are integration fixtures, not gold analyses.

`kaist-short-clauses.conllu` retains complete, byte-identical development
sentences MH2_0149-s11 and MH2_0169-s5 from the pinned KAIST corpus, under its
license described above. They protect 된단 and 노력했단 without rewriting
annotations, spelling or POS. Gold groups do not enumerate all valid alternatives.

`krdict-attachments.json` adds eleven lexical entries (가늘다, 긷다, both 크다
and 늦다 homonyms, 행복하다, both 아니하다 auxiliary classes, 듯하다 and 만하다) for COV-017aa. It preserves every selected sense,
English equivalent and the first example group, reusing the 53-entry
`krdict-report-ni.json` fixture. These are National Institute of Korean Language
Korean Basic Dictionary September 2026 texts under CC BY-SA 2.0 KR, with the same
attribution and license as the other KRDict fixtures.
`dictionary-attachments.json` is a separate source-linked judgment ledger for
the explicit dictionary conflict policy: its forbidden readings remain raw rule
hypotheses. See `docs/dictionary-attachments.md` for scope and exceptions.

`krdict-adverb-focus.json` contains 28 lexical entries for COV-018n, retaining
every selected homonym/sense, English equivalents and the first example group
from the pinned September 2026 KRDict export. WordForm/RelatedForm/global metadata
and idiom subentries are omitted. Attribute the National Institute of Korean
Language, Korean Basic Dictionary, under CC BY-SA 2.0 KR as above.
`kaist-adverb-focus.conllu` preserves complete development sentences
MH2_0069-s118 and MH2_0159-s76; `gsd-adverb-focus.conllu` preserves dev-s382,
dev-s750 and dev-s814. All are byte-identical to the pinned corpus sentences
and retain their original corpus licensing and annotations. Six ADV tokens
explicitly segment an adverb plus a focus particle.

`krdict-continuative-topic.json` contains 38 lexical entries for the COV-019i
auxiliary-topic regressions, projected from the pinned September 2026 National
Institute of Korean Language Korean Basic Dictionary export. It retains all
selected homonyms, senses, attachment notes, English translations and the first
example group per sense; forms, related entries and idiom subentries are omitted.
License: [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Six additional source example groups and their IDs/sense/group indices are
preserved in `docs/continuative-topic-evaluation.json`; joined test surfaces are
explicit transformations of spaced examples, not corpus gold or spelling advice.

`krdict-adjectival-question.json` contains 18 lexical entries for COV-017ac,
projected from the pinned September 2026 National Institute of Korean Language
Korean Basic Dictionary export. All selected homonyms, senses, attachment notes,
English translations and first example groups are retained; forms, related
entries and idiom subentries are omitted. License:
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
`gsd-adjectival-question.conllu` preserves the complete GSD development sentence
`dev-s820` byte-for-byte under the existing corpus attribution. It verifies that
뭐하냐는 retains its gold lemma and general 냐는 ending while a distinct
auxiliary adjectival-ending hypothesis is removed; no recall gain is claimed.

`krdict-uncertainty.json` contains 37 lexical entries for COV-017ad, projected
from the September 2026 National Institute of Korean Language Korean Basic
Dictionary export. All selected homonyms/senses, notes, English translations
and first example groups are retained; word/related forms and idiom subentries
are omitted. Six grammar entries (86488, 86615, 86689, 86719, 86693, 86721)
are added to `krdict-grammar-labels.json` under the same projection policy.
Source license: [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
`kaist-uncertainty.conllu` preserves complete KAIST development sentence
MH2_0159-s309 byte-for-byte under the existing corpus attribution. Token 16,
같을는지 / 같+을는지 / paa+ecs, now recovers its unchanged gold lemma.

`krdict-intention-connectives.json` contains 30 lexical entries for COV-017ae /
COV-019j, projected from the September 2026 NIKL Korean Basic Dictionary export.
All selected homonyms/senses, notes, English translations and first example
groups remain; word/related forms and idiom subentries are omitted. The grammar
fixture adds 18 source entries listed in `intention-connectives-evaluation.json`.
All projections use [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
`kaist-intention-connectives.conllu` and `gsd-intention-connectives.conllu` retain
complete development sentences MH2_0169-s336 and dev-s560 byte-for-byte under the
existing corpus attribution. KAIST 하려다 gains the intended 하다; GSD 갈려는데
matches annotated 갈다 incidentally, with the original sentence/tag preserved.

`krdict-result-connectives.json` contains 46 lexical entries for COV-017af /
COV-019k, projected from the September 2026 NIKL Korean Basic Dictionary export.
All selected homonyms/senses, notes, English translations and first example
groups remain; word/related forms and idiom subentries are omitted. Five new
entries join the existing -어다가 in the grammar fixture. Projections use
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
`kaist-result-connectives.conllu` retains complete development sentences
MH2_0169-s523 and MH2_0169-s307; `gsd-result-connectives.conllu` retains dev-s658,
dev-s837 and dev-s107 byte-for-byte under the existing corpus attribution.
The GSD directional look compounds are annotation matches, not evidence for a
generic result-transfer + 보다 auxiliary rule. Research is paraphrased in
`docs/result-connectives-evaluation.json`; no research PDF is redistributed.

`krdict-attachment-connectives.json` adds 모시다, 노래 and 노랗다 for
COV-017ag, reusing other lexical entries from `krdict-report-ni.json` and
`krdict-attachments.json`. It preserves every selected sense/usage note,
English translation and first example group from the September 2026 NIKL
export; word/related forms and idiom subentries are omitted, under
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The grammar fixture also adds expression -려는 (86688), keeping -으려는
(86717) selectable. The separate dictionary-policy ledger gains 122 cases
(70 required / 52 forbidden), including homonyms, component ownership and the
observed 노래다 ambiguity. All raw hypotheses and headword matches remain.

`krdict-nira.json` contains 51 lexical entries for COV-017ai/COV-020j from the
September 2026 Korean Basic Dictionary export. All sense/attachment notes and
English equivalents are retained, with one example group per sense. Attribution:
National Institute of Korean Language; license:
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Grammar entries 86126/86127/86128 are in `krdict-grammar-labels.json`.
`kaist-nira.conllu` retains the complete unchanged DEV sentences MH2_0159-s301
and MH2_0159-s305 and TRAIN sentence M2TA_084-s95, with the same upstream
attribution/license as the existing KAIST excerpts. The lexical/derived love
predicate, omitted nominal copula and consonant-final adjective are independently
tested. See the [source review](../../docs/nira-evaluation.json) for register,
negative/existential uncertainty and the separate dictionary-policy judgments.

`krdict-short-recipient.json` contains 30 lexical entries for COV-018o from the
September 2026 Korean Basic Dictionary export. It retains English equivalents,
all sense/attachment notes and one example group per sense. Attribution: National
Institute of Korean Language; license: [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
Grammar entries 66937 (게) and 66974 (게서) are in `krdict-grammar-labels.json`.
`kaist-short-recipient.conllu` preserves complete unchanged KAIST DEV sentence
M2TA_089-s64 and TRAIN sentences M2TA_083-s41, M2TA_087-s64 and MH2_0091-s39,
with the same upstream attribution/license as the existing KAIST excerpts. The
four explicit pronoun-particle tokens retain 내/네/제. Different 나 + 에게
annotations elsewhere are recorded as segmentation differences in the
[source review](../../docs/short-recipient-evaluation.json), not rewritten.

`krdict-auxiliary-dictionary.json` contains 32 lexical entries from the September
2026 Korean Basic Dictionary export for COV-019m. It retains English equivalents,
all sense/attachment notes and one example group per sense, excluding idiom/proverb
records that reuse lexical IDs. Attribution: National Institute of Korean Language;
license: [CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
`auxiliary-dictionary.json` records 86 per-entry policy judgments in 43 cases,
with stable IDs, exact roles/morphemes, source URLs and conflict ownership. These
judge dictionary evidence, not raw candidate validity or contextual sense ranking.
The source review and complete candidate comparison are in
[`auxiliary-dictionary-evaluation.json`](../../docs/auxiliary-dictionary-evaluation.json).
The older `krdict-auxiliary-classes.json` remains a separate supplemental fixture.

`krdict-ryeona.json` contains 76 lexical entries for COV-017ah / COV-019l from
the September 2026 NIKL Korean Basic Dictionary export. All selected homonyms,
senses, notes, English translations and first example groups remain; word/related
forms and idiom subentries are omitted, under
[CC BY-SA 2.0 KR](https://creativecommons.org/licenses/by-sa/2.0/kr/).
The grammar fixture adds question entries 79262/79263 and shortened expression
homonyms 86503/86715 with their original POS. `kaist-ryeona.conllu` preserves
complete UD 2.15 KAIST **test** sentence MH2_0010-s336 byte-for-byte, under the
existing corpus attribution/license. It is now targeted regression evidence,
not an independent test observation. Corpus 좋아지다 lacks a KRDict headword;
좋다 + 지다 supplies the independently tested dictionary-backed alternative.

`krdict-vocative.json` contains 31 lexical entries for COV-018p from the local
September 2026 Korean Basic Dictionary export (National Institute of Korean
Language), licensed under CC BY-SA 2.0 KR. Source IDs and definitions are retained;
non-English translations, related forms and word forms are omitted, with at most
one example group per sense. The grammar fixture adds 이여 (86621), 시여 (86091)
and 이시여 (86092); existing 아/야/여 source entries remain.

`kaist-vocative.conllu` contains two complete, unchanged UD Korean KAIST 2.15
sentences: development MH2_0159-s260 and training M2TA_091-s1, covering 검이여
and 젊은이여. Corpus attribution and CC BY-SA 4.0 licensing follow the pinned
KAIST source above. The development observation motivated this fix and is
regression evidence, not held-out evaluation. The source and output review is
`docs/vocative-evaluation.json`.

`krdict-eya.json` contains 29 lexical entries from the September 2026 Korean
Basic Dictionary export (National Institute of Korean Language, CC BY-SA 2.0 KR).
Selection preserves source IDs and definitions, keeps English translations and
at most one example group per sense, and omits related/word forms. The grammar
fixture adds the compound particle 에야 (86578).

`kaist-eya.conllu` preserves three complete UD Korean KAIST 2.15 sentences:
development MH2_0069-s77 (때에야만), MH2_0169-s288 (전에야), and training
MH2_0024-s42 (다음에야). KAIST attribution and CC BY-SA 4.0 licensing follow
the pinned source above. Corpus 때 + 에 + 야만 differs in granularity from the
program's split 때 + 에 + 야 + 만; source gold remains unchanged. The motivating
development miss is regression evidence, not a held-out measure. The NIKL compound
decomposition source and all source hashes are recorded in `docs/eya-evaluation.json`.

`krdict-ra-conditions.json` contains 27 lexical entries from the September 2026
Korean Basic Dictionary export (National Institute of Korean Language,
CC BY-SA 2.0 KR). It preserves IDs/definitions, English equivalents and at most
one example group per sense, omitting word/related forms. The grammar fixture
adds seven source entries for endings -라도/-라야/-라야만 and particles
(이)라야/(이)라야만, preserving their POS distinction.

`kaist-ra-conditions.conllu` preserves complete UD Korean KAIST 2.15 development
MH2_0149-s95 and training M2TA_087-s37 / MH2_0017-s181 sentences.
`gsd-ra-conditions.conllu` preserves complete UD Korean GSD 2.15 development
dev-s820. Attribution and licenses follow the pinned KAIST and GSD sources above.
These reused development observations are regression evidence. The GSD adapter
joins adjacent nouns in 자전거+도로+이+라도; its recovered copula group does not
establish contextual correctness over the existing particle analysis. No source
gold is rewritten. NIKL's compound decomposition and all source hashes appear in
`docs/ra-condition-evaluation.json`.

`krdict-kkaena.json` contains 22 primary lexical entries from the same September
2026 NIKL KRDict export under CC BY-SA 2.0 KR. IDs: 15983, 17204, 26525, 28633,
29970, 36672, 38264, 38536, 41471, 50523, 50525, 57305, 58161, 58272, 62332,
63406, 64717, 64718, 66140, 76201, 87847, 91736. Changes: retain the first sense,
English equivalents and one example group, omit WordForm/RelatedForm and global
metadata, exclude idiom subentries, and reformat JSON. Grammar entry 69715 is
added separately to `krdict-grammar-labels.json` with its sole sense and one
example group. The source-attested head 아씨 is absent from the full snapshot;
no fabricated entry fills that gap.

`kaist-kkaena.conllu` preserves the complete unchanged UD 2.15 KAIST **test**
sentence MH2_0110-s468, containing 족보깨나 → 족보 + 깨나. Source revision,
license and attribution are the KAIST ones listed above. This sentence was
inspected to develop COV-018s and is now an exposed regression fixture, not an
unseen accuracy test. No pinned baseline or source annotation was rewritten.

`krdict-core-case.json` contains 79 primary lexical entries from the pinned
September 2026 NIKL KRDict export (CC BY-SA 2.0 KR); exact IDs and source hashes
are recorded in `docs/core-case-evaluation.json`. Changes: first sense, English
equivalents and one example group retained, WordForm/RelatedForm and global
metadata omitted, primary words only, JSON reformatted. The 17 reviewed grammar
entries in `krdict-grammar-labels.json` retain all senses and example groups.
`krdict-expressive-hada.json` adds eight primary lexical entries (26838, 26841,
29719, 41145, 41561, 69511, 70073, 91168) using the same transformations and
license; the remaining policy heads are in the existing attachment fixtures.
The missing head 곧이 is intentionally not fabricated.

`kaist-core-case.conllu` preserves complete unchanged train sentences M2TA_076-s13
and MH2_0032-s14. `gsd-core-case.conllu` preserves complete unchanged development
sentences dev-s248, dev-s869, dev-s150 and dev-s393. Source revisions, licenses
and attribution are the UD 2.15 KAIST/GSD ones listed above. They are exposed
regressions, not unseen evaluation. The school-name 강원체고를 annotation and
partial 잘해서 recovery remain observations rather than correctness claims.
The 먹고싶은가를 stress snapshot history records its one new unknown predicate
hypothesis and retains all previous hashes/candidates; see the core-case report.

`krdict-source-particles.json` retains 36 primary lexical entries from the pinned
September 2026 NIKL KRDict export under CC BY-SA 2.0 KR. Exact IDs are in
`docs/source-particle-evaluation.json`. Changes: first sense, English equivalents
and one example group retained; WordForm/RelatedForm and global metadata omitted;
primary words only; JSON reformatted. The nine reviewed grammar entries in
`krdict-grammar-labels.json` retain all senses and example groups. Four source
compound entries are added; existing role/means and locative entries are expanded.

`kaist-source-particles.conllu` preserves complete unchanged development sentences
MH2_0169-s369 and MH2_0069-s91. `gsd-source-particles.conllu` preserves complete
unchanged development sentences dev-s266, dev-s703 and dev-s925. Source revisions,
licenses and attribution are the UD 2.15 KAIST/GSD ones listed above. These are
exposed regression fixtures, not unseen evaluation; split and bundled source
annotations are both retained without rewriting the corpus or frozen baselines.

`krdict-concessive-designation.json` retains 67 primary lexical entries from the
pinned September 2026 NIKL KRDict export under CC BY-SA 2.0 KR. Exact IDs appear
in `docs/concessive-designation-evaluation.json`. Changes: first sense, English
equivalents and one example group retained; WordForm/RelatedForm and global
metadata omitted; JSON reformatted. Eleven reviewed grammar entries are added to
`krdict-grammar-labels.json`, retaining all senses, attachment notes and examples.
Source-backed cases supplement the annotated corpus regressions: no target
particle annotation was found in the mined training/development data.

`krdict-concessive-endings.json` retains 50 primary lexical entries from
the pinned September 2026 NIKL KRDict export under CC BY-SA 2.0 KR. Exact IDs
appear in `docs/concessive-ending-evaluation.json`. Changes: first sense, English
equivalents and one example group retained; WordForm/RelatedForm and global
metadata omitted; JSON reformatted. Seven grammar entries added to
`krdict-grammar-labels.json` retain every sense, usage note and example group.

`kaist-concessive-endings.conllu` retains complete unchanged UD 2.15 training
sentences MH2_0021-s154, MH2_0066-s44, MH2_0091-s451, MH2_0092-s53 and
MH2_0092-s333. `gsd-concessive-endings.conllu` retains complete unchanged training
sentence train-s3829. Dataset revisions, licenses and attribution are the
KAIST/GSD ones listed above. These are exposed regression fixtures, not unseen
evaluation; original annotations and frozen corpus baselines remain unchanged.

`krdict-connective-copulas.json` retains 51 primary lexical entries from the pinned
September 2026 NIKL KRDict export under CC BY-SA 2.0 KR. Exact IDs are recorded in
`docs/connective-copula-evaluation.json`. Changes: first sense, English equivalents
and one example group retained; WordForm/RelatedForm and global metadata omitted;
JSON reformatted. Source/license links are above. No new grammar catalog form is
introduced: this tests composition of existing 어서 and 이다 components.

`kaist-connective-copulas.conllu` preserves complete unchanged UD 2.15 training
sentences M2TA_076-s9, M2TA_087-s148 and MH2_0024-s192; the GSD counterpart
preserves train-s130, train-s1439 and train-s3861. Revisions, attribution and
CC BY-SA 4.0 terms above apply. They are exposed regression evidence, not unseen
accuracy measurements. The report separately records incidental test-row exposure.

`krdict-adverb-copulas.json` retains 38 primary entries from the pinned September
2026 NIKL KRDict export, under CC BY-SA 2.0 KR. Exact IDs are recorded in
`docs/adverb-copula-evaluation.json`. Changes: all senses/notes/example groups and
English equivalents retained, WordForm/RelatedForm and global metadata omitted,
JSON reformatted. Source and license links are above. It includes the three
question endings reviewed with the adverb/copula attachment scope.

`kaist-adverb-copulas.conllu` preserves the complete unchanged training sentence
MH2_0045-s446. The GSD counterpart preserves train-s72, train-s122, train-s969,
train-s2154, train-s2648, train-s3031, train-s4389 and development dev-s524.
Revisions, attribution and CC BY-SA 4.0 terms above apply. These are exposed
regressions; role-specific tests are distinct from grouped-lemma recall.

`krdict-hada-complex.json` contains 22 primary KRDict word entries selected from
the pinned local LMF export for COV-021c. It retains all senses, notes, examples
and pronunciation/inflection forms; translations are restricted to English and
RelatedForm links are omitted. Same-number idiom entries are not substituted for
their lexical heads. `kaist-hada-complex.conllu` preserves the full training
sentence MH2_0014-s209 from the pinned UD Korean-Kaist revision, including
값하고. No annotation was rewritten and no shortened corpus example is claimed.
See [the source report](../../docs/hada-complex-evaluation.json) and the existing
dictionary/corpus attribution and licensing notices above.

`krdict-comparison-particles.json` contains 45 primary KRDict word entries from
NIKL's pinned September 2026 export under CC BY-SA 2.0 KR for COV-018w.
It retains all senses, examples, notes and forms, including all homonyms of the
selected lexical heads. Translations are restricted to English; RelatedForm
links and same-ID idiom records are excluded. The three particle entries
22776, 48410 and 68275 supply the source examples and attachment notes.
Exact IDs, fixture hash, sense-to-case mappings and limitations are recorded in
[the audit](../../docs/comparison-particle-audit.json). These examples are exposed
regression evidence, not unseen evaluation or contextual sense annotations.

`krdict-additive-particles.json` selects 59 primary word entries from NIKL's
pinned September 2026 KRDict export (CC BY-SA 2.0 KR). All senses, notes,
examples and forms remain; equivalents are English only and RelatedForm is
omitted. Same-ID idioms are excluded. 나라 supports an unresolved segmentation
probe; the source's proper name 승규 is absent and is not fabricated in the
fixture. `kaist-additive-particles.conllu` preserves ten complete training
sentences from the pinned KAIST revision, with no annotation edits. The corpus
attribution and CC BY-SA 4.0 license above apply. The thesis PDF used for
additional grammar evidence is not redistributed. Exact source IDs, hashes,
sentence/token IDs and four target gains are in the
[review](../../docs/additive-particle-evaluation.json).

`krdict-comparison-case.json` contains 25 primary word entries from the same
pinned NIKL Korean Basic Dictionary export. All senses, notes, forms and examples
are retained, with English equivalents only and RelatedForm omitted; same-number
idioms are excluded. The dictionary's attribution and reuse terms above apply.
모스크바 and 로스앤젤레스 have no primary headword entries in this snapshot and
remain explicit dictionary-coverage omissions. `kaist-comparison-case.conllu`
preserves six complete training sentences under the KAIST attribution/license
above. Five comparison targets are correctly spelled; 커뮤니케이션에서어럼 and
the unrelated 원리을 remain verbatim source observations. No annotation repairs
were made. The NIKL teacher-training PDF is cited, not redistributed. See the
[source and individual-case evaluation](../../docs/comparison-case-evaluation.json).

`krdict-llachimyeon.json` selects 68 primary word entries from the pinned NIKL
Korean Basic Dictionary export. All senses, notes, examples and forms remain,
with English equivalents only and RelatedForm omitted. The existing dictionary
attribution and reuse terms above apply. The grammar-source fixture gains
86489/86616; the general attachment fixture gains 예쁘다 and five 지다 homonyms
for class-conflict and class-reset checks.

`kaist-llachimyeon.conllu` preserves two full training sentences under the KAIST
attribution and license above. No spelling, tags or gold rows were rewritten.
The NIKL 2006 grammar answer and 2007 spelling guide are linked rather than
redistributed. See the [source review](../../docs/llachimyeon-evaluation.json).

`krdict-necessity.json` selects 79 primary word entries from the pinned NIKL
Korean Basic Dictionary export, under its attribution and reuse terms above.
All senses, notes, examples and forms remain; equivalents are English only and
RelatedForm is omitted. The ending sources are 85762/85772, also added to the
grammar-source fixture; 70070 preserves the distinct restrictive particle.
되돌려받다 has no primary headword in this export and is not fabricated.

`kaist-necessity-search.conllu` preserves one complete KAIST training sentence
under the corpus attribution and license above. Its 못하다고밖에 annotation
is a quoted clause plus particle, recovered by COV-018z; it is not a necessity-ending
example. No annotated necessity-ending target was found in the training search.
The NIKL spelling guide and online answer are linked rather than redistributed.
See the [source and candidate review](../../docs/necessity-ending-evaluation.json).

`krdict-quoted-bakke.json` contains 53 primary word entries and nine selected
grammar-expression entries from the pinned NIKL Korean Basic Dictionary export.
The dictionary attribution and reuse terms above apply. All senses, notes,
forms and examples remain, with English equivalents only and RelatedForm omitted;
same-number idioms are excluded. The grammar-source fixture also gains 87443/87444.
The existing attachment fixture supplies 읽다 for the separate dictionary-policy
negative. No required raw headword is missing from this fixture.

This batch reuses the complete `kaist-necessity-search.conllu` discovery sentence,
without editing its annotation. Its reported-clause target now matches. The
frozen KAIST development gain is recorded by stable ID in the
[review](../../docs/quoted-bakke-evaluation.json), not inserted into training data.

`krdict-copular-class.json` is an adapted excerpt of the September 2026 official
KRDict LMF export, National Institute of Korean Language, **CC BY-SA 2.0 KR**.
It retains all senses, attachment notes, examples and word forms for 53 primary
word/grammar-expression entries; English equivalents only, no RelatedForm,
idiom subentries or global export metadata. Source and license links are at the
start of this file. IDs: 15078, 15983, 26847, 26878, 45653, 45654, 45655, 58272, 59531, 61190, 61953, 62091, 62171, 62249, 68832, 69044, 69108, 70060, 72481, 73964, 75476, 76427, 77243, 78220, 78807, 79275, 80211, 80212, 80230, 80237, 80246, 80698, 81469, 81584, 81809, 82122, 82217, 82259, 85121, 86057, 86118, 86232, 86297, 86367, 86370, 86500, 86501, 86509, 86511, 86519, 86638, 91162, 92457.
Source file hashes and review scope are in
[the copular attachment evaluation](../../docs/copular-class-evaluation.json).
The companion policy judgments are agent-authored, with independent Korean
review pending; the fixture itself is source text, not sentence gold.

`krdict-danda.json` contains 111 primary word/selected grammar-expression
entries from the pinned September 2026 NIKL Korean Basic Dictionary export,
under **CC BY-SA 2.0 KR** and the attribution/reuse links above. Full senses,
attachment notes, examples and forms are retained; equivalents are English only,
RelatedForm and same-number idioms are omitted. Fourteen ending sources also
appear in `krdict-grammar-labels.json`. The invented raw lexical hypothesis
뿍다 has no dictionary entry; dictionary tests keep that omission explicit.

`kaist-danda.conllu` and `gsd-danda.conllu` preserve respectively twelve and one
complete training sentences from the pinned corpora, under their attribution
and licenses above. No gold rows, spelling or tags were rewritten; KAIST's
OrigLemma for 않단다 remains intact. Frozen evaluation gains remain in the
[evaluation report](../../docs/danda-evaluation.json), not training fixtures.

`krdict-daji.json` contains 176 primary word/selected grammar-expression
entries from the pinned September 2026 NIKL Korean Basic Dictionary export,
under **CC BY-SA 2.0 KR** and the attribution/reuse links above. Full senses,
attachment notes, examples and forms are retained; equivalents are English only,
RelatedForm and same-number idioms are omitted. Nineteen confirmation-family
sources also appear in `krdict-grammar-labels.json`. No required headword is
missing. Synthetic negative heads are not invented in the dictionary fixture.

`gsd-daji.conllu` preserves the complete training sentence `train-s4336` under
the GSD attribution/license above. Its 좋+다+지+요 / VA+EC+VX+EC annotation
is unchanged and converts to 좋다 + 지다; this is an explicit annotation/model
mismatch, not a newly recovered gold target. See the
[evaluation report](../../docs/daji-evaluation.json) for frozen corpus results.

`krdict-dajiman.json` contains 99 primary word/selected grammar-expression
entries from the pinned September 2026 NIKL Korean Basic Dictionary export,
under **CC BY-SA 2.0 KR** and the attribution/reuse links above. Full senses,
attachment notes, examples and forms remain; equivalents are English only,
RelatedForm and same-number idioms are omitted. Ten contrasting-report sources
also appear in `krdict-grammar-labels.json`. No required headword is missing.

`kaist-dajiman.conllu` preserves five complete training sentences from the
pinned KAIST corpus, under its attribution/license above. Four targets use
contrasting reported endings; 나라지만 retains the neighboring 나라 + 이다 + 지만
annotation. OrigLemma on 있다지만, spelling and all gold tags remain unchanged.
The [evaluation](../../docs/dajiman-evaluation.json) records two frozen test gains
separately; no baseline or held-out source row was moved into training fixtures.

`krdict-jimaneun.json` contains 57 primary word entries from the pinned September
2026 NIKL Korean Basic Dictionary export, under **CC BY-SA 2.0 KR** with the
attribution and links above. Full senses, notes, examples and forms remain;
equivalents are English only, RelatedForm and same-number idioms are omitted.
The new 지마는 source also appears in `krdict-grammar-labels.json`.

`kaist-jimaneun.conllu` preserves all six complete training sentences containing
지마는 in the pinned KAIST corpus, under the corpus attribution/license above.
Original spelling, lemmas, tags and OrigLemma remain, including the differing
높으시지마는 → 높+으시+지+만 annotation. These targets already matched at the
lemma level. [The evaluation](../../docs/jimaneun-evaluation.json) distinguishes
that result from the new dictionary-based ending structure.

`krdict-danikka.json` contains 157 primary word/selected grammar-expression
entries from the pinned September 2026 NIKL Korean Basic Dictionary export,
under **CC BY-SA 2.0 KR**, with the attribution and links above. All senses,
notes, examples and forms remain; equivalents are English only, RelatedForm
and same-number idioms are omitted. The 47 family sources also appear in
`krdict-grammar-labels.json`; their original conflicting notes and typographical
examples remain unchanged. [The source report](../../docs/danikka-evaluation.json)
records them separately from authored judgments.

`kaist-danikka.conllu` preserves two complete unchanged training sentences from
the pinned KAIST corpus, under the corpus attribution/license above. Their
말하자니까 and 미워하자니까 annotations support the two newly recovered lemma
groups. No held-out baseline or source annotation was replaced.

`krdict-continuation-aux.json` contains 94 full primary KRDict entries from the
same September 2026 export (National Institute of Korean Language, CC BY-SA
2.0 KR). All senses, notes, examples and forms are retained; equivalents are
limited to English, RelatedForm/global metadata and same-ID idioms are omitted.
`continuation-aux-sources.json` retains the seven reviewed entries as normalized
importer output and identifies all 44 source example groups, their exact spaced
excerpts, and the separate joined-input ledger cases. These dictionary-derived
parts have the same source license. The review annotations are project-authored;
they do not resolve contextual senses or certify spacing. Source file hashes
are in [the evaluation](../../docs/continuation-aux-evaluation.json).

`kaist-continuation-aux.conllu` contains twelve complete, unchanged sentences
from the pinned KAIST **training** partition. The source fixture lists the exact
sentence/token IDs and original annotations. It covers two joined examples
per 가/오/나가/나/내/버리 auxiliary; no matching joined 치우 token was found
with the documented ecx+px selection criterion. This is regression coverage,
not a held-out benchmark. The KAIST CC BY-SA 4.0 attribution above applies.

`krdict-request-aux.json` contains 109 complete primary entries from the same
September 2026 KRDict export (National Institute of Korean Language, CC BY-SA
2.0 KR). All senses, notes, forms and examples are retained; equivalents are
English only, and RelatedForm/global metadata and same-ID idioms are omitted.
`request-aux-sources.json` retains 54 normalized source entries, 29 exact
excerpts (including every example from 달다 and the three 아/어/여 달다
expressions), plus authored corpus dispositions. The dictionary-derived text
has the same source license; the review annotations are project-authored.
Source hashes are in [the review](../../docs/request-aux-evaluation.json).

`kaist-request-aux.conllu` and `gsd-request-aux.conllu` retain five and four
complete, unchanged training sentences from the pinned corpora. Seven target
tokens retain their matching request groups. 매단 and 나달은 retain original
auxiliary annotations despite the conflicting context; tests record the two
mismatches instead of rewriting gold or broadening the request paradigm. These
fixtures use the corpus attribution and CC BY-SA 4.0 license above.

`krdict-short-reports.json` preserves 148 full primary word/grammar-expression
entries from the pinned September 2026 NIKL Korean Basic Dictionary export,
under **CC BY-SA 2.0 KR**, with the attribution and links above. All senses,
notes, forms and examples remain; equivalents are English-only; RelatedForm
and same-ID idioms are omitted. `short-reports-sources.json` preserves the 28
family entries and 59 exact example excerpts sampling all 51 senses. Spaces
are removed only when feeding a cited auxiliary phrase to word-level tests.
Attachment-note/example conflicts remain unchanged. Eight ending sources and
twenty expression sources are distinguished in the coverage report.

`gsd-short-reports.conllu` preserves two complete unchanged pinned GSD training
sentences (train-s1824 and train-s4304), under the corpus attribution/license
above. Their 쓴대요 and 한대요 annotations support the new lemma matches.
No held-out baseline, annotation or source spelling was rewritten.

`krdict-neura.json` preserves 70 full primary entries from the pinned September
2026 NIKL Korean Basic Dictionary export under **CC BY-SA 2.0 KR**, with the
attribution and links above. All senses, notes, forms and examples remain;
equivalents are English only; RelatedForm and same-ID idioms are omitted.
`neura-sources.json` preserves both ending entries and all eight source-example
groups, linked to exact candidate cases. The grammar-label fixture includes
both ending sources. The evaluation cites additional NIKL grammar research
and consultations separately from this dictionary export.

`kaist-neura.conllu` and `gsd-neura.conllu` preserve eight and two complete
unchanged training sentences, respectively, under the corpus attribution and
licenses above. GSD's 떠+시+느라 annotation and unrelated 동그래진다/늘릴라고
mismatches remain exactly as published; no source gold or frozen baseline was
rewritten to accommodate the implementation.

`krdict-ryeo-expressions.json` preserves 129 full primary entries from the
pinned September 2026 NIKL Korean Basic Dictionary export, under **CC BY-SA
2.0 KR**, with the attribution and links above. All senses, notes, forms and
examples remain; equivalents are English-only, RelatedForm and same-ID idioms
are omitted. `ryeo-expressions-sources.json` preserves fourteen normalized
family entries, twenty senses and all 82 example groups, each linked to an
exact excerpt judgment. The two 어미 assumption entries remain distinct from
the twelve 품사 없음 shortened expressions. The raw-only 유학가다 example
has no headword in this snapshot; an unknown-headword regression also remains
raw-only. Source hashes and the candidate queue are recorded in
[the evaluation](../../docs/ryeo-expressions-evaluation.json).

`kaist-ryeo-expressions.conllu` and `gsd-ryeo-expressions.conllu` preserve seven
and one complete, unchanged sentences from the pinned **training** partitions,
under the corpus attribution and CC BY-SA 4.0 license above. Selection scans
for the six endings at the end of each surface word; -려니와 is a different
form and was not included. Six KAIST targets and one GSD target gain a match.
The original 재견되려던 / 재건+되+려던 spelling mismatch, 상점이고 gold
without a copula, and the Matsunaga-name annotation 마+쓰+나가 remain unchanged.
No source annotation or held-out baseline is rewritten.

`krdict-hieut-compatibility.json` preserves 136 full primary NIKL Korean Basic
Dictionary entries from the pinned September 2026 export, under **CC BY-SA
2.0 KR**, with the attribution and links above. All senses, notes, forms and
examples are retained; equivalents are English-only and RelatedForm/same-ID
idioms are omitted. `hieut-compatibility-sources.json` preserves the 116 native
single-final-ㅎ verb/adjective/auxiliary entries and their written 니 dispositions:
46 regular, 66 irregular, four unknown. These are spelling-profile dispositions,
not certification of every sense or attachment in each entry. Source POS labels,
including 땡그랗다 as 동사, remain unchanged.

The `hieut-compat-*` cases in `dictionary-attachments.json` are scoped filter
judgments: every required and forbidden path exists both raw and under headword
filtering. Compatible filtering retains 175 and rejects 151. Four sources without
usable written forms retain unknown hypotheses. Synthetic homonym and competing
path tests are labeled as contract tests, not invented Korean dictionary evidence.

`kaist-hieut-compatibility.conllu` and `gsd-hieut-compatibility.conllu` preserve
three and four complete unchanged **training** sentences, respectively, under
the corpus attribution and CC BY-SA 4.0 license above. Seven original gold groups
survive compatible filtering. The unrelated 못한다 → 못+하다 mismatch remains.
The four frozen full-corpus reports are unchanged. Sixteen optimization snapshots
add optional spelling metadata; each retains its previous hash and independently
verifies that removing only the new field reproduces the complete old output.

`krdict-digeut-siot.json` contains 138 full primary KRDict entries with English
translations for COV-021e. `digeut-siot-sources.json` preserves the normalized
124-entry ㄷ/ㅅ inventory and individually reviewed written 니 dispositions:
65 regular, 54 irregular, five unknown. Homonymous 걷다 and 묻다 entries have
separate paradigms. Both files retain the NIKL attribution and CC BY-SA 2.0 KR
source terms. Other-language equivalents and related entries are omitted;
senses, notes, forms and example groups of each primary entry remain intact.

The 347 `ds-compat-*` policy cases in `dictionary-attachments.json` require
197 retained and 150 conflicting paths. All are generated raw and retained by
headword-only filtering. These judgments test lexical spelling evidence; unknown
entries remain unjudged linguistically. `digeut_siot.rs` separately tests every
source entry and both paradigms, real homonyms and mixed spelling-class owners.
`kaist-digeut-siot.conllu` and `gsd-digeut-siot.conllu` preserve eight complete
training sentences whose target lemma groups survive compatible filtering.
Four optimization snapshots add only ㄷ/ㅅ metadata; their previous hashes and
pre-existing ㅎ requirements are checked separately from the full new JSON hash.

`krdict-bieup.json` retains 459 full primary KRDict entries, with English
equivalents, for COV-021f. `bieup-sources.json` preserves the 443 native single-ㅂ
predicate entries, their original written forms and all senses/notes/examples,
plus reviewed regular/irregular/unknown profiles. Attribution: NIKL Korean Basic
Dictionary, September 2026; source material is CC BY-SA 2.0 KR. Related entries
and other-language equivalents are omitted. Surrounding form whitespace remains
in the source even though classification trims it.

The 1,087 `bieup-compat-*` dictionary-policy judgments preserve 586 paths and
reject 501 known class conflicts; all remain available raw and with headword-only
filtering. The 36 `bieup-written-*` raw judgments separately require 18 finite
오 spellings and forbid 18 wrong 우/오 counterparts. `bieup.rs` checks each native
entry independently, real homonyms, ownership through auxiliaries/copulas and
fixed -답다, and all 1,674 written 활용 forms. The sole source mismatch
얃잡는 under 얕잡다 (67256) is kept and tracked explicitly. No correction is
inserted into the source fixture or the engine.

`kaist-bieup.conllu` and `gsd-bieup.conllu` preserve eight complete training
sentences and their original annotations. Their target groups survive compatible
filtering. One optimization snapshot adds only ㅂ metadata and tests its prior
hash after removing that metadata; existing ㅎ/ㄷ/ㅅ evidence is preserved.

`krdict-polite.json` retains 48 complete primary entries, with English
equivalents, for COV-017az's basic (으)오/(으)옵 prefinal and the final 리다
bundle. `polite-sources.json` preserves four normalized grammar entries
(86107–86110), all 16 example groups and upstream file hashes. Attribution:
NIKL Korean Basic Dictionary, September 2026; CC BY-SA 2.0 KR. Related forms
and non-English equivalents are omitted; original notes/examples remain intact.
The grammar-label fixture adds complete entries 86107/86108 under this policy.

The 133 `polite-*` judgments require 93 paths and forbid 40 exact paths.
Ten tokens are direct native attestations; remaining positive combinations are
source-backed morphological inferences. No annotated corpus token is invented:
none of the six pinned corpus files explicitly tags these audited forms EP/ep.
The source audit records this narrower claim and the remaining named paradigms.
Canonical 으리다 has no primary entry in the pinned KRDict export; its teaching
label links NIKL's 1998 source article without fabricating a dictionary ID.
The 도와주었다 snapshot gains exactly three raw polite hypotheses; its original
full hash and historical spelling projections remain executable regressions.

`humble-sources.json` tracks five direct primary tokens for the distinct
사오/사옵 and 삽 paradigms, including retained ㄹ in `알사옵니다`, verified
visually in the original EBS PDF. The 130 `humble-*` cases require 96 exact
paths and forbid 34; inferred matrices remain separate from source examples.
`krdict-humble.json` preserves 30 complete primary lexical entries with English
equivalents, all senses/forms/notes/example groups and the KRDict CC BY-SA 2.0 KR
attribution. Grammar labels cite actual 우리말샘 pages without manufacturing
KRDict IDs. These regressions test raw recovery, both dictionary policies,
NFD, spelling/auxiliary/derivation ownership, browser references and exports;
unjudged additions and remaining licenses stay visible in
`docs/humble-evaluation.json` and COV-017az.

`gsd-polite-annotation-conflict.conllu` copies the complete, unchanged frozen
GSD test sentence `test-s188` under its existing corpus attribution/license
above. Its 내쉬와 row has original `VV+EC+VX+EC` tags in a proper-name-looking
context. Basic polite recovery adds a partial 내쉬다 match, while the annotated
two-lemma group remains unrecovered. The test preserves this disagreement and
the nominal 내쉬 + 와 alternative; it does not certify the new partial match
as a contextually correct analysis or repair the gold annotation.

`optsi-sources.json` records four direct primary tokens and attachment notes for
bundled (으)옵시 and 사옵시. The 167 `optsi-*` cases require 132 exact paths
and forbid 35; the inferred following-ending matrix is not contextual gold.
`krdict-optsi.json` preserves 42 complete primary lexical entries with English
equivalents under the KRDict CC BY-SA 2.0 KR attribution above. Grammar references
point to actual 우리말샘 entries instead of fabricated KRDict IDs. Tests cover
NFD/identity, raw and both dictionary-filter results, spelling-owner indices,
auxiliary/답다/copula composition, reference links and browser JSON export parity.
`docs/optsi-draft-corrections.json` preserves the draft confusion between the
past-permitting rhetorical 으려고 sense and the narrower intention construction.
Earlier committed judgments are unchanged. COV-017az remains incomplete.

`jaop-sources.json` records 24 direct primary tokens for the restricted modern
자오/자옵, consonant-following 잡, bundled 자옵시, and 나이다 ending. The
336 stable `jaop-*` cases require 154 paths and forbid 182 exact paths. The
2010 authors' lexical-subset review bounds segmented recovery to 듣다/묻다/
받다/좇다; historical coda distributions and arbitrary compounds are not
generalized. The full KRDict predicates 듣잡다/받잡다 remain independent
alternatives. `krdict-jaop.json` preserves 69 complete native entries, English
equivalents only, under the KRDict attribution and CC BY-SA 2.0 KR license above.
Eight primary grammar pages have recorded hashes and paraphrased attachment
notes; reference-only labels have no manufactured KRDict IDs.

Ten dictionary-policy cases add seven required and three forbidden readings.
They keep bare existential/honorific heads and source-listed intervening
prefinals, rejecting known bare adjectives with 나이다. The uncommitted draft
correction in `docs/jaop-draft-corrections.json` replaces a negative 멀다 scope
that incorrectly included its verb homonym. Eighteen earlier-prefinal negatives
use correctly spelled ㄷ/harmony boundaries to isolate the attachment-order
restriction; their original drafts remain in the correction log. Separate entry assessments preserve
that verb while rejecting its adjective entry. The frozen 하나이다 ambiguity
is tracked individually in `docs/jaop-evaluation.json` and tested without
replacing the annotated 하나 + 이 + 다 reading. Unjudged raw hypotheses and
contextual register remain unresolved; this is not a precision certification.

`naikka-sources.json` records eight direct tokens and four hashed NIKL primary
entries for 나이까, 옵나이까, 으옵나이까 and 사옵나이까. The 147 stable
`naikka-*` cases require 118 exact paths and forbid 29, with eleven separate
dictionary-policy cases (eight required, three forbidden). `krdict-naikka.json`
preserves 58 complete lexical entries with English equivalents under the native
KRDict attribution and CC BY-SA 2.0 KR policy above. The reference-only question
label has no fabricated KRDict entry. Bare lexical adjective conflicts preserve
verbal homonyms and unknown provider classes, while prefinal, auxiliary, copula
and fixed 답다 spelling ownership remain distinct.

`docs/naikka-draft-corrections.json` retains the uncommitted confusion between
basic politeness and earlier subject-honorific bundles: 하왔나이까 must not
gain 으옵 + 었 through this reviewed modern order; 했으옵나이까 tests the
supported opposite order. Previously committed judgments are unchanged. No
annotated corpus example is fabricated when the pinned corpora contain no
나이까 token. Structural tests do not establish contextual register correctness.

`krdict-rikka.json` and `rikka-sources.json` cover COV-017az’s literary
`-(으)리까` questions and explicit polite/humble combinations. The 64 full native
entries preserve source forms, notes, all senses/example groups and English
translations; only RelatedForm and other translation languages are omitted.
Seven separately identified primary senses supply eleven direct tokens. The
172 stable `rikka-*` cases contain 137 required and 35 forbidden paths; ten
compatible-filter cases contain seven required and three forbidden paths.
Adjective/copula classes differ from bare `나이까`, `ㄹ` stays before `리까`,
and fixed `답다` follows its vowel-boundary spelling. Polite `오/으오/사오`
components and spelling ownership remain separate from the final question.
`rikka-corpus-targets.json` saves ten actual annotated base + `까지` rows and
baseline outputs. Their `리까` substring crosses a morpheme boundary; they
are preservation tests, not gold for the new question. The six possible novel
question spans remain unannotated; `리까요` and omitted-copula polite-prefinal
paths remain separately open. See the [baseline source audit](../../docs/rikka-source-audit.json).
