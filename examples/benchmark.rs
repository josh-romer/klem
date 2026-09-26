use klem::{Lemmatizer, Session};
use serde_json::json;
use std::{hint::black_box, sync::Arc, time::Instant};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let engine = Arc::new(Lemmatizer::new());
    let words = [
        "먹다",
        "먹었어요",
        "먹으셨겠어요",
        "들어",
        "학교에서는",
        "먹어보고있다",
    ];
    let start = Instant::now();
    black_box(engine.analyze_word("먹었어요")?);
    let first_lookup_us = start.elapsed().as_secs_f64() * 1e6;
    let iterations = 1000;
    let mut lookups = vec![];
    for word in words {
        let start = Instant::now();
        for _ in 0..iterations {
            black_box(engine.analyze_word(black_box(word))?);
        }
        let uncached_us = start.elapsed().as_secs_f64() * 1e6 / iterations as f64;
        let mut session = Session::new(engine.clone(), 1024 * 1024);
        session.analyze_word(word)?;
        let start = Instant::now();
        for _ in 0..iterations {
            black_box(session.analyze_word(black_box(word))?);
        }
        lookups.push(json!({"word":word,"uncached_us":uncached_us,"cached_us":start.elapsed().as_secs_f64()*1e6/iterations as f64}));
    }
    let sentence = "그는 학교에서는 책을 읽었어요. 친구에게 이야기를 해주고 싶었습니다.\n";
    let text = sentence.repeat(1_048_576 / sentence.len() + 1);
    let mut bulk = vec![];
    for budget in [0, 8 * 1024 * 1024] {
        let mut session = Session::new(engine.clone(), budget);
        let start = Instant::now();
        let mut records = 0;
        klem::analyze_reader(text.as_bytes(), &mut session, |record| {
            black_box(record);
            records += 1;
            Ok(())
        })?;
        let seconds = start.elapsed().as_secs_f64();
        bulk.push(json!({"cache_budget":budget,"retained_cache_bytes":session.cached_bytes(),"input_bytes":text.len(),"records":records,"seconds":seconds,"mib_per_second":text.len() as f64 / 1_048_576.0 / seconds}));
    }
    let mut supplied_text = vec![];
    if let Some(path) = std::env::args().nth(1) {
        for budget in [0, 8 * 1024 * 1024] {
            let input_bytes = std::fs::metadata(&path)?.len();
            let mut session = Session::new(engine.clone(), budget);
            let start = Instant::now();
            let mut records = 0;
            klem::analyze_reader(std::fs::File::open(&path)?, &mut session, |record| {
                black_box(record);
                records += 1;
                Ok(())
            })?;
            let seconds = start.elapsed().as_secs_f64();
            supplied_text.push(json!({"cache_budget":budget,"charged_cache_bytes":session.cached_bytes(),"input_bytes":input_bytes,"records":records,"seconds":seconds,"mib_per_second":input_bytes as f64/1_048_576.0/seconds}));
        }
    }
    let peak_rss_kib = std::fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("VmHWM:"))
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<usize>().ok())
        });
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"first_lookup_us":first_lookup_us,"iterations":iterations,"word_lookups":lookups,"synthetic_repeated_text":bulk,"supplied_text":supplied_text,"process_peak_rss_kib_linux":peak_rss_kib})
        )?
    );
    Ok(())
}
