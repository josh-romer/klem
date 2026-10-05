//! Source-listed -화하다/-시하다 verbs, with independently sourced deeper noun bases.
use crate::{
    Lemma, LemmaKind, Morpheme, MorphemeKind, doeda_identity::OriginSource, engine::PredicateClass,
};
pub(crate) const RULE: &str = "suffix.verb.hada";
pub(crate) fn formation(head: &str) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    let base = match head {
        "가속화하다" => "가속화",
        "가시화하다" => "가시화",
        "간소화하다" => "간소화",
        "개방화하다" => "개방화",
        "객관화하다" => "객관화",
        "내면화하다" => "내면화",
        "다변화하다" => "다변화",
        "다양화하다" => "다양화",
        "다원화하다" => "다원화",
        "민영화하다" => "민영화",
        "민주화하다" => "민주화",
        "보편화하다" => "보편화",
        "상품화하다" => "상품화",
        "생활화하다" => "생활화",
        "의인화하다" => "의인화",
        "이론화하다" => "이론화",
        "이상화하다" => "이상화",
        "일반화하다" => "일반화",
        "일상화하다" => "일상화",
        "제도화하다" => "제도화",
        "조직화하다" => "조직화",
        "최소화하다" => "최소화",
        "토착화하다" => "토착화",
        "특수화하다" => "특수화",
        "표준화하다" => "표준화",
        "합리화하다" => "합리화",
        "황폐화하다" => "황폐화",
        "획일화하다" => "획일화",
        "동일시하다" => "동일시",
        "등한시하다" => "등한시",
        "문제시하다" => "문제시",
        "야만시하다" => "야만시",
        "의문시하다" => "의문시",
        "적대시하다" => "적대시",
        "죄악시하다" => "죄악시",
        "중요시하다" => "중요시",
        _ => return None,
    };
    Some((base, LemmaKind::Nominal, PredicateClass::Verb))
}
pub(crate) fn owned_source(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<&'static OriginSource> {
    if lemma.kind != LemmaKind::Nominal || !rules.iter().any(|r| r == RULE) {
        return None;
    }
    let first = morphs.first()?;
    if first.kind != MorphemeKind::Suffix {
        return None;
    }
    if first.form == "하다" {
        DIRECT
            .iter()
            .chain(SI_DIRECT)
            .find(|s| s.base == lemma.text)
    } else if first.form == "화"
        && crate::nominal_hwa::owner(lemma, rules, morphs)
        && morphs
            .get(1)
            .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "하다")
    {
        NESTED.iter().find(|s| s.base == lemma.text)
    } else if first.form == "시"
        && crate::nominal_si::owner(lemma, rules, morphs)
        && morphs
            .get(1)
            .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "하다")
    {
        SI_NESTED.iter().find(|s| s.base == lemma.text)
    } else {
        None
    }
}
pub(crate) fn owner_class(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<PredicateClass> {
    owned_source(lemma, rules, morphs).map(|_| PredicateClass::Verb)
}
const DIRECT: &[OriginSource] = &[
    OriginSource {
        base: "가속화",
        expected_origins: &["加速化"],
        whole_entries: &["krdict:14636"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "가시화",
        expected_origins: &["可視化"],
        whole_entries: &["krdict:14685"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "간소화",
        expected_origins: &["簡素化"],
        whole_entries: &["krdict:15530"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "개방화",
        expected_origins: &["開放化"],
        whole_entries: &["krdict:23477"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "객관화",
        expected_origins: &["客觀化"],
        whole_entries: &["krdict:22463"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "내면화",
        expected_origins: &["內面化"],
        whole_entries: &["krdict:39526"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "다변화",
        expected_origins: &["多邊化"],
        whole_entries: &["krdict:40535"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "다양화",
        expected_origins: &["多樣化"],
        whole_entries: &["krdict:90472"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "다원화",
        expected_origins: &["多元化"],
        whole_entries: &["krdict:40578"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민영화",
        expected_origins: &["民營化"],
        whole_entries: &["krdict:56497"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민주화",
        expected_origins: &["民主化"],
        whole_entries: &["krdict:57394"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "보편화",
        expected_origins: &["普遍化"],
        whole_entries: &["krdict:59640"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "상품화",
        expected_origins: &["商品化"],
        whole_entries: &["krdict:83324"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "생활화",
        expected_origins: &["生活化"],
        whole_entries: &["krdict:62844"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "의인화",
        expected_origins: &["擬人化"],
        whole_entries: &["krdict:71860"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이론화",
        expected_origins: &["理論化"],
        whole_entries: &["krdict:71745"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이상화",
        expected_origins: &["理想化"],
        whole_entries: &["krdict:72008"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일반화",
        expected_origins: &["一般化"],
        whole_entries: &["krdict:72724"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일상화",
        expected_origins: &["日常化"],
        whole_entries: &["krdict:72810"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "제도화",
        expected_origins: &["制度化"],
        whole_entries: &["krdict:75537"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "조직화",
        expected_origins: &["組織化"],
        whole_entries: &["krdict:75938"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "최소화",
        expected_origins: &["最小化", "最少化"],
        whole_entries: &["krdict:79470", "krdict:79471"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "토착화",
        expected_origins: &["土着化"],
        whole_entries: &["krdict:81114"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "특수화",
        expected_origins: &["特殊化"],
        whole_entries: &["krdict:83017"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "표준화",
        expected_origins: &["標準化"],
        whole_entries: &["krdict:84230"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "합리화",
        expected_origins: &["合理化"],
        whole_entries: &["krdict:85523"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "황폐화",
        expected_origins: &["荒廢化"],
        whole_entries: &["krdict:87802"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "획일화",
        expected_origins: &["劃一化"],
        whole_entries: &["krdict:89067"],
        whole_origins_complete: true,
    },
];
const NESTED: &[OriginSource] = &[
    OriginSource {
        base: "가속",
        expected_origins: &["加速"],
        whole_entries: &["krdict:14636"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "가시",
        expected_origins: &["可視"],
        whole_entries: &["krdict:14685"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "개방",
        expected_origins: &["開放"],
        whole_entries: &["krdict:23477"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "객관",
        expected_origins: &["客觀"],
        whole_entries: &["krdict:22463"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "내면",
        expected_origins: &["內面"],
        whole_entries: &["krdict:39526"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민영",
        expected_origins: &["民營"],
        whole_entries: &["krdict:56497"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "민주",
        expected_origins: &["民主"],
        whole_entries: &["krdict:57394"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "보편",
        expected_origins: &["普遍"],
        whole_entries: &["krdict:59640"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "상품",
        expected_origins: &["商品"],
        whole_entries: &["krdict:83324"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "생활",
        expected_origins: &["生活"],
        whole_entries: &["krdict:62844"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이론",
        expected_origins: &["理論"],
        whole_entries: &["krdict:71745"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "이상",
        expected_origins: &["理想"],
        whole_entries: &["krdict:72008"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일반",
        expected_origins: &["一般"],
        whole_entries: &["krdict:72724"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "일상",
        expected_origins: &["日常"],
        whole_entries: &["krdict:72810"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "제도",
        expected_origins: &["制度"],
        whole_entries: &["krdict:75537"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "조직",
        expected_origins: &["組織"],
        whole_entries: &["krdict:75938"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "최소",
        expected_origins: &["最小", "最少"],
        whole_entries: &["krdict:79470", "krdict:79471"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "토착",
        expected_origins: &["土着"],
        whole_entries: &["krdict:81114"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "특수",
        expected_origins: &["特殊"],
        whole_entries: &["krdict:83017"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "표준",
        expected_origins: &["標準"],
        whole_entries: &["krdict:84230"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "합리",
        expected_origins: &["合理"],
        whole_entries: &["krdict:85523"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "황폐",
        expected_origins: &["荒廢"],
        whole_entries: &["krdict:87802"],
        whole_origins_complete: true,
    },
];

const SI_DIRECT: &[OriginSource] = &[
    OriginSource {
        base: "동일시",
        expected_origins: &["同一視"],
        whole_entries: &["krdict:48643"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "등한시",
        expected_origins: &["等閑視"],
        whole_entries: &["krdict:52827"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "문제시",
        expected_origins: &["問題視"],
        whole_entries: &["krdict:56920"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "야만시",
        expected_origins: &["野蠻視"],
        whole_entries: &["krdict:90042"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "의문시",
        expected_origins: &["疑問視"],
        whole_entries: &["krdict:71414"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "적대시",
        expected_origins: &["敵對視"],
        whole_entries: &["krdict:74577"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "죄악시",
        expected_origins: &["罪惡視"],
        whole_entries: &["krdict:90805"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "중요시",
        expected_origins: &["重要視"],
        whole_entries: &["krdict:26158"],
        whole_origins_complete: true,
    },
];

const SI_NESTED: &[OriginSource] = &[
    OriginSource {
        base: "동일",
        expected_origins: &["同一"],
        whole_entries: &["krdict:48643"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "문제",
        expected_origins: &["問題"],
        whole_entries: &["krdict:56920"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "야만",
        expected_origins: &["野蠻"],
        whole_entries: &["krdict:90042"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "의문",
        expected_origins: &["疑問"],
        whole_entries: &["krdict:71414"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "적대",
        expected_origins: &["敵對"],
        whole_entries: &["krdict:74577"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "죄악",
        expected_origins: &["罪惡"],
        whole_entries: &["krdict:90805"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "중요",
        expected_origins: &["重要"],
        whole_entries: &["krdict:26158"],
        whole_origins_complete: true,
    },
];
