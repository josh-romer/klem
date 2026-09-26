# Coverage and completion tracker

Last reviewed: 2026-09-26.

This tracks the modern written Korean rule coverage needed by the CLI, library,
and sentence explorer. Completion means that the explicitly listed scope has
implementation and regression evidence. It does not establish that every Korean
analysis is generated or that every generated candidate is linguistically valid.
Contextual sense selection and sentence parsing remain separate work.

The open examples below were probed with the current CLI and the local September
2026 Korean Basic Dictionary snapshot. They are audit observations, not yet
executable regression cases unless a test is linked. No overall completion
percentage is assigned: the inventory itself still needs an audit.

## Status and priorities

- **Implemented:** the stated behavior has code and regression coverage; broader
  coverage or independent linguistic review may still be pending.
- **Missing:** the intended analysis is not generated in the audited examples.
- **Partial:** some readings work, but decomposition, roles, or combinations are missing.
- **Audit needed:** coverage has not been inventoried sufficiently to declare it complete.
- **Deferred:** outside the current release scope; not silently counted as complete.

P1 is the next implementation batch, P2 follows it, and P3 needs a scope or
representation decision first. Priorities reflect the concrete failures found,
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

### P1: common missing analyses and a role correction

- [ ] **COV-006 — Contracted particles.** **Missing.** 학교에선 and 선생님께선
  produce no dictionary-filtered analyses. Recover the particle chains
  학교 + 에서 + 는 and 선생님 + 께서 + 는, with an explicitly normalized display.
  Cover contracted ㄴ/ㄹ attachment and interactions with existing particles;
  define canonical forms without confusing them with verb endings.
  Source starting points: KRDict [ㄴ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85847)
  and [ㄹ](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85760).
  Exit cases must include particle chains, boundary failures, and retention of
  genuine lexical/verb alternatives.
- [ ] **COV-007 — Pronoun contractions beyond the special cases.** **Partial.**
  이건 does not recover the intended 이것/이거 + topic reading; 그걸 and 뭘
  survive as whole dictionary entries without the intended pronoun/object split.
  Add source-justified alternatives for these forms and audit the related
  이/그/저 paradigm. Reuse COV-006 where appropriate, retain whole-word readings,
  and avoid inventing character spans for contractions.
  Source starting points: KRDict [이거](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=71128),
  [뭐](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=84991), and
  the ㄴ/ㄹ entries above. Review exactly which expanded lexical alternatives
  each form licenses before adding required judgments.
- [ ] **COV-008 — Polite particle 요.** **Missing.** 저도요 and 친구는요 return
  no dictionary-filtered analyses. Required initial paths: 저 + 도 + 요 and
  친구 + 는 + 요. Audit attachment after nominals, other particles, adverbials,
  and endings; preserve existing 어요-family analyses. Do not strip every final
  요 indiscriminately. Source: [NIKL explanation and attachment examples](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=312410).
- [ ] **COV-009 — Distinguish the 들 particle from nominal -들.** **Partial.**
  빨리들 currently survives headword filtering through a nominal plural
  hypothesis, although 빨리 is an adverb. The appropriate particle analysis
  is missing; 먹어들 also has no dictionary-filtered reading in the audit.
  Model the grammatical role and its attachment conditions separately, keep
  지식인들을 working, and show the correct grammar entry/label in the browser.
  Source: KRDict [들 particle](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86264)
  versus [plural suffix -들](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74906).
  Dictionary-free hypotheses remain hypotheses; do not silently change the
  existing headword-only filter into a strict POS filter.

### P2: additional morphology

- [ ] **COV-010 — Productive suffix decomposition.** **Partial.** 학생답다
  returns no dictionary-filtered results. 선생님께 already recovers 선생님 + 께,
  and 과학적이다 recovers 과학적 + 이다, but neither exposes the internal suffix.
  Start with separately scoped -답다, -님, and -적 support. Decide how a suffix
  that forms a predicate is represented and conjugated before implementing it.
  Preserve recognized whole-word lemmas; make deeper learner decomposition an
  additional analysis, not mandatory destructive splitting. Audit attachment
  restrictions and suffix combinations instead of allowing arbitrary recursion.
  Sources: KRDict [-답다](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=92145),
  [-님](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88852),
  [-적](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88966).
- [ ] **COV-011 — Further 하다 contractions.** **Missing.** 생각지 and 생각건대
  do not recover 생각하다. The documented aspiration gap includes 피케;
  비유컨대 also appears in the saved development misses. Add independently
  sourced deletion/aspiration conditions, conjugation paths, and paired negative
  cases. Extend the [spelling audit](rules.md#candidate-correctness-audit), rather
  than treating every shortened consonant sequence as a 하다 contraction.
- [ ] **COV-012 — Adverbial derivation.** **Partial.** 같이 and 없이 have useful
  whole-word dictionary entries, but the corpus-expected paths to 같다/없다
  are missing; 달리 → 다르다 is also a recorded development miss. Decide which
  derivations should be additional analyses and which remain lexical entries.
  Preserve whole-word meanings and source-check each attachment family.
  Evidence to triage: [KAIST development report](../data/baselines/kaist-dev.jsonl)
  and [adapter conventions](evaluation.md#adapters-and-metrics).
- [ ] **COV-013 — Ending, particle-chain, and auxiliary inventory audit.**
  **Audit needed.** Compare the implemented tables with dictionary grammar
  entries and cluster saved corpus misses by rule family. Previously recorded
  examples include 보듯이, 있습니다만, 어디까지나, and 번져나갔다; re-probe them
  before promoting a miss to a required test. Distinguish true missing rules
  from annotation errors and differing lexical segmentation. Split this item
  into individually scoped entries as families are reviewed. Corpus gold does
  not enumerate every valid alternative.

### P3: dictionary and representation boundaries

- [ ] **COV-014 — Names, unknown words, numbers, and foreign letters.**
  **Partial.** ABC는 and 3은 do not recover their intended particle attachment
  in the audit. Separate pronunciation uncertainty, tokenizer boundaries, and
  absent dictionary headwords: fixing a rule cannot create a missing dictionary
  entry. Define pronunciation inputs or explicit alternative hypotheses before
  relaxing consonant/vowel conditions. Keep unknown tokens visible and report
  uncertainty. Any new filter mode or fallback must preserve the documented
  semantics of `--dict-only`. See [release boundaries](../README.md#boundaries-and-licensing)
  and [dictionary integration](dictionary.md).
- [ ] **COV-015 — Grammar-label and presentation coverage.** **Partial.**
  Common grammar labels exist; unmapped forms fall back to generic role labels.
  Inventory missing labels, attach source IDs, and test kind-sensitive lookup
  and ordering whenever a morphology family is added. Continue separating
  normalized expansion, independent word combinations, and dictionary senses.
  Evidence: [label data](../web/src/breakdown.ts),
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
