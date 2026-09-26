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
