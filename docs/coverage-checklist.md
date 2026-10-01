# Coverage and completion tracker

Last reviewed: 2026-10-01.

This tracks the modern written Korean rule coverage needed by the CLI, library,
and sentence explorer. Completion means that the explicitly listed scope has
implementation and regression evidence. It does not establish that every Korean
analysis is generated or that every generated candidate is linguistically valid.
Contextual sense selection and sentence parsing remain separate work.

The examples below were initially probed with the CLI and the local September
2026 Korean Basic Dictionary snapshot. Closed items describe subsequent fixes.
Open examples are audit observations, not yet
executable regression cases unless a test is linked. No overall completion
percentage is assigned: the inventory itself still needs an audit.

## Status and priorities

- **Implemented:** the stated behavior has code and regression coverage; broader
  coverage or independent linguistic review may still be pending.
- **Missing:** the intended analysis is not generated in the audited examples.
- **Partial:** some readings work, but decomposition, roles, or combinations are missing.
- **Audit needed:** coverage has not been inventoried sufficiently to declare it complete.
- **Deferred:** outside the current release scope; not silently counted as complete.

P1 and the bounded COV-010/011/012/014/015/016/017a–av/017ax–ay/017ba–bm/018a–k/018m–z/019a–g/019i–r/020a–o/021a–h/022a–d batches are implemented.
COV-013 has an initial inventory pass; its remaining work is split into
COV-017..022 below. P3 needs further scope or representation decisions.
Priorities reflect the concrete failures found,
not measured frequency estimates across novels.

## Existing coverage to preserve

These checked items record implemented scopes, not entire grammar families.
The examples and source references are expanded in [Grammar coverage](rules.md).

- [x] **COV-001 — Predicate endings and spelling recovery.** Regular conjugation,
  consonant attachment, common 아/어 contractions, 하/푸/ㅡ recovery, and the
  implemented irregular boundaries. Preserve alternative lexical hypotheses.
  Evidence: [rule fixtures](../tests/rules.rs),
  [positive/negative constraints](../tests/candidate_correctness.rs), and the
  [candidate judgment ledger](../tests/fixtures/validity.json).
- [x] **COV-002 — Prefinals, copulas, and auxiliary grouping.** Implemented
  honorific/tense/modal ordering, copular components, nominalizations followed
  by particles, and licensed attached auxiliary chains. This does not certify
  nonstandard spacing or cover every auxiliary. Evidence:
  [grouping tests](../tests/candidate_correctness.rs),
  [ordered breakdown tests](../src/breakdown.rs), and
  [stress/output compatibility tests](../tests/stress.rs).
- [x] **COV-003 — Ordinary particle chains and selected nominal contractions.**
  Implemented chains such as 학교에서는 and 학교에서만은; the special forms
  내가, 제가, 누가, 내, 게, 건, 걸. Broader contraction work is COV-006/007.
  Evidence: [curated rules](../tests/rules.rs).
- [x] **COV-004 — Nominal plural suffix -들.** Bare plurals, particles after
  plurals, and copulas after plurals; retain unsplit lexical alternatives such
  as 아들. Reject the tested wrong particle allomorphs and recursive plural
  stripping. Evidence: `nominal_plural_precedes_particles_and_copulas_without_replacing_lexical_readings`
  in [candidate correctness](../tests/candidate_correctness.rs),
  `plural_nominal_survives_cli_dictionary_filtering` in
  [dictionary tests](../tests/dictionary.rs), `nominal-plural-*` case IDs in the
  [ledger](../tests/fixtures/validity.json), and the 지식인들을
  [browser regression](../web/tests/browser.mjs). The separate 들 particle is COV-009.
- [x] **COV-005 — Dictionary-backed display and candidate preservation.** Grouped
  dictionary filtering, ordered components, normalized-form notices, per-word
  alternatives, bounded combination display, and filtered JSON export.
  Evidence: [dictionary tests](../tests/dictionary.rs),
  [breakdown tests](../src/breakdown.rs), and
  [browser/API tests](../web/tests/browser.mjs).
  A headword match is not contextual or POS validation; see COV-009/014.

## Open coverage checklist

### P1: implemented particle/pronoun batch

- [x] **COV-006 — Contracted particles.** **Implemented for the scoped attachment families.**
  학교에선 and 선생님께선 now recover the particle chains
  학교 + 에서 + 는 and 선생님 + 께서 + 는, with an explicitly normalized display.
  Contracted ㄴ/ㄹ attachment and existing particle chains use canonical 는/를,
  separate from verb endings. Tests also cover 병원엘, 보곤, and 걷질.
  Source starting points: KRDict [ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847)
  and [ㄹ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85760).
  Evidence: `contractions_preserve_case_chains_and_pronoun_alternatives` and
  `particle_slots_and_ending_boundaries_do_not_overstrip` in
  [particle tests](../tests/particles.rs), `particle-contracted-topic` in the
  ledger, and browser/CLI regressions.
- [x] **COV-007 — Pronoun contractions beyond the special cases.** **Implemented
  for 이/그/저 subject/topic/object paradigms and 뭘.** Both short and expanded
  pronouns are retained with the appropriate particles; outer particles compose,
  e.g. 이건요. Productive ㄴ/ㄹ recovery also covers 난/날, 넌/널, 우린/우릴.
  Whole-word readings remain available; contractions do not invent character spans.
  Source starting points: KRDict [이거](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=71128),
  [뭐](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84991), and
  the ㄴ/ㄹ entries above. Evidence: the full three-pronoun paradigm and NFD
  tests in [particles.rs](../tests/particles.rs), `pronoun-*` ledger IDs, and
  the browser's 이건요 alternative selector. Other contractions remain COV-013 work.
- [x] **COV-008 — Polite particle 요.** **Implemented for nominal/adverbial bases,
  particle chains, and explicitly licensed ending families.** 저 + 도 + 요,
  친구 + 는 + 요, and 먹다 + 으면 + 요 now survive dictionary filtering.
  Existing 어요-family analyses remain alongside separated 어 + 요 readings.
  One outer 요 slot is supported; arbitrary stripping after adnominal or formal
  endings is not enabled. Source: [NIKL explanation and attachment examples](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=312410).
  Evidence: particle attachment/boundary tests, `particle-polite-*` ledger IDs,
  and dictionary/browser regressions.
- [x] **COV-009 — Distinguish the 들 particle from nominal -들.** **Implemented
  for nominal/adverbial bases and the listed connective/final endings.** 빨리들
  now has an adverbial + particle analysis; 먹어들 has 먹다 + 어 + 들.
  지식인들을 remains a nominal + suffix + particle analysis. The browser shows
  the correct grammar entry/label for the selected role.
  Source: KRDict [들 particle](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86264)
  versus [plural suffix -들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74906).
  `LemmaKind::Adverbial` has dictionary compatibility with 부사. Headword-only
  filtering still retains incompatible hypotheses; POS-aware consumers can
  distinguish them. Evidence: `adverbs_and_plural_nouns_have_distinct_role_hypotheses`
  in [particles.rs](../tests/particles.rs), the dictionary role test, and the
  browser regression that opens the 들 particle entry.

Batch limits and sources: [P1 rule scope](rules.md#particle-and-pronoun-expansion-p1).
Further ending licenses and other pronoun contractions remain in COV-013.
COV-019a covers one internal particle in joined auxiliary chains. Independent linguistic
review remains open under the completion review below.

### P2: additional morphology

- [x] **COV-010 — Productive suffix decomposition.** **Implemented for bounded
  -님, -적, and -답다 hypotheses.** 선생님께 additionally exposes 선생 + 님 + 께;
  과학적이다 exposes 과학 + 적 + 이다 + 다. 학생답다 and 학생다워요 now retain
  dictionary-filtered paths through 학생. Whole-word alternatives remain and
  the browser initially prefers a compact dictionary-compatible reading.
  `MorphemeKind::Suffix` uses canonical 답다 before its inflection; the display
  shows 답 and links the -답다 entry. The known suffix uses ㅂ-irregular vowel
  attachment. Nominal paths allow one 님, 적, or 들, or 님 + 들; these can
  precede particles/copulas. 답다 may follow an unsplit base or 님/들/님 + 들,
  before licensed inflection and existing auxiliaries. No recursive derivation,
  님 stem alternation, or semantic noun-class validation is claimed. Further
  combinations and adjective ending licenses remain COV-013 audit work.
  Sources: KRDict [-답다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=92145),
  [-님](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88852),
  [-적](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88966).
  Evidence: [suffix path and boundary tests](../tests/derivation.rs),
  `derivational_suffixes_survive_dictionary_filtering_and_keep_lexical_readings`
  in [dictionary tests](../tests/dictionary.rs), eight `suffix-*` ledger cases,
  and browser selection/entry regressions. Scope: [suffix rules](rules.md#bounded-suffix-decomposition-cov-010).
- [x] **COV-011 — Further 하다 contractions.** **Implemented for the listed
  Article 40 ending families and simple coda classes.** 생각지/생각건대 recover
  생각하다; 피케 and 비유컨대 recover 피하다 and 비유하다. Separate deletion and
  aspiration rules preserve canonical endings and their auxiliary connections.
  The scoped inventory is 게/게요, 지/지요/지만/지만요, 다/다고/다는/다니/다면,
  도록, 고자, 건대. Paired negative cases reject the swapped coda classes and
  prevent a restored 하 from being reinterpreted as a nominal before a zero copula.
  Evidence: [Article 40 examples and boundary tests](../tests/hada.rs),
  `shortened_hada_matches_full_lemmas_in_cli_and_pos_filtering` in
  [dictionary tests](../tests/dictionary.rs), nine `hada-*` judgment cases,
  and browser normalization/grammar-entry checks. Source:
  [NIKL's Article 40 explanation](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=325451).
  COV-021a adds 잖/찮 contractions; COV-021c adds eight fixed complex-coda classes.
  Other coda and ending families remain COV-013
  audit work. See [the implemented scope](rules.md#shortened-hada-cov-011).
- [x] **COV-012 — Adverbial derivation.** **Implemented for bounded -이 families.**
  Adjective bases ending in 같/없, the stems 굳/길/깊/높/많, and the historical
  달리/빨리 mappings gain optional suffix analyses. 같이 → 같다 + 이,
  없이 → 없다 + 이, and 달리 → 다르다 + 이 now recover the recorded corpus gold.
  Whole-word readings remain preferred in the browser; the deeper path has a
  suffix, not a fabricated ending. Particles 도/만/는/요/들 compose through the
  existing chain order (including 만은). Noun/case and arbitrary -이/히 stripping
  are not enabled. Evidence: [adverb tests](../tests/adverbs.rs),
  [three complete annotated KAIST sentences](../tests/fixtures/kaist-adverbs.conllu),
  `annotated_adverb_derivations_recover_previously_missed_gold_cases` in
  [corpus tests](../tests/corpus.rs), eight `adverb-*` ledger cases, and
  dictionary/browser tests for preservation and the correct -이 homonym.
  Sources and exclusions: [adverb derivation scope](rules.md#adverbial-derivation-cov-012).
  Remaining -이/-히 families, nominal/adverbial homonyms, and attachment classes
  are COV-013 inventory work. This does not certify all adverbial derivation.
- [ ] **COV-013 — Ending, particle-chain, and auxiliary inventory audit.**
  **Partial: initial inventory, development-miss clustering, and persistent
  entry review queue implemented.** The [715-entry queue](inventory-review-queue.json)
  preserves homonyms, source attachment notes, and links to existing evidence.
  The [manual review ledger](inventory-reviews.json) records 386 scoped
  dispositions from COV-016/017c/017h–i/017m–n/017p–z/017aa–ap/017ar–az/017ba–bg/017bm/018e–k/018m–z/019d–g/019i–r/020d–h/020j–k/020n–o/021d; 328 entries have no disposition in this
  ledger yet, including entries with implemented behavior elsewhere. One entry (마다, COV-018l) retains an observed gap with unresolved
  acceptability; COV-017ah resolves the two question-ending gaps. Neither
  catalog links nor test citations automatically certify coverage. Source and
  evidence drift checks run offline and in `nix flake check`. See the
  [review workflow](inventory-audit.md#persistent-entry-review-queue).
  See [the reproducible audit](inventory-audit.md) and its
  [compact report](inventory-audit.json): 715 dictionary grammar entries are
  inventoried for triage, without treating literal table mentions as coverage.
  COV-016 fixes the reviewed -듯/-듯이 family; 19 additional development cases
  match, leaving 378 KAIST and 242 GSD development misses. COV-017..022 split
  the remaining morphology work. Every-entry linguistic review is still open.
  Compare the implemented tables with dictionary grammar
  entries and cluster saved corpus misses by rule family. Previously recorded
  examples include 보듯이, 있습니다만, 어디까지나, and 번져나갔다; re-probe them
  before promoting a miss to a required test. Distinguish true missing rules
  from annotation errors and differing lexical segmentation. Split this item
  into individually scoped entries as families are reviewed. Corpus gold does
  not enumerate every valid alternative.
  Include the remaining P1 extensions: pronoun contractions outside the finite
  이/그/저 and 뭘 paradigms, additional particle/ending combinations, and particles
  inside joined auxiliary chains. Spaced input is already analyzed token by token.
  Audit further suffix combinations/adjective ending licenses. COV-020a adds
  direct nominalization + copula without an intervening particle, including
  학생다움이다, alongside the existing 학생다움만이다 particle path.
  For 하다 shortening, audit complex coda pronunciation, remaining ending/particle
  combinations, and Article 39 잖/찮 forms separately; COV-011 covers Article 40.
  Audit remaining adverbial -이/-히 bases, spelling recoveries (e.g. 가까이),
  and nominal -이 separately. COV-012 does not infer unrestricted -이 removal or
  a productive 르 → ㄹ리 rule from the historical 달리/빨리 pairs.

### Work split from COV-013

- [x] **COV-016 — Comparative -듯/-듯이 endings.** **Implemented for literal
  predicate attachment.** 보듯이 → 보다 + 듯이; 살듯 preserves ㄹ. Existing
  honorific/past/modal markers, copulas, and auxiliary chains compose before
  these endings. They do not themselves license an auxiliary connector.
  No bound-noun 듯 segmentation, additional particle attachment, or shortened
  하다 variants are included. Sources: KRDict
  [-듯](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80280) and
  [-듯이](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=80282).
  Evidence: [path/boundary tests](../tests/comparative_endings.rs), six
  `comparative-*` ledger cases, two full [KAIST sentences](../tests/fixtures/kaist-comparative.conllu),
  dictionary/CLI parity and browser grammar-entry checks. All 30 existing
  fingerprints remain unchanged; no frozen corpus baseline was regenerated.
- [ ] **COV-017 — Further ending families.** **Partial: COV-017a–av and
  COV-017ax–ay/017ba–bm implemented; COV-017aw/az remain open.**
  Remaining: other quoted contractions and unreviewed inventory
  entries. Re-probe each path and check verb/adjective attachment, prefinals,
  and whole-word alternatives. Corpus signatures identify candidates for review,
  not a blanket license to add every dictionary spelling as a literal suffix.
- [x] **COV-017a — Present conditional -ㄴ다면/-는다면.** Implemented with
  canonical ending 는다면. 한다면/산다면 use attached ㄴ, while 먹는다면 uses
  the non-ㄹ consonant boundary. Honorific 시 is permitted; this present path
  rejects recovered past/modal/retrospective markers. Existing plain 다면 paths
  such as 먹었다면 remain. Vowel-only ㅂ/ㅎ/ㄷ recovery is not applied at the
  present ending. Existing auxiliaries can precede it, but it is not itself an
  auxiliary connector. Evidence: [boundary/group tests](../tests/conditional_endings.rs),
  eight `conditional-*` ledger cases, three offline annotated cases,
  dictionary/CLI parity and browser normalization/homonym checks.
  Sources: KRDict [-ㄴ다면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=66956)
  and [-는다면](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=68738).
  The rule-only engine does not distinguish lexical verb/adjective classes;
  the quoted-expression homonyms and additional outer particles are not added.
  See [rule scope](rules.md#present-conditionals-cov-017a) and
  [the recorded development comparison](conditional-evaluation.json).
- [x] **COV-017b — Shortened adnominal expressions (으)려는 and 자는.**
  **Implemented as bundled grammatical components.** 먹으려는 recovers 먹다,
  살려는 preserves ㄹ, 들으려는/도우려는 recover their irregular stems, and
  바꿔보자는 retains the 바꾸다 + 보다 auxiliary group. Canonical endings are
  으려는 and 자는; no implicit 하다 lemma is inserted. Intention expressions
  permit honorific 시; the proposal expression is bounded to bare stems in
  this batch. Other prefinals, outer particles, lexical verb/adjective class
  validation, and a fully expanded quotation analysis remain for review.
  Sources: KRDict [-으려는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86717),
  [-려는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86688),
  [-자는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=83896).
  These are tagged 문법‧표현 / 품사 없음. Browser lookup admits the two canonical
  expression IDs through an explicit exception; unrelated unclassified entries
  remain excluded. Evidence: [path and boundary tests](../tests/adnominal_expressions.rs),
  eight `adnominal-*` ledger cases, three complete KAIST sentence fixtures,
  dictionary/CLI parity, and browser/source-lookup regressions.
  See [rule scope](rules.md#shortened-adnominal-expressions-cov-017b) and
  [the development comparison](adnominal-evaluation.json).
- [x] **COV-017c — Literal -다가.** Implemented separately from existing
  vowel-boundary -어다가. 먹다가, 갔다가, 불렀다가, and 먹으셨다가 recover
  their stems and ordered prefinals. Copulas, existing auxiliaries, and known
  -답다 derivation compose with it. Honorific/past markers are supported;
  recovered 겠/더 paths are excluded. 가다가 retains both 다가/어다가 readings.
  Sources: KRDict [-다가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85740)
  and [-어다가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86099).
  Evidence: [path/boundary tests](../tests/daga.rs), eight `daga-*` ledger cases,
  three positive offline corpus cases plus the preserved quoted-subject
  annotation for 살겠다가, dictionary/CLI parity and browser alternative/link
  checks. See [scope](rules.md#literal-daga-cov-017c) and
  [the development comparison](daga-evaluation.json). Further outer particles,
  joined auxiliary uses of 다가, and short-form 다 sense selection remain open. The
  [full native source review](daga-native-source-audit.json) now adds 19 stable
  target-occurrence cases across all four senses and 15 original groups,
  retaining repeated -다가 constructions and adjective examples. [Four tests](../tests/daga_source.rs)
  verify unchanged source turns, exact paths/kinds/order, ambiguity, dictionary
  filters and CLI word/text exports. The inventory now records a scoped
  disposition for 85740. Source integrity, 620 Rust tests, pinned corpus,
  lint/format and preview API parity pass; see the
  [evaluation](daga-native-evaluation.json). Nix CLI/web builds and all three
  x86_64 Linux flake checks pass; packaged API/CLI and asset parity pass.
  Parent inventories and independent Korean review remain open.

- [x] **COV-017d — Bundled quoted questions -냐는/-느냐는.** Literal
  attachment supports 아니냐는, 했느냐는, ㄹ deletion in 사느냐는, and
  honorific/past/modal prefinals in order. Existing auxiliary chains compose;
  bare copulas use 냐는, while copula + past + 느냐는 remains available.
  Both expressions retain one `Ending` component without an inferred 하다.
  Sources: KRDict [-냐는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86030)
  and [-느냐는](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86031).
  Evidence: [path/boundary tests](../tests/quoted_questions.rs), eight
  `quoted-question-*` ledger cases, two complete KAIST sentence fixtures,
  dictionary/CLI parity, and browser component/source-link checks. See
  [scope](rules.md#quoted-questions-cov-017d) and
  [the development comparison](quoted-question-evaluation.json).
  Adjective allomorphy and retrospective quotation are covered by COV-017e.
  Lexical verb/adjective validation and additional outer particles remain open.
- [x] **COV-017e — Adjective quoted-question boundaries and retrospective 더.**
  좋으냐는, 기냐는, 추우냐는, and 파라냐는 recover canonical 으냐는
  through the existing 으 boundary, including ㄹ/ㅂ/ㅎ recovery. Bare adjective
  suffix -답다 uses its known ㅂ-irregular boundary. Literal 냐는 remains
  separate; honorific/past/modal markers still use 냐는/느냐는, and retrospective
  더 now composes with 냐는, including copulas and auxiliaries. No implicit
  하다 is inserted. Evidence: expanded [quoted-question tests](../tests/quoted_questions.rs),
  eight `quoted-adjective-*`/`quoted-retrospective` ledger cases, attributed
  dictionary fixtures, CLI parity, and browser canonical-form/link tests.
  [Scope and sources](rules.md#adjective-and-retrospective-questions-cov-017e)
  explain the representation and lexical-class limit. No new development
  gold matches are attributed to this family; its examples are source-backed
  constructions, not independently annotated corpus cases.
- [x] **COV-017f — Confirmation expressions -잖아/-잖아요.** Bundled
  confirmation/correction readings remain separate from the negative contraction
  in COV-021a. 먹잖아요 preserves 먹다 + 잖아요 as well as 먹다 + 지 + 않다 +
  어요; the app labels and links the confirmation expression. Honorific, past,
  and modal prefinals compose; retrospective 더 is excluded for the bundled
  expression. Copulas and existing auxiliary groups retain their components.
  Sources: KRDict [86756](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86756)
  and [86757](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86757).
  Evidence: [negative/confirmation tests](../tests/negative_contractions.rs),
  three confirmation-related ledger cases, dictionary/CLI parity and browser
  source-link checks. No new development gold match is attributed to these
  expressions; source-backed synthetic cases cover them.
- [x] **COV-017g — Correct propositive -(으)ㅂ시다.** The label audit exposed
  a legacy 습시다 spelling. Canonical 읍시다 now covers 먹읍시다 and attached
  갑시다/삽시다, with the vowel-boundary recoveries 들읍시다, 부읍시다,
  and 도웁시다. Existing auxiliary groups and lexical alternatives remain.
  The change does not classify unknown lexical stems or establish sentence-mood
  compatibility; further lexical/prefinal restrictions remain COV-017/019 work.
  Evidence: [boundary/group tests](../tests/propositive_endings.rs), eleven
  `propositive-*` ledger cases, complete KAIST MH2_0159-s160, dictionary/CLI
  parity, and browser normalization/source-link checks. Sources and candidate
  changes are recorded in [the audit](grammar-label-evaluation.json).
- [x] **COV-017h — Intention/expectation and concessive endings.**
  Canonical 으리라고, 을지라도, and 자면 recover 되리라고, 할지라도,
  and 들자면. Vowel/ㄹ and consonant allomorphs preserve the existing irregular
  alternatives; literal 자면 does not restore vowel-triggered irregulars.
  Prefinal licenses are family-specific. Known auxiliary adjectives, -답다
  derivatives, and copulas reject verb-only 자면, including after honorific 시;
  restrictions apply to the relevant predicate, not an entire auxiliary chain.
  Copulas and adjective derivatives retain 으리라고/을지라도. The new endings
  do not themselves license an auxiliary connector. Bundled expressions have
  sourced browser labels without an inferred reporting verb. Unknown lexical
  verb/adjective classes and contextual intention/quotation senses remain open.
  Evidence: [boundary and composition tests](../tests/intention_endings.rs),
  fifteen `intention-*` ledger cases, eleven full annotated source sentences,
  dictionary/CLI parity, and six browser/source-link regressions. See
  [scope and sources](rules.md#intention-expectation-and-concession-cov-017h)
  and [development comparison](intention-ending-evaluation.json). The
  [complete native source review](native-conditionals-source-audit.json) adds four
  stable -자면 target cases across all original groups of entry 80338. Existing
  literal, class and prefinal boundary exclusions remain unchanged; contextual
  senses and broader lexical licenses remain open.
- [x] **COV-017i — Concessive -(으)나마 ending.** Canonical 으나마 is
  separate from the nominal/adverbial (이)나마 particle. 작으나마, 약소하나마,
  and 먹지못하나마 retain their predicate/auxiliary groups; 조금이나마 retains
  both particle and copular-ending readings. Existing vowel-boundary irregulars,
  ㄹ deletion, honorific/past/modal markers, and known -답다 spelling apply;
  retrospective 더 and new auxiliary links are not licensed. These are
  source-backed synthetic cases, not additional corpus gains. Evidence and
  sources are shared with COV-018c below. Broader omitted-copula and outer-particle
  licenses remain COV-018/020. The same
  [native review](native-conditionals-source-audit.json) preserves all ten groups
  of entries 80167/80164, adding ten exact ending-path cases, full dialogue turns
  and separate 조금이나마 particle alternatives. [Three tests](../tests/native_conditionals.rs)
  cover all 14 native occurrences across these ending families, Unicode, source
  identity, dictionary filters and ordered CLI word/text exports. Source integrity, 623 Rust tests, full pinned corpus, lint/format and preview
  API parity pass; see the [evaluation](native-conditionals-evaluation.json).
  Nix CLI/web builds, all three x86_64 Linux flake checks and packaged API/CLI
  parity pass; the preview is refreshed. No additional generation license is inferred.
- [x] **COV-017j — Short quoted facts and commands -란/-(으)란.**
  학생이란 preserves 학생 + 이다 + 란 alongside the separate particle reading.
  Explicit and vowel-final omitted copulas, 아니다, honorific copulas and
  retrospective forms such as 먹었더란 are supported. 먹으란/먹어보란 use
  canonical 으란 with their own allomorph and prefinal licenses. Conjectural
  (으)리 is a scoped prefinal before 란, including 작으리란 and 먹었으리란;
  existing -(으)리라/-(으)리라고 remain bundled. Explicit standalone 이란 gains
  a Copula-kind reading without joining tokens or inserting a nominal component.
  The source's 행복하란 example prevents a blanket adjective-command ban;
  further lexical/mood restrictions and -답다 command licenses remain open.
  Evidence: [path and boundary tests](../tests/quoted_definitions.rs), shared
  twenty-one `definition-*` ledger cases, dictionary/CLI role checks and eight
  browser/source-link cases. [Scope and sources](rules.md#definition-particles-and-short-quotations-cov-018d017j),
  [evaluation](quoted-definition-evaluation.json).
- [x] **COV-017k — Intention/necessity -아/어/여야겠-.** The canonical
  `어야겠` component occupies a prefinal position before a final ending.
  Existing vowel recovery covers 해야겠다, 와야겠다, 들어야겠다 and 도와야겠다;
  copulas, honorific/past markers, -답다, and existing auxiliary groups compose.
  No implicit 하다 lemma is inserted. The new progressive-order check preserves
  먹고 있어야겠다 while rejecting 먹어야겠고 있다. Broader ending/prefinal and
  auxiliary restrictions remain COV-017/019 work. Evidence: [path/boundary tests](../tests/obligation.rs),
  twelve `obligation-*` ledger cases, five complete annotated sentences,
  dictionary/CLI parity, and nine browser reading/source-link checks.
  The [evaluation](obligation-evaluation.json) records three new grouped matches
  and two GSD implicit-하다 representation differences; no prior recoveries or
  current output fingerprints are lost. See [scope and sources](rules.md#intention-and-necessity-bundle-cov-017k).
- [x] **COV-017l — Factual 라-family and command prefinal licenses.**
  먹었더라 retains bundled 더라 and factual 더 + 라; conjectural 으리 also
  composes with the reviewed 라/라서/라고/라면 family. Incompatible recovered
  past/modal/retrospective paths are removed from the reviewed command, quoted
  command, and formal request/proposal endings, preserving honorific paths and
  lexical alternatives. The separate 더라는 bundle preserves 못하더라는's corpus
  gold without an invalid 더 + 으라는 analysis. Copular factual readings and
  declarative/question 세요 remain; exclamatory 어라 and homonymous 자 require
  further audit beyond the restrictions documented here.
  Evidence: [path/boundary tests](../tests/prefinal_licenses.rs), seventeen
  `prefinal-license-*` ledger cases, one complete KAIST test sentence,
  dictionary/CLI parity, and browser/source-link checks. The
  [evaluation](prefinal-license-evaluation.json) records every candidate change
  for 63 surfaces and the reviewed 먹었었겠더라 fingerprint: twenty invalid
  command paths become ten factual paths, preserving bundled 더라. No frozen
  corpus baseline is changed. See [scope and sources](rules.md#factual-라-family-and-command-prefinal-licenses-cov-017l).
- [x] **COV-017m — Polite informative and reported endings.** 답니다,
  present-verb ㄴ/는답니다, copular/factual 랩니다 and reported-command
  (으)랍니다 now retain distinct canonical paths. Literal/attached/vowel
  boundaries, honorific/past/modal/retrospective licenses, known adjective
  auxiliary/suffix restrictions and copula roles are checked. No implicit 하다
  is inserted; informative/reported senses remain dictionary alternatives.
  Evidence: [boundary and composition tests](../tests/reporting_endings.rs),
  fourteen `reporting-*` ledger cases, four complete annotated sentences,
  dictionary/CLI parity, and browser alternatives with nine primary-source
  entries. The [evaluation](reporting-evaluation.json) records four development
  recoveries with no lost groups/component sets or changed stress fingerprints.
  Arbitrary lexical head verb/adjective classes remain unknown; other quoted
  contractions remain open. See [scope](rules.md#polite-informative-and-reported-endings-cov-017m).
- [x] **COV-017n — Causal -기에/-길래.** Literal predicate, explicit copula,
  known adjective suffix and auxiliary paths retain the ending as one component.
  The existing 기 + 에 nominalization reading remains separately selectable.
  Source-listed honorific/past attachment is supported for both; 기에 additionally
  permits modal 겠, including the existing 어야겠 bundle. Retrospective 더 and
  vowel-only irregular recovery at ㄱ are excluded. Evidence:
  [boundary/composition tests](../tests/causal_endings.rs), twelve `causal-*`
  ledger cases, two complete GSD sentences, dictionary/CLI parity, and browser
  source links with nominalization alternatives. See [scope](rules.md#causal-endings-cov-017n)
  and [evaluation](causal-evaluation.json). Omitted-copula and shortened 하다
  allomorphs, further outer particles, and contextual interpretation remain open.
- [x] **COV-017o — Quoted alternatives and enumerations.** Ten source-listed
  expressions map to eight canonical bundles: 는다거나/다거나/라거나/으라거나/
  자거나 and 는다든가/다든가/라든가. Attached ㄴ/non-ㄹ consonant, command
  vowel boundaries, copulas, prefinals and known auxiliary/suffix classes have
  distinct licenses. Factual 라든가 retains 시/더/으리 attachment. No implicit
  하다 is inserted. Evidence: [boundary/composition tests](../tests/quoted_alternatives.rs),
  twenty-two `quoted-alt-*` ledger cases, three complete annotated development
  sentences, dictionary/CLI parity, and browser source links. The
  [comparison](quoted-alternatives-evaluation.json) records each candidate change
  and the source dispositions. These entries are 문법‧표현, outside COV-013's
  715-entry POS inventory. Other quotation contractions, expanded quotation
  analysis, particle alternatives and quoted-clause copulas remain open. See
  [scope](rules.md#quoted-alternatives-cov-017o).
- [x] **COV-017p — Literal choice ending -든가.** Bare predicates and the
  source-listed honorific/past markers are supported, including copulas,
  auxiliaries and 답다. Literal ㄷ attachment preserves ㄹ and excludes
  vowel-boundary irregular recovery. Recovered 겠/더/어야겠 are not licensed.
  The ending remains distinct from particle 든가 and bundled quoted alternatives.
  Evidence: [ending/boundary tests](../tests/enumerative_particles.rs), eight
  `choice-ending-*` ledger cases, dictionary/CLI and browser homonym checks,
  and [evaluation](enumerative-particle-evaluation.json). Further outer particles
  and contextual choice remain open. Source: KRDict
  [-든가](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=82342).
- [x] **COV-017q — Sequential 고서 and emphatic 어서야.** Literal 고서
  preserves consonant stems and honorific 시, rejects recovered past/modal/
  retrospective stacks, and distinguishes verb/아니다 attachment from known
  adjective or represented-copula paths. Vowel-boundary 어서야 preserves
  아/어/여 allomorphs, irregulars, 하 contractions and a separate 어서 + 야
  reading. Evidence: [boundary/composition tests](../tests/seo_connectives.rs),
  source-cited `seo-connectives-*` judgments, dictionary/CLI parity and browser
  alternatives/source links. [The comparison](seo-connective-evaluation.json)
  records gains shared with COV-018i; broader 어서야 prefinal constraints and
  lexical class/sense selection remain open. See [scope](rules.md#seo-connectives-and-particles-cov-017q018i).
- [x] **COV-017r — Retrospective following-ending licenses.** Recovered 더
  is rejected before 33 reviewed ordinary or retrospective-bundled endings,
  including 다, 지, 어/어요, formal endings, 고 and doubled 더라/던데.
  The same condition applies to lexical predicates, explicit/omitted copulas,
  derived adjectives, auxiliary chains and outer particles. Licensed 라/니/냐/
  구나 families and literal bundles remain. Evidence: [132-path matrix and
  composition tests](../tests/retrospective_licenses.rs), 81 source-cited ledger
  cases, four complete unchanged annotated sentences, dictionary/CLI/browser
  checks and [comparison](retrospective-license-evaluation.json). The report
  accounts for every removed candidate across 184 surfaces and preserves all
  30 stress fingerprints. COV-017s below extends this review to 나 and nominalizing 기,
  including the separately represented 더 + 나 + 요 alternative.
  This closes the 더 + 다 gap recorded by COV-020g. See
  [scope](rules.md#retrospective-following-ending-licenses-cov-017r).
- [x] **COV-017s — Retrospective nominalization and connective boundaries.**
  Recovered 더 is rejected before 33 further reviewed endings, including
  나/으나, 기 and its bundles, 음, 게/도록/듯, 으면/으며/으면서/으므로,
  어서 and related AEO connectives, 고자/건대/소/오. Nominal particles,
  later copulas and auxiliaries cannot bypass the boundary. Licensed prefinal
  stacks, lexical stems and bundled/component alternatives remain. Evidence:
  [132-path matrix and composition tests](../tests/retrospective_connectives.rs),
  107 source-cited ledger cases, four complete unchanged annotated sentences,
  dictionary/CLI/browser checks and [comparison](retrospective-connective-evaluation.json).
  Every removal across 211 surfaces contains the reviewed boundary; all 30
  stress fingerprints and development gold/component recovery remain unchanged.
  Three short 며/면서/므로 sources are added to their existing canonical labels.
  Spaced 기로 하다 remains a nominalized clause followed by a lexical main verb;
  it does not establish a joined auxiliary connector. Other retrospective
  followers and attachment restrictions remain open. See
  [scope](rules.md#retrospective-nominalization-and-connectives-cov-017s).
- [x] **COV-017t — Retrospective adnominal and question alternatives.**
  Preserve 더 + 은/은데/은가/은지-family component analyses; NIKL documents
  alternative segmentation, so ordinary adnominal notes do not justify a
  blanket retrospective ban. Add dictionary bundles 던가/던지, with their
  licensed prefinals, copulas, particles and the 던가 + 보다/싶다 auxiliary
  construction. Reject 더 before 17 reviewed present/prospective endings,
  and prevent doubled 더 before the new bundles. Eleven dictionary source
  entries attribute the bundles and short ㄴ/ㄹ-family allomorphs.
  Evidence: [68-path matrix, preserved alternatives and composition](../tests/retrospective_adnominals.rs),
  144 source-cited ledger cases, four complete unchanged annotated sentences,
  dictionary/CLI/browser checks and [comparison](retrospective-adnominal-evaluation.json).
  Across 157 surfaces, every added bundled path has a split counterpart and
  every removal contains a reviewed incompatible boundary. All 30 stress
  fingerprints and development gold/component recovery are preserved.
  Other followers, omitted-copula adnominals and lexical/contextual restrictions
  remain open. See [scope](rules.md#retrospective-adnominal-and-question-alternatives-cov-017t).
- [x] **COV-017u — 놓아 → 놔 contraction.** Article 35 supplement 1
  restores 놓다 in 놔/놔라/놨다, including compound-final 놓다, double past,
  existing particles and auxiliary chains. Both verb and adjective/copular left
  contexts of auxiliary 놓다 remain. This lexical exception does not generalize
  ㅎ deletion (좋아 does not become 좌), treat phonetic 노아 as the written form,
  or restore 놓 before a non-아/어 boundary. Lexical 놔두다 and split 놓다 + 두다
  remain distinct; internal headword normalization is not added.
  Evidence: [boundary/full-form tests](../tests/noh_contraction.rs), 64 `noh-*`
  ledger cases, two complete KAIST sentences, dictionary/CLI parity and browser
  normalization/source checks. The [comparison](noh-contraction-evaluation.json)
  reviews 119 surfaces and 192 additions, with no lost candidates or changed
  existing provenance. 놨었지요 newly matches development gold; all 30 stress
  fingerprints remain unchanged. Broader auxiliary restrictions remain COV-019.

- [x] **COV-017v — Informative/reported 다네 and 다는데 families.**
  Ten canonical forms preserve present ㄴ/는 allomorphs, plain adjective/prefinal
  attachment, copular/factual 라 forms and separate (으)라 command readings.
  더라네/더라는데 bundles coexist with split retrospective components;
  source-listed polite 요 and concessive 도 paths retain the same restrictions.
  No implicit reporting 하다 or contextual sense is selected. Known auxiliary
  roles and -답다 derivation constrain attachment; unknown lexical classes and
  broader honorific judgments remain unverified.
  The shorter 라는데 entry has a narrower note than 더라는데/라는데요/라는데도;
  the latter entries support the retrospective/conjectural family paths. The
  [review](report-ne-evaluation.json) records this compositional interpretation.
  Evidence: [path/boundary tests](../tests/report_ne_endings.rs), 187 `report-ne-*`
  ledger cases, five complete annotated sentences, dictionary/CLI parity and
  browser homonym/source/normalization checks. The comparison accounts for 954
  additions on 186 surfaces with no lost candidates or changed prior provenance;
  all 30 stress fingerprints remain unchanged. Five development groups newly
  match, including 대부분이라는데, 풍속이었다네 and 판매한다네요.
  Further quoted families, outer particles, sense choice and independent Korean
  review remain open. See [scope and sources](rules.md#informative-and-reported-ne-families-cov-017v).

- [x] **COV-017w — Literal 되 and licensed 으되.** Canonical 으되
  preserves literal 되 after ordinary stems/honorific 시 and full 으되 after
  bare 있다/없다 (including compounds) or past/modal markers. It does not apply
  general 으-boundary irregular recovery: 살되/듣되/돕되 preserve their stems.
  Existing copulas, auxiliaries, -답다 and polite 요 compose. 치렀으되 and 그리되
  newly match their annotated development groups.
  Evidence: [boundary/composition tests](../tests/doe_endings.rs), 54 `doe-*`
  ledger cases, two complete annotated sentences, dictionary/CLI parity and
  browser allomorph/source checks. The [comparison](doe-evaluation.json) accounts
  for 132 additions on 67 surfaces without losing prior candidates or changing
  provenance; all 30 stress fingerprints remain unchanged.
  **Still unjudged:** short existential 있되/없되 and their compounds; the broad
  되 and specific 으되 notes do not settle their exclusivity in this review.
  Named followups `doe-short-existential` and `doe-further-composition` also keep
  omitted copulas and additional particles visible. This closes only the stated
  positive and boundary scope, not those unresolved judgments. See
  [scope and sources](rules.md#literal-doe-and-licensed-eudoe-cov-017w).

- [x] **COV-017x — Quoted/confirmatory -며/-면서 families.** Eighteen
  canonical components cover statements, commands, proposals, questions and
  retrospective reports, including ㄴ/는다며 and 다면서. Copular/factual 라
  stays distinct from command 으라; bundled 더라 alternatives coexist with
  더 + 라 components. Present forms retain attached-ㄴ boundaries and honorific
  licenses. Commands/proposals, question allomorphs, known adjective/auxiliary
  classes and copulas have separate checks. Auxiliary 있다/계시다 and inherited
  negatives preserve source-attested stative plain-다 readings in these new
  families. Polite 요 and longer -면서 + 도 compose; broader particles remain
  unjudged. No implicit reporting 하다 or contextual sense is selected.
  There are 157 required and 78 forbidden judgments, six complete unchanged
  annotated sentences, dictionary/CLI parity and browser source regressions.
  Six development gains leave 106 KAIST and 151 GSD misses, with no losses.
  Generic 더 + 냐며/냐면서 hypotheses remain unjudged: missing examples or
  an omitted prefinal in a short dictionary note is not a categorical ban.
  Evidence: [tests](../tests/report_myeo_endings.rs), stable `report-myeo-*`
  ledger cases, `report_myeo_endings_preserve_dictionary_and_cli_parity`,
  [rules](rules.md#quoted-and-confirmatory-myeo-families-cov-017x) and
  [source/candidate review](report-myeo-evaluation.json).

- [x] **COV-017y — Shared present-declarative prefinal and class licenses.**
  Eleven canonical ㄴ/는다 families now share their verb and prefinal constraints.
  Older 는다/는다고/는다는 reject recovered past/modal/retrospective markers;
  honorific 시 remains. Known adjective/copula roles, including 답다 and inherited
  negatives, cannot gain present declaratives through honorifics. Later verbal
  auxiliaries reset the class. Plain-다 counterparts, unknown lexical heads and
  nondeclarative 는데/는지 remain distinct. Nine missing full/attached source
  homonyms are now mapped in the browser. Evidence: [role/NFD/unknown-head
  tests](../tests/present_licenses.rs), 338 stable `present-license-*` ledger cases,
  dictionary/CLI parity and browser source selections, plus [source/candidate
  review](present-license-evaluation.json). The 343-surface comparison removes
  306 unsupported paths with no added candidates, lost corpus gold or changed
  stress fingerprints. This also resolves COV-019h's generic past/modal + present
  declarative gap; existential honorific/question/adnominal review stays open.

- [x] **COV-017z — Surprise and quoted -니 families.** Nine canonical
  components cover 다니/는다니/라니/으라니/더라니/자니/냐니/느냐니/으냐니.
  Present attached-ㄴ and consonant-는 boundaries, factual versus command 라,
  question allomorphs and prefinal/known-class licenses remain distinct. Bare
  verbal 다니 surprise is preserved (하다니 and 한다니 are both possible).
  Bundled 더라니 coexists with split 더 + 라니; source-listed polite surprise
  readings compose with 요 without licensing every homonymous sense. No implicit
  reporting verb is inserted. There are 109 required and 54 forbidden judgments,
  three complete unchanged corpus sentences, dictionary/CLI parity and browser
  source selections. Development misses fall to 104 KAIST and 150 GSD with no
  lost gold groups or changed stress fingerprints. All eight new components
  have labels; 24 added source IDs preserve full/short and expression homonyms.
  Evidence: [role/NFD tests](../tests/report_ni_endings.rs), stable `report-ni-*`
  ledger cases, `report_ni_preserves_dictionary_roles_and_cli_parity`,
  [rules](rules.md#surprise-and-quoted-ni-families-cov-017z) and
  [source/candidate review](report-ni-evaluation.json). Generic 더 + 냐니 and
  further existential paradigms remain unjudged. Broader quoted contractions
  such as 된단 and 노력했단 are now covered by COV-017ab; other families remain open.

- [x] **COV-017aa — Lexical attachment classes in dictionary-backed readings.**
  Added a finite, source-backed per-reading policy and opt-in `--dict-compatible`
  CLI/library/browser filtering. It excludes lexical-role conflicts, adjective
  present declaratives (가는다니 → 가늘다 + 는다니), verbal bare adjectival
  questions (길으냐니 → 긷다 + 으냐니), and the distinct command hypothesis
  아니다 + 으라니 while preserving factual 아니라니. Valid homonyms and unknown
  provider classes remain. Separately written auxiliaries such as 싶었다 are
  unknown without their preceding word, not automatically conflicting. Wish
  uses 행복하란/행복하자 remain; this is not a blanket adjective-command ban.
  The [separate dictionary-policy ledger](../tests/fixtures/dictionary-attachments.json)
  initially had 63 exact cases (39 required, 24 forbidden); COV-017ag expands
  it to 185 cases. All judgments are present before filtering
  and after headword-only filtering. The raw rule API and `--dict-only` candidate
  groups remain unchanged across 2,389 regression surfaces. Per-entry evidence,
  component ownership, Unicode/cache behavior, CLI/library parity and browser
  choices/glosses/export are covered. See [policy and limits](dictionary-attachments.md)
  and [review/measurements](dictionary-attachment-evaluation.json).
  Further lexical/sense restrictions remain COV-017/019; the novel audit exposes
  missing adverbial-role alternatives under COV-018n. Dictionary matching or
  passing this finite policy still does not certify grammatical correctness.

- [x] **COV-017ab — Short quoted modifiers and change/conditional endings.**
  Eight components cover 단/는단/잔/냔/느냔/으냔/다간/다가는. Preserve both
  quoted and change/conditional 단 homonyms; the latter admits bare verbs,
  including auxiliary verbs. Present full/attached boundaries, proposals,
  question allomorphs and known-class/prefinal conditions remain distinct.
  The source-illustrated 누구냔 recovers an omitted copula without permitting
  consonant-final 학생냔 as 학생 + 이다. Existing 란/으란 paths remain.
  The noun suffix -단 is excluded from ending lookups. No implicit reporting
  verb is inserted. There are 92 required / 50 forbidden judgments, two complete
  annotated sentences, dictionary/CLI parity and browser source checks. 된단
  and 노력했단 newly match; misses fall to 102 KAIST / 150 GSD with no lost
  gold groups or changed stress fingerprints. The 151-surface comparison adds
  599 candidates without removing or changing existing ones. Evidence:
  [tests](../tests/short_clauses.rs), `short-clause-*` ledger cases,
  `short_clauses_preserve_dictionary_roles_and_cli_parity`,
  [rules](rules.md#short-quoted-modifiers-and-changeconditionals-cov-017ab) and
  [source/candidate review](short-clause-evaluation.json). Further outer particles,
  copula omission, 하다 shortening, existential questions and lexical-class
  choices remain explicitly tracked followups under COV-018/020/021/019h/017aa.

- [x] **COV-017ac — Shared adjectival question-family attachment.**
  The six canonical 으냐/으냐는/으냐며/으냐면서/으냐니/으냔 forms now
  share bare-adjective licensing. Plain 으냐 and 으냐는 no longer bypass
  the known auxiliary-verb restriction; recovered prefinals cannot precede the
  adjectival family. General 냐 and verbal 느냐 paths remain distinct, including
  계시냐, 싶었냐 and 싶으시느냐. Negative auxiliaries inherit only represented
  classes; unknown lexical heads remain available without a dictionary.
  Evidence: [169 ledger cases](../tests/fixtures/validity.json) (120 required / 49
  forbidden), [Unicode/dictionary/CLI tests](../tests/adjectival_question.rs),
  one complete GSD sentence, browser source/selection checks, and
  [source/candidate review](adjectival-question-evaluation.json). Twenty-one
  ending/expression entries are reviewed; three grammar-POS entries receive
  new scoped inventory dispositions. Thirty-six scoped hypotheses are removed
  across 187 focused/stress/observation surfaces, without additions or provenance
  changes. The only changed development token loses a distinct auxiliary
  으냐는 hypothesis; its gold lemma and general 냐는 remain. Stress hashes
  and all development recovery outcomes are unchanged. Broader existential
  paradigms, honorific 있다 and past adnominals remain open under COV-019h.

- [x] **COV-017ad — Uncertain possibility and shortened intention questions.**
  -(으)ㄹ는지 and -(으)려는가/지 now expose canonical 을는지, 으려는가
  and 으려는지. Boundary and irregular recovery retain ㄹ; possibility admits
  honorific/past markers, while the intention expressions admit only honorific
  시. The latter reject represented adjective auxiliaries, inherited known
  adjective/copula negatives, direct copulas and 답다 derivation. Unknown lexical
  heads remain; dictionary filtering does not certify every lexical attachment.
  Existing ordered nominal/question particles compose, including 나올는지는
  and 있을는지요. No implicit 하다 or contextual sense is selected.
  Evidence: [92 stable judgments](../tests/fixtures/validity.json) (55 required /
  37 forbidden), [Unicode/dictionary/CLI tests](../tests/uncertainty.rs),
  the complete unchanged KAIST MH2_0159-s309 sentence, six dictionary grammar
  sources, browser source/selection checks and [review](uncertainty-evaluation.json).
  같을는지 recovers 같다, leaving 101 KAIST and 150 GSD development misses;
  no prior gold recovery is lost. All thirty stress fingerprints are unchanged.
  Nonstandard 을런지 spelling repair, broader intention-family/class licenses,
  contextual particle distribution and independent Korean review remain open.

- [x] **COV-017ae — Intention connectives and represented verb attachment.**
  Eight canonical forms cover -(으)려거든/기에/는데/다/다가/더니/도/야.
  Both allomorphs, irregular stems and honorific 시 are supported; recovered
  past/modal/retrospective slots are rejected. Known adjective auxiliaries,
  copulas, inherited negative classes and 답다 cannot supply the verb slot.
  Existing 으려는 now shares this represented-class check; lexical heads remain
  unknown, and other 려 families retain their separate source licenses.
  Ordered connective particles compose, including source-attested 려는데요.
  The conditional form preserves both 어미 and expression dictionary homonyms.
  Evidence: [252 stable cases](../tests/fixtures/validity.json) (130 required /
  122 forbidden), [boundary/Unicode/dictionary/CLI tests](../tests/intention_connectives.rs),
  two unchanged complete annotated sentences, 18 new grammar sources, browser
  allomorph/homonym selection, and [source/candidate comparison](intention-connectives-evaluation.json).
  Across 2,974 ledger/stress surfaces, 765 hypotheses are added and three
  represented nonverbal 으려는 paths removed; no provenance or stress hashes
  change. KAIST 하려다 → 하다 is recovered. GSD 갈려는데 → 갈다 is an
  incidental annotation match in a sentence apparently intending 가다, not
  spelling repair. Development misses are 100 KAIST / 149 GSD, with no prior
  gold recovery lost. Following auxiliary composition is scoped in COV-019j;
  lexical/contextual constraints, other 려 expressions and Korean review remain.

- [x] **COV-017af — Short/full result-transfer connectives.** Canonical
  어다 and 어다가 recover all six -아/어/여다(가) source forms, with ordinary
  contraction and irregular recovery. Both select bare verbs: recovered
  시/었/겠/더, represented adjective auxiliaries, copulas and 답다 are rejected.
  Lexical 모시다 remains valid in 모셔다(가); its 시 is part of the stem.
  Existing literal 다/다가 and the separate interrupted-intention forms remain.
  Evidence: [85 stable cases](../tests/fixtures/validity.json) (51 required /
  34 forbidden), [class/Unicode/dictionary/CLI and corpus tests](../tests/result_connectives.rs),
  five unchanged annotated sentences, six grammar sources, browser allomorph
  selection, and [source/output review](result-connectives-evaluation.json).
  Across 3,059 ledger/stress surfaces, 174 candidates are added, 23 unsupported
  paths removed and 146 retained paths gain provenance. One reviewed stress hash
  changes (의사다 gains an unknown predicate hypothesis removed by dictionary
  filtering); 29 remain unchanged. Development misses fall to 99 KAIST / 146 GSD
  without losing prior gold recovery. Directional 내려다/쳐다도 annotation
  matches do not establish generic 어다 + 보다 composition. Clause-level
  transfer semantics, transitivity, lexical restrictions and Korean review remain.

- [x] **COV-017ag — Dictionary classes for reviewed intention/result endings.**
  The optional compatible filter shares the engine's eleven verbal intention
  and two result-transfer forms. Lexical adjective-only entries conflict;
  verbal homonyms remain, and unknown provider classes are not guessed.
  Per-entry reasons identify `intention_verb` or `result_transfer_verb` and
  the ending's component index. Honorifics/outer particles do not alter the
  lexical class; auxiliary 하다 retains ownership of its own ending in
  좋아하려다가보면 and 좋아해다주었다. Neighboring 으려면/으려고 and
  을는지 retain their adjective readings. Negative-auxiliary class inheritance,
  other ending families and contextual senses remain unreviewed.
  Evidence: 122 [dictionary-policy cases](../tests/fixtures/dictionary-attachments.json)
  (70 required / 52 forbidden), [entry/unknown/CLI/cache tests](../tests/dictionary_attachments.rs),
  browser filtering/gloss/export/source selection, and
  [source/candidate comparison](attachment-connectives-evaluation.json).
  Across 3,162 surfaces, raw and headword-only candidates are unchanged; the
  compatible filter removes 52 individually tracked conflicts. All 30 stress
  fingerprints remain unchanged. The additional 노래다 → 노랗다 + 어다
  conflict has its own regression; 노래 + 이다 + 다 remains. The catalog adds
  source -려는 (86688) beside -으려는 (86717), preserving both expression IDs.

- [x] **COV-017ah — -(으)려나 question and expression homonyms.**
  Canonical 으려나 recovers both allomorphs with existing irregular handling.
  The question ending allows verbs/adjectives/copulas and 시/었/겠; recovered
  더/으리 are rejected. The engine's atomic 어야겠 follows its final modal
  boundary, with contextual scope unjudged. The two shortened intention-expression
  sources retain narrower notes without suppressing valid question readings or
  inserting 하다. Four dictionary homonyms remain separately selectable.
  Polite 요, explicit copulas, existing omitted honorific copulas and 답다
  derivation compose; broader nominal/particle and omitted-copula uses remain open.
  Evidence: [92 cases](../tests/fixtures/validity.json) (69 required / 23 forbidden),
  [Unicode/class/dictionary/CLI/corpus tests](../tests/ryeona.rs), eight source
  reviews, browser allomorph/homonym selection and [comparison](ryeona-evaluation.json).
  Across 3,253 ledger/policy/stress surfaces, 313 candidates are added with no
  removals or provenance changes; all 30 stress fingerprints are unchanged.
  Development results remain identical (99 KAIST / 146 GSD misses). The unchanged
  KAIST TEST sentence MH2_0010-s336 newly recovers 좋아지다 for 좋아지려나;
  this sentence is now explicit regression evidence, not held-out evaluation.
  The corpus lexical lemma lacks a dictionary headword; the required dictionary
  alternative 좋다 + 지다 remains. Following inference 보다 is COV-019l.

- [x] **COV-017ai — Literary assertions -(으)니라/-느니라.**
  Added dictionary-listed stative/copular 으니라 and verbal/existential 느니라,
  with ㄹ/allomorph and irregular boundaries. The first permits honorific 시;
  the second additionally permits past/modal markers. Known auxiliary and 답다
  classes constrain bare attachment, while uncertain negative/existential
  paradigms remain visible: KRDict explicitly illustrates 되지는 않으니라.
  The optional dictionary policy checks bare lexical class conflicts, preserves
  valid 크다/늦다 homonyms, separately written auxiliaries and unknown providers,
  and follows each ending's owner. It does not treat honorific/past/modal use as
  bare lexical attachment. Evidence: [54 morphology cases](../tests/fixtures/validity.json)
  (37 required / 17 forbidden), [15 dictionary-policy cases](../tests/fixtures/dictionary-attachments.json)
  (12 required / 3 forbidden), [tests](../tests/nira.rs), three complete unchanged
  KAIST sentences, browser source/homonym/export checks and
  [the source/output review](nira-evaluation.json). Vowel-final omitted copulas
  are COV-020j. This modern dictionary-listed literary register does not imply
  general historical or dialectal grammar coverage.

- [x] **COV-017aj — Copular conditional/concessive 라 endings.** Added
  라도, 라야 and 라야만 with explicit/omitted copula and 아니다 boundaries.
  All permit honorific 시; only 라도 additionally admits 더 and conjectural
  으리. Bare lexical predicates, command 으라 and unsupported prefinals retain
  distinct boundaries. Factual 라 + 도 remains beside bundled 라도, matching
  the original 교양만이라도 annotation. 라야 + 만 remains beside 라야만.
  Evidence: [73 judgments across 72 cases](../tests/fixtures/validity.json),
  [role/boundary, dictionary/CLI and corpus tests](../tests/ra_conditions.rs),
  four complete unchanged corpus sentences, browser role/source checks and
  [the source/output review](ra-condition-evaluation.json). Particle homonyms
  are COV-018r and vowel-final copula omission is COV-020k. Contextual discourse
  and temporal readings, other following auxiliaries/particles and independent
  Korean review remain open.

- [x] **COV-017ak — Concessive and counterfactual predicate endings.** Added
  -ㄴ들/-은들, -(으)ㄹ망정, -(으)ㄹ지언정 and past -던들 with distinct coda,
  irregular and prefinal boundaries. NIKL's 있은들/없은들 forms are retained;
  -는들 is not substituted. Explicit copulas, 아니다, auxiliary chains,
  답다 derivatives and polite 요 preserve ordered components. 학생인들 has
  both 학생 + 인들 and 학생 + 이다 + 은들. Evidence: [130 judgments and three
  integration tests](../tests/concessive_endings.rs), six complete annotated
  training sentences, and [source/candidate review](concessive-ending-evaluation.json).
  All six target corpus misses are recovered; exposed fixtures are not unseen
  evaluation. The report links the novel 간들/한들 observations to their new
  predicate paths. Broader 은들 prefinals, omitted copulas, discourse conditions
  and independent Korean review remain open. The inherited 따다 + 어 + 를 +
  이다 alternative in 딸이었던들 is tracked for COV-020 attachment review.

- [x] **COV-017al — Recurring-condition -(으)ㄹ라치면.** Added both allomorphs
  with honorific 시, regular/irregular verb recovery, auxiliary groups and polite
  요. Source-attested existential 있다 remains available. Explicit copulas,
  derived 답다, represented adjective auxiliaries and unsupported prefinal stacks
  do not inherit the verb license. Dictionary filtering checks lexical adjective
  entries separately from raw generation, follows the dependency through
  지-negatives, and resets it at other auxiliaries. 늦다 homonyms remain separate;
  unknown evidence stays unknown. Evidence: [42 raw judgments and class/CLI tests](../tests/llachimyeon.rs),
  ten [dictionary-policy judgments](../tests/fixtures/dictionary-attachments.json),
  two [complete KAIST sentences](../tests/fixtures/kaist-llachimyeon.conllu),
  browser source/selection/export checks and [source/candidate review](llachimyeon-evaluation.json).
  Both target gaps are recovered, including the COV-018x 있을라치면 observation.
  All 37 converted fixture rows match; frozen evaluation and novel output remain
  unchanged. Independent Korean review, contextual sense selection and wider
  combinations remain open.

- [x] **COV-017am — Necessity ending -(으)ㄹ밖에.** Both allomorphs and
  their reviewed attachments pass source, browser and package validation.
  KRDict 85762/85772 support both allomorphs, verbs/adjectives/copulas, 시 and 었.
  All ten ending example surfaces, NIKL spelling examples, irregular/auxiliary/
  답다 composition and inferred polite 요 have exact role judgments. Restrictive
  particle 밖에 remains distinct; NIKL's continuing 을밖에는 example has a
  separate forbidden final-ending/topic path. [66 judgments and CLI/dictionary
  tests](../tests/necessity.rs) pass; [the review](necessity-ending-evaluation.json)
  preserves the unjudged queue, missing KRDict headword 되돌려받다 and novel
  줄밖에 ambiguity. No annotated necessity-ending examples were found in the
  training search; COV-018z records its unrelated quoted-clause miss.
  Independent review, contextual interpretation and wider copula omission remain
  open rather than receiving an unsupported blanket license.

- [x] **COV-017an — Explicit quoted-question allomorphs.** Implemented and
  validated with COV-018z, including browser sources and Nix packages.
  KRDict 87443/87444 supply -느냐고/-으냐고, including the previously missing
  source example surfaces, their prefinal/irregular boundaries and separate
  browser labels. The general 냐고 alternative remains. Per-entry dictionary
  checks reject a known lexical verb before bare adjectival 으냐고 but retain
  an unknown standalone auxiliary homonym. The frozen corpus gains
  빼앗느냐고 (MH2_0169-s711/4); no previous matches are lost. This is lexical
  recovery evidence, not a claim of full syntactic parsing or contextual class
  selection. See the [shared evaluation](quoted-bakke-evaluation.json).

- [x] **COV-017ao — Familiar informative and reported endings.** Implemented
  and validated with Rust, corpus, browser, full-dictionary packaged checks
  and final Nix CLI/web builds. Covers 단다/는단다, factual 란다 versus command 으란다,
  냔다/느냔다/으냔다, 잔다 and 더란다. Fourteen full KRDict entries
  distinguish informative and reported senses without inserting implicit 하다.
  [144 raw judgments](../tests/danda.rs) preserve prefinal, irregular,
  auxiliary, 답다 and copula boundaries; 23 separate dictionary-policy judgments
  preserve homonyms, uncertain existential classes and component ownership.
  The complete KAIST/GSD training fixtures recover all 13 selected targets;
  frozen KAIST test gains 나왔단다 and 있겠단다 without baseline edits.
  Independent review, contextual interpretation and the unjudged candidates
  remain open. The synthetic 뿍다 hypothesis has no dictionary entry.
  See the [source and candidate review](danda-evaluation.json).

- [x] **COV-017ap — Confirming/reported -다지/-라지 and polite forms.**
  Implemented and validated with Rust, corpus, browser, full-dictionary
  packaged checks and Nix CLI/web builds. Nineteen full KRDict entries distinguish confirmation, reported
  speech and dismissive commands. 다지/는다지/라지/으라지 take one polite 요;
  contracted 다죠/는다죠/라죠/으라죠 retain their own sourced components.
  Factual 라지 and command 으라지 remain separate, including after honorific 시.
  [243 raw judgments](../tests/daji.rs) and 42 dictionary-policy judgments cover
  source examples, prefinals, irregulars, auxiliary/답다/copula ownership and
  lexical alternatives. The same audit fixes COV-017ao's unsupported ㅂ/ㅎ
  recovery before attached present 는단다; all 27 observed removed candidates
  have individual forbidden judgments. Frozen corpus recall is unchanged.
  The GSD training annotation for 좋다지요 remains verbatim (좋다 + 지다 after
  conversion), with its mismatch reported rather than rewriting gold.
  Independent Korean review, contextual interpretation and the unjudged queue
  remain open. See the [source and candidate evaluation](daji-evaluation.json).

- [x] **COV-017aq — Contrasting reported clauses (-다지만 family).**
  Rust/corpus, browser, full-dictionary packaged runtime and Nix checks pass.
  Ten full KRDict grammar-expression entries
  cover 다지만/는다지만, factual 라지만 versus command 으라지만,
  냐지만/느냐지만/으냐지만, 자지만 and 더라지만, with one inferred polite 요.
  Both bundled 더라지만 and its split retrospective alternative remain;
  the latter uses the explicit longer entry, not just the shorter 라지만 note.
  [160 raw judgments](../tests/dajiman.rs) and 45 dictionary-policy judgments
  cover prefinal/irregular boundaries and lexical/auxiliary/derived/copular
  ownership. Per-entry question checks retain explicit existential adjectives
  and compatible verb homonyms; negative auxiliaries are not rejected solely
  from an inherited adjective class. Wider negative paradigms remain COV-019h.
  Four newly recovered KAIST training targets and two frozen test gains are
  recorded without changing gold or baselines; the neighboring 나라 + 이다 + 지만
  parse remains. The full dictionary-compatible novel output is byte-identical.
  These ten expressions have POS 품사 없음 and are outside the 715-entry queue;
  its 295 scoped/419 unreviewed counts are unchanged. Broader outer particles,
  contextual interpretation and independent Korean review remain open.
  See the [source and candidate evaluation](dajiman-evaluation.json).

- [x] **COV-017ar — Long contrast ending -지마는.**
  Rust/stress/corpus, browser, Nix and full-dictionary package checks pass.
  KRDict 78637 supports predicates and 이다,
  past/modal composition, and the independently listed shorter -지만 (78638).
  The long ending now composes with honorifics, auxiliaries, 답다 derivation,
  vowel-final omitted copulas and inferred polite 요. Article 40 shortening
  preserves 흔치마는 and 깨끗지마는 with existing pronunciation boundaries.
  [79 judgments across 77 cases](../tests/jimaneun.rs) cover exact components,
  spelling/prefinal boundaries and both dictionary filters with CLI parity.
  Existing 지 + 마는 and lexical readings remain. Six unchanged complete KAIST
  training sentences already had matching lemmas; the new ending structure
  does not claim recall gains or change their gold. Frozen reports are unchanged.
  The novel gains ending alternatives at 62 tokens, with none removed.
  Wider outer particles and contextual interpretation remain open.
  See the [source and candidate evaluation](jimaneun-evaluation.json).

- [x] **COV-017as — Assertive and reason-reporting -다니까 family.**
  Rust/stress/corpus, browser, Nix and full-dictionary package checks pass.
  Nine canonical statement, factual,
  command, question, proposal and retrospective endings compose with source-listed
  full 는, contracted ㄴ and polite 요. 47 full KRDict entries retain all senses;
  76 exact source-example tokens sample all 74 senses and two additional cases.
  [223 raw judgments](../tests/danikka.rs) and 49 dictionary-policy judgments
  cover class/allomorph/prefinal boundaries, copulas, auxiliaries and 답다.
  도와달라니까 retains request auxiliary 달다. The explicit 들으냐니까는
  example conflicts with its adjective-only note, so that lexical-head/topic
  reading remains Unknown in dictionary assessment; bare/polite-only forms
  retain the usual class check. Source typos are preserved without spelling repair.
  Two unchanged KAIST training targets gain matches; frozen reports are unchanged.
  Three novel hypotheses are added at two tokens, with no prior candidates removed.
  Seven ending entries enter the scoped inventory; forty expression sources are
  outside its POS-filtered queue. Broader paradigms and independent review remain.
  See the [source and candidate evaluation](danikka-evaluation.json).

- [x] **COV-017at — Short reported statements, requests, proposals and questions.**
  Implemented nine canonical endings and their polite 요 variants. Rust/stress,
  browser, frozen-corpus and Nix/package checks pass. 28 full source entries
  preserve 51 senses, sampled by 59 exact source excerpts. [168 raw judgments](../tests/short_reports.rs)
  and 23 dictionary-policy cases cover allomorphs, prefinals, auxiliaries, copulas,
  답다 and command/intention ambiguity. 도와달래 now includes 돕다 + 달다 + 어 + 으래.
  입으냬요 remains Unknown because its source example conflicts with the adjective
  note; bare/other-head checks remain. 가져다 달래요 also supports COV-019r.
  Two unchanged GSD training examples gain complete lemma matches. Frozen grouped
  totals are unchanged, while candidate means and one partial lemma recovery change.
  The novel gains 137 hypotheses at 95 tokens, with none removed; contextual
  interpretation remains unjudged. Eight ending sources enter the scoped queue,
  with twenty expression sources tracked separately. Independent review remains.
  See the [source and candidate evaluation](short-reports-evaluation.json).

- [x] **COV-017au — Action reason/purpose -느라/-느라고.**
  Implementation, Rust/stress/corpus, browser and Nix/package checks pass.
  The missing short 느라 joins full
  느라고 with source-listed honorific 시 and polite 요; tense/modal/retrospective,
  known adjective/답다 and copular paths are rejected. Dictionary `neura_verb`
  conflicts belong to each lexical entry owning the ending, preserving verb
  homonyms and unknown entries. [96 raw judgments](../tests/neura.rs), 22 policy
  cases, all eight source-example groups, and ten complete unchanged training
  sentences cover this scope. Six training tokens gain grouped lemma matches,
  including GSD's original noisy 떠다 annotation, retained separately from 떨다.
  Frozen reports are byte-identical; six novel records gain provenance only.
  Subject identity, clause mood and interpretation remain contextual; broader
  outer particles and independent review remain open. Two source entries enter
  the scoped queue. See the [evaluation](neura-evaluation.json).

- [x] **COV-017av — Doubt endings -ㄹ라고/-을라고 and intention homonyms.**
  Added the rhetorical ending and separately licensed polite expression, with
  adjective/copula, honorific/past and polite-only modal paths. [125 judgments](../tests/llago.rs)
  (105 required, 20 forbidden) and all 50 example groups from six full entries
  pass raw/dictionary/CLI checks. 늘릴라고 now recovers 늘리다 in the unchanged
  GSD training gold; this is lemma recovery, not confirmation of its colloquial
  intention sense. Factual/command 라고 and existing -(으)려고 remain distinct.
  Full Rust/stress, frozen-corpus, browser and Nix/package checks pass. Frozen
  gold matches are unchanged; three candidate means increase. The novel gains
  21 hypotheses at 11 records, none removed, including lexical irregular
  candidates needing COV-021d review. Two core sources receive scoped reviews;
  the two polite expressions are tracked separately. Broader -(으)려고 license
  corrections remain COV-017aw, with independent Korean review still pending.
  See the [candidate/source/performance evaluation](llago-evaluation.json).

- [ ] **COV-017aw — Intention connective versus final -(으)려고 licenses.**
  The initial audit found 먹겠으려고, 먹었으려고한다 and 학생이려고한다.
  The latter finite constructions are now constrained as described below. KRDict 68846/69067 distinguish verbal intention/change
  connectives from final rhetorical senses (including 넓으려고,
  풀었으려고 and 학생이려고). Review the connective's owning prefinal and
  lexical/auxiliary class without removing those final homonyms. Audit the
  asymmetric adjective notes with additional sources before assigning dictionary
  conflicts; the previously missing derived 학생다우려고 path is now present. COV-017av preserves
  all 25 source-example groups as regression evidence; it does not certify
  the full attachment space of these two existing entries.
  **Partial implementation:** derived 학생다우려고 now has the adjective path,
  and the browser label includes the rhetorical sense. Sixty candidate judgments
  cover the derived path and direct 하다/들다 constructions ending in 는다,
  다, 어요 or 습니다. These finite constructions reject a preceding represented
  copula or non-honorific prefinal, preserving earlier owners and right-hand tense.
  The [22-entry source review](ryeogo-source-review.json) records broader
  adjective/copula and tense notes in related shortened expressions. Their full
  expansions and lexical adjective/coercive readings remain unresolved; four
  explicit preservation checks prevent blanket pruning. Broader dictionary
  conflicts and standalone prefinal restrictions still need review. The
  follow-up [primary-source audit](ryeogo-license-source-audit.json) retrieves
  NIKL's full adjective state-making answer and both OpenDict final homonyms,
  resolving the vowel-adjective note asymmetry. Represented intention
  하다/들다 now marks known adjective entries `unknown`, independently of
  compatible verb homonyms. Negatives inherit the dependency; explicit 답다
  and adjective auxiliaries use their own class, while other auxiliaries reset
  ownership. Both dictionary filters retain these uncertain paths. Forty-five
  stable cases track 66 entry judgments, separately from raw required/forbidden
  judgments; 53 complete native entries preserve provenance. See the
  [follow-up evaluation](ryeogo-licenses-evaluation.json) and
  [earlier candidate evaluation](ryeogo-evaluation.json). Standalone prefinal
  exclusions and conflicting full expansions remain open; uncertainty does not
  certify state-making uses. The unchanged KAIST training sentence
  `MH2_0014-s388` explicitly annotates `인간적이려고 하는` as a copular
  connective construction; this competing evidence is tracked before broader
  exclusions. All four complete frozen corpus reports and both filtered novel
  outputs are byte-identical. Rust/stress, browser and x86_64 Linux Nix
  package/flake checks pass.
  The [full-expansion follow-up](ryeogo-expansions-evaluation.json) now recovers
  finite relational `인간적이려고한다`, retaining both whole-word and `-적`
  suffix readings as possible state-making hypotheses with unknown dictionary
  attachment. Existing copula/tense constraints on ordinary finite intention
  remain, and split `어 + 요` now obeys the same reviewed boundary as `어요`.
  Thirty stable raw cases (21 required / 9 forbidden) and 57 entry cases
  (119 judgments) cover ownership, homonyms, negatives and both polite paths.
  Retained copula/prefinal full expansions have explicit per-entry uncertainty;
  earlier and right-hand tense remain separate. The original KAIST sentence is
  now an offline regression (all eight converted tokens still match).
  A published linguist's independent usage corroborates the copular token,
  without certifying all generalized relational readings. Two new paths remain
  unjudged; standalone prefinal and contextual licenses remain open.
  Full Rust/stress and browser checks pass; x86_64 Linux CLI/web packages
  build and pass the complete-dictionary HTTP/CLI checks; flake checks pass.
  Three interleaved
  release runs process the 179,112-record novel in median 1.55 s (headword)
  and 1.52 s (compatible), with peak RSS below 30 MiB; this small sample
  does not establish statistical equivalence. The local preview is refreshed.
  The source audit also records Cho (2026), DOI `10.19033/sks.2026.3.91.35`,
  as a primary research lead. The official one-page preview and abstract
  distinguish final senses but provide no prefinal judgments; full-text review
  remains pending and supplies no new generation or attachment policy.
  This item remains open.

- [x] **COV-017ax — Remaining shortened intention expressions.**
  **Implemented for the reviewed attachment scope.** All six canonical paths
  now compose with their reviewed allomorph, prefinal, adjective, copula,
  derived 답다 and auxiliary boundaries. Fourteen full entries include the
  two previously unlisted assumption homonyms of -(으)려니, which license
  adjective/past/modal readings independently of shortened intention.
  All 82 source example groups are preserved, with 230 required and 63 forbidden
  raw judgments in [the tests](../tests/ryeo_expressions.rs). Both dictionary
  filters and CLI parity pass; 유학가다 and an unknown-head probe explicitly
  remain raw-only. The separate 들다 analysis of 먹으려든지 is retained.
  Eight unchanged training sentences recover seven gold matches; original
  annotation/spelling conflicts remain visible. Full-expansion conflicts stay
  under COV-017aw, and broader omitted-copula variants need separate review.
  Rust/stress, browser and x86_64 Linux Nix/package checks pass. The full novel
  comparison adds 59 hypotheses across 41 records, with no removals; this is
  candidate preservation, not contextual validation. See the
  [candidate and corpus evaluation](ryeo-expressions-evaluation.json).

- [x] **COV-017ay — Modern literary/request prayer endings.** Implementation
  and targeted tests cover 소서/으소서 and the synchronic 옵소서/으옵소서
  final bundle, canonical 으소서/으옵소서. Verbs and adjectives take the
  immediate (으) allomorph, ㄹ drops, and preceding honorific 시 stays separate.
  Existing auxiliary and 답다 derivations retain component ownership; represented
  copulas, wrong allomorphs and final-as-connector paths are excluded. This is
  structural recovery, without judging a prayer's contextual suitability.
  Evidence: 91 stable `soseo-*` judgments (59 required, 32 forbidden), four
  `attachment-soseo-*` shortened-stem policy cases, complete native fixtures,
  two original KAIST training annotations, [tests](../tests/soseo.rs),
  [corpus test](../tests/corpus.rs), [browser tests](../web/tests/browser.mjs),
  [draft corrections](soseo-draft-corrections.json), and
  [candidate comparison](soseo-evaluation.json). Rust/stress, pinned corpus,
  lint/format, browser, packaged native-dictionary and x86_64 Linux Nix checks
  pass. All 340 probe additions retain provenance; 277 remain unjudged. The
  full novel gains ten hypotheses across six records, with no removals under
  either dictionary filter. Independent Korean review remains pending.

- [ ] **COV-017az — General polite prefinal paradigms.** Audit -오-/-으오-,
  -옵-/-으옵-, 옵시-, 사옵-/사오-/삽 and their licensed combinations separately
  from COV-017ay's final bundle. Preserve full native source examples, including
  읽으옵고 in KRDict 86110; the modern final-ending implementation does not
  establish general prefinal attachment, tense/modal order or segmentation.
  Distinguish modern literary usage from historical/dialectal coverage, which
  remains deferred. Do not infer a general paradigm solely from 옵소서.
  **Partial:** the basic (으)오/(으)옵 paradigm now emits canonical 으옵,
  selecting allomorphs from both boundaries and preserving honorific, past,
  modal, auxiliary and derivation ownership. 읽으옵고 is covered. The three
  native 오리다 examples retain polite + final 으리다 components; the final
  bundle has a primary NIKL reference instead of an invented KRDict entry.
  Evidence: 133 stable `polite-*` cases (93 required, 40 forbidden), ten direct
  native tokens, 48 full native fixture entries, [tests](../tests/polite.rs),
  [source audit](polite-source-audit.json), and the individually reviewed
  [snapshot additions](polite-snapshot-changes.json). The distinct consonant-stem
  사오/사옵 and consonant-only 삽 paradigms now preserve ㄹ, reviewed tense/modal
  order, contractions and auxiliary/답다 ownership. Five primary-source tokens
  and 130 stable `humble-*` cases (96 required, 34 forbidden) are tracked in
  [tests](../tests/humble.rs) and the [source fixture](../tests/fixtures/humble-sources.json).
  Their teaching labels link actual external entries without invented KRDict IDs.
  Bundled 옵시/으옵시 and distinct 사옵시 now retain one prefinal component,
  local spelling ownership and source-listed earlier past/modal licenses. Four
  primary tokens and 167 stable `optsi-*` cases (132 required, 35 forbidden)
  are tracked in [tests](../tests/optsi.rs) and the
  [source fixture](../tests/fixtures/optsi-sources.json). The
  [draft correction](optsi-draft-corrections.json) preserves the past-permitting
  rhetorical 으려고 sense while testing the narrower intention construction.
  Modern 자오/자옵, consonant-following 잡 and bundled 자옵시 now use the
  source-reviewed 듣/묻/받/좇 lexical subset, preserving the whole dictionary
  predicates 듣잡다/받잡다 as independent alternatives. The newly required
  나이다 ending keeps the source-attested retained-ㅂ polite combinations,
  ordinary ㄹ deletion, bare verbal/existential classes and intervening
  prefinals. Twenty-four primary tokens and 336 stable `jaop-*` cases (154
  required, 182 forbidden), 69 complete native entries and ten dictionary-policy
  cases are tracked in [tests](../tests/jaop.rs), the
  [source fixture](../tests/fixtures/jaop-sources.json), and
  [evaluation](jaop-evaluation.json). The [draft correction](jaop-draft-corrections.json)
  preserves verbal 멀다 instead of rejecting all homonyms. The raw comparison
  adds 322 candidates across 162 of 9,573 probes with no removals; 185 are
  unjudged. Frozen corpus recall and per-token results remain identical; mean
  candidate counts rise slightly. The separate 하나이다
  candidate comparison retains annotated 하나 + 이 + 다 alongside the new
  literary alternative. The full 179,112-record novel adds 22 paths at 19 records
  under each dictionary filter and removes none. Three additions match required
  structural ledger paths; the other 19 remain unjudged, including contextual
  alternatives retained alongside existing readings. Wider bundled combinations,
  additional source-listed endings and their licensed combinations remain open.
  The 나이까 question and explicit 옵/으옵/사옵 combinations now preserve
  separate prefinal components with the same source-listed bare verbal/
  existential class and independent question conflict rule. Eight primary tokens,
  147 stable `naikka-*` cases (118 required, 29 forbidden), eleven policy cases,
  and 58 complete native entries are tracked in [tests](../tests/naikka.rs), the
  [source fixture](../tests/fixtures/naikka-sources.json), and
  [evaluation](naikka-evaluation.json). The [draft correction](naikka-draft-corrections.json)
  keeps basic politeness outside past tense instead of borrowing the separate
  subject-honorific bundle's earlier position. Across 9,720 probe surfaces,
  146 change with 642 added paths and no removals; 522 additions remain unjudged.
  All four frozen corpus reports are byte-identical and contain no normalized
  나이까 tokens, establishing preservation rather than new-ending validation.
  The full novel adds one unjudged 하다 + 나이까 path at 하나이까 under each
  dictionary filter, with a stable byte-span case ID and context recorded.
  Three interleaved release runs per filter retain median processing times of
  about 1.5 seconds for 179,112 records; these measurements do not establish
  statistical equivalence. The -(으)리까 question now preserves predicate,
  adjective and copula classes, retained ㄹ, vowel-final copula omission and
  explicit 오/으오/사오 components. Reviewed prefinal licenses, local spelling,
  auxiliary/답다 ownership and post-question 마는/만 are tested separately.
  Eleven direct primary tokens from seven senses, 172 stable `rikka-*` cases
  (137 required, 35 forbidden), ten policy cases and 64 full native entries are
  tracked in [tests](../tests/rikka.rs), the
  [source fixture](../tests/fixtures/rikka-sources.json),
  [baseline audit](rikka-source-audit.json) and [evaluation](rikka-evaluation.json).
  The source audit corrects its initial ㄹ-deletion instruction: 리까 retains ㄹ;
  the separate basic polite boundary keeps its reviewed deletion. Across 9,886
  probe surfaces, 160 change with 1,031 additions and no removals; 898 additions
  remain unjudged. All four frozen corpus reports are byte-identical. Ten
  substring hits across all six pinned files are lexical/adverbial base + 까지,
  preserving their old outputs rather than providing question-ending gold.
  The full novel adds four paths at three records under each dictionary filter
  and removes none. Two additions match required structural ledger paths;
  the two alternatives at 비오리까마는 remain unjudged. All eight marker spans
  retain individual tracking, including the three unresolved question forms
  and two lexical 소리 + 까지 false positives. Three interleaved release runs
  per dictionary filter measured roughly 1.5-second medians for 179,112 records
  and about 30 MiB peak RSS; this is descriptive performance evidence rather
  than statistical equivalence.
  Direct omitted-copula 오 + 리까 now handles 누구오리까 and 어디오리까.
  The current publisher text of Choi Min-sun's Psalms translation independently
  attests 누구오리까; this supports literary occurrence, not an annotated parse.
  Twenty-five `copula-polite-*` cases (13 required, 12 forbidden), eight complete
  unchanged-output controls and 26 complete native entries are tracked in
  [tests](../tests/polite_copulas.rs), the
  [source audit](polite-copula-source-audit.json) and
  [evaluation](polite-copula-evaluation.json). Across 9,908 probe surfaces,
  68 change with 76 additions and no removals; 67 additions remain unjudged.
  All four complete frozen corpus reports are byte-identical, proving
  preservation rather than new omitted-polite gold. Under each dictionary
  filter the novel adds three paths at three records: the two requested
  structural readings and an unjudged nominal 비 + 이다 alternative at
  비오리까마는. Each has its stable byte-span ID, full candidate and context.
  The [draft correction](polite-copula-draft-corrections.json) records why
  generic omission before every polite follower was retracted: it introduced
  unsupported contracted 어 paths and changed a reviewed stress fingerprint.
  Three interleaved release runs per filter measured roughly 1.5-second
  medians and about 30 MiB peak RSS for the 179,112-record novel; this is
  descriptive evidence, not statistical equivalence.
  Broader polite allomorphs/followers, intervening markers, bundled honorific
  omission, 리까요 and independent linguistic review remain open.
  See [basic evaluation](polite-evaluation.json) and
  [humble evaluation](humble-evaluation.json) and
  [bundle evaluation](optsi-evaluation.json). The bundle probe comparison adds
  568 candidates across 140 of 9,276 surfaces without removals; 439 are unjudged.
  In that earlier bundle comparison, all four frozen corpus reports are
  byte-identical. The full novel adds one
  morphological path for 하옵시고 under each dictionary filter; its contextual
  interpretation remains unjudged. This row remains incomplete.

- [x] **COV-017ba — Bare verbal promise -ㅁ세/-음세.** The inventory audit
  found missing `연락함세`, `삼세`, `입음세` and `읽음세`. Canonical 음세 now
  preserves attached ㅁ, retained ㄹ + ㅁ (삶세), and local regular/irregular
  vowel boundaries. Bare represented copulas, 답다-derived adjectives and known
  adjectival auxiliary owners do not inherit verb attachment; unknown lexical
  alternatives remain. Per-entry dictionary checks preserve valid verb homonyms
  such as 크다/멀다/쓰다/있다 while identifying their adjective conflicts.
  Generic prefinal combinations are explicitly unknown, not certified licenses.
  Evidence: 55 stable `eumse-*` raw cases (37 required / 18 forbidden), 14
  dictionary-policy cases (8 required / 6 forbidden), all ten complete native
  example groups, 87 complete attributed entries, [tests](../tests/eumse.rs),
  one complete unchanged KAIST development sentence, CLI/library Unicode and
  component parity, and browser labels/choices/export. The
  [individual comparison](eumse-evaluation.json) retains all 199 added paths
  across 64 of 10,011 surfaces with no removals; 154 additions remain unjudged.
  KAIST `MH2_0149-s26/4` 줌세 now recovers 주다; this is the sole changed frozen
  corpus case. The other three full reports are byte-identical. The full
  179,112-record novel adds only the source-backed 맡다 + 음세 reading at
  맡음세 under each dictionary filter, with no removed readings. Three
  interleaved release runs per filter measured roughly 1.5-second medians and
  about 30 MiB peak RSS; these are descriptive measurements. Rust/stress,
  lint/format, frontend/browser and x86_64 Linux Nix package/flake checks pass; the
  packaged preview on 8081 is refreshed and verified. Prefinal
  paradigms, negative inheritance, following particles/endings and independent
  Korean-language/contextual review remain open under COV-017/COV-013.

- [x] **COV-017bb — Background connectives -ㄴ바/-은바/-는바/-던바.**
  All senses and 24 complete native example groups from KRDict 87110–87113
  support three canonical ending bundles 은바/는바/던바. 은바 uses attached
  ㄴ with ㄹ deletion or a full vowel boundary; literal 는바 deletes ㄹ and
  던바 retains it. 은바 accepts listed 시; 는바/던바 accept listed 시/었/겠.
  Represented copula and adjective owners retain 은바/던바; bare 는바 selects
  verbs or listed existential exceptions. Optional per-entry dictionary policy
  identifies bare adjective conflicts while preserving verbal homonyms and
  있다/없다/계시다 exceptions. Unknown lexical classes remain hypotheses.
  Evidence: 98 stable `ba-*` raw cases (78 required / 20 forbidden), 13 policy
  cases (8 required / 5 forbidden), 84 complete attributed native entries,
  [four regression tests](../tests/background_ba.rs), CLI/library NFC/NFD and
  filter parity, and browser choices/source labels/export. NIKL consultation
  325710 explicitly approves 확인한바 in the supplied report context. The
  [individual comparison](background-ba-evaluation.json) retains all 546 added
  paths across 103 of 10,109 surfaces with no removals; 463 remain unjudged.
  Discovery in all six pinned corpus files finds only lexical 이른바, with no
  annotated target ending. All frozen per-token grouped matches remain; only
  ambiguity means in the two test summaries change on lexical 이른바. Both
  filters compare all 179,112 novel records, retaining the lexical adverb and
  adding one unjudged 이르다 + 은바 path at each of two occurrences, with no
  removals. Rust/stress, pinned corpus, lint/format, frontend/browser and packaged
  Nix/flake checks pass on x86_64 Linux; the refreshed 8081 preview matches the tested
  bundle and complete-dictionary CLI output. Bound noun 바, omitted-copula variants, wider polite/
  historical combinations, negative inheritance and independent Korean-language/
  contextual review remain open under COV-017/COV-013; this batch does not
  certify them or introduce nominal-case attachment to these connectives.

- [x] **COV-017bc — 느니 comparison/listing/assertion and comparison/reason bundles.**
  Implementation and targeted regressions now cover canonical 느니, 느니만,
  느니만큼, 니만 and 으니만큼 from all senses and 34 complete example groups
  across eight native source entries. KRDict 85824 is an exact reviewed expression
  with 품사 없음; its identity is reviewed outside the ending/particle queue.
  No absent 으니만 entry or unsupported full comparative allomorph is invented.
  Optional per-entry policy preserves verb/adjective homonyms and explicitly
  unknown prefinal, compound existential and auxiliary-role readings. NIKL
  331720 directly licenses 알다 + 니만큼 despite narrower KRDict notes; other
  bare verbal reason paths remain unknown. Evidence: 151 raw cases (111 required /
  40 forbidden), 16 policy cases (10 required / 6 forbidden), 103 complete native
  entries, [four tests](../tests/neuni.rs), five unchanged annotated corpus tokens
  in four full sentences, [source audit](neuni-source-audit.json) and
  [individual evaluation](neuni-evaluation.json). The complete comparison retains
  666 added candidates across 148 of 10,265 surfaces with no removals; 554 remain
  unjudged. All five selected corpus tokens become grouped matches; four are
  training observations, and one adds a frozen KAIST test match. Both novel
  filters preserve all 179,112 records, adding 17 paths at 12 occurrences without
  removals; their contextual interpretations remain unjudged. Rust/stress, pinned
  corpus, lint/format, frontend/browser and Nix package/flake checks pass on x86_64 Linux;
  the refreshed complete-dictionary preview has exact CLI/HTTP and asset parity.
  Contextual sense, wider prefinals/followers, missing full comparative entry
  and independent Korean
  review remain open under COV-017/COV-013.

- [x] **COV-017bd — Quoted statements/questions/commands/proposals with 느니.**
  Nine bundles now preserve canonical 다느니/는다느니/라느니/으라느니/자느니/
  냐느니/느냐느니/으냐느니/더라느니 from ten primary entries, all 11 senses
  and 49 complete example groups. Factual/copular 라느니 stays distinct from
  command 으라느니, including its explicit 시/더/으리 licenses. The source
  사 달라느니 extends only the bare request tail; no ordinary tense/honorific
  paradigm is borrowed for 달다. Exact expressions 88986/86074 retain 품사 없음
  outside the inventory queue. Evidence: 176 raw cases (133 required / 43 forbidden),
  16 policy cases (9 required / 7 forbidden), 143 complete native entries, 90 direct
  token cases and three explicitly joined auxiliary inputs, [four tests](../tests/quoted_neuni.rs),
  four annotated KAIST train tokens in two unchanged original sentences,
  [source audit](quoted-neuni-source-audit.json) and
  [individual evaluation](quoted-neuni-evaluation.json). Corpus 열등하다 uses
  a verbal derivation tag while KRDict labels it adjective; the original annotation
  is preserved without pretending to settle POS from lemma recovery. The original
  unspaced 결혼을하라느니 is an explicit COV-020p observation. The comparison
  retains 821 added candidates across 160 of 10,425 surfaces without removals;
  693 remain unjudged. All four frozen full dev/test reports and both 179,112-record
  novel streams are byte-identical; the four new annotated matches are training
  observations. Rust/stress, pinned corpus, lint/format, frontend/browser and
  x86_64 Linux Nix package/flake checks pass; the refreshed preview has exact complete-
  dictionary HTTP/CLI and asset parity. Contextual sense, wider prefinals/followers,
  unknown auxiliary roles and independent Korean review remain
  open under COV-017/COV-013.

- [x] **COV-017be — Exact comparative 느니보다/느니보다는 expressions.**
  Both native expression entries preserve 품사 없음 outside the 715-entry queue.
  Source-listed verbs, existential predicates/compounds and 시 use the existing
  literal ㄴ-onset boundary and immediate-owner checks. Unlisted generic prefinals
  remain dictionary-unknown; ordinary adjective/verb homonyms are checked separately.
  Evidence: 58 raw cases (48 required / 10 forbidden), twelve policy cases
  (eight required / four forbidden), 43 complete native entries, eight complete
  example groups/direct tokens and two explicitly joined auxiliary inputs,
  [four regression tests](../tests/neuni_comparison.rs),
  [source audit](neuni-comparison-source-audit.json) and
  [individual evaluation](neuni-comparison-evaluation.json). The comparison adds
  148 candidates across 55 of 10,479 inputs without removals; 99 remain unjudged.
  All four frozen corpus reports are byte-identical; both 179,112-record novel
  streams are byte-identical in debug/release comparisons. Six-file discovery and the novel
  have no exact target occurrences; no annotated recall gain or novel positive
  coverage is claimed. Rust/stress, lint/format, frontend/browser, pinned corpus
  and x86_64 Linux Nix package/flake checks pass. The refreshed preview has exact
  complete-dictionary HTTP/CLI and asset parity. Contextual choice, wider followers,
  contraction 느니보단 and independent Korean review remain open under COV-017/COV-013.

- [x] **COV-017bf — Realization/retrospective/guess endings -걸.**
  Native -은걸/-ㄴ걸, -는걸, -던걸 and -을걸/-ㄹ걸 preserve distinct
  canonical bundles, allomorphs, immediate owners and source-listed prefinals.
  Six polite expressions compose with separate 요. Bare 는걸 checks each
  dictionary verb/existential homonym; adjective/copula readings after licensed
  prefinals survive. Guess and regret senses remain unresolved, preserving the
  adjective paths licensed by guessing. Evidence: 164 raw cases (143 required /
  21 forbidden), eleven policy cases (eight required / three forbidden), 124 full
  native entries, 106 original groups and 105 direct source tokens, plus three
  NIKL tokens. [Four family tests](../tests/geol.rs), the
  [annotated corpus regression](../tests/corpus.rs),
  [source audit](geol-source-audit.json) and
  [individual evaluation](geol-evaluation.json) track each candidate change.
  Four original training tokens gain lemma recovery; frozen dev/test reports
  remain unchanged. The malformed native 끝난던걸요 is preserved as unjudged.
  The full comparison retains 1,832 additions at 299 of 10,803 inputs without
  removals; 1,564 remain unjudged. Both full novel filters retain ten additions
  at eight occurrences and all 5,555 optional spacing alternatives are unchanged.
  Rust/stress, lint/format, corpus, frontend/browser and x86_64 Linux Nix gates
  pass; the refreshed packaged preview has HTTP/CLI/export/asset parity.
  Bound-noun parsing, contextual sense,
  wider colloquial variants/attachment licenses and independent Korean review
  remain open under COV-017/COV-013/COV-020.

- [x] **COV-017bg — Exclamation endings and native redirects.**
  Distinct base 구나/군/구먼/구려, present 는구나/는군/는구먼/는구려,
  retrospective 더구나/더군/더구먼/더구려 and copular 로 counterparts retain
  their bundles, owner classes, listed prefinals and source-specific senses.
  구려 keeps its verbal recommendation sense. Bare verbal 더구나 remains
  unknown because its full note and direct 잘되더구나 example disagree.
  Four native 구만 arrows normalize with explicit variant provenance, preserving
  nonstandard input without normative certification; 92511 retains native
  headword 로구만. Eight polite expressions preserve existing bundles and
  licensed separate 요. Auxiliary 있다 is checked separately from lexical
  verb/adjective homonyms. Evidence: 276 raw cases (213 required / 63 forbidden),
  nineteen policy cases (ten required / nine forbidden), 175 full native entries,
  all 127 original groups/direct tokens and four NIKL tokens. The
  [four family tests](../tests/exclamation.rs),
  [six unchanged training targets](../tests/corpus.rs),
  [source audit](exclamation-source-audit.json) and
  [individual evaluation](exclamation-evaluation.json) preserve the evidence.
  All prior raw paths survive across 11,181 inputs; 1,480 additions remain
  unjudged. Frozen dev/test recall and individual cases are unchanged; mean
  candidate counts increase. Novel compatible filtering removes two reviewed
  누다+구나 lexical conflicts at 누구나, preserving whole-word readings.
  Rust/stress, lint/format, corpus, frontend/browser and x86_64 Linux Nix
  gates pass. The updated packaged preview has API/CLI/export/asset parity.
  Three optional novel spacing sidecars change (5,555 to 5,556 alternatives),
  with their original context and unjudged status retained.
  Quoted contractions, contextual
  sense/register, broader polite/follower licenses and independent review
  remain open under COV-017/COV-013/COV-020.

- [x] **COV-017bh — Quoted declarative exclamation contractions.**
  **Implemented for fourteen reviewed native expression identities.**
  먹는다는구나/간다는군/예쁘다는구나/먹는다더군 recover their
  predicates with distinct report bundles. Present ㄴ/는 allomorphs, local
  owner classes, listed prefinals, past/modal copulas and other-speaker
  더라는구나/더라는군 experience reports compose. Three polite forms
  preserve bundled and base + 요 alternatives without inserting implicit 하다.
  [Four family tests](../tests/quoted_exclamation.rs), 175 `qex-` raw and
  37 dictionary-policy cases, [full source audit](quoted-exclamation-source-audit.json)
  and [individual comparison](quoted-exclamation-evaluation.json) preserve
  all 56 groups, 55 unchanged direct targets and the unresolved native
  여행간다더군 joined spelling. Per-entry homonyms and uncertain verbal
  honorific/polite boundaries stay separate; Unknown retention is not
  grammatical-validity gold. Ten teaching labels retain actual 품사 없음
  source identities. Across 11,275 inputs, 1,563 paths are added and none
  removed; 1,309 additions remain unjudged. All four frozen dev/test reports,
  novel filter outputs and optional spacing sidecars are unchanged. The six
  pinned corpus files contain no targets for this family; no annotated gold
  is fabricated. Rust/stress, lint/format, corpus, browser and x86_64 Linux
  Nix gates pass, including packaged API/CLI/export/asset parity and refreshed
  preview. Other quote families and independent review remain open below.

- [x] **COV-017bi — Quoted question exclamations and recalled questions.**
  **Implemented for twelve reviewed native expression identities.**
  먹느냐는구나/좋으냐는군 now recover their predicates; general spoken 냐,
  verbal/existential 느냐 and adjective 으냐 stay distinct through
  는구나/는군/더군/더군요 reports. Eu allomorphs, local owner classes,
  listed prefinals, negative inheritance, derived 답다 and copula omission
  compose. All 51 original groups and unchanged direct targets appear in
  the [full source audit](question-exclamation-source-audit.json), with the
  narrow-note/verbal-example disagreement and NIKL 5876 preserved.
  [Four family tests](../tests/question_exclamation.rs), 251 raw and
  55 optional dictionary cases distinguish per-entry homonyms, explicit
  bundled/split polite paths and three inferred 군 + 요 candidates retained
  as Unknown. Unlisted 구나 followers have no forbidden gold; broader
  follower review stays COV-018aa. Honorific-only ordinary nonverbal 느냐,
  broader polite prefinals and unclassified negative owners remain Unknown.
  No implicit reporting 하다 or auxiliary connector is inserted.
  The [individual comparison](question-exclamation-evaluation.json) covers
  11,556 inputs, 3,776 added paths and zero removals; 3,399 additions stay
  unjudged. Four frozen corpus reports, novel filter outputs and spacing
  sidecars are unchanged. No target exists in the six pinned corpus files,
  so no annotated gold is fabricated. Twelve labels keep actual source POS
  품사 없음. Rust/stress, lint/format, corpus, browser and x86_64 Linux Nix
  checks pass, including packaged API/CLI/export/asset parity and refreshed
  preview. Other question/quote families and independent review stay open.

- [x] **COV-017bj — Quoted copular reports and command exclamations.**
  **Implemented for eight reviewed native expression identities.**
  학생이라더군 and 가라더군 now preserve factual copular and reported
  command readings with distinct 라/으라 bundles. Consonant/vowel/ㄹ and
  written irregular command allomorphs, 아니다, copula omission and local
  honorific/conjectural slots compose. Four original 라 entries have both
  factual and imperative senses; each command label preserves both the 라
  and 으라 identities without borrowing bare copular attachment for a
  lexical verb. Restricted 달다 request reports, bundled/split polite forms
  and two inferred Unknown 군 + 요 followers retain separate owner paths.
  Ordinary/derived adjective wishes and noncopular factual prefinal extensions
  remain Unknown; broader followers remain COV-018aa. No implicit reporting
  하다 or contextual sense is inserted. [Four family tests](../tests/copular_command_exclamation.rs),
  212 raw and 57 dictionary-policy cases and the
  [full source audit](copular-command-exclamation-source-audit.json) preserve
  all 53 original groups and unchanged direct targets. The
  [individual comparison](copular-command-exclamation-evaluation.json) covers
  11,701 inputs, 2,510 added paths and zero removals; 2,180 additions remain
  unjudged. Four frozen corpus reports, novel filter outputs and spacing
  sidecars are unchanged. No target exists in the six pinned corpus files,
  so no annotated gold is fabricated. Eight labels retain actual source POS
  품사 없음. Rust/stress, lint/format, corpus, browser and x86_64 Linux Nix
  checks pass, including packaged API/CLI/export/asset parity and refreshed
  preview. Proposal/conditional-question reports and independent review stay
  open below.

- [x] **COV-017bk — Quoted proposal exclamations and recalled proposals.**
  **Implemented for four reviewed native expression identities.**
  먹자는구나 and 살자더군 preserve 자는구나/자는군/자더군/자더군요,
  immediate proposal owners, consonant-initial stem boundaries and lexical
  alternatives. Explicit NIKL 시/past/modal exclusions transfer to the embedded
  proposal as marked inference; earlier auxiliary-chain prefinals remain local.
  Adjective/derived wishes, existential and unclassified negative auxiliary
  owners, unlisted prefinals and inferred 군 + 요 remain Unknown. Native
  polite bundled/split paths stay separate; unlisted 구나 followers remain
  unjudged under COV-018aa. No implicit reporting 하다 or contextual sense
  is inserted. [Four family tests](../tests/proposal_exclamation.rs), 173 raw
  and 59 dictionary-policy cases and the
  [source audit](proposal-exclamation-source-audit.json) preserve all 17 original
  example groups/direct tokens. The
  [individual comparison](proposal-exclamation-evaluation.json) covers 11,841
  inputs, 632 added paths and zero removals; 422 additions remain unjudged.
  Four frozen corpus reports, novel filter output and spacing sidecars are
  unchanged. No target exists in the six pinned corpus files, so no annotated
  gold is fabricated. Four labels retain actual source POS 품사 없음.
  Rust/stress, lint/format, corpus, browser and x86_64 Linux Nix checks pass,
  including packaged API/CLI/export/asset parity and refreshed preview.
  Conditional-question reports, parent inventories and independent review stay
  open below.

- [x] **COV-017bl — Conditional reported questions -(으/느)냐면.**
  **Implemented for three reviewed native expression identities.** Native
  IDs 80177/83769/80180 preserve 냐면/느냐면/으냐면, all 17 original example
  groups/direct tokens and distinct general/verbal/Eu owner and prefinal
  licenses. The [NIKL answer](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=311818)
  directly supports both 먹냐면 and 먹느냐면. Copulas, lexical alternatives,
  ㄹ/ㅂ/ㅎ boundaries and derived/auxiliary owners stay separate. Unresolved
  honorific-only nonverbal, negative/existential and inferred polite paths stay
  Unknown; no implicit reporting predicate or universal follower license is
  inserted. [Four family tests](../tests/conditional_question.rs), 126 raw and
  46 dictionary cases and the [source audit](conditional-question-source-audit.json)
  preserve the bounded scope and five byte-identical older 냐고/냬요 controls.
  The [individual comparison](conditional-question-evaluation.json) covers
  11,903 inputs, 1,774 added paths and zero removals; 1,572 additions remain
  unjudged. Four corpus reports, novel filter outputs and spacing sidecars are
  unchanged. Six target scans including 요/도 probes are empty; no annotated
  gold is fabricated. Three labels retain actual source POS 품사 없음.
  Rust/stress, lint/format, corpus, browser and x86_64 Linux Nix checks pass,
  including packaged API/CLI/export/asset parity and refreshed preview.
  General polite prefinals, wider followers, existential paradigms, parent
  inventories and independent Korean review remain open.

- [x] **COV-017bm — Formal proposal source and class review.** Both native
  -ㅂ시다/-읍시다 entries and all eight original example groups have source
  regressions, preserving consonant, vowel, ㄹ/ㄷ/ㅂ boundaries and lexical /
  auxiliary alternatives. Their verb notes do not settle contextual adjective
  wishes: NIKL [318597](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=318597)
  describes exceptions. Known adjective entries, adjective auxiliaries and
  unclassified negative owners retain Unknown; compatible verb homonyms and
  existing conflicts remain distinct. The canonical label links both native
  allomorph identities with their actual headwords/POS. [Four tests](../tests/proposal_review.rs),
  8 raw cases / 9 source judgments, 16 dictionary-retention cases, 73 complete
  attributed entries and [the source audit](proposal-source-audit.json) record
  the scope. [The evaluation](proposal-evaluation.json) verifies 11,883
  byte-identical raw outputs. Seven regression inputs change only per-entry
  assessments; two novel spans change the adjective 되다 homonym to Unknown
  without adding/removing candidates or rejecting the compatible verb.
  Full Rust/stress, pinned corpus, lint/format, frontend, browser and x86_64 Linux
  Nix checks pass, including packaged API/CLI/export/assets and preview.
  Both inventory entries have scoped dispositions. Contextual wish subsets,
  social register, further paradigms and independent Korean review remain open.

- [ ] **COV-018 — Further particle attachments and pronoun contractions.**
  **Partial: COV-018a–k and COV-018m–z cover post-ending, outer choice, emphatic,
  concessive, definition, enumerative, destination and recipient particles,
  including nominal (이)라고 alternatives, the noun-attached 치고 family and
  source-attested case marking after range particles, and comparison/extent particles.**
  Remaining: pronouns outside the existing finite paradigms. Preserve homonym-specific
  dictionary labels and review additional ending/particle licenses.
  Include quoted clauses marked as nominals: KAIST MH2_0169-s444/3 살겠다가
  is annotated 살 + 겠 + 다 + 가 (subject particle), not a -다가 example.
- [x] **COV-018a — Post-ending particles.** Connective 는/도 and scoped
  restrictive 만 now compose, including 먹고는, 하면서도, and 통해서만.
  Final-ending 만/마는 supports 있습니다만, 먹는다마는, copulas and auxiliary
  groups. The browser distinguishes concessive 만 (86555) from nominal or
  restrictive 만 (86554); full 마는 (86552) is never stripped from bare nominals.
  Evidence: [particle paths/boundaries](../tests/particles.rs), eight
  `post-ending-*` ledger cases, five offline corpus tokens, dictionary/CLI and
  browser homonym tests. One compatibility snapshot gains four reviewed
  unverified lexical hypotheses; all previous analyses remain. See
  [scope](rules.md#post-ending-particles-cov-018a) and
  [development comparison](post-ending-evaluation.json).
- [x] **COV-018b — Outer choice/emphasis and nominal quotative particles.**
  Case/restrictive chains admit (이)나, (이)라도, (이)든지, and (이)야 with
  the allomorph selected by the immediately preceding surface. 어디까지나 and
  이제부터라도 recover their bases. Duplicate choice families are rejected;
  nominal, adverbial, nominalized, and reviewed post-ending readings coexist.
  Nominal (이)라고 is a `Particle`, distinct from copular `Ending` 라고;
  학생이라고 retains both alternatives. Labels link to particle entries and
  retain homonyms. Evidence: [path/boundary tests](../tests/particles.rs), twelve
  `chain-*` ledger cases, four annotated offline tokens, dictionary/CLI parity,
  browser/source-link tests, and [development comparison](particle-chain-evaluation.json).
  All 30 current compatibility fingerprints remain unchanged. See
  [scope and sources](rules.md#outer-choice-and-quotative-particles-cov-018b).
  Quoted clauses followed by subject particles and cross-token quotation
  structure are not implemented by these nominal paths.
- [x] **COV-018c — Emphatic/concessive particles and locative 서.**
  (이)야말로, (이)나마, 은/는커녕 and bare 커녕 compose with the existing
  nominal/suffix/particle order. Contracted ㄴ커녕 normalizes to 는커녕, as
  in 먹긴커녕 → 먹다 + 기 + 는커녕. Nominalizations, auxiliary groups, and
  adverbial phrases retain distinct roles; bare 커녕 has nominal attachment
  only. 나마 additionally accepts the source-listed adverbial 게 ending.
  Locative 서 now follows consonants too, including 서울서/시장서, and carries
  no foreign-base pronunciation assumption. This does not broaden the separate
  count-emphasis 서 homonym's lexical scope. No new auxiliary connector is added.
  Evidence: [boundary/role tests](../tests/emphatic_particles.rs), nineteen
  `emphatic-*` judgments, dictionary/CLI parity, twelve browser/source-link
  cases, and [evaluation](emphatic-particle-evaluation.json). Thirteen newly
  recovered corpus tokens have explicit tests. A fourteenth numerical gain,
  확약서 → 확약, stays a segmentation-review case, not a required linguistic
  judgment. See [scope and sources](rules.md#emphatic-and-concessive-particles-cov-018c017i).
- [x] **COV-018d — Definition/topic particles 란/이란.** Nominal allomorphs
  preserve 문화란 → 문화 and 학생이란 → 학생, with nominalization and suffix
  composition. They do not accept adverbial/case-marked bases; 학생 + 이 + 란
  is not substituted for the bundled particle or copula + ending. Unknown foreign
  bases retain explicit pronunciation conditions. Together with COV-017j this
  recovers 26 annotated groups, protected by complete source sentences and a
  stable-ID index. The same [evaluation](quoted-definition-evaluation.json)
  records eight remaining 라는 cases: three annotation/representation differences
  preserve existing copula + ending analyses; quoted-clause and omitted-copula
  fragments remain COV-018/020 review. No unsupported 라는 particle is added
  solely to match corpus segmentation. Evidence is shared with COV-017j above.
- [x] **COV-018e — Enumerative (이)라든가/(이)라든지 and choice (이)든가.**
  Six particle forms preserve nominal, reviewed adverbial/case-phrase and
  nominalization paths, alongside existing copular/ending alternatives.
  든가 separately follows final 다/는다/라 allomorphs; 먹는다든가 retains both
  the bundle and 는다 + 든가. Nominal suffixes, polite 요, NFD and conditional
  foreign-base pronunciation compose. Full 이라든가/이라든지 have nominal-only
  attachment; the short forms do not strip subject/object case phrases.
  The viewer uses explicitly mapped related entries when the pinned dictionary
  lacks a separate 라든가 or 이든가 particle entry. Evidence:
  [path/role/boundary tests](../tests/enumerative_particles.rs), twenty
  `enum-*`/`choice-particle-*` ledger cases, dictionary/CLI parity and browser
  source links. Three further ledger judgments exclude known adjective/copula
  classes before present 는다 even after 시, preventing the composed particle
  reading from bypassing the same restriction. [Scope and sources](rules.md#enumerative-particles-and-choice-ending-cov-018e017p)
  and [evaluation](enumerative-particle-evaluation.json) retain unjudged candidates.
  Further particle stacks and quoted-clause attachment remain open.
- [x] **COV-018f — Emphatic destination/recipient particles.** 에다/에다가,
  에게다/에게다가, 한테다/한테다가, (으)로다가 and 보고/더러 preserve
  nominal paths and existing predicate readings. Separate emphatic 다/다가
  attaches after eight reviewed case forms or seven deictic location/direction
  words, retaining bundled and component alternatives. Nominalizations, suffixes,
  outer particles, NFD and conditional foreign pronunciation compose. Arbitrary
  nouns, adverbs, predicate endings and subject/object case phrases do not license
  emphatic 다/다가. Recipient suitability and contextual senses remain explicit
  limitations. Evidence: [path/boundary tests](../tests/destination_particles.rs),
  twenty-four `destination-*` ledger cases, three complete development sentences,
  dictionary/CLI parity and browser homonym/source-link checks. [Evaluation](destination-particle-evaluation.json)
  records two KAIST and one GSD recovery, with all thirty stress fingerprints
  unchanged. [Scope and sources](rules.md#destination-recipient-and-emphatic-adverbial-particles-cov-018f)
  leave other adverbial bases and further particle stacks open; COV-018g adds
  enumerative 다/이다 separately.
- [x] **COV-018g — Enumerative 다/이다 particles.** Vowel-final 다 and
  consonant-final 이다 attach to nominals, bounded suffixes and nominalizations,
  preserving copular and emphatic alternatives. Prior case phrases and predicate
  endings do not license enumeration. Foreign-base pronunciation conditions and
  existing outer 들/요 slots remain explicit hypotheses. Identical paths such
  as 저기 + 다 merge provenance and display “Enumeration / emphasis”; separate
  copula paths retain their roles. Evidence: [boundary/composition tests](../tests/enumerative_da.rs),
  sixteen `enumerative-da-*` judgments, an unchanged annotated copula sentence,
  dictionary/CLI parity and browser source/alternative checks.
  [Evaluation](enumerative-da-evaluation.json) records every candidate change,
  unchanged development recall and three individually reviewed stress changes,
  retaining prior candidates and hashes. Contextual enumeration, lexical
  suitability and broader particle combinations remain open. See
  [scope and sources](rules.md#enumerative-daida-particles-cov-018g).
- [x] **COV-018h — 은 after consonant-final connectives.** The connective
  attachment inventory now accepts both topic/emphatic allomorphs 은/는 with
  their existing consonant/vowel boundary checks. 먹지만은 and 의사지만은
  retain bundled 지만 + 은 alongside existing component alternatives.
  Wrong allomorphs and arbitrary adnominal/formal endings remain excluded.
  Source: KRDict [은 86111](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86111),
  sense 3. Evidence: `closed_connectives_accept_eun_without_losing_neun_boundary_checks`
  in [tests](../tests/omitted_connectives.rs), six `omitted-connectives-topic-*`
  judgments, dictionary/CLI parity and browser source checks. This corrects
  the existing allomorph omission; it does not expand the connective inventory
  or auxiliary-internal particle slots.
- [x] **COV-018i — Reviewed particles after 서 connectives.** Connective
  고서 admits the existing 은/는, 도, 만, 요 slots and emphatic 야; 어서
  also admits 야. 부터 follows 어서/고/으면서, while comparative 보다
  follows 어서, with existing outer particles. Examples include 돌리고서는,
  되어서야, 나오면서부터 and 통해서보다는. Together with COV-017q,
  nine complete unchanged KAIST development sentences become exact grouped
  matches; no prior gold or candidates are lost. Evidence: [tests](../tests/seo_connectives.rs),
  twenty-nine ledger cases across both items, attributed dictionary fixtures,
  CLI/browser checks and [evaluation](seo-connective-evaluation.json).
  Other ending/particle families, especially broader 부터/보다 attachment,
  remain for review. No unrestricted clause nominalization is introduced.
- [x] **COV-018j — Noun-attached 치고 family.** 치고, 치고는 and 치고서
  retain separate source-backed bundles, plural bases and reviewed topic/polite
  composition. 학생치고는 preserves both 치고는 and 치고 + 는; 사람치고서는
  preserves 치고서 + 는. Existing 치다/고치다/놓치다 predicate readings remain.
  Bare predicate endings and intervening case particles do not license noun
  attachment. The GSD 아파트치고 group now recovers 아파트. Evidence:
  [boundary/ambiguity tests](../tests/chigo_particles.rs), 63 stable ledger
  cases, one complete unchanged annotated sentence, dictionary/CLI parity,
  source-linked browser alternatives and [comparison](chigo-evaluation.json).
  The required raw 교수님 plural paths have an explicit dictionary headword gap;
  the existing 교수 + 님 + 들 alternatives survive dictionary-only filtering.
  Further outer particles, repeated topics, nominalized-base semantics and
  contracted 치곤 remain unjudged in the report; COV-018 remains open.

- [x] **COV-018k — Case marking after range particles.** Source examples
  support 까지 + 가/를/에/로 and 부터 + 가 across the ordinary particle
  ordering stages. 역사까지를, 여기까지가, 페이지까지로, 정착되기까지에는
  and 제목부터가 now recover their bases. Existing nominalizations,
  honorific/plural suffixes, topic/polite particles and attached ㄹ compose;
  case allomorphs still follow the immediately preceding sound. Evidence:
  [boundary tests](../tests/range_case_particles.rs), 47 stable ledger cases,
  dictionary/CLI parity, source-linked browser alternatives and
  [candidate/source comparison](range-case-evaluation.json). One unchanged
  annotated sentence preserves the KAIST 역사까지를 gain; another records the
  separate unjudged COV-018l observation. All prior analyses remain; two existing
  contracted paths gain provenance only. Other case chains remain open.
- [ ] **COV-018l — Resolve 마다 + 에 distribution.** The complete KAIST
  `MH2_0159-s285/15` observation 편마다에도 is retained in
  [the fixture](../tests/fixtures/kaist-range-case.conllu). Its expected
  편 + 마다 + 에 + 도 path is not generated. KRDict 마다 specifies noun
  attachment but does not settle following case marking. The primary paper's
  abstract links distribution to semantic restrictions; the full distribution
  evidence and Korean review are still needed. This observed gap is neither
  a required nor forbidden candidate judgment. A [six-file discovery audit](mada-distribution-audit.json)
  finds only that original occurrence across pinned train/dev/test partitions,
  records current filter behavior, and tracks primary full-text retrieval and
  regional-distribution leads. See the named followup and bibliography in
  [the review](range-case-evaluation.json).

- [x] **COV-018m — Comparison and extent particles.** Noun-attached 토록
  and 마냥, noun/particle 만치, and explicit 어서 + 만치/만큼 now compose
  with existing suffixes and reviewed outer particles. 필생토록 recovers 필생;
  있어서만치는 and 있어서만큼은 preserve the connective and particle roles.
  Lexical 그토록 and standalone 마냥 remain selectable, and shortened
  하다 + 도록 paths remain. Grammar lookup excludes the bound-noun 만치 and
  adverb 마냥 homonyms from particle labels. Evidence:
  [role/boundary tests](../tests/extent_particles.rs), 63 stable ledger cases,
  two complete unchanged corpus sentences, dictionary/CLI parity and browser
  alternatives/source checks. [The comparison](extent-evaluation.json) accounts
  for all additions and retains explicit followups for further connectors,
  case/particle chains and nominalized-base semantics. Adnominal + bound-noun
  joining is a separate representation; its valid homonym is not forbidden by
  an exact particle-role judgment. COV-018 remains open.

- [x] **COV-018n — Adverbial bases before ordinary focus particles.** Added
  dictionary-free Adverbial alternatives before 도/은/는/만/까지/부터, including
  아직도, 퍽도, 너무도, 자세히는 and 아직까지. New paths check the whole
  particle chain; arbitrary noun-case marking is not inherited. Source-listed
  derived adverbs also accept reviewed range particles. Nominal and unchanged
  candidates remain, including genuine 오늘/지금 homonyms. The optional dictionary
  conflict filter distinguishes 학교 + 도 as nominal and 아직 + 도 as adverbial.
  Evidence: [55 ledger cases](../tests/fixtures/validity.json) (38 required / 17
  forbidden), [role/dictionary/CLI tests](../tests/adverb_focus.rs), 28 attributed
  lexical entries and five complete KAIST/GSD sentences covering six explicitly
  annotated adverb-particle tokens. Browser choices, glosses and exports agree
  with the CLI. [The review](adverb-focus-evaluation.json) records 54 additions
  across 82 surfaces with no removals/provenance changes; three stress hashes
  have four reviewed new hypotheses with old hashes preserved. Corpus lemma
  recall is unchanged; the novel gains complete filtered readings for 86 tokens
  across 18 types without losing any previous filtered readings. The inherited
  adverbial + particle + copula hypotheses remain unjudged under COV-020;
  additional particle subclasses and contextual sense selection remain open.

- [x] **COV-018o — Independent 게/게서 recipient and source particles.**
  내게/네게/제게 and 내게서/네게서/제게서 now preserve their represented
  pronoun base plus the dictionary-listed particle. Ordinary outer particles,
  contracted topics (내겐/내게선), emphatic object marking and 게 + 다/다가
  compose through existing particle stages. Whole words and predicate-ending 게
  remain selectable. [NIKL's analysis](https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=308388)
  explicitly distinguishes 네 + 게 from a 너에게 contraction; some corpus
  annotations use the latter segmentation, which is retained as a separate
  normalization question. Source notes permit person/animal nominal referents;
  lexical and contextual eligibility is not established by dictionary presence.
  Evidence: [93 ledger cases](../tests/fixtures/validity.json) (77 required /
  16 forbidden), [path/dictionary/CLI and corpus tests](../tests/short_recipient.rs),
  four complete unchanged KAIST sentences, browser particle/ending source
  selection and export, and [the candidate/corpus/novel review](short-recipient-evaluation.json).
  Across 3,377 tracked surfaces, 114 hypotheses are added on 104 surfaces;
  none are removed, no old provenance changes, and all 30 stress hashes remain.
  Broader personal-pronoun normalization and particle-marked copula bases remain
  under COV-018/020.

- [x] **COV-018p — Vocative allomorphs and respectful address.** Added
  consonant-final 이여 and the honorific 시여/이시여 pair as nominal particles,
  preserving their surface forms. Reviewed the existing 아/야 and 여 boundaries;
  ㄹ counts as a consonant here. 검이여 exposes 검 + 이여, and 국민들이여
  exposes 국민 + 들 + 이여. Honorific suffixes compose independently of the
  respectful particle, as in 선생님이시여. Copula/ending and whole-word readings
  remain available. Evidence: [34 required/forbidden judgments](../tests/fixtures/validity.json),
  [boundary, dictionary/CLI and Unicode tests](../tests/vocative.rs), two complete
  unchanged KAIST sentences, browser source/export checks and
  [source/output review](vocative-evaluation.json). Foreign final pronunciation
  remains conditional; noun POS does not establish contextual addressability.
  This scope does not certify all inherited outer-particle/copula combinations
  or decide politeness and sentence meaning. Independent Korean review remains open.

- [x] **COV-018q — Emphatic time/place 에야 and explicit decomposition.**
  Added KRDict's nominal compound 에야 while retaining NIKL's documented 에 + 야
  representation. Both compose with outer 만: 때에야만 exposes 때 + 에야 + 만
  and 때 + 에 + 야 + 만. The general particle-order stages remain unchanged;
  this rule does not authorize arbitrary 야 + 만 or other compound decompositions.
  Nominal suffixes, nominalizations and copulas preserve component ownership.
  Evidence: [34 judgments](../tests/fixtures/validity.json), [ordered decomposition,
  Unicode and dictionary/CLI tests](../tests/eya.rs), three complete unchanged
  KAIST sentences, browser alternatives/source/export checks, and
  [source/candidate review](eya-evaluation.json). The motivating corpus's
  때 + 에 + 야만 has different morpheme granularity but the same lexical group;
  its gold is preserved. Noun POS does not establish time/place semantics;
  contextual scope, other particle orders and independent Korean review remain open.

- [x] **COV-018r — Conditional (이)라야/(이)라야만 particles.** Added
  noun/adverbial 라야/이라야 with vowel/consonant allomorphs, and nominal
  라야만/이라야만. NIKL's explicit compound decompositions retain (이)라야 + 만
  alongside each longer particle. Case-marked adverbials such as 뒤에라야
  compose; subject/object case markers do not gain those nominal/adverbial
  licenses. The copula ending homonyms remain separate candidates and sources.
  Evidence: COV-017aj's [tests](../tests/ra_conditions.rs), attributed dictionary
  fixtures, the complete 꽃다발이라야 corpus sentence, browser alternatives and
  [review](ra-condition-evaluation.json). Nominalization, unknown lexical heads
  and further case/copula alternatives remain hypotheses, not contextual judgments.

- [x] **COV-018s — Nominal degree 깨나.** 땀깨나, 족보깨나 and
  사람들깨나 retain their nominal heads; plural 들 remains separate. The
  existing 깨 + 나, 깨다 + 나/으나, 깨나다 and 꽤 + 나 readings remain.
  No spelling repair, bare predicate/adverbial attachment or preceding-case
  peeling is added. The source-attested 아씨들깨나 path remains raw-only when
  its headword is absent from KRDict. Evidence: [four tests](../tests/kkaena.rs),
  27 `kkaena-*` judgments, dictionary/CLI parity, browser display/export and
  [source/candidate review](kkaena-evaluation.json). The complete KAIST test
  sentence MH2_0110-s468 is now an exposed regression case, not held-out evidence.
  Semantic quantifiability, wider particle combinations, inherited nominalization
  and copula alternatives, and contextual sense selection remain open.

- [x] **COV-018t — Core cases and recipient directions.** Bundled 게로/에게로/
  한테로 coexist with split recipient + 로 readings. Nominal/plural/honorific
  boundaries, case allomorphs and 에서의/으로의 are reviewed. Finite emphatic
  adverbs add 도대체가, 맘껏을/매번을/매일을 and 빨리를/곧이를; 빨리
  also retains its 빠르다 + 이 derivation. KRDict lacks 곧이, so its raw path
  is removed by both dictionary filters. Evidence: 105 stable morphology judgments
  (69 required / 36 forbidden), [five tests](../tests/core_case.rs), six complete
  annotated sentences, browser/CLI/export checks and [review](core-case-evaluation.json).
  Animate/honorific semantics, other emphatic adverb bases and contextual senses
  remain open. The GSD 강원체고를 copula match and 잘해서 partial component
  match are tracked observations, not correctness gains.

- [x] **COV-018u — Source compounds and role/means case audit.** Dictionary
  로부터/으로부터/에서부터/서부터 alternatives now coexist with split case +
  부터 paths. Their inner case boundary and outer 부터 boundary remain separate:
  inner 만/까지 and outer topic/focus/genitive/subject options preserve the split
  behavior. Existing (으)로서/(으)로써 coda distinctions, 음 nominalizations and
  locative 서 are reviewed. Evidence: 99 stable judgments (73 required / 26
  forbidden), [four tests](../tests/source_particles.rs), an 868-surface
  split/bundled equivalence check, five complete annotated sentences, browser
  alternatives/source/export checks and [review](source-particle-evaluation.json).
  Contextual senses, count-emphasis 서 and wider inner-particle acceptability
  remain open. The report assigns stable observation IDs to 학교+가+로써,
  선생님+이+로서 and novel 와/나+서부터 homonyms; these are unjudged readings.

- [x] **COV-018v — Concessive and designation particles.** ㄴ들/인들,
  ㄹ랑/을랑/일랑/설랑/에설랑 and the four dictionary 은 compounds now retain
  their distinct nominal, adverbial and finite post-ending boundaries. NIKL's
  vowel-final 새인들/장사인들 exception is preserved. Bundled 은 forms coexist
  with split paths; 들 plurals, lexical 샌들 and conjunction 랑 remain available.
  Evidence: [98 judgments and three integration tests](../tests/concessive_designation.rs),
  a 149-surface split/bundled check, dictionary/CLI/browser regressions and the
  [source and individual-case review](concessive-designation-evaluation.json).
  No target particle annotations were found in the mined training/development
  data; full corpus recall is unchanged. Wider attachment and independent
  Korean review remain open. COV-017ak now recovers the separately tracked
  predicate **-ㄴ들/-은들** in KAIST MH2_0092-s333 한들 and novel 간들/한들;
  their particle alternatives remain distinct.

- [x] **COV-018w — Existing 같이/대로/처럼 particle audit.** The 24 distinct
  surface forms in all five source senses retain nominal + particle paths,
  including 새벽같이/매일같이 and 겨울옷대로/공부대로. Nine judgments
  reject direct 고/어서/는 ending attachment with no intervening nominal.
  Existing 같다 + 이 hypotheses and whole-word readings remain available;
  dictionary presence is separate from contextual validity. Evidence:
  [33 stable judgments and three tests](../tests/comparison_particles.rs),
  attributed offline dictionary fixtures, both dictionary filters and CLI parity,
  ordered breakdowns, normalization, and [source audit](comparison-particle-audit.json).
  This is an audit of existing behavior, with no engine or label change.
  Contextual sense selection, wider particle chains, and bound-noun 대로
  constructions remain separate review work; independent Korean review is pending.

- [x] **COV-018x — Additive connective and particle distribution.** 조차 accepts
  어서/으려고/다가 and the KAIST-attested 게, while 마저 accepts 어서.
  잠깐/조금/천천히 gain separate adverbial 조차 paths. 까지 + 조차/마저 and
  조차/마저 + 가/를 cross the existing ordering stages only at these reviewed
  pairs. Nominalized questions, auxiliaries, copulas, suffixes and outer particles
  retain their roles. Evidence: [50 judgments and three tests](../tests/additive_particles.rs),
  [ten complete KAIST sentences](../tests/fixtures/kaist-additive-particles.conllu),
  dictionary/CLI parity and [source and case review](additive-particle-evaluation.json).
  All ten target groups are recovered, including four new matches. The proper
  name 승규 remains a raw candidate but is absent from KRDict and removed by
  dictionary filtering. The thesis's ambiguous 밖에 example and conflicting
  generalizations remain unjudged; no universal semantic pruning is inferred.
  More adverb bases, ending/particle combinations and independent Korean review
  remain open. COV-017al now recovers the fixture's previously unrelated 있을라치면 miss.

- [x] **COV-018y — Case phrases before comparison particles.** Reviewed
  에/에서/서 + 처럼 chains recover 학교에서처럼만, 전에처럼 and 학교서처럼,
  with existing plural, nominalized and outer-particle composition. NIKL directly
  attests 에서; KAIST supplies 에 and 에서. Short locative 서 is explicitly an
  inference from KRDict, pending independent Korean review. Case phrases before
  separate adverb 같이 retain their token boundary; no shared particle exception
  or unrestricted case repetition is introduced. Evidence: [22 judgments and
  three tests](../tests/comparison_case.rs), [six full training sentences](../tests/fixtures/kaist-comparison-case.conllu),
  both dictionary filters, CLI parity, browser selection/export, and the
  [individual-case review](comparison-case-evaluation.json). Five valid training
  targets and two frozen KAIST test cases become matches. Source spelling
  disagreements and two proper-name dictionary omissions remain explicit.
  Wider particle pairs, semantic restrictions and contextual sense choice remain
  separate review work.

- [x] **COV-018z — Quoted clauses before 밖에.** Source review, regression
  coverage, browser and Nix validation pass. The KAIST
  못하다고밖에 target and all 12 converted rows in its complete sentence
  now match. Full KRDict lexical examples attest 있다고밖에,
  명궁이라고밖에, 능력이라고밖에 and 초능력이라고밖에는, beyond the
  particle entry's short noun/기 note. Reported statements, copulas, questions,
  commands and proposals preserve distinct ending/particle roles; combinations
  beyond exact examples are marked inference. Nominal quotation alternatives,
  auxiliaries, topic and polite components remain. [56 raw judgments and
  dictionary/CLI tests](../tests/quoted_bakke.rs), four separate dictionary-policy
  cases and [the source/candidate review](quoted-bakke-evaluation.json) record
  the boundaries. Independent review, contextual polarity and further reported
  paradigms remain open.

- [ ] **COV-018aa — Review polite followers of quoted exclamations.**
  The missing dictionary labels for quoted 군/구나 + 요 do not prove
  invalidity. NIKL [330060](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=27&pageIndex=1&qna_seq=330060)
  identifies 요 after 하는군 as a polite particle. COV-017bi keeps inferred
  냐는군/느냐는군/으냐는군 + 요 hypotheses as Unknown rather than certifying
  a quoted-context license or register. Review declarative quote followers,
  quoted 구나 followers, full native examples and distinct ending/particle
  alternatives. Record unsupported exclusions as unjudged observations;
  absence from a source inventory alone cannot supply forbidden gold.
  **Partial implementation verified:** a full pinned dictionary
  example scan finds 17 original declarative 군 + 요 groups, including
  갔다는군요/한다는군요/온다는군요. These paths now preserve separate
  quote endings and the polite particle. Experience 더라는군 + 요 transfers
  through the explicit expansion as Unknown; quoted 구나 followers remain
  unjudged. [Four family tests](../tests/quote_followers.rs), 67 raw cases
  (55 required / 12 forbidden), 33 dictionary cases (30 required / 3 forbidden)
  and the [source audit](quote-followers-source-audit.json) retain the full
  native groups, idiom identities, homonyms and existing owner restrictions.
  The [individual comparison](quote-followers-evaluation.json) covers 11,929
  inputs, 519 added paths and zero removals; 410 additions remain unjudged.
  Four corpus reports, both novel filter outputs and optional spacing sidecars
  are unchanged. Rust/stress, lint/format, browser and x86_64 Linux Nix checks
  pass, including packaged API/CLI/export/asset parity and refreshed preview.
  This item stays open for quoted 구나, contextual register and independent
  Korean review.

- [ ] **COV-019 — Auxiliary inventory and internal particles.** **Partial:
  COV-019a implements the structural connector catalog and bounded internal
  particles; COV-019b adds negative contrast particles and short prohibitives.**
  COV-019c checks known auxiliary adjective inflections and removes unsupported
  어 + 없다. COV-019d checks the known left class before expressive 어 하다.
  Remaining: other left verb/adjective and lexical-subset restrictions,
  further ending/prefinal constraints, and additional particle combinations.
  Distinguish independent compounds and
  contextual auxiliary senses; dictionary presence does not resolve these.
  The negative 말다 mood audit in COV-019b rules out a blanket command-only
  filter; questions and indirect wishes can also be valid. Sentence-mood and
  sense selection require context beyond this token-level candidate generator.
  COV-019e adds internal 는 before 싶다 (학생이고는싶다).
  COV-019f rejects known adjective/copula roles before 어/고 있다/계시다.
  Other lexical subsets and attachment constraints still need review.
- [x] **COV-019a — Auxiliary connectors and one internal particle.** The
  [source inventory](auxiliary-inventory.json) preserves attachment notes for all
  54 KRDict auxiliary entries. Added paths include 나다/나가다, 계시다,
  adnominal 만하다/듯하다, nominal 음 + 직하다, and connector-specific
  uses of 하다/보다/들다. 가지다/갖다 and 달다 have restricted following
  forms; 으면 + 하다/싶다 requires recovered past. One reviewed particle
  slot supports 먹어들봐요, 먹고야말았다, 먹기나했다, and contracted
  먹곤했다, retaining bundled and whole-word alternatives. These are tolerant
  joined-input analyses, not spelling recommendations or cross-token parsing.
  Evidence: [path/boundary tests](../tests/auxiliary_inventory.rs), twelve
  `aux-inventory-*` ledger cases, five annotated offline tokens,
  dictionary/CLI parity, browser component/link tests, and
  [development comparison](auxiliary-evaluation.json). Packed iterative search
  and the 1,024-syllable memory test pass. One snapshot gains two unknown-stem
  hypotheses; all prior analyses remain. See [scope](rules.md#auxiliary-connectors-and-internal-particles-cov-019a).
- [x] **COV-019b — Negative auxiliary particles and short prohibitives.**
  마/마라/마요 recover 말다 with canonical 어/어라/어요; the full forms
  remain. Shortening is limited to prohibitive inflection, not arbitrary ㄹ
  stems, past tense, connective endings, or completive 고 말다. Joined input
  supports 지 + 는 (also contracted 진) before 않다/못하다/말다/아니하다,
  including 먹어보진마요. Existing 도/만 paths and lexical readings remain.
  NIKL's mood guidance preserves questions and indirect wishes rather than
  restricting every 말다 path to an imperative ending. Evidence: expanded
  [auxiliary tests](../tests/auxiliary_inventory.rs), fourteen `negative-aux-*`
  ledger cases, full GSD dev-s312, dictionary/CLI parity, and browser alternatives
  with -어라/는 source links. All current snapshots remain unchanged.
  See [scope and sources](rules.md#negative-auxiliary-particles-and-short-prohibitives-cov-019b)
  and [development comparison](negative-auxiliary-evaluation.json).
- [x] **COV-019c — Known auxiliary adjective inflections and legacy link audit.**
  The [class audit](auxiliary-class-audit.json) records all 54 source entries:
  34 verb-only, eight adjective-only, and six dual-class headwords. Bare
  adjective auxiliaries reject the reviewed verbal present/adnominal/question
  endings. Connector-specific 보다/못하다 uses and known classes inherited
  through 않다/아니하다/못하다 are checked, including particles, contractions,
  copulas, and an explicit 답다 suffix. Unknown lexical heads stay unclassified;
  prefinal and homonym alternatives remain. The unsupported 어 + 없다 auxiliary
  path is removed without changing lexical 없다 or 없이. Evidence: matrix and
  composition tests in [auxiliary tests](../tests/auxiliary_inventory.rs), fourteen
  `aux-class-*` ledger cases, four complete GSD sentences, dictionary/CLI parity,
  and browser/API checks. The [evaluation](auxiliary-class-evaluation.json)
  records each removed candidate in the targeted cases; all current fingerprints
  and corpus recoveries remain. See [scope](rules.md#auxiliary-adjective-inflections-and-legacy-links-cov-019c).
- [x] **COV-019d — Known left classes before expressive -어 하다.**
  Known auxiliary verbs and represented copulas no longer feed expressive 어 하다.
  Classes propagate through negatives, including contracted 잖 and internal
  particles; the immediately preceding class is checked after causative 게 하다.
  Adjective auxiliary and explicit 답다 paths remain, as do unclassified lexical
  hypotheses and other copula/하다 connectors. Evidence:
  [class/composition tests](../tests/auxiliary_left_class.rs), twelve `left-hada-*`
  ledger cases, dictionary/CLI parity, the retained expressive source sense,
  and browser regressions. [The comparison](auxiliary-left-hada-evaluation.json)
  lists each removed candidate and verifies unchanged corpus recovery and stress
  fingerprints. This is not a blanket left-class filter for all auxiliaries;
  lexical-subset and contextual sense restrictions remain open. See
  [scope and sources](rules.md#expressive-hada-left-class-cov-019d).
- [x] **COV-019e — Contrastive 고는/곤 before 싶다.** One internal 는 now
  connects 고 to 싶다, including 먹고는싶다, 먹곤싶다, 학생이고는싶다
  and 의사곤싶다. Prefinals, negative/expressive chains, nominalization and
  existing dictionary alternatives remain. Known adjective-ending and nominal
  boundary restrictions still apply. KRDict's 좀 entry supplies the direct
  spaced example 놀고는 싶지만; joined tests exercise tolerant input only.
  Evidence: [path/composition tests](../tests/desire_topic.rs), thirteen
  `desire-topic-*` ledger cases, dictionary/CLI parity, browser particle-source
  checks and [the comparison](desire-topic-evaluation.json). Other internal
  particles and auxiliary left-class licenses remain open. COV-019f resolves
  the known-adjective 어 있다 case discovered here. See
  [scope](rules.md#contrastive-desire-links-cov-019e).
- [x] **COV-019f — Known left classes before continuative 있다/계시다.**
  Both 어 and 고 links reject known adjective auxiliaries, inherited negative
  adjective classes, explicit 답다 derivation and represented copulas. Existing
  verb paths, class changes through expressive/causative 하다 and unclassified
  lexical heads remain. Specific dictionary expression notes establish verb
  attachment; the broader connector inventory is not a license for every pairing.
  Evidence: [44-combination matrix and composition tests](../tests/continuative_class.rs),
  twenty `continuative-class-*` ledger cases, dictionary/CLI parity and browser
  regressions. [The comparison](continuative-class-evaluation.json) reviews all
  removals across 83 surfaces and the two changed stress fingerprints, with no
  lost corpus gold. Transitivity, verb subsets, other prefinal/particle conditions
  and independent review remain open. See [scope](rules.md#continuative-left-classes-cov-019f).
- [x] **COV-019g — Stative auxiliary inflection across older report families.**
  Auxiliary 있다/계시다 now retain plain-다 readings before 다네/다는데 and
  다거나/다든가, including inherited negative readings. A later dynamic auxiliary
  resets that possibility. Bare auxiliary 있다 no longer takes the reviewed
  declarative 는다 families; lexical 있다, 계신다 and 있지 않는다 remain distinct.
  Present adnominal 는, background 는데, question 느냐 and prefinal-bearing
  reports retain their existing behavior. Evidence: [role and normalization
  tests](../tests/stative_reports.rs), 166 stable `stative-report-*` ledger cases,
  dictionary/CLI parity and browser selections, plus [source/candidate
  review](stative-report-evaluation.json). The review distinguishes direct
  attestations from morphological inferences, accounts for 96 additions and
  50 removals, and preserves all corpus gold and stress fingerprints. This does
  not settle all existential paradigms; COV-019h retains that work.
- [ ] **COV-019h — Further existential auxiliary paradigms.** **Partial:
  COV-017y applies shared present-declarative restrictions to auxiliary chains,
  including 먹고있었는다고 and modal equivalents; COV-017ac unifies the
  six bare-adjective question forms and preserves general 냐/verbal 느냐.**
  Remaining: honorific 있다
  paradigms, existential question allomorphs and past adnominals. Probe observations
  such as 먹고있으신다네 and 앉아있은 remain explicitly unjudged in
  [the latest source review](present-license-evaluation.json). Official consultation
  material does not provide a categorical auxiliary-wide judgment for every
  honorific or past-adnominal reading. Keep lexical 있다 and auxiliary 있다/계시다
  senses distinct. COV-019i resolves the missing internal-particle path
  먹고는있다네 without settling these existential paradigms.
  The [native-paradigm review](existential-paradigm-review.json) now records
  direct auxiliary honorification in `밟고 있으신데요`, honorific `계신가`
  questions, and NIKL’s explicit approval of progressive `지켜보고 있은 지`
  for elapsed time. Twenty-one stable `existential-paradigm-*` cases (17
  required / 4 forbidden), 24 complete native entries and four unchanged
  training sentences protect these paths and their owner/allomorph boundaries.
  `먹고있은` now retains a source-backed possible past reading; the exact
  vowel-final `계시 + 으냐며` boundary is forbidden. These judgments do not
  settle `앉아있은`, consonant existential `으냐며`, contextual honorification
  or auxiliary-versus-lexical sense choice. All 15 KAIST and 18 GSD converted
  fixture tokens match; the target annotations are lexical. Runtime rules are
  unchanged, with zero changes across 9,944 comparison surfaces. This item
  remains open for those explicitly recorded judgments.
  Rust/stress, Clippy, final browser/display/export, complete-dictionary
  HTTP/CLI checks and x86_64 Linux Nix package/flake checks pass. The release
  executables are byte-identical to the preceding packages.

- [x] **COV-019i — Contrastive particles before continuative auxiliaries.**
  Added 고 + 는 and 어 + 는 before 있다/계시다, including existing 곤
  expansion: 먹고는있다네, 먹곤있다, 살아는있을까, 앉아는계신다.
  Six direct dictionary examples support the spaced constructions; joined
  input and honorific/contracted composition are explicitly distinguished from
  source attestations. Existing immediate-left class, boundary, reporting and
  prefinal checks remain, with unknown lexical heads and whole-word alternatives
  preserved. Evidence: [52 ledger cases](../tests/fixtures/validity.json)
  (33 required / 19 forbidden), [Unicode/component/dictionary/CLI tests](../tests/continuative_topic.rs),
  browser component/source checks, and [candidate/source review](continuative-topic-evaluation.json).
  Across 82 focused/stress surfaces, 106 hypotheses are added with no prior
  analyses or provenance removed. All thirty stress fingerprints remain intact.
  More internal particles, lexical subsets, contextual suitability and COV-019h
  existential paradigms remain open; this is not cross-token parsing.

- [x] **COV-019j — Interrupted intention before 보니/보면.**
  -(으)려다/다가 can precede auxiliary 보다 only with 으니/으면, preserving
  the existing 다(가) 보다 restriction. 먹으려다보니 and 먹으려다가보면
  expose 먹다 + 보다 without inserting the contracted expression's implicit
  하다. The complete KAIST MH2_0169-s336 sentence directly attests spaced
  하려다 보니. Auxiliary 보다 inherits a Verb class for following checks;
  unrestricted 보다/보았다, 싶다 and other shortened-expression connectors
  are not enabled. Evidence: `intention-connectives-*-aux-*` ledger judgments,
  the [annotated/joined path test](../tests/intention_connectives.rs),
  [KRDict 보다 sense review](intention-connectives-evaluation.json) (62171),
  dictionary/CLI and browser chain parity. Other senses and connector/prefinal
  classes of 보다 remain unreviewed; this is a bounded connector disposition.

- [x] **COV-019k — Result-transfer auxiliaries.** Canonical 어다/어다가
  can precede 주다, 드리다, 놓다 and 두다. Joined 가져다주었다,
  모셔다드렸어요 and 빌려다놓았다 expose ordered predicate groups. The
  source review combines all four KRDict auxiliary entries, NIKL's teaching
  grammar report and Yang (2020)'s indexed primary-journal excerpt; the latter's
  full PDF was unavailable. Other following auxiliaries and internal particles
  are not licensed by this batch. Existing ordinary 어 놓다 adjective/copula
  senses remain distinct. Shared subjects, surviving objects, transitivity and
  location constraints require lexical/contextual review. Evidence is shared
  with COV-017af's [tests](../tests/result_connectives.rs) and
  [source report](result-connectives-evaluation.json).

- [x] **COV-019l — Inference 보다 after -(으)려나.** Joined 오려나보다,
  좋으려나봐 and 좋아지려나보다 expose ordered predicates. KRDict auxiliary
  보다 sense 1 (62249), expression entries 75177/76465 and the complete KAIST
  sentence directly support the connector. This 보다 has an Adjective class;
  present 는다/는 and incompatible following auxiliaries are rejected, including
  through inherited negative classes. Its ordinary past and polite inflection
  remains. Other following auxiliaries (including 싶다), internal particles and
  contextual inference choice remain unreviewed. Evidence: `ryeona-following-*`
  and `ryeona-class-boundary-*` ledger cases, [tests](../tests/ryeona.rs),
  dictionary/CLI/browser parity and the [source report](ryeona-evaluation.json).

- [x] **COV-019m — Dictionary evidence for known auxiliary classes.**
  Shared structural classes now constrain individual auxiliary dictionary entries.
  오려나봐 supports inference 보다 (62249), while 먹어봐 supports trial 보다
  (62171); repeated 보다 slots can choose different homonyms. Known negative-class
  inheritance and 답다 derivation compose through owned connectors, including
  internal particles. Unknown provider POS, ambiguous classes, separately written
  auxiliaries and valid alternative groups remain. Copula inheritance is preserved
  as a distinct class, not assumed to be adjectival; ordinary lexical-negative
  inheritance still needs a separate homonym-consistency audit under COV-019.
  Evidence: [86 per-entry judgments in 43 cases](../tests/fixtures/auxiliary-dictionary.json),
  [ownership/filter/CLI regressions](../tests/auxiliary_dictionary.rs), browser
  homonym/source/export checks, and [candidate/novel comparisons](auxiliary-dictionary-evaluation.json).
  Across 3,286 tracked surfaces, 324 entry assessments change on 245 surfaces;
  raw, headword-only and compatible candidate groups and all 30 stress hashes
  remain unchanged. This repairs dictionary evidence and display selection;
  contextual sense ranking and new morphology are separate work.

- [x] **COV-019n — Internal emphatic case particles.** Full 를 after 어/게/지/고
  and 가 after 지 compose only with licensed auxiliaries: 찾지를못했다,
  익지가않는다, 들어를보세요, 먹게를했다 and 먹고를있다. Contracted
  ㄹ retains canonical 를 in 물얼봐야지 and 먹질않았다. Exact role/ordering,
  invalid connector boundaries and full/contracted equivalence are covered by
  [core-case tests](../tests/core_case.rs) and the [review](core-case-evaluation.json).
  One stress case gains a reviewed unknown predicate; previous candidates and
  provenance remain. Wider particle combinations remain under COV-019.

- [x] **COV-019o — Explicit dictionary uncertainty before expressive 하다.**
  KRDict's adjective note is insufficient to reject all lexical verbs: NIKL
  licenses 꺼려 하다 and 내키지 않아 하다. Per-entry assessment now marks
  lexical verb attachments unknown, following only class-preserving 지 negatives.
  Adjective homonyms, class-resetting auxiliaries and raw candidates remain.
  Evidence: 22 additional [policy cases](../tests/fixtures/dictionary-attachments.json),
  [per-entry tests](../tests/dictionary_attachments.rs), browser homonym/export
  checks and [source review](core-case-evaluation.json). These tests preserve
  uncertainty, not certify the intended readings. The semantic verb subset and
  lexical-negative homonym consistency for other constraints remain unresolved;
  in particular 잘해서 → 자다 + 어 + 를 + 하다 is still an unjudged option.

- [x] **COV-019p — Continuation and completion source-sense audit.**
  Reviewed all nine senses and 44 example groups of 가다, 오다, 나가다,
  나다, 내다, 버리다 and 치우다. Existing 어 links and both 어/고 나다
  paths pass; no runtime change was needed. Explicit adjective examples before
  가다 prevent a blanket verb-only filter. Exact spaced excerpts remain separate
  from tolerant joined inputs, and compound alternatives remain distinct.
  Evidence: 90 `continuation-aux-*` ledger cases (70 required / 20 forbidden),
  [source/role/Unicode/dictionary/CLI tests](../tests/continuation_aux.rs), twelve
  unchanged annotated KAIST training targets, and [the review](continuation-aux-evaluation.json).
  Boundary judgments address auxiliary roles only, not separate independent
  verbs. Lexical-subset restrictions, further internal particles and contextual
  sense selection remain under COV-019; this is a scoped source audit.

- [x] **COV-019q — Request auxiliary across existing quoted-command endings.**
  Added twelve right-ending combinations after 어 달다, including the source's
  도와 달라며, 빌려 달라는데, 도와 달라네 and 받아 달라지. Existing
  달라/다오 and quoted forms remain; ordinary tense/honorific inflections and
  factual 라-family components remain excluded from this auxiliary role.
  Source notes, all 17 examples of the auxiliary and its three expression
  entries, plus twelve corroborating excerpts are retained. Evidence:
  [118 ledger judgments](../tests/request_aux.rs) (72 required / 46 forbidden),
  per-entry dictionary homonym checks, CLI/browser/export parity, and
  [the review](request-aux-evaluation.json). Seven unchanged annotated training
  targets remain matched; 매단 and 나달은 retain their original conflicting
  auxiliary annotations as explicit mismatches. No corpus baseline is repaired.
  New short-report endings such as 으래 are covered by COV-017at; wider lexical and
  particle restrictions remain under COV-019.

- [x] **COV-019r — Result-transfer before request auxiliary 달다.**
  Implementation, regressions, browser and Nix/package validation pass, shared
  with COV-017at. KRDict 86537 sense 4 explicitly illustrates 가져다 달래요.
  어다 now links to 달다; full 어다가 and existing request right endings are
  compositional inferences, covered separately from direct source excerpts.
  Ordinary indicative/past/honorific right forms remain rejected. Broader lexical
  selection is unreviewed. See [tests](../tests/short_reports.rs) and the
  [evaluation](short-reports-evaluation.json).

- [ ] **COV-020 — Derived nominal/copula composition and attachment classes.**
  **Partial: COV-020a adds direct nominalization + copula; COV-020b adds
  quoted copula fragments; COV-020c adds reviewed omitted-copula endings and
  finite 거/것 nominal alternatives; COV-020d adds enumerative -요 and
  COV-020e adds reviewed consonant-initial ending families; COV-020f adds
  honorific omission and short 세요; COV-020g adds modal/retrospective omission;
  COV-020h adds attached question endings; COV-020i adds nominal approximation -쯤;
  COV-020j adds literary 니라 omission; COV-020k adds conditional/concessive 라 endings; COV-020l adds direct 어서 clauses; COV-020m adds reviewed adverb bases and 냐 questions.**
  Remaining: additional suffix order and adjective ending licenses, other
  omitted-copula endings/prefinals, and particle-marked nominal bases. Quoted or
  connective clauses before copulas need a separate source/representation audit;
  nominalization does not authorize arbitrary ending + copula attachment.
- [x] **COV-020a — Direct nominalization + copula.** 기/음 nominalizations
  compose with explicit copulas, vowel-final omission, and existing polite
  copula allomorphs. 학생다움이다 exposes 학생 + 답다 + 음 + 이다 + 다;
  먹기다 and 먹기예요 preserve 먹다 + 기 + 이다. Existing prefinals, suffix
  order, auxiliary groups, outer particles, and nested nominalizations compose
  without a fixed nesting cutoff. Consonant-final bases still require 이 and
  known -답다 still requires its ㅂ-irregular boundary. Whole-word readings remain.
  Evidence: [composition/boundary tests](../tests/nominal_copulas.rs), eight
  `nominal-copula-*` ledger cases, one complete annotated KAIST sentence,
  dictionary/CLI parity and browser selector/source-link tests. All current
  snapshots and frozen corpus recoveries remain; the new 떠먹이기다 group is
  recorded in [the evaluation](nominal-copula-evaluation.json). See
  [scope and sources](rules.md#direct-nominalization-and-copulas-cov-020a).
- [x] **COV-020b — Quoted copula fragments.** Standalone 이라는 gains a
  Copula-role analysis; standalone 라는 additionally recovers omitted 이다
  with explicit provenance requiring preceding quoted material. Tokenization,
  original byte offsets, and lexical alternatives remain. The browser displays
  the condition with the selected breakdown and exports it with the analysis.
  Evidence: [fragment/streaming tests](../tests/copula_fragments.rs), two complete
  [KAIST sentences](../tests/fixtures/kaist-copula-fragments.conllu), three
  `quoted-copula-*` ledger cases, dictionary/CLI parity, and browser/export checks.
  [Evaluation](copula-fragment-evaluation.json) records two additional grouped
  recoveries, with no losses or changed current fingerprints. This does not
  parse preceding quoted material or license arbitrary ending + copula
  attachment inside a token. Other fragment endings and particle combinations
  remain COV-020 review. See [scope and source](rules.md#quoted-copula-fragments-cov-020b).
- [x] **COV-020c — Omitted copulas and colloquial nominal alternatives.**
  지/지요/죠, 면, attached ㄴ데, and attached ㅂ니다/ㅂ니까 now recover 이다
  after vowel-final nominals, including 겁니다, 건데, 거죠, and 의삽니다.
  Recovery preserves the ending consonants and does not apply verb irregulars
  to nouns. Exactly 거/이거/그거/저거 also expose 것/이것/그것/저것 before
  copulas, retaining short and whole-word alternatives. Existing nominalizations,
  auxiliaries, and outer particles compose; unknown-script pronunciation
  conditions remain explicit. Evidence: [boundary/composition tests](../tests/omitted_copulas.rs),
  fourteen `omitted-copula-*` ledger cases, nine complete annotated sentences,
  dictionary/CLI parity, and browser alternative/source-link checks.
  [Evaluation](omitted-copula-evaluation.json) records nine new development
  recoveries with no losses, and one reviewed additive noun/copula hypothesis
  in each of three stress fingerprints. Every prior candidate and hash is
  preserved. Other omission families and broader colloquial paradigms remain
  open. See [scope and sources](rules.md#omitted-copulas-and-colloquial-nominal-alternatives-cov-020c).
- [x] **COV-020d — Enumerative copular -요.** 연장이요, 자화상이요,
  아비요 and 아니요 gain connective-ending paths distinct from polite particle
  요. Bare 이다/아니다, vowel-final omission, nominal suffixes/particles,
  nominalizations and explicit 이요 fragments compose. General predicates and
  recovered prefinals do not gain this ending. Evidence: [role/boundary tests](../tests/copula_yo.rs),
  eight `copula-yo-*` judgments, five complete annotated sentences,
  dictionary/CLI parity and browser role-specific source links. The
  [evaluation](copula-yo-evaluation.json) separates five connective recoveries
  from two incidental sentence-final gold-group matches. Two stress snapshots
  gain reviewed unknown-nominal hypotheses; every prior candidate and hash is
  retained. Other copula families and contextual reading selection remain open.
  See [scope and sources](rules.md#enumerative-copular-yo-cov-020d).
- [x] **COV-020e — Omitted copula before further consonant-initial endings.**
  니/니까, 고, 지만, 거든 and 네, including existing 지만요/거든요/네요
  bundles, restore 이다 after vowel-final nominals. Canonical 니/으니 alternatives,
  explicit copulas, nominalizations, colloquial 거 forms and existing particle/
  auxiliary connectors remain. Consonant-final nominals do not lose their coda
  or receive predicate irregulars. Conditional foreign pronunciation is explicit.
  Evidence: [boundary/composition tests](../tests/omitted_connectives.rs),
  thirty `omitted-connectives-*` judgments shared with COV-018h, nine complete
  annotated sentences, dictionary/CLI parity and browser normalized source checks.
  [Evaluation](omitted-connective-evaluation.json) records six KAIST and three
  GSD grouped gains; the latter include an incidental place-name annotation
  match, not a linguistic improvement. Four stress changes retain every previous
  candidate and hash, with unknown nominal/auxiliary hypotheses explicitly
  unjudged. COV-020f separately adds honorific omission; other prefinals,
  further endings and copula/auxiliary eligibility remain open. See [scope and sources](rules.md#further-omitted-copulas-and-connective-eun-cov-020e018h).
- [x] **COV-020f — Honorific copula omission and short 세요.** 선수셨다
  restores 선수 + 이다 + 시 + 었 + 다; 의사시니까 and 의사세요 retain
  represented copulas. Restoration occurs before the existing prefinal stack,
  preserving contracted/uncontracted past, double past, modal/retrospective order,
  ending restrictions, nominalizations and licensed particle/auxiliary links.
  Consonant-final nouns cannot borrow predicate irregulars; restored 이 cannot
  become an invented lexical predicate, including through an outer copula.
  Evidence: [boundary/parity tests](../tests/honorific_copulas.rs), twenty-six
  `honorific-copula-*` judgments, three unchanged annotated verb sentences,
  dictionary/CLI parity and browser normalized/source checks. The
  [comparison](honorific-copula-evaluation.json) records all additions and
  unchanged development recall. One stress fingerprint gains two unjudged nominal
  hypotheses; every prior candidate and hash remains. The short 세요 component
  stays bundled; generic 시어-to-세 recovery, other prefinal omissions, contextual
  honorific suitability and broader auxiliary restrictions remain open. See
  [scope and sources](rules.md#honorific-copula-omission-cov-020f).
- [x] **COV-020g — Modal and retrospective copula omission.** Recover 이
  before 겠/더 after vowel-final nominals, preserving represented copula roles,
  normal prefinal order and explicit forms. Reviewed literal bundles 더라,
  더라고, 더군/더군요, 더니, 더라도 and 던데/던데요 retain alternatives to
  decomposed prefinals. 마찬가지겠지만, 최고더군요 and 어디더라 gain exact
  annotated groups in three complete unchanged development sentences. Evidence:
  [boundary/composition tests](../tests/prefinal_copulas.rs), thirty-five
  `prefinal-copula-*` ledger cases, attributed dictionary/CLI/browser checks and
  [comparison](prefinal-copula-evaluation.json). Bare 던/더라는 omission,
  wider prefinal-ending licenses and contextual senses remain open. The report
  records the then-existing 더 + 다 attachment problem; COV-017r now rejects
  that path across lexical and represented-copula classes. See [scope](rules.md#modal-and-retrospective-copula-omission-cov-020g).

- [x] **COV-020h — Omitted copula in attached questions.** 뭔지/뭔가
  recover 뭐 + 이다 + 은지/은가; 뭘까 recovers 뭐 + 이다 + 을까.
  Six forms cover 은지/은가/은가요/을까/을까요/을지 after vowel-final
  nominals, including 누구/어디/언제/얼마/무어 and ordinary nominal bases.
  Existing 거/것 alternatives, full spellings, nominalizations, particles and
  licensed auxiliary composition remain. Attached ㄴ/ㄹ is required; nominal
  consonants are not repaired through verb irregulars, and the recovered 이
  cannot fabricate a lexical verb. Evidence: [48-pair full-form matrix and
  composition tests](../tests/question_copulas.rs), 95 cited ledger cases,
  dictionary/CLI/browser checks and [comparison](question-copula-evaluation.json).
  Four complete annotated sentences capture two GSD gains (뭔지/뭔가) and
  preserve two explicit KAIST copulas. The comparison accounts for all 132
  additions across 105 surfaces with no removals or changed provenance.
  One stress fingerprint adds an unverified nominal hypothesis; its prior
  history is retained and dictionary filtering is checked. The other 29 are
  unchanged. This does not expand 뭐/무어 into all longer lexical counterparts;
  that remains part of COV-018's pronoun audit. See
  [scope](rules.md#omitted-copula-in-attached-questions-cov-020h).
- [x] **COV-020i — Nominal approximation -쯤.** 번쯤 exposes 번 + 쯤;
  particles and copulas compose in 내일쯤에, 번쯤은요 and 중간쯤이었다.
  Existing 님/들/님 + 들 suffix paths can precede 쯤, including 교수님들쯤은.
  Whole 그쯤/이쯤/저쯤 lexical readings survive dictionary filtering. The known
  ㅁ boundary selects outer allomorphs even after numeric/foreign spelled bases.
  The browser labels the suffix “About / approximately” and links entry 88691.
  Thirty required and nine forbidden judgments cover the stated scope. The
  complete KAIST sentence preserves 번쯤 → 번 gold, while retaining the source
  jxc tag rather than relabeling it as proof of the dictionary's suffix role.
  No recursive 쯤 splitting, predicate nominalization/inner-particle peeling,
  semantic noun-class validation or 쯤 + 답다 derivation is claimed. Existing
  적 hypotheses before 쯤 remain unjudged; other approximation suffixes -경/-여
  need their own semantic/homonym review. These followups remain COV-020 work.
  Evidence: [rules](rules.md#nominal-approximation-suffix-cov-020i),
  [tests](../tests/approximation.rs), stable `approximation-*` ledger cases,
  `approximation_suffix_preserves_dictionary_and_cli_parity`, browser source
  selections, and [source/candidate review](approximation-evaluation.json).

- [x] **COV-020j — Omitted copula before literary 니라.**
  그림자니라 exposes 그림자 + 이다 + 으니라, alongside explicit 그림자이니라
  and consonant-final 학생이니라. Existing nominalization and honorific-copula
  recovery remain available. A consonant-final nominal still requires 이;
  no lexical predicate is invented from the reconstructed copula. Bare copulas
  reject 느니라, while licensed prefinals can precede it (학생이었느니라).
  The unchanged KAIST DEV MH2_0159-s305 sentence supplies the omitted-copula
  annotation. Evidence: COV-017ai's [tests](../tests/nira.rs), ledger boundaries,
  dictionary/browser parity and [review](nira-evaluation.json). Broader
  particle-marked bases remain COV-020; historical tense uses are not inferred.

- [x] **COV-020k — Omitted copulas before conditional/concessive 라 endings.**
  의사라도/의사라야/의사라야만 preserve 의사 + 이다 and their respective endings,
  while consonant-final nominals still require explicit 이. Nominal suffixes and
  existing particle-marked bases compose, including 교양 + 만 + 이다 + 라도.
  The full KAIST annotation's 라 + 도 alternative and GSD's 자전거도로 + 이다
  group remain beside particle readings. The GSD annotation does not prove
  which reading is intended in its sentence. Evidence: COV-017aj's
  [tests](../tests/ra_conditions.rs), full corpus fixtures and
  [review](ra-condition-evaluation.json). Broader particle-marked nominal/copula
  attachment and contextual interpretation remain COV-020 and completion review.

- [x] **COV-020l — Connective -어서 clauses before copulas.** 넘어서였다,
  나서이다, 생각해서다 and 추워서인지 preserve the connective before 이다,
  with existing explicit/omitted copulas, irregular stems, auxiliaries and 답다.
  The new provenance distinguishes this boundary from nominalization.
  Evidence: [53 judgments and composition/filter tests](../tests/connective_copulas.rs),
  six full annotated training sentences tested in `connective_copulas_recover_six_annotated_training_cases`,
  browser selection/export checks and [source/candidate review](connective-copula-evaluation.json).
  Five development misses gain exact grouped matches without lost recoveries.
  Novel additions are individually unjudged contextual alternatives. The inherited
  따다 + 어 + 를 + 이다 alternative in 딸이었던들 remains a source-review
  question; this extension does not certify that path or generic clause attachment.
  COV-020m resolves the recorded `제법이다` adverb-role miss; other quoted/
  connective bases and the wider adverb inventory remain open.

- [x] **COV-020m — Source-attested adverbial copulas and 냐 questions.** Added
  Adverbial + Copula readings for 고만/그만/그럭저럭/그대로/그만큼/딱/
  들쑥날쑥/들쭉날쭉/먼저/물론/별로/왜/제법, retaining nominal homonyms.
  `제법이다` now survives compatible filtering. Vowel-final 냐/냐고 omission
  recovers 뭐냐/왜냐고; bare copula + 느냐 is rejected while 시/었/겠 forms
  remain. Evidence: [72 judgments and role/filter tests](../tests/adverb_copulas.rs),
  nine complete annotated sentences, browser dictionary/selection/export checks,
  and [source/candidate review](adverb-copula-evaluation.json). The separate audit
  recovers compatible Adverbial + Copula roles for 21 of 26 training/development
  observations; five nonstandard or questionable annotations remain identified.
  GSD development adds one grouped match, 뭐냐, with no lost recoveries.
  This finite inventory does not license all adverbs or select contextual senses.
  Novel alternatives, generic particle/copula attachment and independent review
  remain open, including the inherited 딸이었던들 and 왜요 alternatives.

- [x] **COV-020n — Factual copular ending ownership in dictionary filtering.**
  Implemented a bare lexical attachment check for 17 exact factual 라-family
  canonical endings, retaining distinct command forms, 아니다, nominal quotation,
  copular 이다, recovered prefinals and unknown entry classes. The lexical verb
  이다 cannot borrow the copula entry's role. Added 105 policy judgments
  (63 retained / 42 excluded), including all 18 distinct removed novel paths.
  Raw output is identical on 4,533 regression/stress/probe surfaces; headword-only
  candidates are unchanged across 179,112 novel records. Compatible filtering
  removes 59 paths at 56 occurrences / 16 word types; every changed context is
  recorded with stable policy IDs in [the review](copular-class-evaluation.json).
  Rust, browser, full-dictionary packaged preview and Nix checks pass. Missing
  KRDict 모란 remains a vocabulary gap; quoted/Hanja-separated copulas still
  require contextual token handling.
- [x] **COV-020o — Family-specific factual prefinal licenses.** Source audit,
  regression, browser and Nix checks pass. A 51-cell matrix records
  17 endings with 시/더/으리: 42 source-listed paths and nine unlisted combinations,
  without treating source omission as a universal ban. Fixed missing factual
  시 + 란 for noncopular predicates, also through irregular recovery, auxiliaries
  and 답다; command 으란 remains separate. Added 63 raw judgments (59 required /
  4 forbidden) and three retained dictionary-policy paths. COV-017v already
  documents the wider 더라는데/라는데요 support for split 라는데 paths; the
  initial followup observation duplicated that earlier review.
  KRDict 라서 and NIKL 318485 still differ: a normative restriction is explicitly
  deferred pending authoritative clarification. Generated source-listed hypotheses
  remain; their contextual grammaticality is not certified. The
  [review](factual-prefinal-evaluation.json) records 48 added candidates across
  13 of 4,567 compared surfaces, zero removals/provenance changes, unchanged
  frozen-corpus match counts and byte-identical compatible-filtered novel output.

- [x] **COV-020p — Missing spaces across nominal case and lexical predicates.**
  The preserved native 결혼을하라느니 now has an explicit dictionary-backed
  결혼을 하라느니 hypothesis. `spacing::suggest`, CLI `--suggest-spacing` and
  the browser's **Suggest missing spaces** keep original word candidates and
  byte spans, while each proposed word retains independent readings/dictionary
  assessments. Multiple case phrases, plurals, outer particles, contractions and
  음/기 nominalizations compose before a separately analyzed predicate. No
  dictionary head 결혼을하다 or nominal-particle auxiliary link is invented.
  Every search reports whether the declared template/dictionary search completed;
  default 64 NFC characters / 256 segment probes / 16 alternatives are configurable
  in CLI/library and truncation is visible. Twenty stable cases (14 required /
  six forbidden) in [the spacing ledger](../tests/fixtures/spacing-validity.json),
  47 complete native entries and [six tests](../tests/spacing.rs) cover original
  source identity, exact grouped components, NFD/original UTF-8 spans, streaming
  CLI parity, cache immutability, limits and ambiguous-prefix stress. Failed suffix
  searches are memoized without merging successful prefix alternatives. [Source audit](spacing-source-audit.json)
  and [individual evaluation](spacing-evaluation.json) retain extra partitions
  as unjudged. Default output is unchanged across 10,514 raw inputs, all four
  frozen corpus reports and both 179,112-record novel streams. Opt-in spacing
  retains 5,555 unjudged hypotheses at 4,940 novel occurrences, with original
  spans/context and no reached limits; this is not a segmentation recall claim.
  Rust/stress, lint/format, frontend/browser, pinned corpus, final x86_64 Linux
  Nix and refreshed packaged-preview checks pass. General
  word-spacing correction, missing dictionary vocabulary and contextual sentence
  interpretation are outside this rule template; no broader segmentation is certified.

- [ ] **COV-021 — Remaining spelling and 하다 shortening.** **Partial: Article 39 잖/찮
  forms are covered by COV-021a; COV-021b adds shortened 기 nominalizations;
  COV-021c adds eight fixed complex-coda classes; COV-021d adds per-entry
  written ㅎ compatibility; COV-021e adds ㄷ/ㅅ and COV-021f adds ㅂ
  compatibility and three finite 오 spelling exceptions; COV-021g adds
  per-entry 르/러 written paradigms; COV-021h adds twelve entry-specific
  shortened-stem restrictions.** Remaining: other lexical paradigms and unmapped
  shortened-stem senses, ㄼ lexical
  pronunciation exceptions, ㄶ/ㅀ before 하, and further ending/particle
  families. Do not extend stop/sonorant rules without pronunciation evidence.
  The [dictionary discovery audit](hada-complex-coda-audit.json) found three
  complex-coda 하다 words among 7,571 entries: 한몫하다, 값하다 and 꼴값하다.
  COV-021c now recovers their licensed shortened forms. Dictionary absence does
  not establish that hypothetical words in other coda classes are impossible.
- [x] **COV-021a — Article 39 negative contractions.** 잖 recovers 지 + 않다;
  찮 restores 하지 + 않다. The left predicate uses existing spelling and
  prefinal recovery; the negative auxiliary retains its own inflection.
  Examples include 적잖은, 만만찮았다, and 먹고싶잖다. Original lexical
  readings remain, including 적잖다, 만만찮다, and 괜찮다. Recovery does not
  establish lexical membership or semantic equivalence to a lexicalized word.
  Evidence: [path/boundary tests](../tests/negative_contractions.rs), eight
  contraction/lexical ledger cases, the complete KAIST MH2_0159-s86 sentence,
  dictionary/CLI parity and browser reading selectors. All current fingerprints
  remain unchanged. See [scope and sources](rules.md#negative-contractions-and-confirmation-cov-021a017f)
  and [development comparison](negative-contraction-evaluation.json).
- [x] **COV-021b — Shortened 하다 before 기 nominalizations.** 강구키 and
  조성키로 recover 강구하다 and 조성하다. Stop-final 생각기에 recovers
  생각하다 through deletion rather than aspiration. The eight existing 기
  bundles retain full-form parity, ordinary nominal particles/copulas, and
  licensed auxiliary connectors, including 돌변키도했다. Wrong coda classes,
  unknown-script bases and standalone 키 do not gain this restoration.
  Evidence: [boundary/composition tests](../tests/hada.rs), eight `hada-ki-*`
  ledger cases, two complete annotated sentences, dictionary/CLI parity, and
  browser normalization/alternative/source-link checks. The
  [evaluation](hada-ki-evaluation.json) records two supported development
  recoveries and a separate incidental match to GSD's erroneous predicate
  annotation of the place name 이시가키와. No prior candidates, gold groups,
  component recoveries or stress fingerprints are lost. See
  [scope and sources](rules.md#shortened-hada-nominalizations-cov-021b).
- [x] **COV-021c — Fixed complex-coda shortening and predicate restoration.**
  Pronunciation Articles 10–11 plus spelling Article 40 license deletion after
  ㄳ/ㄺ/ㄿ/ㅄ and aspiration after ㄵ/ㄻ/ㄽ/ㄾ. The 22 existing shortening
  endings retain full-form predicate parity, NFD, nominalization, auxiliaries
  and negative contractions; original spellings and lexical readings remain.
  Restored 하 in -찮- cannot become a nominal before an invented copula.
  The 54 `hada-complex-*` judgments (28 required / 26 forbidden),
  [class/composition tests](../tests/hada_complex.rs), one unchanged KAIST
  sentence, dictionary/CLI parity and browser selection/export checks provide
  regression evidence. [Evaluation](hada-complex-evaluation.json) distinguishes
  inferred spellings from direct examples and hypothetical lemmas from dictionary
  words. The finite dictionary has three complex-coda 하다 heads, all covered;
  this does not close the remaining three pronunciation classes or all COV-021.
- [x] **COV-021d — Written ㅎ regular/irregular compatibility.**
  **Implemented for per-entry written ㅎ paradigms.**
  Per-entry written 니 forms classify 116 native entries: 46 regular, 66
  irregular and four unknown. Pronunciation-only or missing forms do not infer
  regularity; lexical homonyms keep separate evidence. Component-owned spelling
  paths prevent one auxiliary's recovery from constraining another lemma.
  닿다 at 달라고 and 놓다 at 놀라고 now conflict under compatible filtering;
  raw/headword-only hypotheses, valid inflections and 놓아 → 놔 remain.
  The reverse mismatch 하얗으니 is also checked against the irregular entry.
  [Tests](../tests/hieut_compatibility.rs) cover 326 filter judgments, complete
  source profiles, competing paths, legacy JSON, Unicode and both CLI filters.
  Seven unchanged training groups survive filtering; all frozen corpus reports
  remain byte-identical. The novel comparison retains raw/headword candidates
  and traces 1,121 compatible-filter removals to explicit spelling conflicts.
  All 6,577 compared surfaces retain their raw candidate components/order/rule
  IDs; only owned spelling metadata changes. Rust, browser and x86_64-linux Nix
  checks pass, including full-dictionary packaged API/CLI/export parity. Three
  interleaved novel runs measured compatible-filter medians of 1.256 → 1.367 s
  and peak RSS of 28,552 → 30,068 KiB. Other lexical irregular classes remain
  under the broader COV-021 audit.
  See [policy and API details](dictionary-attachments.md#written-ㅎ-inflection-compatibility-cov-021d)
  and [individual-case evaluation](hieut-compatibility-evaluation.json).

- [x] **COV-021e — Written ㄷ/ㅅ regular/irregular compatibility.**
  **Implemented for per-entry written ㄷ/ㅅ paradigms.** The native inventory has
  124 entries: 65 regular, 54 irregular and five without a usable written 니
  paradigm. Real 걷다/묻다 homonyms keep separate evidence; a matching regular
  entry cannot veto a supported irregular homonym. Compatible filtering rejects
  the unsupported 믿다 at 밀으면, 듣다 at 듣으니 and 짓다 at 짓어 hypotheses.
  Raw/headword-only candidates remain; prefinals, auxiliary chains and
  nominalization/copula combinations retain their owning spelling requirements.
  [Tests](../tests/digeut_siot.rs) cover 347 policy cases and every source entry;
  eight unchanged training targets survive filtering. All four frozen corpus
  reports remain byte-identical, and 6,897 compared inputs preserve their raw
  candidate components/order/rule IDs and earlier ㅎ requirements. The novel
  comparison traces 309 compatible-filter removals across 109 word types to
  written spelling conflicts without removing headword-only candidates.
  Rust, browser and x86_64-linux Nix checks pass, including packaged full-dictionary
  API/CLI/export parity. Three interleaved novel runs measured compatible-filter
  medians of 1.356 → 1.378 s and peak RSS of 29,848 → 30,240 KiB.
  껴묻다/내딛다/딛다/잡숫다/줄짓다 remain unknown; separate shortened-stem
  attachment notes, ㅂ/르 and other lexical classes remain under COV-021.
  See [policy](dictionary-attachments.md#written-ㄷㅅ-inflection-compatibility-cov-021e)
  and [individual-case evidence](digeut-siot-evaluation.json).

- [x] **COV-021f — Written ㅂ paradigms and finite 오 exceptions.**
  **Implemented for the scoped written paradigms.** Per-entry written forms
  classify 443 native single-ㅂ entries: 56 regular, 377 irregular and 10 unknown.
  Whitespace is trimmed for classification while original evidence is retained;
  written 운/온 also establishes the irregular class of adnominal-only entries.
  곱다/굽다 homonyms remain independent. The fixed -답다 suffix does not impose
  a lexical spelling constraint on its preceding nominal lemma.
  Raw recovery adds the source forms 곱디고와, 듣자와 and 받자오니, including
  prefinal/auxiliary composition, and rejects their swapped vowel counterparts.
  [Tests](../tests/bieup.rs) cover 1,087 dictionary-policy and 36 raw judgments,
  every source entry, and 1,674 source conjugations. One mismatch is explicit:
  얃잡는 under 얕잡다 (67256) remains unrecovered without spelling correction.
  Eight original training groups survive filtering; all frozen raw corpus reports
  remain byte-identical. On 8,000 compared inputs, raw changes (39 additions,
  24 removals on 43 surfaces) belong only to the three finite heads. Prior
  candidate order/rule IDs and ㅎ/ㄷ/ㅅ requirements remain unchanged on shared
  paths. Novel headword candidates remain; compatible filtering removes only
  지워→집다 and 어원→업다, with written-class conflicts recorded individually.
  Rust, browser and x86_64-linux Nix checks pass, including packaged full-dictionary
  API/CLI/export parity. Three interleaved novel runs measured compatible-filter
  medians of 1.376 → 1.386 s and peak RSS of 29,952 → 30,224 KiB.
  Ten entries lacking usable forms and separate shortened-stem restrictions
  remain under COV-021, alongside 르/러 and other unreviewed paradigms.
  See [policy](dictionary-attachments.md#written-ㅂ-inflection-compatibility-cov-021f)
  and [individual-case evidence](bieup-evaluation.json).

- [x] **COV-021g — Written 르/러 paradigm compatibility.**
  **Implemented for per-entry written 아/어 paradigms.** Forms classify
  149 entries: 8 vowel deletion,
  126 ㄹ doubling, 6 러 addition and 9 unknown. 이르다/누르다 homonyms retain
  independent evidence. Consonant/(으) endings impose no class restriction;
  past/auxiliary boundaries retain component ownership. Raw/headword-only
  candidates remain unchanged. The [tests](../tests/reu.rs) cover 663 policy
  judgments, every source entry, unknown/legacy/custom-dictionary evidence,
  Unicode and CLI parity. Eight unchanged training targets survive filtering.
  All 404 written forms are audited: 403 recover their listed headword; 서툰
  under 서투르다 is an explicit source discrepancy, with 서툴다 preserved.
  All four frozen raw corpus reports remain byte-identical. Across 8,565 inputs,
  raw components/order/rule IDs and prior spelling requirements remain unchanged.
  The novel retains headword candidates and traces 1,231 compatible-filter
  removals across 73 types to per-entry spelling conflicts.
  Every dev/test row with a 르다 gold lemma is also checked: 524 previously
  retained groups remain among 538 rows, with the 14 existing misses explicit.
  Rust, browser and x86_64-linux Nix package checks pass, including full-dictionary
  packaged API/CLI/export parity and desktop/mobile layouts. Three interleaved
  release novel runs measured compatible-filter medians of 1.402 → 1.421 s
  and peak RSS of 30,004 → 30,140 KiB; this is not a statistical equivalence claim.
  Other paradigms and shortened-headword restrictions remain under COV-021.
  See [policy](dictionary-attachments.md#written-르러-inflection-compatibility-cov-021g)
  and [individual-case evidence](reu-evaluation.json).

- [x] **COV-021h — Entry-specific shortened-stem attachment restrictions.**
  **Finite native-entry implementation and regression coverage pass.**
  A [source inventory](short-stem-inventory.json) binds seven consonant-only
  and five no-아/어 restrictions to native entry identities. It distinguishes
  the 까불다 homonyms and records unavailable or unrelated source senses.
  First-owned-boundary checks preserve later auxiliaries/prefinals/copulas and
  valid ㄹ-stem (으) allomorphs. Three contradictory KRDict written forms and
  the unchanged KAIST 내딛었다 annotation are tracked explicitly; raw candidates
  remain. Ten earlier unknown-retention judgments are superseded with preserved
  before/after evidence. [Tests](../tests/short_stems.rs) cover 223 policy cases,
  complete native sources, homonyms, boundaries and CLI parity. Seven unchanged
  training groups survive filtering; all 45 previously retained scoped dev/test
  groups remain among 46 rows. The 8,769-input raw comparison is byte-identical.
  Novel filtering removes only six 갖은 → 갖다 + 은 readings; lexical 갖은 remains.
  Full Rust, browser, Nix builds and packaged API/CLI/export checks pass. Three
  interleaved release runs process 179,112 novel records in median 1.508 seconds
  with headword filtering and 1.509 seconds with compatibility filtering, using
  less than 30 MiB peak child RSS; these timings are observational. Independent
  Korean review and unavailable source senses remain open.
  See [policy](dictionary-attachments.md#restricted-short-stem-endings-cov-021h)
  and [evaluation](short-stem-evaluation.json).

- [ ] **COV-022 — Remaining adverbial and nominal derivations.** Review -이/-히
  lexical classes and nominal -이 independently. **Partial: COV-022a adds
  source-listed predicate adverbs, including 가까이; COV-022b adds finite adverb
  and repeated nominal bases plus shortened 익히/특히; COV-022c adds the finite
  opaque 천천/분연 roots; COV-022d adds the eight source-listed
  predicate-base noun formations.** Remaining: other lexical
  classes, other opaque roots beyond the finite COV-022c forms, subdivision of nonlexical
  repeated bases, suffix/auxiliary interactions, and other nominal -이 senses/classes. Keep lexical readings and causative/noun homonyms; historical
  달리/빨리 do not license a general 르 inflection rule.
- [x] **COV-022a — Source-listed predicate adverbs.** Six explicit ㅂ-stem
  recoveries include 가까이 → 가깝다 and 가벼이 → 가볍다. 헛되이 and 적잖이
  preserve their adjective stems. A [recorded inventory](adverb-inventory.json)
  licenses 57 이/히 roots and related 하다 lookup lemmas, without claiming
  that 하 is present in the surface derivation: 조용히 displays 조용 + 히 and
  links 조용하다. Whole lexical adverbs remain preferred/selectable; particle
  licenses stay separate from noun case marking and causative/passive suffixes.
  Evidence: expanded [adverb tests](../tests/adverbs.rs), eight
  `adverb-expansion-*` ledger cases, four complete KAIST sentences,
  dictionary/CLI parity, browser root/suffix/source-link tests, and
  [development comparison](adverb-expansion-evaluation.json). All current
  snapshots remain unchanged. See [scope](rules.md#additional-predicate-adverbs-cov-022a).

- [x] **COV-022b — Adverb/repeated nominal roots and shortened adverbs.**
  A [33-form inventory](adverb-root-inventory.json) adds eight adverb bases,
  twenty-one repeated nominal bases, shortened 익히/특히, and their full forms.
  The new paths retain base roles and adverbial suffixes, preserve whole lexical
  readings and homonymous particle paths, and compose with the existing
  adverb-compatible particles. Repeated bases remain single components; fourteen
  base/role dictionary gaps are explicit. The source-backed shortening uses
  익숙하다/특별하다 for lookup rather than inventing 익하다/특하다.
  Evidence: [role/boundary tests](../tests/adverb_roots.rs), twelve
  `adverb-root-*` ledger cases, four complete corpus sentences preserving lexical
  gold, dictionary/CLI parity, and browser suffix/source-link checks. Optional
  role constraints now distinguish homonymous paths in the ledger and retain
  unjudged alternatives. [Evaluation](adverb-root-evaluation.json) records all
  additions for 55 surfaces, unchanged development recall, and all thirty
  unchanged stress fingerprints. See [scope](rules.md#adverb-and-repeated-nominal-bases-shortened-adverbs-cov-022b).

- [x] **COV-022c — Finite opaque adverb roots.** **Implementation verified by
  627 Rust tests, full pinned corpus checks, broader candidate and novel
  comparisons, browser/HTTP checks, and Nix CLI/web builds and flake checks.**
  천천히 and both 분연히 homonyms now retain 천천/분연 + 히 paths with the
  explicit `Root` role. This role asserts a derivational base without asserting
  a standalone noun, adverb or predicate POS. Existing adverb-compatible particle
  chains compose after the suffix; source-listed modern spelling is preserved.
  A separate 천천하다 + 히 lookup hypothesis is inferred from KRDict's suffix
  example and NIKL's independently attested contemporary 천천하다. Missing
  dictionary heads remain missing, and both filters retain whole lexical adverbs
  while removing these unmatched bases. No related 분연하다 is invented.
  Sources: KRDict [-히](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88504),
  [천천히](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=26902),
  [분연히¹](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=60522),
  [분연히²](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=60708),
  and NIKL [304542](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=304542)/
  [324669](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=324669).
  [Four tests](../tests/opaque_adverbs.rs), 63 stable `opaque-*` cases (61 required /
  2 forbidden), 84 complete native groups with 40 target occurrences, and two
  unchanged annotated training sentences protect roles, source spelling, Unicode,
  lexical alternatives, dictionary uncertainty, ordered CLI word/text exports and
  the new JSON role. Native examples do not choose contextual senses, and the
  annotated gold remains lexical. Across 12,060 probes no candidate is removed;
  42 additions have required-path judgments and 114 remain unjudged. Both novel
  dictionary filters, including spacing suggestions, remain byte-identical. See
  [the source review](opaque-adverb-source-audit.json) and
  [evaluation](opaque-adverb-evaluation.json).
  Other opaque roots, class subdivision, suffix/auxiliary interactions, nominal
  -이 and independent Korean-language review remain in COV-022/completion review.

- [x] **COV-022d — Native predicate-base noun-forming -이.** Implemented
  and verified for all eight sense-1 examples of KRDict 88924: 굽이, 깊이,
  넓이, 길이, 놀이, 높이, 먹이 and 벌이. The finite noun paths preserve
  predicate lookup lemmas, whole lexical nouns, adverb homonyms, existing
  nominal particles/copulas, plural 들 and approximation 쯤. Noun and adverb
  suffix provenance remains separate despite identical bare lemma/morpheme
  fields; browser sources use 88924/88927 respectively. `required_rules`
  constraints keep ledger judgments specific to the noun derivation.
  Source: [noun-forming -이](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88924).
  [Source review](nominal-i-source-audit.json) retains all three senses and
  44 native groups, including eight direct target examples, and complete
  training sentences with four unchanged lexical noun targets. The native
  fixture has 33 complete source entries. Five [tests](../tests/nominal_i.rs),
  151 stable cases (127 required / 24 forbidden), and exact noun/copula/quote
  controls pass targeted validation. Wider compound/root senses,
  other suffix/auxiliary attachments and independent Korean-language review
  remain COV-022 work. All 632 Rust tests, candidate comparisons, full frozen
  corpus outcomes, lint/format/build, browser, Nix CLI/web/flake checks and
  refreshed packaged preview gates pass. The novel retains 179,112 records,
  adding 41 candidates at 39 occurrences in all five modes without removals;
  their contextual senses remain unjudged. One spacing segment gains a noun
  path while boundaries and search limits stay unchanged. Three interleaved
  release samples per filter have after medians of 1.61/1.59 seconds on this host;
  timings are descriptive. See [evaluation](nominal-i-evaluation.json).

- [ ] **COV-022e — Remaining native noun-forming -이 base classes.**
  The [discovery audit](nominal-i-remaining-audit.json) records every remaining
  native group of KRDict 88924: six sense-2 compound forms and thirty sense-3
  noun/root/sound-or-manner forms, each with a stable observation ID. All 108
  bare-word CLI probes (raw/headword/compatible) currently lack the new
  noun-forming rule; existing lexical candidates remain in the report. Fourteen
  prefix occurrences across six pinned corpus partitions retain complete
  sentence bodies and original rows. All are in KAIST training data and retain
  whole lexical noun gold; they do not license a new derivational segmentation.
  Review selected nominal-plus-predicate combinations such as 길잡이/목걸이/
  옷걸이/젖먹이, the explicit unresolved 떠돌이/미닫이 class examples, and
  each sense-3 base class before adding required paths. Preserve lexical/adverb/
  causative homonyms and add an explicit compound boundary if needed for ordered
  display and outer particles/copulas. Missing dictionary bases do not establish
  Root status, and dictionary POS does not certify derivational relationships.
  The [read-only audit tool](../tools/audit_nominal_i.py) records pinned source,
  dictionary, CLI and corpus hashes without changing gold or baselines.

### P3: dictionary and representation boundaries

- [x] **COV-014 — Names, unknown words, numbers, and foreign letters.**
  **Implemented within the existing unbroken-word tokenization scope.** ABC는
  and 3은 preserve their spelled bases with explicit pronunciation conditions
  in rule provenance. Particle allomorphs distinguish vowel, consonant,
  non-ㄹ consonant, and vowel-or-ㄹ assumptions. Omitted/contracted copulas
  also report their vowel condition, separately from later auxiliary contractions.
  A Hangul boundary stays known, including suffixes and units in ABC들로 and
  2026년은. Original-word candidates, unknown-name spellings, source offsets,
  and dictionary-only semantics remain: a rule cannot create a dictionary entry.
  The browser displays pronunciation conditions and exports them with each
  candidate. Tests cover Unicode/NFD, chain violations, source-backed judgments,
  39 new annotated groups, dictionary/CLI parity, and browser alternatives.
  [Scope and sources](rules.md#foreign-nominals-and-pronunciation-conditions-cov-014),
  [tests](../tests/foreign_nominals.rs), and [evaluation](foreign-nominal-evaluation.json).
  Punctuation-bearing names, decimals, and formatted numbers remain split at
  punctuation under the existing [release boundary](../README.md#boundaries-and-licensing);
  this is now covered by exact streaming/offset tests, not presented as recovered
  whole-name/number segmentation. Transliteration, choosing a numeral reading,
  and named-entity recognition are not inferred by these conditional hypotheses.
  Broader copula attachment constraints remain COV-020.
- [x] **COV-015 — Grammar-label and presentation coverage.** **Implemented
  for all 473 currently emitted canonical grammar forms.** The initial catalog
  adds 140 missing labels with source IDs, headwords, and grammatical kinds.
  Reviewed expression entries and bundled/component mappings resolve without
  a general unclassified-POS fallback. Hover notes distinguish bundles,
  contractions, and joined representations of spaced dictionary expressions.
  Table-inventory tests detect new unlabeled forms; offline source tests validate
  all mappings and reject wrong kinds/IDs/headwords/POS for exceptions. Browser
  regressions cover ten representative labels, source panes, normalized order,
  and unchanged CLI candidates. Labels describe common functions, not contextual
  senses; independent linguistic review remains in the completion review.
  Forms missing from the pinned dictionary may cite verified primary references;
  으리다 links to NIKL's source article and retains an empty API dictionary-entry
  list. Browser source links work independently of a connected dictionary.
  Evidence: [label data](../web/src/grammar-labels.json),
  [inventory test](../src/grammar.rs), [source tests](../src/bin/klem-web/grammar_labels.rs),
  [audit](grammar-label-evaluation.json),
  [source notice](../web/public/Grammar-labels-LICENSE.txt), and
  [web API/display contract](web.md).

## Definition of done for each open item

Copy this checklist into the implementation notes for an item. A fix to one
example does not close a broader family unless the family scope is narrowed
explicitly and remaining cases get their own IDs.

- [ ] State the supported forms, attachment conditions, and remaining exclusions;
  identify primary-source evidence. Record unresolved linguistic judgments.
- [ ] Add stable case/judgment IDs to the
  [candidate ledger](../tests/fixtures/validity.json) where supported, plus tests
  for exact lemma groups, morpheme order/kinds, and rule provenance as relevant.
- [ ] Cover positive paths, boundary violations, ambiguity preservation, and
  interactions with neighboring rules. Forbidden judgments target a specific
  analysis; they must not reject all readings of an ambiguous surface.
- [ ] Verify dictionary-backed behavior using attributed offline fixtures.
  Confirm that headword presence, POS compatibility, and sense choice remain
  distinguishable. Preserve the unfiltered exhaustive candidate API.
- [ ] Verify CLI/library parity and ordered display/export. For a new grammar
  kind or label, include a browser regression and inspect contraction handling.
- [ ] Pass existing candidate, dictionary, and stress regressions. Compare all
  available frozen corpus cases without overwriting the baseline being checked.
  Review changed output fingerprints individually; never regenerate them just
  to make a failure pass.
- [ ] Run the relevant [verification commands](#verification), update this item's
  status with test names/case IDs, and document any remaining review work.

## Completion review

- [ ] Close or explicitly defer each open item with a reason and bounded scope.
- [ ] Finish COV-013's inventory audit; make newly discovered gaps visible here.
- [ ] Review remaining corpus misses and the candidate ledger's unjudged queue.
  Independent Korean-language review is still pending; test success is not a
  linguistic precision estimate.
- [ ] Check representative passages separately from repeatedly used regression
  corpora, including dictionary misses and reader-visible breakdown quality.
- [ ] Publish the supported scope and unresolved limits, alongside recall,
  candidate ambiguity, dictionary coverage, and performance evidence. Do not
  describe the tool as complete for all Korean.

Historical/dialectal coverage, spelling correction, whitespace repair, arbitrary
compound segmentation, exhaustive derivational morphology, contextual ranking,
sentence parsing, and EPUB extraction remain **deferred** under the
[current release boundaries](../README.md#boundaries-and-licensing).
COV-010/012 track bounded extensions, not a commitment to exhaustive derivation.

## Verification

Run checks appropriate to the change; a documentation-only tracker edit does not
require rebuilding the application. Existing offline fixtures require no data
downloads. Full corpus checks require the already downloaded data/baselines;
browser checks require Chromium. See [evaluation](evaluation.md) and
[web setup](web.md#tests) for prerequisites and details.

```sh
python3 -m unittest discover -s tools -p 'test_review_inventory.py'
python3 tools/review_inventory.py --verify
cargo test --locked --offline --features web
cargo clippy --locked --offline --all-targets --features web -- -D warnings
cargo fmt --all -- --check
cargo test --locked --offline --features web --test corpus pinned_full_corpus_regressions -- --ignored
cargo build --locked --offline --features web
npm run build --prefix web
CHROMIUM_PATH=/path/to/chromium npm test --prefix web
nix flake check
nix build .#web
```

To reproduce an individual dictionary-filtered miss:

```sh
cargo run --locked --offline -- word 저도요
cargo run --locked --offline -- word 저도요 --dictionary data/dictionaries/krdict/krdict.db --dict-only
```

Record the input, intended path, actual path(s), dictionary fingerprint, source,
and relevant tracker ID. An empty filtered result can reflect missing grammar
or missing vocabulary; a nonempty result can still omit the intended analysis.
