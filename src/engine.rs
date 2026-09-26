use crate::{Analysis, Error, Lemma, LemmaKind, Morpheme, MorphemeKind, WordAnalysis};
use crate::{
    grammar::{self, Boundary, Recovery},
    hangul::*,
};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    rc::Rc,
};
use unicode_normalization::UnicodeNormalization;

fn lemma(text: impl Into<String>, kind: LemmaKind) -> Lemma {
    Lemma {
        text: text.into(),
        kind,
    }
}
fn morph(form: impl Into<String>, kind: MorphemeKind) -> Morpheme {
    Morpheme {
        form: form.into(),
        kind,
    }
}

// Strip at most one plural suffix at the nominal boundary, before any
// particles or copula. Keep the unstripped lexical hypothesis as well: a word
// ending in 들 need not contain a productive plural suffix (e.g. 아들).
fn plural_nominal(word: &str) -> Option<Analysis> {
    let base = word.strip_suffix('들').filter(|s| !s.is_empty())?;
    Some(Analysis {
        lemmas: vec![lemma(base, LemmaKind::Nominal)],
        morphemes: vec![morph("들", MorphemeKind::Suffix)],
        rules: vec!["suffix.plural".into()],
        unchanged: false,
    })
}

fn nominal_bases(word: &str) -> Vec<Analysis> {
    let mut out = vec![Analysis {
        lemmas: vec![lemma(word, LemmaKind::Nominal)],
        morphemes: vec![],
        rules: vec![],
        unchanged: false,
    }];
    out.extend(plural_nominal(word));
    out
}

#[derive(Clone)]
struct Predicate {
    stem: String,
    auxiliaries: Vec<String>,
    morphs: Vec<Morpheme>,
    rules: Vec<String>,
    connector: bool,
}
type PrefinalMemo = HashMap<(String, u8, u8), Vec<Predicate>>;

fn prefinals(stem: &str, stage: u8, pasts: u8, memo: &mut PrefinalMemo) -> Vec<Predicate> {
    let key = (stem.to_owned(), stage, pasts);
    if let Some(result) = memo.get(&key) {
        return result.clone();
    }
    let mut out = vec![Predicate {
        stem: stem.into(),
        auxiliaries: vec![],
        morphs: vec![],
        rules: vec![],
        connector: false,
    }];
    let mut choices: Vec<(Recovery, u8, u8, &str, &str)> = vec![];
    if stage >= 4 {
        for r in grammar::recover(stem, "더", Boundary::Literal) {
            choices.push((r, 3, pasts, "더", "prefinal.retrospective"));
        }
    }
    if stage >= 3 {
        for r in grammar::recover(stem, "겠", Boundary::Literal) {
            choices.push((r, 2, pasts, "겠", "prefinal.modal"));
        }
    }
    if stage >= 2
        && pasts < 2
        && let Some((_, v, 20)) = last(stem)
    {
        for r in grammar::aeo(&replace_last(stem, v, 0).unwrap()) {
            choices.push((r, 2, pasts + 1, "었", "prefinal.past"));
        }
    }
    if stage >= 1 {
        for (suffix, boundary) in [("으시", Boundary::EuFull), ("시", Boundary::EuZero)] {
            for r in grammar::recover(stem, suffix, boundary) {
                choices.push((r, 0, pasts, "시", "prefinal.honorific"));
            }
        }
    }
    for (r, next, count, form, rule) in choices {
        for mut p in prefinals(&r.stem, next, count, memo) {
            p.morphs.push(morph(form, MorphemeKind::Prefinal));
            p.rules.extend(r.rules.clone());
            p.rules.push(rule.into());
            out.push(p);
        }
    }
    memo.insert(key, out.clone());
    out
}

fn predicates(word: &str) -> Vec<Predicate> {
    let mut out = vec![];
    let mut memo = HashMap::new();
    for ending in grammar::matching_endings(word) {
        for r in grammar::recover(word, ending.suffix, ending.boundary) {
            for mut p in prefinals(&r.stem, 4, 0, &mut memo) {
                p.morphs.push(morph(ending.form, MorphemeKind::Ending));
                p.rules.extend(r.rules.clone());
                p.rules.push("ending".into());
                p.connector = ending.connector;
                out.push(p);
            }
        }
    }
    out
}

fn predicate_analysis(p: &Predicate) -> Analysis {
    Analysis {
        lemmas: vec![lemma(format!("{}다", p.stem), LemmaKind::Predicate)],
        morphemes: p.morphs.clone(),
        rules: p.rules.clone(),
        unchanged: false,
    }
}

fn expand_predicate(p: &Predicate) -> Vec<Analysis> {
    let mut out = vec![predicate_analysis(p)];
    add_copulas(p, &mut out);
    for a in &mut out {
        a.lemmas.extend(
            p.auxiliaries
                .iter()
                .map(|s| lemma(format!("{s}다"), LemmaKind::Auxiliary)),
        );
    }
    out
}

fn add_copulas(p: &Predicate, out: &mut Vec<Analysis>) {
    if let Some(base) = p.stem.strip_suffix('이').filter(|s| !s.is_empty()) {
        let mut nominal_alternatives = nominal_bases(base);
        nominals(base, 5, false, &[], &mut nominal_alternatives);
        for mut a in nominal_alternatives {
            a.lemmas.push(lemma("이다", LemmaKind::Copula));
            a.morphemes.extend(p.morphs.clone());
            a.rules.extend(p.rules.clone());
            a.rules.push("copula".into());
            out.push(a);
        }
    }
    // The 라 family reconstructs 이 at its boundary; 다 permits omission here.
    if p.morphs.len() == 1 && coda(&p.stem) == Some(0) && p.morphs[0].form == "다" {
        let mut rules = p.rules.clone();
        rules.push("copula.zero".into());
        out.push(Analysis {
            lemmas: vec![
                lemma(&p.stem, LemmaKind::Nominal),
                lemma("이다", LemmaKind::Copula),
            ],
            morphemes: p.morphs.clone(),
            rules,
            unchanged: false,
        });
    }
}

/// Suffix peeling is acyclic: each particle consumes input, decreases a grammar
/// stage, or uses the one 만-before-case transition. No depth/candidate cutoff.
fn nominals(
    word: &str,
    stage: u8,
    after_case: bool,
    suffixes: &[Morpheme],
    out: &mut Vec<Analysis>,
) {
    for particle in grammar::particles() {
        let outer = suffixes.first().map(|m| m.form.as_str());
        let allowed = particle.class < stage
            || (after_case && particle.form == "만")
            || (outer == Some("만") && matches!(particle.form, "까지" | "부터"))
            || (outer == Some("의") && matches!(particle.class, 2 | 3) && particle.form != "의");
        if !allowed {
            continue;
        }
        let Some(base) = word.strip_suffix(particle.form) else {
            continue;
        };
        if !grammar::particle_matches(base, particle.condition) {
            continue;
        }
        let mut morphs = vec![morph(particle.form, MorphemeKind::Particle)];
        morphs.extend_from_slice(suffixes);
        for mut a in nominal_bases(base) {
            a.morphemes.extend(morphs.clone());
            a.rules.push("particle".into());
            out.push(a);
        }
        // 기 / (으)ㅁ nominalizations can be followed by particles.
        with_auxiliaries(base, PredicateEnd::Nominalized, |p| {
            for mut a in expand_predicate(&p) {
                a.morphemes.extend(morphs.clone());
                a.rules.extend(["particle".into(), "nominalization".into()]);
                out.push(a);
            }
        });
        let next = if after_case && particle.form == "만" {
            1
        } else {
            particle.class
        };
        nominals(
            base,
            next,
            particle.class == 1 || particle.class == 2,
            &morphs,
            out,
        );
    }
}

fn aux_allowed(stem: &str, connector: &str) -> bool {
    match connector {
        "어" => matches!(
            stem,
            "보" | "주"
                | "드리"
                | "버리"
                | "놓"
                | "두"
                | "가"
                | "오"
                | "지"
                | "있"
                | "없"
                | "내"
                | "대"
        ),
        "고" => matches!(stem, "있" | "싶" | "말"),
        "지" => matches!(stem, "않" | "못하" | "말"),
        "게" => matches!(stem, "되" | "하"),
        "어야" => stem == "하",
        _ => false,
    }
}

#[derive(Clone, Copy)]
enum PredicateEnd {
    Any,
    Nominalized,
}
impl PredicateEnd {
    fn accepts(self, p: &Predicate) -> bool {
        matches!(self, Self::Any)
            || p.morphs.last().is_some_and(|m| {
                matches!(
                    m.form.as_str(),
                    "기" | "음" | "는가" | "은가" | "는지" | "은지"
                )
            })
    }
}

struct AuxEdge {
    left: usize,
    tails: Rc<Vec<Predicate>>,
}
struct AuxNode {
    bases: Vec<Predicate>,
    edges: Vec<AuxEdge>,
}

// A packed prefix DAG stores only single predicates and links to shorter input.
// Expanded chains are never cached. Equal suffix strings share tail recoveries.
// Both construction and traversal are iterative, including on very long tokens.
fn with_auxiliaries(word: &str, ending: PredicateEnd, mut emit: impl FnMut(Predicate)) {
    let mut boundaries: Vec<_> = word.char_indices().map(|(i, _)| i).collect();
    boundaries.push(word.len());
    let root = boundaries.len() - 1;
    let mut nodes: Vec<Option<AuxNode>> = (0..=root).map(|_| None).collect();
    let mut tails_cache: HashMap<&str, Rc<Vec<Predicate>>> = HashMap::new();
    let mut pending = vec![root];
    while let Some(end) = pending.pop() {
        if nodes[end].is_some() {
            continue;
        }
        let accepts = |p: &Predicate| {
            if end == root {
                ending.accepts(p)
            } else {
                p.connector
            }
        };
        let bases = predicates(&word[..boundaries[end]])
            .into_iter()
            .filter(&accepts)
            .collect();
        let mut edges = vec![];
        for start in 1..end {
            let right = &word[boundaries[start]..boundaries[end]];
            let tails = tails_cache.entry(right).or_insert_with(|| {
                Rc::new(
                    predicates(right)
                        .into_iter()
                        .filter(|p| {
                            ["어", "고", "지", "게", "어야"]
                                .iter()
                                .any(|c| aux_allowed(&p.stem, c))
                        })
                        .collect(),
                )
            });
            if tails.iter().any(&accepts) {
                edges.push(AuxEdge {
                    left: start,
                    tails: Rc::clone(tails),
                });
                if nodes[start].is_none() {
                    pending.push(start);
                }
            }
        }
        nodes[end] = Some(AuxNode { bases, edges });
    }
    // Frames enumerate one right-to-left path at a time. Every link consumes
    // input; no search-depth or candidate cutoff is needed.
    struct Frame {
        node: usize,
        base: usize,
        edge: usize,
        tail: usize,
    }
    let frame = |node| Frame {
        node,
        base: 0,
        edge: 0,
        tail: 0,
    };
    let mut frames = vec![frame(root)];
    let mut path: Vec<&Predicate> = vec![];
    while let Some(current) = frames.last_mut() {
        let node = nodes[current.node].as_ref().unwrap();
        let accepts = |p: &Predicate| match path.last() {
            Some(right) => p.connector && aux_allowed(&right.stem, &p.morphs.last().unwrap().form),
            None => ending.accepts(p),
        };
        if let Some(base) = node.bases.get(current.base) {
            current.base += 1;
            if accepts(base) {
                let mut joined = base.clone();
                // Provenance is a set, not a derivation trace. Deduplicate it
                // before materializing output, rather than retaining every step.
                let mut rules: BTreeSet<&str> = base.rules.iter().map(String::as_str).collect();
                for tail in path.iter().rev() {
                    joined.auxiliaries.push(tail.stem.clone());
                    joined.morphs.extend(tail.morphs.iter().cloned());
                    rules.extend(tail.rules.iter().map(String::as_str));
                    rules.insert("auxiliary");
                    joined.connector = tail.connector;
                }
                joined.rules = rules.into_iter().map(str::to_owned).collect();
                emit(joined);
            }
        } else if let Some(edge) = node.edges.get(current.edge) {
            if let Some(tail) = edge.tails.get(current.tail) {
                current.tail += 1;
                if accepts(tail) {
                    path.push(tail);
                    frames.push(frame(edge.left));
                }
            } else {
                current.edge += 1;
                current.tail = 0;
            }
        } else {
            frames.pop();
            path.pop();
        }
    }
}

pub(crate) fn analyze(word: &str) -> Result<WordAnalysis, Error> {
    if word.is_empty() {
        return Err(Error::EmptyWord);
    }
    if word.chars().any(char::is_whitespace) {
        return Err(Error::WhitespaceInWord);
    }
    let normalized: String = word.nfc().collect();
    let mut out = vec![Analysis {
        lemmas: vec![lemma(&normalized, LemmaKind::Unclassified)],
        morphemes: vec![],
        rules: vec!["identity".into()],
        unchanged: true,
    }];
    if has_hangul(&normalized) {
        out.extend(plural_nominal(&normalized));
        for (suffix, vowel_only) in [
            ("이에요", false),
            ("예요", true),
            ("이야", false),
            ("야", true),
        ] {
            if let Some(base) = normalized.strip_suffix(suffix).filter(|s| !s.is_empty())
                && (!vowel_only || coda(base) == Some(0))
            {
                for mut a in nominal_bases(base) {
                    a.lemmas.push(lemma("이다", LemmaKind::Copula));
                    a.morphemes.push(morph(
                        if suffix.ends_with("요") {
                            "에요"
                        } else {
                            "야"
                        },
                        MorphemeKind::Ending,
                    ));
                    a.rules.push("copula.polite".into());
                    out.push(a);
                }
            }
        }
        if normalized == "아니에요" {
            out.push(Analysis {
                lemmas: vec![lemma("아니다", LemmaKind::Predicate)],
                morphemes: vec![morph("에요", MorphemeKind::Ending)],
                rules: vec!["negative_copula.polite".into()],
                unchanged: false,
            });
        }
        for (form, particle) in [("게", "이"), ("건", "는"), ("걸", "를")] {
            if normalized == form {
                for base in ["거", "것"] {
                    out.push(Analysis {
                        lemmas: vec![lemma(base, LemmaKind::Nominal)],
                        morphemes: vec![morph(particle, MorphemeKind::Particle)],
                        rules: vec!["nominal.contraction".into()],
                        unchanged: false,
                    });
                }
            }
        }
        with_auxiliaries(&normalized, PredicateEnd::Any, |p| {
            out.extend(expand_predicate(&p));
        });
        nominals(&normalized, 5, false, &[], &mut out);
        for (surface, base, particle) in [
            ("내가", "나", "가"),
            ("네가", "너", "가"),
            ("제가", "저", "가"),
            ("누가", "누구", "가"),
            ("내", "나", "의"),
            ("네", "너", "의"),
            ("제", "저", "의"),
        ] {
            if normalized == surface {
                out.push(Analysis {
                    lemmas: vec![lemma(base, LemmaKind::Nominal)],
                    morphemes: vec![morph(particle, MorphemeKind::Particle)],
                    rules: vec!["pronoun".into()],
                    unchanged: false,
                });
            }
        }
    }
    // Semantic duplicates share provenance; sorting is independent of hash order.
    let mut unique: BTreeMap<(Vec<Lemma>, Vec<Morpheme>, bool), Vec<String>> = BTreeMap::new();
    for a in out {
        unique
            .entry((a.lemmas, a.morphemes, a.unchanged))
            .or_default()
            .extend(a.rules);
    }
    let analyses = unique
        .into_iter()
        .map(|((lemmas, morphemes, unchanged), mut rules)| {
            rules.sort();
            rules.dedup();
            Analysis {
                lemmas,
                morphemes,
                rules,
                unchanged,
            }
        })
        .collect();
    Ok(WordAnalysis {
        normalized,
        analyses,
    })
}

pub(crate) fn retained_bytes(result: &WordAnalysis) -> usize {
    use std::mem::size_of;
    size_of::<WordAnalysis>()
        + result.normalized.capacity()
        + result.analyses.capacity() * size_of::<Analysis>()
        + result
            .analyses
            .iter()
            .map(|a| {
                a.lemmas.capacity() * size_of::<Lemma>()
                    + a.lemmas.iter().map(|l| l.text.capacity()).sum::<usize>()
                    + a.morphemes.capacity() * size_of::<Morpheme>()
                    + a.morphemes.iter().map(|m| m.form.capacity()).sum::<usize>()
                    + a.rules.capacity() * size_of::<String>()
                    + a.rules.iter().map(String::capacity).sum::<usize>()
            })
            .sum::<usize>()
}
