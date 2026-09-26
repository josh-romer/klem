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

`optimization.json` contains complete-output SHA-256 fingerprints for 30 manually
chosen words, captured from the engine before replacing the auxiliary chart.
These project-licensed compatibility snapshots protect grouping, morphemes, rule
provenance and ordering; they are not independently annotated linguistic gold.
Intentional grammar changes require reviewing any resulting fingerprint changes.

`validity.json` is a separate, agent-authored candidate-judgment ledger under the
project's MIT OR Apache-2.0 license, not an excerpt from the corpora below. It
contains short illustrative forms and source-backed rationales, with independent
Korean-language review still pending. See the [evaluation workflow](../../docs/evaluation.md#candidate-judgment-ledger-and-review-queue).

These are unmodified first-four-sentence excerpts from the **development**
partitions of Universal Dependencies 2.15. They are deliberately small offline
adapter/regression fixtures, not a representative accuracy benchmark.

* `kaist.conllu`: [UD Korean KAIST](https://github.com/UniversalDependencies/UD_Korean-Kaist/tree/888f855c7bcf1e39291246744f4e98f6bda6742e), sentences M2TA_069-s1 through M2TA_069-s4.
* `gsd.conllu`: [UD Korean GSD](https://github.com/UniversalDependencies/UD_Korean-GSD/tree/60ffc4f2f0cbf0bf816f0d44a7339512f5ce9c25), sentences dev-s1 through dev-s4.

Both datasets specify **CC BY-SA 4.0**, separately from klem's code license.
See [LICENSE.txt](LICENSE.txt) and the upstream READMEs. GSD's README distinguishes
the annotation license from rights in the underlying source texts.

Attribution: Jayeol Chun, Na-Rae Han, Jena D. Hwang, and Jinho D. Choi,
*Building Universal Dependency Treebanks in Korean*, LREC 2018; the KAIST corpus
contributors, including Key-Sun Choi; and the GSD contributors, including Ryan
McDonald, Joakim Nivre, and Daniel Zeman. GSD also requests citation of
McDonald et al., *Universal Dependency Annotation for Multilingual Parsing*,
ACL 2013. Full upstream notices are downloaded alongside each corpus.
