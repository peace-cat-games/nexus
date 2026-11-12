//! `prove` mode: does side X force a win within d turns?  (n = 3, 4, 5)
//!
//! A two-valued AND/OR depth-limited search over complete histories: at X's
//! nodes one winning turn suffices, at the opponent's nodes every turn must
//! lose.  Every ko test uses the exact superko history of the real path from
//! the empty board, so without a transposition table the search is plain
//! exact minimax (sound: "false at d" means X has no strategy that wins by
//! turn d against all replies).
//!
//! History-aware transposition table (`--tt`, sound; see README):
//! the generator's output at a node depends on the history only through
//! membership tests of superko keys, and every key it tests is the board
//! right after a placement (and its captures).  For a searched subtree we
//! record theta = the fewest stones on any board whose key was tested anywhere
//! in it (including, recursively, under reused entries).  A result for
//! position P computed with history H is reused at P with history H' only if
//! H and H' contain the same keys among those with >= theta stones (compared
//! via a 128-bit order-independent hash of that sub-multiset).  Then every
//! membership test the stored search made has the same answer under H', so
//! the stored search is a valid search under H'.  Win/loss monotonicity in d
//! is used as usual (win within r ⇒ win within r' ≥ r).
//!
//! Sound horizon pruning (no history dependence):
//!  (A) X to move with 1 turn left: X wins only by completing a line now,
//!      which needs X's line distance ≤ 1.
//!  (B) opponent to move with 2 turns left and X's line distance ≥ 2: the
//!      opponent's turn cannot add X stones, so X cannot complete a line on
//!      the last turn; X wins iff every opponent turn loses at once.

use crate::game::*;
use std::collections::HashMap;
use std::hash::BuildHasherDefault;
use std::io::Write;
use std::time::{Duration, Instant};

type Map<V> = HashMap<u128, V, BuildHasherDefault<crate::MixHasher>>;

const INF: u32 = 255;

#[derive(Clone, Copy)]
struct Entry {
    r: u16,
    val: bool,
    theta: u8,
    hh: u128,
}

#[inline]
fn mix64(mut z: u64) -> u64 {
    z = z.wrapping_add(0x9E37_79B9_7F4A_7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

#[inline]
fn mix128(k: u128) -> u128 {
    let lo = k as u64;
    let hi = (k >> 64) as u64;
    let a = mix64(lo ^ mix64(hi ^ 0x1234_5678_9ABC_DEF1));
    let b = mix64(lo.rotate_left(29) ^ mix64(hi ^ 0x0F1E_2D3C_4B5A_6978) ^ 0x5555_AAAA_3333_CCCC);
    (a as u128) << 64 | b as u128
}

/// Order-independent hash of the history keys with at least `theta` stones.
fn hist_hash(hist: &[u128], theta: u32) -> u128 {
    if theta >= INF {
        return 0;
    }
    hist.iter().filter(|&&k| key_stones(k) >= theta).fold(0u128, |a, &k| a.wrapping_add(mix128(k)))
}

pub struct Prover {
    g: Geom,
    prm: Params,
    /// The side trying to win (0 = Black, 1 = White).
    x: u8,
    tt: Map<Entry>,
    /// Use stored values (sound, history-aware).  If false the table only orders moves.
    tt_values: bool,
    max_tt: usize,
    pub nodes: u64,
    pub hits: u64,
    pub illdef: u64,
    deadline: Instant,
    pub timed_out: bool,
    hheur: [[u32; 32]; 2],
}

impl Prover {
    fn order_score(&self, mover_is_x: bool, r: u16, t: &Turn, p: &Pos) -> i64 {
        // Higher = tried first.  X wants a child where X wins; the opponent
        // wants a child where X fails.
        let tt = self.tt.get(&p.tt_key());
        let xs = if self.x == 0 { p.b } else { p.w };
        let dx = self.g.line_distance(xs) as i64;
        let h = self.hheur[p.stm as usize ^ 1][t.place as usize] as i64;
        let mut s = h.min(1 << 30);
        if mover_is_x {
            s -= dx << 32;
            if let Some(e) = tt {
                if e.val {
                    s += (1 << 50) - e.r as i64;
                } else if e.r + 1 >= r {
                    s -= 1 << 50;
                }
            }
        } else {
            s += dx << 32;
            if let Some(e) = tt {
                if !e.val && e.r + 1 >= r {
                    s += 1 << 50;
                } else if e.val {
                    s -= 1 << 50;
                }
            }
        }
        s
    }

    /// Does X force a win within `r` turns from `pos` (history `hist`, which
    /// ends with pos's own key)?  Returns (value, theta).
    pub fn win(&mut self, pos: &Pos, hist: &mut Vec<u128>, r: u16) -> (bool, u32) {
        self.nodes += 1;
        if self.nodes & 0xFFFF == 0 && Instant::now() > self.deadline {
            self.timed_out = true;
        }
        if self.timed_out {
            return (false, 0);
        }
        if r == 0 {
            return (false, INF);
        }
        let xm = pos.stm == self.x;
        let xs = if self.x == 0 { pos.b } else { pos.w };
        let dx = self.g.line_distance(xs);
        if xm && r == 1 && dx >= 2 {
            return (false, INF); // (A)
        }
        let key = pos.tt_key();
        if self.tt_values {
            if let Some(e) = self.tt.get(&key) {
                let ok = if e.val { e.r <= r } else { e.r >= r };
                if ok && hist_hash(hist, e.theta as u32) == e.hh {
                    self.hits += 1;
                    return (e.val, e.theta as u32);
                }
            }
        }
        let (gres, mut theta) = gen_t(&self.g, pos, hist, self.prm, false);
        let val = match gres {
            Gen::NoMove => !xm,
            Gen::IllDefined => {
                self.illdef += 1;
                !xm
            }
            Gen::Turns(v) => {
                if v.iter().any(|(_, o)| matches!(o, Outcome::MoverWins)) {
                    xm
                } else {
                    let mut kids: Vec<(i64, Turn, Pos, u128)> = v
                        .iter()
                        .filter_map(|(t, o)| match o {
                            Outcome::Cont(p, k) => Some((0, *t, *p, *k)),
                            _ => None,
                        })
                        .collect();
                    if kids.is_empty() {
                        !xm // every turn of the mover loses at once
                    } else if r == 1 {
                        false
                    } else if !xm && r == 2 && dx >= 2 {
                        false // (B)
                    } else {
                        for k in kids.iter_mut() {
                            k.0 = self.order_score(xm, r, &k.1, &k.2);
                        }
                        kids.sort_by(|a, b| b.0.cmp(&a.0));
                        // X node: any child true.  Opponent node: all children true.
                        let mut res = !xm;
                        for (_, t, p, k) in kids {
                            hist.push(k);
                            let (cv, th) = self.win(&p, hist, r - 1);
                            hist.pop();
                            theta = theta.min(th);
                            if self.timed_out {
                                return (false, 0);
                            }
                            if cv == xm {
                                res = xm;
                                let hh = &mut self.hheur[pos.stm as usize][t.place as usize];
                                *hh = hh.saturating_add((r as u32) * (r as u32));
                                break;
                            }
                        }
                        res
                    }
                }
            }
        };
        if self.tt.len() < self.max_tt || self.tt.contains_key(&key) {
            let th = theta.min(INF);
            self.tt.insert(key, Entry { r, val, theta: th as u8, hh: hist_hash(hist, th) });
        }
        (val, theta)
    }

    /// Exact strategy extraction for X within `r` turns: full history at every
    /// node; at X nodes one turn that `win` proves, at opponent nodes every turn.
    fn extract(&mut self, pos: &Pos, hist: &mut Vec<u128>, r: u16, out: &mut Vec<(String, u32)>) -> Option<u32> {
        let g = gen(&self.g, pos, hist, self.prm, false);
        if pos.stm == self.x {
            let Gen::Turns(v) = g else { return None };
            if let Some((t, _)) = v.iter().find(|(_, o)| matches!(o, Outcome::MoverWins)) {
                out.push((self.g.turn_string(t), 0));
                return Some(1);
            }
            if r <= 1 {
                return None;
            }
            let mut kids: Vec<(i64, Turn, Pos, u128)> = v
                .iter()
                .filter_map(|(t, o)| match o {
                    Outcome::Cont(p, k) => Some((self.order_score(true, r, t, p), *t, *p, *k)),
                    _ => None,
                })
                .collect();
            kids.sort_by(|a, b| b.0.cmp(&a.0));
            for (_, t, p, k) in kids {
                hist.push(k);
                let (cv, _) = self.win(&p, hist, r - 1);
                if !cv || self.timed_out {
                    hist.pop();
                    continue;
                }
                let mark = out.len();
                out.push((self.g.turn_string(&t), 0));
                let res = self.extract(&p, hist, r - 1, out);
                hist.pop();
                if let Some(c) = res {
                    out[mark].1 = c;
                    return Some(1);
                }
                out.truncate(mark);
            }
            None
        } else {
            match g {
                Gen::NoMove => Some(0),
                Gen::IllDefined => Some(0), // the checker rejects these; never seen
                Gen::Turns(v) => {
                    if v.iter().any(|(_, o)| matches!(o, Outcome::MoverWins)) {
                        return None;
                    }
                    let start = out.len();
                    let mut n = 0;
                    for (t, o) in &v {
                        n += 1;
                        match o {
                            Outcome::MoverLoses => out.push((self.g.turn_string(t), 0)),
                            Outcome::Cont(p, k) => {
                                if r <= 1 {
                                    out.truncate(start);
                                    return None;
                                }
                                let mark = out.len();
                                out.push((self.g.turn_string(t), 0));
                                hist.push(*k);
                                let res = self.extract(p, hist, r - 1, out);
                                hist.pop();
                                match res {
                                    Some(c) => out[mark].1 = c,
                                    None => {
                                        out.truncate(start);
                                        return None;
                                    }
                                }
                            }
                            Outcome::MoverWins => unreachable!(),
                        }
                    }
                    Some(n)
                }
            }
        }
    }
}

fn arg<T: std::str::FromStr>(args: &[String], name: &str, default: T) -> T {
    match args.iter().position(|a| a == name) {
        Some(i) => args[i + 1].parse().ok().expect("bad argument"),
        None => default,
    }
}

fn peak_rss_mb() -> f64 {
    std::fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| s.lines().find(|l| l.starts_with("VmHWM:")).map(|l| l.to_string()))
        .and_then(|l| l.split_whitespace().nth(1).and_then(|v| v.parse::<f64>().ok()))
        .map(|kb| kb / 1024.0)
        .unwrap_or(0.0)
}

/// usage: prove --n N --side black|white [--min-depth D0] [--max-depth D]
///        [--time SECS] [--no-tt-values] [--max-tt ENTRIES] [--out FILE]
///        [--line "t1 t2 ..."]  (start after these turns, e.g. "-/0/-")
pub fn prove(args: &[String]) {
    let n: usize = arg(args, "--n", 3);
    let g = Geom::new(n);
    let prm = Params { p1: arg(args, "--p1", 2), p2: arg(args, "--p2", 4) };
    let side_s: String = arg(args, "--side", "black".to_string());
    let x: u8 = if side_s == "black" { 0 } else { 1 };
    let min_d: u16 = arg(args, "--min-depth", 1);
    let max_d: u16 = arg(args, "--max-depth", 99);
    let secs: u64 = arg(args, "--time", 2700);
    let max_tt: usize = arg(args, "--max-tt", 12_000_000);
    let out_path: String = arg(args, "--out", format!("strategy_{}x{}_{}.txt", n, n, side_s));
    let line: String = arg(args, "--line", String::new());
    let tt_values = !args.iter().any(|a| a == "--no-tt-values");
    let t0 = Instant::now();
    let mut p = Prover {
        g: g.clone(),
        prm,
        x,
        tt: Map::default(),
        tt_values,
        max_tt,
        nodes: 0,
        hits: 0,
        illdef: 0,
        deadline: t0 + Duration::from_secs(secs),
        timed_out: false,
        hheur: [[0; 32]; 2],
    };
    // Optional forced opening line.
    let mut root = Pos::start();
    let mut hist: Vec<u128> = Vec::new();
    let mut prefix: Vec<String> = Vec::new();
    for ts in line.split_whitespace() {
        let Gen::Turns(v) = gen(&g, &root, &hist, prm, true) else { panic!("no move in line") };
        let (t, o) = v.iter().find(|(t, _)| g.turn_string(t) == ts).expect("turn of --line not legal");
        let Outcome::Cont(np, k) = o else { panic!("line ends the game") };
        prefix.push(g.turn_string(t));
        root = *np;
        hist.push(*k);
    }
    println!(
        "# prove n={} p1={} p2={} side={} line=[{}] tt_values={} max_tt={} time_limit={}s",
        n, prm.p1, prm.p2, side_s, line, tt_values, max_tt, secs
    );
    let mut proved: Option<u16> = None;
    let mut deepest_false: Option<u16> = None;
    for d in min_d..=max_d {
        let nodes0 = p.nodes;
        let ti = Instant::now();
        let (v, th) = p.win(&root, &mut hist, d);
        if p.timed_out {
            println!(
                "depth {:2}: TIMEOUT after {} nodes, {:.1}s (depth not completed)",
                d,
                p.nodes - nodes0,
                ti.elapsed().as_secs_f64()
            );
            break;
        }
        println!(
            "depth {:2}: {}  nodes {} (total {})  tt {}  hits {}  illdef {}  theta {}  {:.1}s (total {:.1}s)  rss {:.0}MB",
            d,
            if v { "WIN" } else { "no forced win" },
            p.nodes - nodes0,
            p.nodes,
            p.tt.len(),
            p.hits,
            p.illdef,
            th,
            ti.elapsed().as_secs_f64(),
            t0.elapsed().as_secs_f64(),
            peak_rss_mb()
        );
        std::io::stdout().flush().ok();
        if v {
            proved = Some(d);
            break;
        }
        deepest_false = Some(d);
    }
    let who = if x == 0 { "Black" } else { "White" };
    match deepest_false {
        Some(d) => println!("RESULT: {} has no forced win within {} turns (exact search, depths {}..={})", who, d + prefix.len() as u16, min_d, d),
        None => println!("RESULT: no depth completed without a win"),
    }
    let Some(d) = proved else { return };
    println!("RESULT: {} forces a win within {} further turns (search); extracting", who, d);
    p.deadline = Instant::now() + Duration::from_secs(secs);
    p.timed_out = false;
    let t1 = Instant::now();
    let mut out: Vec<(String, u32)> = vec![("root".into(), 0)];
    for (i, t) in prefix.iter().enumerate() {
        out[i].1 = 1;
        out.push((t.clone(), 0));
    }
    let base = out.len();
    let Some(c) = p.extract(&root, &mut hist, d, &mut out) else {
        println!("extraction FAILED");
        std::process::exit(2);
    };
    out[base - 1].1 = c;
    let mut maxd = 0;
    let mut leaves = 0u64;
    let mut stack: Vec<u32> = Vec::new();
    for (_, c) in &out {
        maxd = maxd.max(stack.len());
        if *c == 0 {
            leaves += 1;
        }
        if let Some(top) = stack.last_mut() {
            *top -= 1;
        }
        if *c > 0 {
            stack.push(*c);
        }
        while let Some(&0) = stack.last() {
            stack.pop();
        }
    }
    let winner = if x == 0 { "BLACK" } else { "WHITE" };
    let mut f = std::io::BufWriter::new(std::fs::File::create(&out_path).unwrap());
    writeln!(
        f,
        "# nexus {}x{} strategy{} p1={} p2={} winner={} first={}",
        n,
        n,
        if n == 3 { String::new() } else { format!(" n={}", n) },
        prm.p1,
        prm.p2,
        winner,
        if prefix.is_empty() { "any".to_string() } else { prefix.join(",") }
    )
    .unwrap();
    writeln!(f, "# preorder; each line: <turn> <number of children>; turn = unblock/place/remove cells (r*{}+c), '-' = none", n).unwrap();
    for (t, c) in &out {
        writeln!(f, "{} {}", t, c).unwrap();
    }
    drop(f);
    println!(
        "extracted {} strategy: {} turns ({} leaves), max game length {} turns, {:.1}s -> {}",
        winner,
        out.len() - 1,
        leaves,
        maxd,
        t1.elapsed().as_secs_f64(),
        out_path
    );
}
