# Grammar coverage

Use the [coverage completion checklist](coverage-checklist.md) to track open
families, priorities, regression requirements, and release completion criteria.

The runtime grammar is authored in Rust, with no learned weights or corpus answer
lookup table. `src/grammar.rs` holds endings and spelling transformations;
`src/engine.rs` composes them. A reverse suffix trie indexes terminal rules.

| Family | Covered examples |
| --- | --- |
| Regular predicates | 먹고, 먹지만, 먹는데, 먹기, 가는, 간다 |
| Consonant attachment | 갑니다, 삽니다, 먹습니다, 간, 갈, 감, 삶 |
| 아/어 contractions | 먹어, 잡아, 봐, 줘, 돼, 마셔 |
| 하 / 푸 / ㅡ | 해, 하여, 퍼, 아파, 써, 커 |
| ㄷ / ㅅ / ㅂ | 들어, 들으면, 지어, 지으면, 추워, 추운, 도와 |
| ㅎ / 르 / 러 | 빨개, 빨간, 그래, 그러면, 몰라, 불러, 이르러 |
| ㄹ deletion | 사는, 삽니다, 사세요, 사니까, 사느냐 |
| Prefinal order | honorific → past (up to twice) → 겠 → 더 → terminal |
| Ending allomorphs | 먹으리라 / 가리라; interrogative 먹니 / connective 먹으니 |
| Copulas | 학생입니다, 학생이었다, 의사였다, 의사예요, 학생이에요 |
| Particle chains | 학교에서는, 학교에서만은, 사람만으로도, 길로 |
| Nominal plural suffix | 지식인들, 지식인들을, 친구들은, 지식인들이다 |
| Nominalized/embedded predicates | 먹기를, 먹음은, 있는가를, 것임을 |
| Attached auxiliaries | 먹어봤어요, 먹고있다, 하지않았다, 먹어보고있다, 먹어야한다 |
| Contracted nominals/pronouns | 내가, 제가, 누가, 내, 게, 건, 걸 |

Prefinal traversal decreases grammatical stage or consumes a past-marker slot.
Particle traversal consumes input with finite ordering rules. Auxiliary analysis
stores shared links between shorter input prefixes, reuses equal suffix recoveries,
and expands final paths iteratively. It does not cache copies of entire chains.
There is no arbitrary search-depth, beam-width,
or candidate-count cutoff. Distinct analyses are materialized, so termination
does not imply constant cost.

Lexical membership in an irregular class remains a hypothesis. For example,
`들어` admits `들다` and `듣다`. Some generated stems may not exist in dictionaries.
Rules enforce spelling boundaries and the implemented morphotactics, not lexical
existence. Corpus segmentation may also disagree with preserved vocabulary units.
Joined auxiliary input is analyzed morphologically, including some nonstandard
spacing; this does not certify that writing the components together is correct.

Known gaps include contracted 하 aspiration (피케), broad adverbial derivation
(같이, 없이, 달리), rarer endings/particle combinations, and foreign spelling
whose pronunciation determines particle allomorphs. Evaluation reports retain
measured misses and separately count unsupported annotations.

Nominal plural [-들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74906)
is a `suffix` morpheme, separate from a lemma or particle. One plural slot is
recognized before particles or a copula, and bare plurals are supported. The
unsplit alternative remains available (e.g. 아들 is also a lexical noun).
Particle allomorphs are checked against the plural surface, so 지식인들을
recovers 지식인 + 들 + 을 but 지식인들를 does not recover that path.
This rule does not implement the separate distributive particle 들 after
adverbs/endings or general derivational suffix analysis.

Background: [Korean UD conventions](https://universaldependencies.org/ko/index.html),
[Lovit's rule-based lemmatization explanation](https://lovit.github.io/nlp/2018/06/07/lemmatizer/),
and [conjugation boundaries](https://lovit.github.io/nlp/2019/01/22/trained_kor_lemmatizer/).
This implementation does not import their code, dictionaries, or extracted rules.

## Candidate correctness audit

`tests/candidate_correctness.rs` specifies required and forbidden recoveries
independently of the reverse engine. Cases are manually authored spelling
constraints, not generated forward/inverse round trips or dictionary blacklists.

* Stem-final ㄹ must drop at the relevant ㄴ/ㅂ/ㅅ and -오 boundaries. The suite
  checks 살다, 알다, 만들다, and 놀다 across endings and tests retained ㄹ at
  non-triggering boundaries. For example, 사니까 recovers 살다, while 살니까
  cannot recover that lemma. Attached consonants and ㄷ irregulars have separate
  boundary checks. This follows the National Institute of Korean Language's
  [orthography Article 18](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001&regltn_no=222)
  and [explanation of ㄹ deletion](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=319173).
* Copular 이 remains part of the recovered stem. 학생이라고 retains the group
  학생 + 이다 and cannot generate 학생다 by stripping 이라고. Zero copulas
  after vowels and the negative copula 아니다 remain available. In particular,
  라서 is restricted to copular contexts; it cannot recover 가다 from 가라서.
  NIKL documents this restriction in its
  [discussion of 이라서 and 아니라서](https://www.korean.go.kr/nkview/nklife/1996_4/6_10.html).
  The separate imperative (으)라 family still licenses 먹으라고 and 가라고.
* Ambiguous 들어 → 들다/듣다 and 사는 → 사다/살다, and unchanged hypotheses,
  remain available. A forbidden recovery does not imply that an entire input
  token has no valid nominal or other interpretation.

The second audit adds these constraints and preservation checks:

* The ㅂ rule distinguishes 도와/고와 from 도워/고워 for 돕다/곱다 before
  아/어-family endings and past markers. Both stems still use 우 before (으)
  endings, as in 도우면 and 고우니. Regular 도우다/고우다 hypotheses remain
  available for 도워/고워. See NIKL's
  [ㅂ-irregular explanation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&pageIndex=1&qna_seq=316687).
* 리라 cannot bypass (으) boundary selection: 먹으리라 is accepted for 먹다,
  while 먹리라 is rejected for that lemma. Tests preserve 가리라, 살리라,
  and irregular recovery through 들으리라, and check past/modal combinations.
  The Korean Basic Dictionary specifies the
  [리라 attachment conditions](https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaWordNo=79280&nation=jpn).
* Interrogative 니 and connective (으)니 are separate morpheme paths. Both 먹니
  and 먹으니 recover 먹다; 그렇니 and 그러니 recover 그렇다 through different
  endings. Tests check the paths, not just the flattened lemma list. NIKL
  [explicitly distinguishes these endings](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313616).
* In joined obligation input such as 먹어야한다, 어야 is the connector and 하다
  is the auxiliary; 야하다 must not become an auxiliary component. Past forms,
  하 contractions, and nested auxiliaries are checked. The dictionary describes
  [auxiliary 하다](https://krdict.korean.go.kr/eng/dicSearch/SearchView?ParaWordNo=62888&nation=eng).
  NIKL requires [spacing between 어야 and 하다](https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6204);
  recognizing joined input is tolerance, not a spacing recommendation.
* Additional paired cases cover ㄷ/ㅅ/ㅎ/르/ㅡ boundaries and preserve regular
  alternatives. They check, for example, 들으면 versus 들면 for 듣다 and 몰라
  versus 몰러 for 모르다. These follow the spelling transformations in
  [orthography Article 18](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001&regltn_no=222).

The audit covers these cases and boundary families only. Broader ending selection,
irregular-class membership, lexical validity, and contextual interpretation
still need independent evidence. Corpus regression snapshots protect previously
recovered gold groups separately from these negative correctness tests.
