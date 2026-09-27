# Dictionary-backed attachment checks (COV-017aa)

`--dict-compatible` keeps headword-matching analyses unless the dictionary supplies
only conflicting lexical evidence for at least one component. It is an explicit,
finite conflict policy, not a grammaticality score. Unknown classes remain.
`--dict-only` still checks headword presence regardless of POS. Neither option
changes the rule engine or its cached, unfiltered analyses.

The browser offers **Exclude known grammar conflicts** under **Dictionary matches
only**. Reading choices, counts, combinations and JSON export use the same policy.
The browser prefers a homonym supported by that particular reading for its short
gloss; all dictionary entries and their senses remain available for inspection.
This does not select a sense from sentence context.

## Evidence and decisions

The [source review](dictionary-attachment-evaluation.json) retains the pinned
KRDict entries, all notes/senses and source hashes. The independent
[dictionary-policy ledger](../tests/fixtures/dictionary-attachments.json) has
stable case/judgment IDs and exact lemma/morpheme roles. Its required/forbidden
verdicts apply **after this filter**. They are separate from the unfiltered rule
ledger because an unknown-class rule hypothesis must still be generated.

| Check | Scope | Example |
|---|---|---|
| `lexical_role` | Existing broad POS-to-role mapping | 가늘다 as a nominal base before omitted 이다 conflicts with its adjective-only entry. |
| `present_declarative_verb` | Lexical predicates with the shared canonical present-declarative family, including honorific 시 | 가는다니 → 가늘다 + 는다니 conflicts; 먹는다니 remains. |
| `bare_adjectival_question` | Bare lexical predicates with 으냐/으냐는/으냐며/으냐면서/으냐니/으냔 | 길으냐니 → 긷다 + 으냐니 conflicts; 좋으냐니 remains. |
| `negative_copula_command` | Lexical 아니다 with canonical command 으라니 | 아니라니 retains 아니다 + factual 라니, excluding its distinct command hypothesis. |

The present family is shared with the engine: 는다/는다고/는다는/는다면/는답니다/
는다거나/는다든가/는다네/는다는데/는다며/는다면서/는다니/는단. Attached ㄴ
spellings have these canonical forms. An outer particle does not change the
attachment class, and honorific 시 does not turn an adjective into a verb.
The [는다니 source](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86182)
and [으냐니 source](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=87425)
state their different lexical attachment classes.

The command/factual distinction is deliberately narrow. The source for
[라니](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86509)
separates factual 이다/아니다 readings from verbal commands. This supports
excluding the command analysis of 아니다, not every adjective command.
[란](https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86297)
illustrates 행복하란, and
[NIKL's consultation](https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=261&pageIndex=1&qna_seq=318597)
explains wish uses of some adjective commands/proposals. 행복하란 and 행복하자
therefore remain. Broader command restrictions need lexical and contextual review.

## Homonyms, unknowns and ownership

Each entry must satisfy both the proposed lexical role and the applicable ending
check. Evidence from different homonyms is never mixed to make an otherwise
unsupported entry pass. Any compatible entry preserves the lemma slot. If none
is compatible but at least one has an unknown class, the slot is unknown. With
no entries it is also unknown; both CLI filters independently require headword
presence. A reading conflicts if any slot conflicts, is unknown if at least one
slot is unknown, and otherwise passes the finite checks.

Thus 큰다니 retains verbal 크다 while marking adjectival 크다 as conflicting;
늦으냐니 retains adjectival 늦다 while marking its verbal homonym as conflicting.
Unchanged/unclassified dictionary words remain unknown and are retained.
Unknown provider POS labels are not guessed. A token-initial predicate matching
an auxiliary entry is also unknown: 싶었다 in 먹고 싶었다 needs the preceding
word to establish its auxiliary role. Its broad `pos_compatibility` remains the
legacy role-only value; the per-reading assessment records this boundary-aware
exception. No missing preceding verb is invented. Existential/honorific 있다/없다/
계시다 question paradigms are not rejected from their verbal POS alone; they
remain COV-019h. An adjectival homonym may independently support such a reading.

Checks follow the ordered component breakdown. In 가늘어한다니, 는다니 belongs
to auxiliary 하다, not lexical 가늘다. Nominalization, later copulas and adjective
suffixes likewise do not lend their ending to another lexical head. Malformed
externally constructed analyses with no supported breakdown are unknown.

## Library and JSON

`DictionarySession::annotate` adds `readings`, aligned with `WordAnalysis.analyses`.
Each reading includes a status and lemma-slot assessments. Each entry assessment
references its dictionary ID, status and conflict reasons, with a morpheme index
for ending conflicts. `compatible` means only that the entry passes the checks
above, not that every ending or sense is licensed.

`Annotation::assess(&Analysis)` evaluates one reading.
`Annotation::filter(&mut WordAnalysis, DictionaryFilter::Compatible)` retains
whole groups and updates both the lemma references and reading indices. It
recomputes evidence against the supplied analyses, handling reordered candidates
and older deserialized annotations without a `readings` field. Use an owned clone
or `Arc::make_mut` when filtering a cached analysis. `DictionaryFilter::Headword`
provides the existing headword-only policy through the same library API.

Annotations use the existing bounded headword-summary cache. Bulk analysis does
not load definitions or build a Cartesian product of senses. Per-reading evidence
increases JSON output size; its memory is released with each streamed token.
The web adapter loads short hints for compatible homonyms on demand within its
existing input limits.

## Remaining scope

Further lexical subsets, negative-auxiliary class inheritance, other reporting/
adnominal/question endings, sense-specific selection, existential paradigms and
contextual command/wish judgments remain under COV-017/019. Incompatible is not a
spelling-error diagnosis, and compatible/unknown is not a correctness guarantee.
Independent Korean review and fresh-prose evaluation remain pending.
