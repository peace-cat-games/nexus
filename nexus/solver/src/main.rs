//! 3x3 Nexus solver.  See README.md for the rules interpretation and the
//! soundness argument.
//!
//! Modes:
//!   nexus-solver movegen            read positions on stdin, print every turn + outcome
//!   nexus-solver solve [options]    iterative-deepening search + exact strategy extraction
mod game;

use game::*;
use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::io::{BufRead, Write};
use std::time::Instant;

#[derive(Default)]
struct MixHasher(u64);
impl Hasher for MixHasher {
    fn write(&mut self, _: &[u8]) {
        unimplemented!()
    }
    fn write_u64(&mut self, x: u64) {
        let mut z = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        self.0 = z ^ (z >> 31);
    }
    fn finish(&self) -> u64 {
        self.0
    }
}
type Map<V> = HashMap<u64, V, BuildHasherDefault<MixHasher>>;

/// Value from the point of view of the side to move.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum V {
    /// Mover wins; the game ends within this many further turns.
    Win(u16),
    /// Mover loses within this many further turns (0 = cannot move at all).
    Loss(u16),
    /// Not resolved within the given remaining depth.
    Unk(u16),
}

struct Solver {
    prm: Params,
    tt: Map<V>,
    nodes: u64,
    illdef: u64,
    deadline: Instant,
    timed_out: bool,
    max_tt: usize,
    /// false = no transposition table at all: plain exact depth-limited minimax.
    use_tt: bool,
    // extraction
    ex_nodes: u64,
    ex_budget: u64,
    ex_illdef: u64,
    ex_maxdepth: u32,
}

const PRIO_UNK: u32 = 10_000;
const PRIO_WIN: u32 = 20_000;

impl Solver {
    fn prio(&self, p: &Pos) -> u32 {
        match self.tt.get(&p.tt_key()) {
            Some(V::Loss(d)) => *d as u32,
            Some(V::Win(d)) => PRIO_WIN + *d as u32,
            _ => PRIO_UNK,
        }
    }

    /// Depth-limited negamax.  `hist` is the exact superko history of the path,
    /// so every ko test made here is exact; the transposition table, keyed on
    /// the position without history, is the only heuristic part (see README).
    fn search(&mut self, pos: &Pos, hist: &mut Vec<u64>, depth: u16) -> V {
        self.nodes += 1;
        if self.nodes & 0xFFFF == 0 && Instant::now() > self.deadline {
            self.timed_out = true;
        }
        if self.timed_out {
            return V::Unk(0);
        }
        let key = pos.tt_key();
        if self.use_tt {
            match self.tt.get(&key) {
                Some(V::Unk(d)) if *d >= depth => return V::Unk(*d),
                Some(v @ (V::Win(_) | V::Loss(_))) => return *v,
                _ => {}
            }
        }
        if depth == 0 {
            return V::Unk(0);
        }
        let res = match gen(pos, hist, self.prm, false) {
            Gen::NoMove => V::Loss(0),
            Gen::IllDefined => {
                self.illdef += 1;
                V::Loss(0)
            }
            Gen::Turns(v) => {
                if v.iter().any(|(_, o)| matches!(o, Outcome::MoverWins)) {
                    V::Win(1)
                } else {
                    let mut worst = 0u16;
                    let mut kids: Vec<(u32, Pos, u64)> = Vec::with_capacity(v.len());
                    for (_, o) in &v {
                        match o {
                            Outcome::MoverLoses => worst = worst.max(1),
                            Outcome::Cont(p, k) => kids.push((self.prio(p), *p, *k)),
                            Outcome::MoverWins => unreachable!(),
                        }
                    }
                    kids.sort_by_key(|k| k.0);
                    let mut unk = false;
                    let mut win = None;
                    for (_, p, k) in kids {
                        hist.push(k);
                        let r = self.search(&p, hist, depth - 1);
                        hist.pop();
                        match r {
                            V::Loss(d) => {
                                win = Some(d + 1);
                                break;
                            }
                            V::Win(d) => worst = worst.max(d + 1),
                            V::Unk(_) => unk = true,
                        }
                    }
                    if self.timed_out {
                        return V::Unk(0);
                    }
                    match win {
                        Some(d) => V::Win(d),
                        None if unk => V::Unk(depth),
                        None => V::Loss(worst),
                    }
                }
            }
        };
        if self.use_tt && (self.tt.len() < self.max_tt || self.tt.contains_key(&key)) {
            self.tt.insert(key, res);
        }
        res
    }

    /// Exact strategy extraction for `prover` (0 = Black, 1 = White): full
    /// history, no transposition cut-offs (the table only orders the prover's
    /// candidate moves).  Appends the subtree below `pos` to `out` in preorder
    /// as (turn, #children) and returns the number of children of `pos`.
    fn extract(&mut self, pos: &Pos, hist: &mut Vec<u64>, depth_left: u32, prover: u8, out: &mut Vec<(String, u32)>) -> Option<u32> {
        self.ex_nodes += 1;
        if self.ex_nodes > self.ex_budget {
            return None;
        }
        self.ex_maxdepth = self.ex_maxdepth.max(hist.len() as u32);
        let g = gen(pos, hist, self.prm, false);
        if pos.stm == prover {
            let Gen::Turns(v) = g else { return None };
            if let Some((t, _)) = v.iter().find(|(_, o)| matches!(o, Outcome::MoverWins)) {
                out.push((turn_string(t), 0));
                return Some(1);
            }
            if depth_left <= 1 {
                return None;
            }
            let mut kids: Vec<(u32, Turn, Pos, u64)> = v
                .iter()
                .filter_map(|(t, o)| match o {
                    Outcome::Cont(p, k) => Some((self.prio(p), *t, *p, *k)),
                    _ => None,
                })
                .collect();
            kids.sort_by_key(|k| k.0);
            for (_, t, p, k) in kids {
                if !self.use_tt {
                    // Exact mode: only follow a child that exact (no-TT) search
                    // proves lost for the opponent within the remaining depth.
                    hist.push(k);
                    let r = self.search(&p, hist, (depth_left - 1) as u16);
                    hist.pop();
                    if !matches!(r, V::Loss(_)) {
                        continue;
                    }
                }
                let mark = out.len();
                out.push((turn_string(&t), 0));
                hist.push(k);
                let r = self.extract(&p, hist, depth_left - 1, prover, out);
                hist.pop();
                if let Some(n) = r {
                    out[mark].1 = n;
                    return Some(1);
                }
                out.truncate(mark);
                if self.ex_nodes > self.ex_budget {
                    return None;
                }
            }
            None
        } else {
            match g {
                Gen::NoMove => Some(0),
                Gen::IllDefined => {
                    self.ex_illdef += 1;
                    Some(0)
                }
                Gen::Turns(v) => {
                    if v.iter().any(|(_, o)| matches!(o, Outcome::MoverWins)) {
                        return None;
                    }
                    let start = out.len();
                    let mut n = 0;
                    for (t, o) in &v {
                        n += 1;
                        match o {
                            Outcome::MoverLoses => out.push((turn_string(t), 0)),
                            Outcome::Cont(p, k) => {
                                if depth_left <= 1 {
                                    out.truncate(start);
                                    return None;
                                }
                                let mark = out.len();
                                out.push((turn_string(t), 0));
                                hist.push(*k);
                                let r = self.extract(p, hist, depth_left - 1, prover, out);
                                hist.pop();
                                match r {
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

fn movegen() {
    let stdin = std::io::stdin();
    let mut so = std::io::BufWriter::new(std::io::stdout());
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let f: Vec<&str> = line.split_whitespace().collect();
        if f.is_empty() {
            continue;
        }
        let prm = Params { p1: f[0].parse().unwrap(), p2: f[1].parse().unwrap() };
        let stm: u8 = f[2].parse().unwrap();
        let (b, w) = parse_board(f[3]);
        let pos = Pos { b, w, db: f[4].parse().unwrap(), dw: f[5].parse().unwrap(), stm };
        let hist: Vec<u64> = f[6..]
            .iter()
            .map(|e| {
                let (bs, d) = e.split_once(':').unwrap();
                let (hb, hw) = parse_board(bs);
                ko_key(hb, hw, d.parse().unwrap())
            })
            .collect();
        let s = match gen(&pos, &hist, prm, true) {
            Gen::NoMove => "NOMOVE".to_string(),
            Gen::IllDefined => "ILLDEF".to_string(),
            Gen::Turns(v) => {
                let mut items: Vec<String> = v
                    .iter()
                    .map(|(t, o)| {
                        let os = match o {
                            Outcome::MoverWins => "MW".to_string(),
                            Outcome::MoverLoses => "ML".to_string(),
                            Outcome::Cont(p, _) => format!("C:{}:{}:{}", p.board_string(), p.db, p.dw),
                        };
                        format!("{}={}", turn_string(t), os)
                    })
                    .collect();
                items.sort();
                items.join(" ")
            }
        };
        writeln!(so, "{}", s).unwrap();
    }
}

fn arg<T: std::str::FromStr>(args: &[String], name: &str, default: T) -> T {
    match args.iter().position(|a| a == name) {
        Some(i) => args[i + 1].parse().ok().expect("bad argument"),
        None => default,
    }
}

fn solve(args: &[String]) {
    let prm = Params { p1: arg(args, "--p1", 2), p2: arg(args, "--p2", 4) };
    let max_depth: u16 = arg(args, "--max-depth", 60);
    let secs: u64 = arg(args, "--time", 3600);
    let max_tt: usize = arg(args, "--max-tt", 40_000_000);
    let ex_budget: u64 = arg(args, "--extract-budget", 200_000_000);
    let out_path: String = arg(args, "--out", "strategy.txt".to_string());
    let first: i32 = arg(args, "--first", -1);
    let use_tt = !args.iter().any(|a| a == "--no-tt");
    let t0 = Instant::now();
    let mut s = Solver {
        prm,
        tt: Map::default(),
        nodes: 0,
        illdef: 0,
        deadline: t0 + std::time::Duration::from_secs(secs),
        timed_out: false,
        max_tt,
        use_tt,
        ex_nodes: 0,
        ex_budget,
        ex_illdef: 0,
        ex_maxdepth: 0,
    };
    let mut root = Pos::start();
    let mut hist = Vec::new();
    // Optional forced first move for Black (analysis of each opening move).
    let mut prefix: Option<String> = None;
    if first >= 0 {
        let Gen::Turns(v) = gen(&root, &hist, prm, false) else { unreachable!() };
        let (t, o) = v.iter().find(|(t, _)| t.place as i32 == first).expect("illegal first move");
        let Outcome::Cont(p, k) = o else { unreachable!() };
        prefix = Some(turn_string(t));
        root = *p;
        hist.push(*k);
    }
    let mut val = V::Unk(0);
    for d in 1..=max_depth {
        val = s.search(&root, &mut hist, d);
        eprintln!(
            "depth {:2}: {:?}  nodes {}  tt {}  illdef {}  {:.1}s",
            d,
            val,
            s.nodes,
            s.tt.len(),
            s.illdef,
            t0.elapsed().as_secs_f64()
        );
        if !matches!(val, V::Unk(_)) || s.timed_out {
            break;
        }
    }
    println!(
        "p1={} p2={} first={} tt={} root value (side to move = {}): {:?}",
        prm.p1,
        prm.p2,
        first,
        use_tt,
        if root.stm == 0 { "Black" } else { "White" },
        val
    );
    println!("search nodes {} tt entries {} time {:.2}s", s.nodes, s.tt.len(), t0.elapsed().as_secs_f64());
    let prover = match val {
        V::Win(_) => root.stm,
        V::Loss(_) => root.stm ^ 1,
        V::Unk(_) => return,
    };
    let depth = match val {
        V::Win(d) | V::Loss(d) => d as u32,
        _ => 0,
    };
    let t1 = Instant::now();
    let mut out: Vec<(String, u32)> = vec![("root".into(), 0)];
    if let Some(t) = &prefix {
        out[0].1 = 1;
        out.push((t.clone(), 0));
    }
    let base = out.len();
    let mut found = None;
    for slack in [0u32, 2, 4, 8] {
        s.ex_nodes = 0;
        out.truncate(base);
        if let Some(n) = s.extract(&root, &mut hist, depth + slack, prover, &mut out) {
            found = Some(n);
            break;
        }
    }
    let Some(n) = found else {
        println!("exact extraction FAILED (ex_nodes {})", s.ex_nodes);
        std::process::exit(2);
    };
    out[base - 1].1 = n;
    // Tree statistics: max depth (turns) via the preorder child counts.
    let mut maxd = 0;
    let mut leaves = 0u64;
    let mut stack: Vec<u32> = Vec::new();
    for (_, c) in &out {
        maxd = maxd.max(stack.len());
        if *c == 0 {
            leaves += 1;
        }
        // pop finished ancestors
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
    let winner = if prover == 0 { "BLACK" } else { "WHITE" };
    let mut f = std::io::BufWriter::new(std::fs::File::create(&out_path).unwrap());
    writeln!(
        f,
        "# nexus 3x3 strategy p1={} p2={} winner={} first={}",
        prm.p1,
        prm.p2,
        winner,
        prefix.as_deref().unwrap_or("any")
    )
    .unwrap();
    writeln!(f, "# preorder; each line: <turn> <number of children>; turn = unblock/place/remove cells (r*3+c), '-' = none").unwrap();
    for (t, c) in &out {
        writeln!(f, "{} {}", t, c).unwrap();
    }
    drop(f);
    println!(
        "extracted {} strategy for {}: {} nodes ({} leaves), max game length {} turns, extraction nodes {}, illdef-in-tree {}, {:.2}s -> {}",
        winner,
        winner,
        out.len() - 1,
        leaves,
        maxd,
        s.ex_nodes,
        s.ex_illdef,
        t1.elapsed().as_secs_f64(),
        out_path
    );
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("movegen") => movegen(),
        Some("solve") => solve(&args[2..]),
        _ => eprintln!("usage: nexus-solver movegen | solve [--p1 N --p2 N --max-depth D --time S --out FILE]"),
    }
}
