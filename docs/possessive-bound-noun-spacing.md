`spacing.nominal_bound_noun` adds bounded missing-space hypotheses for possessions
before 것 and nominal causes before 때문. It preserves the original word candidates
and earlier spacing options. Each proposed word retains independently analyzed,
dictionary-compatible readings and original UTF-8 byte spans.

`내것은` offers `내 것은`, with 내 independently recovered as 나 + 의.
Explicit genitives such as 친구의, contracted 내/네/제, and the exact source-listed
bare owners 우리/누구/언니/친구/동생/할머니/선생님 can license possession.
Plural forms of these listed nominal owners are supported. Known noun/pronoun
cause phrases can include multiple words: `아버지건강때문에` offers
`아버지 건강 때문에`, and `아이학교때문에` offers `아이 학교 때문에`.
The right noun requires exact KRDict entry 62835 or 64555 and bound-noun POS.
Other same-head entries cannot supply that license. All passes share the existing
64 NFC-character, 256-probe and 16-option defaults and report reached bounds.

These are structural alternatives. Dictionary homonyms can admit additional
splits such as `피곤 하 기 때문이다` and `미 등록 어 때문에`; context may
exclude them. Original broad negative expectations, failed captures and explicit
scope corrections remain recorded. The direct predicate nominalization
`피곤하기 때문이다` retains its separate modifier/bound-noun rule.
Demonstratives 이것/그것/저것 retain their whole-word analyses.

The complete original dictionary proposal `박 선생님 것` remains unmet.
KRDict's 박 entries mean gourd and a unit for nights, and cannot license the
surname. Proper-name lexical data and a source-backed bounded name/noun phrase
license are still needed. An earlier implementation borrowed the gourd identity;
that branch was removed and its captures retained as superseded evidence.
Numerals, additional nominal formations/possessors, wider constructions and
contextual sense selection require further review. No sentence parsing or
linguistic precision claim follows from these finite checks.

The isolated and installed versions pass 1,077 Rust tests, zero failures and one
ignored test, formatting and Clippy. Forty-two stable cases produce 756 observed
Unicode/filter/cache results, with the surname requirement explicitly unmet.
Installed SolidJS checks verify 210 diagrams, six exact exports and 218 complete
Native dictionary entries. All 1,128,312 observed corpus/novel frames retain
the same word candidates and prior spacing options in the same order. The new
rule changes reached-limit metadata in 506 frames and adds no options in those
particular cohorts; the dedicated cases exercise its positive behavior. Both
32,096/21,406-word cohorts and all 66,570 annotated adapter rows are preserved.
The exact installed source union has 977 inputs: 960 Rust/package inputs and
18 frontend inputs with one overlap. Thirty source/runtime/performance integrity controls reject
altered evidence. All 80 paired timings and ten complete cache streams pass;
observed spacing medians are 12.17 → 12.16 and 12.09 → 11.82 seconds. These
measurements describe this novel/machine, without statistical equivalence or
causality claims. Current-main source binding, normal Git-backed Nix build,
repository-default audits and actual web launcher/browser checks pass. A new
complete combined inventory gate and wider/contextual coverage remain open.

Dictionary fixtures and source groups are attributed to the National Institute
of Korean Language, Korean Basic Dictionary, under CC BY-SA 2.0 KR. Full native
and original LMF entries, source-export hashes and unabridged multiword/dialogue
groups are retained. Authored transformations are separate from quotations and
annotated-corpus gold. See the coverage checklist for remaining review work.
