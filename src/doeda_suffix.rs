//! Source-listed and reviewed native -되다 formations (KRDict 74902; COV-022m).
//! Whole heads, source conflicts and unreviewed native leads remain separate.
use crate::{Lemma, LemmaKind, Morpheme, MorphemeKind, engine::PredicateClass};

pub(crate) const FORMS: &[(&str, &str, LemmaKind, PredicateClass)] = &[
    ("가결되다", "가결", LemmaKind::Nominal, PredicateClass::Verb),
    ("가공되다", "가공", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "가석방되다",
        "가석방",
        LemmaKind::Nominal,
        PredicateClass::Verb,
    ),
    ("가열되다", "가열", LemmaKind::Nominal, PredicateClass::Verb),
    ("감금되다", "감금", LemmaKind::Nominal, PredicateClass::Verb),
    ("감염되다", "감염", LemmaKind::Nominal, PredicateClass::Verb),
    ("개봉되다", "개봉", LemmaKind::Nominal, PredicateClass::Verb),
    ("개선되다", "개선", LemmaKind::Nominal, PredicateClass::Verb),
    ("개편되다", "개편", LemmaKind::Nominal, PredicateClass::Verb),
    ("거래되다", "거래", LemmaKind::Nominal, PredicateClass::Verb),
    ("거론되다", "거론", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "거짓되다",
        "거짓",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("건조되다", "건조", LemmaKind::Nominal, PredicateClass::Verb),
    ("결정되다", "결정", LemmaKind::Nominal, PredicateClass::Verb),
    ("결제되다", "결제", LemmaKind::Nominal, PredicateClass::Verb),
    ("계획되다", "계획", LemmaKind::Nominal, PredicateClass::Verb),
    ("고되다", "고", LemmaKind::Root, PredicateClass::Adjective),
    ("공개되다", "공개", LemmaKind::Nominal, PredicateClass::Verb),
    ("관찰되다", "관찰", LemmaKind::Nominal, PredicateClass::Verb),
    ("구조되다", "구조", LemmaKind::Nominal, PredicateClass::Verb),
    ("구출되다", "구출", LemmaKind::Nominal, PredicateClass::Verb),
    ("규정되다", "규정", LemmaKind::Nominal, PredicateClass::Verb),
    ("규제되다", "규제", LemmaKind::Nominal, PredicateClass::Verb),
    ("금지되다", "금지", LemmaKind::Nominal, PredicateClass::Verb),
    ("기대되다", "기대", LemmaKind::Nominal, PredicateClass::Verb),
    ("기록되다", "기록", LemmaKind::Nominal, PredicateClass::Verb),
    ("낙오되다", "낙오", LemmaKind::Nominal, PredicateClass::Verb),
    ("당선되다", "당선", LemmaKind::Nominal, PredicateClass::Verb),
    ("당첨되다", "당첨", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "덜되다",
        "덜",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    ("마련되다", "마련", LemmaKind::Nominal, PredicateClass::Verb),
    ("마비되다", "마비", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "막되다",
        "막",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    (
        "망령되다",
        "망령",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("매각되다", "매각", LemmaKind::Nominal, PredicateClass::Verb),
    ("면제되다", "면제", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "못되다",
        "못",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    ("밀폐되다", "밀폐", LemmaKind::Nominal, PredicateClass::Verb),
    ("반감되다", "반감", LemmaKind::Nominal, PredicateClass::Verb),
    ("반복되다", "반복", LemmaKind::Nominal, PredicateClass::Verb),
    ("발견되다", "발견", LemmaKind::Nominal, PredicateClass::Verb),
    ("발굴되다", "발굴", LemmaKind::Nominal, PredicateClass::Verb),
    ("발급되다", "발급", LemmaKind::Nominal, PredicateClass::Verb),
    ("발효되다", "발효", LemmaKind::Nominal, PredicateClass::Verb),
    ("방영되다", "방영", LemmaKind::Nominal, PredicateClass::Verb),
    ("방해되다", "방해", LemmaKind::Nominal, PredicateClass::Verb),
    ("배출되다", "배출", LemmaKind::Nominal, PredicateClass::Verb),
    ("변형되다", "변형", LemmaKind::Nominal, PredicateClass::Verb),
    ("보관되다", "보관", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "보람되다",
        "보람",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    (
        "복되다",
        "복",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("복제되다", "복제", LemmaKind::Nominal, PredicateClass::Verb),
    ("부담되다", "부담", LemmaKind::Nominal, PredicateClass::Verb),
    ("비교되다", "비교", LemmaKind::Nominal, PredicateClass::Verb),
    ("사용되다", "사용", LemmaKind::Nominal, PredicateClass::Verb),
    ("생각되다", "생각", LemmaKind::Nominal, PredicateClass::Verb),
    ("생산되다", "생산", LemmaKind::Nominal, PredicateClass::Verb),
    ("선출되다", "선출", LemmaKind::Nominal, PredicateClass::Verb),
    ("설립되다", "설립", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "세련되다",
        "세련",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("세습되다", "세습", LemmaKind::Nominal, PredicateClass::Verb),
    ("소각되다", "소각", LemmaKind::Nominal, PredicateClass::Verb),
    ("소개되다", "소개", LemmaKind::Nominal, PredicateClass::Verb),
    ("소유되다", "소유", LemmaKind::Nominal, PredicateClass::Verb),
    ("소장되다", "소장", LemmaKind::Nominal, PredicateClass::Verb),
    ("속되다", "속", LemmaKind::Root, PredicateClass::Adjective),
    ("습득되다", "습득", LemmaKind::Nominal, PredicateClass::Verb),
    ("시작되다", "시작", LemmaKind::Nominal, PredicateClass::Verb),
    ("실시되다", "실시", LemmaKind::Nominal, PredicateClass::Verb),
    ("악화되다", "악화", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "안되다",
        "안",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    ("애용되다", "애용", LemmaKind::Nominal, PredicateClass::Verb),
    ("앳되다", "앳", LemmaKind::Root, PredicateClass::Adjective),
    ("연결되다", "연결", LemmaKind::Nominal, PredicateClass::Verb),
    ("연상되다", "연상", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "영광되다",
        "영광",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    (
        "오래되다",
        "오래",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    (
        "외람되다",
        "외람",
        LemmaKind::Root,
        PredicateClass::Adjective,
    ),
    (
        "욕되다",
        "욕",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("운행되다", "운행", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "유감되다",
        "유감",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("유배되다", "유배", LemmaKind::Nominal, PredicateClass::Verb),
    ("의심되다", "의심", LemmaKind::Nominal, PredicateClass::Verb),
    ("이룩되다", "이룩", LemmaKind::Nominal, PredicateClass::Verb),
    ("이송되다", "이송", LemmaKind::Nominal, PredicateClass::Verb),
    ("이식되다", "이식", LemmaKind::Nominal, PredicateClass::Verb),
    ("이용되다", "이용", LemmaKind::Nominal, PredicateClass::Verb),
    ("인수되다", "인수", LemmaKind::Nominal, PredicateClass::Verb),
    ("임명되다", "임명", LemmaKind::Nominal, PredicateClass::Verb),
    ("입양되다", "입양", LemmaKind::Nominal, PredicateClass::Verb),
    ("잘못되다", "잘못", LemmaKind::Nominal, PredicateClass::Verb),
    ("장착되다", "장착", LemmaKind::Nominal, PredicateClass::Verb),
    ("재건되다", "재건", LemmaKind::Nominal, PredicateClass::Verb),
    ("저장되다", "저장", LemmaKind::Nominal, PredicateClass::Verb),
    ("적용되다", "적용", LemmaKind::Nominal, PredicateClass::Verb),
    ("전개되다", "전개", LemmaKind::Nominal, PredicateClass::Verb),
    ("전달되다", "전달", LemmaKind::Nominal, PredicateClass::Verb),
    ("전멸되다", "전멸", LemmaKind::Nominal, PredicateClass::Verb),
    ("전수되다", "전수", LemmaKind::Nominal, PredicateClass::Verb),
    ("전승되다", "전승", LemmaKind::Nominal, PredicateClass::Verb),
    ("전시되다", "전시", LemmaKind::Nominal, PredicateClass::Verb),
    ("전염되다", "전염", LemmaKind::Nominal, PredicateClass::Verb),
    ("전파되다", "전파", LemmaKind::Nominal, PredicateClass::Verb),
    ("정리되다", "정리", LemmaKind::Nominal, PredicateClass::Verb),
    ("제외되다", "제외", LemmaKind::Nominal, PredicateClass::Verb),
    ("조정되다", "조정", LemmaKind::Nominal, PredicateClass::Verb),
    ("종료되다", "종료", LemmaKind::Nominal, PredicateClass::Verb),
    ("준비되다", "준비", LemmaKind::Nominal, PredicateClass::Verb),
    ("중계되다", "중계", LemmaKind::Nominal, PredicateClass::Verb),
    ("중시되다", "중시", LemmaKind::Nominal, PredicateClass::Verb),
    ("지배되다", "지배", LemmaKind::Nominal, PredicateClass::Verb),
    ("지불되다", "지불", LemmaKind::Nominal, PredicateClass::Verb),
    ("진압되다", "진압", LemmaKind::Nominal, PredicateClass::Verb),
    ("진열되다", "진열", LemmaKind::Nominal, PredicateClass::Verb),
    ("진전되다", "진전", LemmaKind::Nominal, PredicateClass::Verb),
    ("진행되다", "진행", LemmaKind::Nominal, PredicateClass::Verb),
    ("진화되다", "진화", LemmaKind::Nominal, PredicateClass::Verb),
    ("징용되다", "징용", LemmaKind::Nominal, PredicateClass::Verb),
    ("차단되다", "차단", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "참되다",
        "참",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("채택되다", "채택", LemmaKind::Nominal, PredicateClass::Verb),
    ("첨가되다", "첨가", LemmaKind::Nominal, PredicateClass::Verb),
    ("출제되다", "출제", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "충만되다",
        "충만",
        LemmaKind::Nominal,
        PredicateClass::Adjective,
    ),
    ("취소되다", "취소", LemmaKind::Nominal, PredicateClass::Verb),
    ("취직되다", "취직", LemmaKind::Nominal, PredicateClass::Verb),
    ("타도되다", "타도", LemmaKind::Nominal, PredicateClass::Verb),
    ("투입되다", "투입", LemmaKind::Nominal, PredicateClass::Verb),
    ("파견되다", "파견", LemmaKind::Nominal, PredicateClass::Verb),
    ("파손되다", "파손", LemmaKind::Nominal, PredicateClass::Verb),
    ("파악되다", "파악", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "편벽되다",
        "편벽",
        LemmaKind::Root,
        PredicateClass::Adjective,
    ),
    ("평가되다", "평가", LemmaKind::Nominal, PredicateClass::Verb),
    ("폐기되다", "폐기", LemmaKind::Nominal, PredicateClass::Verb),
    ("폐지되다", "폐지", LemmaKind::Nominal, PredicateClass::Verb),
    ("포함되다", "포함", LemmaKind::Nominal, PredicateClass::Verb),
    ("폭로되다", "폭로", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "한갓되다",
        "한갓",
        LemmaKind::Adverbial,
        PredicateClass::Adjective,
    ),
    ("함락되다", "함락", LemmaKind::Nominal, PredicateClass::Verb),
    ("함몰되다", "함몰", LemmaKind::Nominal, PredicateClass::Verb),
    ("함유되다", "함유", LemmaKind::Nominal, PredicateClass::Verb),
    ("해방되다", "해방", LemmaKind::Nominal, PredicateClass::Verb),
    ("해산되다", "해산", LemmaKind::Nominal, PredicateClass::Verb),
    ("해임되다", "해임", LemmaKind::Nominal, PredicateClass::Verb),
    ("해제되다", "해제", LemmaKind::Nominal, PredicateClass::Verb),
    ("해직되다", "해직", LemmaKind::Nominal, PredicateClass::Verb),
    ("허가되다", "허가", LemmaKind::Nominal, PredicateClass::Verb),
    ("허락되다", "허락", LemmaKind::Nominal, PredicateClass::Verb),
    (
        "허황되다",
        "허황",
        LemmaKind::Root,
        PredicateClass::Adjective,
    ),
    ("헛되다", "헛", LemmaKind::Root, PredicateClass::Adjective),
    ("형성되다", "형성", LemmaKind::Nominal, PredicateClass::Verb),
    ("호되다", "호", LemmaKind::Root, PredicateClass::Adjective),
    ("혼동되다", "혼동", LemmaKind::Nominal, PredicateClass::Verb),
    ("확대되다", "확대", LemmaKind::Nominal, PredicateClass::Verb),
    ("확립되다", "확립", LemmaKind::Nominal, PredicateClass::Verb),
    ("확보되다", "확보", LemmaKind::Nominal, PredicateClass::Verb),
    ("확산되다", "확산", LemmaKind::Nominal, PredicateClass::Verb),
    ("휴전되다", "휴전", LemmaKind::Nominal, PredicateClass::Verb),
];

pub(crate) fn formation(head: &str) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    if !head.ends_with("되다") {
        return None;
    }
    if let Ok(i) = FORMS.binary_search_by_key(&head, |&(word, _, _, _)| word) {
        let (_, base, kind, class) = FORMS[i];
        return Some((base, kind, class));
    }
    // Missing recorded origins do not exclude a finite formation supported by
    // separately reviewed native noun/verb definitions. Available tagged
    // contexts are tracked separately; missing origins stay unknown.
    if let Some(source) = crate::doeda_originless_forms::source(head.strip_suffix("되다")?) {
        return Some((source.base, LemmaKind::Nominal, PredicateClass::Verb));
    }
    // These extra native heads have individually reviewed whole/noun origin
    // pairs and verb POS; they add no rule for arbitrary nominal spellings.
    let i = crate::doeda_native_forms::FORMS
        .binary_search_by_key(&head, |&(word, _)| word)
        .ok()?;
    Some((
        crate::doeda_native_forms::FORMS[i].1,
        LemmaKind::Nominal,
        PredicateClass::Verb,
    ))
}

pub(crate) fn rule(class: PredicateClass) -> &'static str {
    match class {
        PredicateClass::Verb => "suffix.verb.doeda",
        PredicateClass::Adjective => "suffix.adjective.doeda",
        PredicateClass::Copula => unreachable!("suffix is never copular"),
    }
}

// Resolve this owner, not a global class flag from another suffix.
pub(crate) fn owner_class(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<PredicateClass> {
    if !morphs
        .first()
        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "되다")
    {
        return None;
    }
    let (base, kind, class) = formation(&format!("{}되다", lemma.text))?;
    (lemma.text == base && lemma.kind == kind && rules.iter().any(|r| r == rule(class)))
        .then_some(class)
}
