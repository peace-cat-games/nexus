//! Complexity measurements for Nexus, Go and Enhanced Go on n×n boards (n ≤ 5).
//!
//!   complexity legal N [SAMPLES]      board counts: Go-legal boards, those with no
//!                                     monochrome full line; exact for N ≤ 4 (plus
//!                                     Go reachability by BFS), Monte Carlo for N = 5
//!   complexity cycle N                search for a Nexus debt-pumping cycle
//!   complexity playout GAME N GAMES SEED [Q]
//!                                     random playouts, GAME = go | ego | nexus;
//!                                     Q = probability of a random special turn (ego)
//!   complexity egodump N COUNT SEED   sample Enhanced Go positions (for the TS cross-check)
//!   complexity egocount               count legal Enhanced Go turns of positions on stdin
//!
//! Go rules here: positional superko on the board alone (the start position
//! counts), suicide illegal, passes always legal, two passes end the game.
//! Enhanced Go adds the special turn (rules in README / complexity.tex).
#[path = "../game.rs"]
#[allow(dead_code)]
mod game;

use game::*;
use std::collections::{HashMap, HashSet};
use std::io::{BufRead, Write};

// ---------------------------------------------------------------- utilities

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn below(&mut self, n: usize) -> usize {
        ((self.next() >> 11) as u128 * n as u128 >> 53) as usize
    }
    fn unit(&mut self) -> f64 {
        (self.next() >> 11) as f64 / (1u64 << 53) as f64
    }
}

/// Stones of `s` connected to an empty point of `e`.
fn alive(g: &Geom, s: u32, e: u32) -> u32 {
    let mut a = g.expand(e) & s;
    loop {
        let na = (a | g.expand(a)) & s;
        if na == a {
            return a;
        }
        a = na;
    }
}

fn go_legal(g: &Geom, b: u32, w: u32) -> bool {
    let e = g.full & !(b | w);
    alive(g, b, e) == b && alive(g, w, e) == w
}

fn bits(m: u32) -> Vec<usize> {
    (0..32).filter(|i| m >> i & 1 == 1).collect()
}

/// Call f on every k-subset of the cells in `m` (as a mask).
fn for_each_comb(m: u32, k: usize, f: &mut impl FnMut(u32)) {
    let v = bits(m);
    fn rec(v: &[usize], k: usize, start: usize, acc: u32, f: &mut impl FnMut(u32)) {
        if k == 0 {
            f(acc);
            return;
        }
        for i in start..=v.len().saturating_sub(k) {
            if v.len() < k {
                return;
            }
            rec(v, k - 1, i + 1, acc | 1 << v[i], f);
        }
    }
    if v.len() >= k {
        rec(&v, k, 0, 0, f);
    }
}

fn bkey(b: u32, w: u32) -> u64 {
    b as u64 | (w as u64) << 32
}

fn board_str(g: &Geom, b: u32, w: u32) -> String {
    (0..g.nn).map(|i| if b >> i & 1 == 1 { 'b' } else if w >> i & 1 == 1 { 'w' } else { '.' }).collect()
}

fn parse_bw(s: &str) -> (u32, u32) {
    let (mut b, mut w) = (0, 0);
    for (i, c) in s.chars().enumerate() {
        match c {
            'b' => b |= 1 << i,
            'w' => w |= 1 << i,
            _ => {}
        }
    }
    (b, w)
}

// ---------------------------------------------------------------- legal positions

fn trit_index(g: &Geom, b: u32, w: u32) -> usize {
    let mut idx = 0usize;
    for i in (0..g.nn).rev() {
        idx = idx * 3 + if b >> i & 1 == 1 { 1 } else if w >> i & 1 == 1 { 2 } else { 0 };
    }
    idx
}

fn legal_cmd(n: usize, samples: u64) {
    let g = Geom::new(n);
    if n <= 4 {
        let (mut legal, mut noline, mut total) = (0u64, 0u64, 0u64);
        let mut b: u32 = 0;
        loop {
            let comp = g.full & !b;
            let mut w = comp;
            loop {
                total += 1;
                if go_legal(&g, b, w) {
                    legal += 1;
                    if !g.has_line(b) && !g.has_line(w) {
                        noline += 1;
                    }
                }
                if w == 0 {
                    break;
                }
                w = (w - 1) & comp;
            }
            if b == g.full {
                break;
            }
            b += 1;
        }
        println!("n={} exact: boards 3^{} = {}  Go-legal {}  Go-legal with no monochrome full line {}", n, g.nn, total, legal, noline);
        // Go reachability: BFS over boards, either colour may move (passes switch the mover).
        let size = 3usize.pow(g.nn as u32);
        let mut seen = vec![0u64; size / 64 + 1];
        let mut q: Vec<(u32, u32)> = vec![(0, 0)];
        seen[0] |= 1;
        let mut head = 0;
        while head < q.len() {
            let (b, w) = q[head];
            head += 1;
            for col in 0..2 {
                let (m, o) = if col == 0 { (b, w) } else { (w, b) };
                for c in 0..g.nn {
                    if let Some((m2, o2, _)) = g.place(m, o, c) {
                        let (nb, nw) = if col == 0 { (m2, o2) } else { (o2, m2) };
                        let i = trit_index(&g, nb, nw);
                        if seen[i / 64] >> (i % 64) & 1 == 0 {
                            seen[i / 64] |= 1 << (i % 64);
                            q.push((nb, nw));
                        }
                    }
                }
            }
        }
        println!("n={} Go boards reachable from the empty board (BFS; passes allowed, so either colour may move): {}", n, q.len());
    } else {
        // Monte Carlo: uniform random boards.
        let threads = 8u64;
        let per = samples / threads;
        let res: Vec<(u64, u64)> = std::thread::scope(|s| {
            let hs: Vec<_> = (0..threads)
                .map(|t| {
                    let g = g.clone();
                    s.spawn(move || {
                        let mut r = Rng(0xC0FFEE ^ t.wrapping_mul(0x1234567));
                        let (mut l, mut nl) = (0u64, 0u64);
                        for _ in 0..per {
                            let (mut b, mut w) = (0u32, 0u32);
                            let mut x = r.next();
                            let mut left = 0;
                            for i in 0..g.nn {
                                // one trit from 2 bits, rejection sampling
                                loop {
                                    if left == 0 {
                                        x = r.next();
                                        left = 32;
                                    }
                                    let v = x & 3;
                                    x >>= 2;
                                    left -= 1;
                                    if v < 3 {
                                        if v == 1 {
                                            b |= 1 << i;
                                        } else if v == 2 {
                                            w |= 1 << i;
                                        }
                                        break;
                                    }
                                }
                            }
                            if go_legal(&g, b, w) {
                                l += 1;
                                if !g.has_line(b) && !g.has_line(w) {
                                    nl += 1;
                                }
                            }
                        }
                        (l, nl)
                    })
                })
                .collect();
            hs.into_iter().map(|h| h.join().unwrap()).collect()
        });
        let ns = per * threads;
        let l: u64 = res.iter().map(|r| r.0).sum();
        let nl: u64 = res.iter().map(|r| r.1).sum();
        let tot = 3f64.powi(g.nn as i32);
        for (name, k) in [("Go-legal", l), ("Go-legal, no monochrome full line", nl)] {
            let p = k as f64 / ns as f64;
            let se = (p * (1.0 - p) / ns as f64).sqrt();
            println!(
                "n={} Monte Carlo ({} uniform boards): {} fraction {:.6} ± {:.6} (1 s.e.) => count {:.5e} ± {:.2e}",
                n, ns, name, p, se, p * tot, se * tot
            );
        }
    }
}

// ---------------------------------------------------------------- Nexus debt-pumping cycle

/// Search the graph of non-terminal Nexus boards (with side to move) reachable
/// from the empty board by placements that complete no line, with edge weight
/// = change of (debt_black - debt_white).  A closed walk of non-zero weight
/// lets the debt difference grow without bound; superko (on board + difference)
/// never forbids repeating it.  Prints the path from the empty board and one lap.
fn cycle_cmd(n: usize) {
    let g = Geom::new(n);
    let prm = Params { p1: 2, p2: 4 };
    type Node = (u32, u32, u8);
    let mut id: HashMap<Node, usize> = HashMap::new();
    let mut nodes: Vec<Node> = vec![(0, 0, 0)];
    id.insert((0, 0, 0), 0);
    let mut adj: Vec<Vec<(usize, i32, u16)>> = vec![];
    let mut parent: Vec<(usize, u16)> = vec![(usize::MAX, 0)];
    let mut unb: Vec<(u32, u16)> = vec![];
    let mut head = 0;
    while head < nodes.len() {
        let (b, w, stm) = nodes[head];
        let (m, o) = if stm == 0 { (b, w) } else { (w, b) };
        let mut out = vec![];
        // Placements; if none is Go-legal, forced unblocking with each minimum
        // set S of opponent stones (Go legality only; superko is checked when
        // the cycle is replayed through game.py).  Edge label: placed cell, or
        // 100 + index of the unblocking edge (decoded when printing).
        let mut sets: Vec<u32> = vec![0];
        if (0..g.nn).all(|c| g.place(m, o, c).is_none()) {
            sets.clear();
            for k in 1..=o.count_ones() {
                for_each_comb(o, k as usize, &mut |s| {
                    if (0..g.nn).any(|c| g.place(m, o & !s, c).is_some()) {
                        sets.push(s);
                    }
                });
                if !sets.is_empty() {
                    break;
                }
            }
        }
        for &sset in &sets {
            let o0 = o & !sset;
            for c in 0..g.nn {
                if let Some((m2, o2, k)) = g.place(m, o0, c) {
                    if g.has_line(m2) {
                        continue;
                    }
                    let (nb, nw) = if stm == 0 { (m2, o2) } else { (o2, m2) };
                    let d = k * prm.p1 + sset.count_ones() as i32 * prm.p2;
                    let wgt = if stm == 0 { d } else { -d };
                    let key = (nb, nw, stm ^ 1);
                    let lbl = if sset == 0 { c as u16 } else { (100 + unb.len()) as u16 };
                    if sset != 0 {
                        unb.push((sset, c as u16));
                    }
                    let j = *id.entry(key).or_insert_with(|| {
                        nodes.push(key);
                        parent.push((head, lbl));
                        nodes.len() - 1
                    });
                    out.push((j, wgt, lbl));
                }
            }
        }
        adj.push(out);
        head += 1;
    }
    let nv = nodes.len();
    // Potentials along the BFS tree; an edge u->v with pot[v] != pot[u] + w
    // inside a strongly connected component witnesses a non-zero cycle.
    let mut pot = vec![0i64; nv];
    for v in 1..nv {
        let (p, c) = parent[v];
        let wgt = adj[p].iter().find(|e| e.0 == v && e.2 == c).unwrap().1;
        pot[v] = pot[p] + wgt as i64;
    }
    // reverse adjacency for "can v reach u"
    let mut radj: Vec<Vec<(usize, i32, u16)>> = vec![vec![]; nv];
    for u in 0..nv {
        for &(v, wgt, c) in &adj[u] {
            radj[v].push((u, wgt, c));
        }
    }
    println!("n={} non-terminal (board, side) nodes reachable by line-free placements: {}", n, nv);
    // Try edges with a capture; find a path back v -> u by BFS.
    for u in 0..nv {
        for &(v, wgt, c) in &adj[u] {
            if wgt == 0 || pot[v] == pot[u] + wgt as i64 {
                continue;
            }
            // BFS from v to u
            let mut prev: HashMap<usize, (usize, u16, i32)> = HashMap::new();
            let mut q = std::collections::VecDeque::new();
            q.push_back(v);
            prev.insert(v, (usize::MAX, 0, 0));
            while let Some(x) = q.pop_front() {
                if x == u {
                    break;
                }
                for &(y, wy, cy) in &adj[x] {
                    if !prev.contains_key(&y) {
                        prev.insert(y, (x, cy, wy));
                        q.push_back(y);
                    }
                }
            }
            if !prev.contains_key(&u) {
                continue;
            }
            // lap: u -c-> v ... -> u
            let mut back = vec![];
            let mut x = u;
            let mut wsum = wgt as i64;
            while x != v {
                let (p, cp, wp) = prev[&x];
                back.push(cp);
                wsum += wp as i64;
                x = p;
            }
            back.reverse();
            if wsum == 0 {
                continue;
            }
            let mut path = vec![];
            let mut x = u;
            while x != 0 {
                let (p, cp) = parent[x];
                path.push(cp);
                x = p;
            }
            path.reverse();
            let mut lap = vec![c];
            lap.extend(back);
            println!("start node: board {} side {}", g.board_string(nodes[u].0, nodes[u].1), nodes[u].2);
            let show = |v: &[u16]| -> String {
                v.iter()
                    .map(|&l| if l < 100 { format!("-/{}/-", l) } else { let (s, c) = unb[l as usize - 100]; format!("{}/{}/-", g.cells(s), c) })
                    .collect::<Vec<_>>()
                    .join(" ")
            };
            println!("path from empty board ({} turns): {}", path.len(), show(&path));
            println!("lap ({} turns, debt-difference change {:+} per lap): {}", lap.len(), wsum, show(&lap));
            return;
        }
    }
    println!("no non-zero cycle found");
}

// ---------------------------------------------------------------- Go / Enhanced Go

struct GoState {
    b: u32,
    w: u32,
    stm: u8,
    passes: u8,
    seen: HashSet<u64>,
}

impl GoState {
    fn new() -> GoState {
        let mut seen = HashSet::new();
        seen.insert(0);
        GoState { b: 0, w: 0, stm: 0, passes: 0, seen }
    }
    fn mo(&self) -> (u32, u32) {
        if self.stm == 0 {
            (self.b, self.w)
        } else {
            (self.w, self.b)
        }
    }
    fn bw(&self, m: u32, o: u32) -> (u32, u32) {
        if self.stm == 0 {
            (m, o)
        } else {
            (o, m)
        }
    }
}

/// Resolve a special turn: remove R (own), place P (⊆ empty ∪ R), capture
/// opponent groups without liberties, refuse if an own group has none.
fn special_result(g: &Geom, m: u32, o: u32, r: u32, p: u32) -> Option<(u32, u32)> {
    let m1 = (m & !r) | p;
    let e1 = g.full & !(m1 | o);
    let mut cap = 0u32;
    let mut rest = o;
    while rest != 0 {
        let bit = rest & rest.wrapping_neg();
        let mut grp = bit;
        loop {
            let ng = (grp | g.expand(grp)) & o;
            if ng == grp {
                break;
            }
            grp = ng;
        }
        rest &= !grp;
        if g.expand(grp) & e1 == 0 {
            cap |= grp;
        }
    }
    let o2 = o & !cap;
    let e2 = g.full & !(m1 | o2);
    if alive(g, m1, e2) != m1 {
        return None;
    }
    Some((m1, o2))
}

struct Counts {
    ordinary: u64,
    special: u64,
    distinct_succ: u64, // distinct successor boards of placing turns (+1 for pass added by caller)
}

/// Legal ordinary moves (result boards), and optionally all legal special turns.
fn go_moves(g: &Geom, s: &GoState, with_special: bool, specials_out: Option<&mut Vec<(u32, u32)>>) -> (Vec<(usize, u32, u32)>, Counts) {
    let (m, o) = s.mo();
    let mut ord = vec![];
    let mut boards: HashSet<u64> = HashSet::new();
    for c in 0..g.nn {
        if let Some((m2, o2, _)) = g.place(m, o, c) {
            let (b, w) = s.bw(m2, o2);
            if !s.seen.contains(&bkey(b, w)) {
                ord.push((c, b, w));
                boards.insert(bkey(b, w));
            }
        }
    }
    let mut special = 0u64;
    let mut sp_out = specials_out;
    if with_special {
        let own = m.count_ones() as usize;
        let empty = g.full & !(m | o);
        let mut k = 2;
        while k * k <= own {
            for_each_comb(m, k * k, &mut |r| {
                for_each_comb(empty | r, k, &mut |p| {
                    if let Some((m1, o2)) = special_result(g, m, o, r, p) {
                        let (b, w) = s.bw(m1, o2);
                        if !s.seen.contains(&bkey(b, w)) {
                            special += 1;
                            boards.insert(bkey(b, w));
                            if let Some(v) = sp_out.as_deref_mut() {
                                v.push((r, p));
                            }
                        }
                    }
                });
            });
            k += 1;
        }
    }
    let n_ord = ord.len() as u64;
    (ord, Counts { ordinary: n_ord, special, distinct_succ: boards.len() as u64 })
}

fn is_own_eye(g: &Geom, m: u32, c: usize) -> bool {
    let nb = g.expand(1 << c);
    nb & m == nb
}

fn random_special(g: &Geom, s: &GoState, rng: &mut Rng) -> Option<(u32, u32)> {
    let mut v = vec![];
    go_moves(g, s, true, Some(&mut v));
    if v.is_empty() {
        None
    } else {
        Some(v[rng.below(v.len())])
    }
}

fn apply_board(s: &mut GoState, b: u32, w: u32) {
    s.b = b;
    s.w = w;
    s.seen.insert(bkey(b, w));
    s.stm ^= 1;
    s.passes = 0;
}

#[derive(Default, Clone)]
struct Stats {
    games: u64,
    capped: u64,
    plies: u64,
    sum_b: f64,     // pooled sum of branching factors (turn counts)
    sum_b2: f64,    // pooled sum of distinct-successor counts
    sum_log: f64,   // per-game sum of log10 b, summed over games
    sum_log2: f64,  // same for distinct successors
    sum_len2: f64,  // sum of squared lengths
    ends: [u64; 4], // nexus: line win, bankruptcy, no move, capped
}

impl Stats {
    fn add(&mut self, o: &Stats) {
        self.games += o.games;
        self.capped += o.capped;
        self.plies += o.plies;
        self.sum_b += o.sum_b;
        self.sum_b2 += o.sum_b2;
        self.sum_log += o.sum_log;
        self.sum_log2 += o.sum_log2;
        self.sum_len2 += o.sum_len2;
        for i in 0..4 {
            self.ends[i] += o.ends[i];
        }
    }
}

fn go_playout(g: &Geom, ego: bool, q: f64, rng: &mut Rng, st: &mut Stats, cap: u64) {
    let mut s = GoState::new();
    let mut len = 0u64;
    let (mut lg, mut lg2) = (0f64, 0f64);
    loop {
        if s.passes >= 2 {
            break;
        }
        if len >= cap {
            st.capped += 1;
            break;
        }
        let (ord, cnt) = go_moves(g, &s, ego, None);
        let bt = (cnt.ordinary + cnt.special + 1) as f64; // + pass
        let bd = (cnt.distinct_succ + 1) as f64;
        st.sum_b += bt;
        st.sum_b2 += bd;
        lg += bt.log10();
        lg2 += bd.log10();
        len += 1;
        let (m, _) = s.mo();
        if ego && cnt.special > 0 && rng.unit() < q {
            let (r, p) = random_special(g, &s, rng).unwrap();
            let (m0, o0) = s.mo();
            let (m1, o2) = special_result(g, m0, o0, r, p).unwrap();
            let (b, w) = s.bw(m1, o2);
            apply_board(&mut s, b, w);
            continue;
        }
        let cand: Vec<&(usize, u32, u32)> = ord.iter().filter(|(c, _, _)| !is_own_eye(g, m, *c)).collect();
        if cand.is_empty() {
            s.passes += 1;
            s.stm ^= 1;
        } else {
            let &(_, b, w) = cand[rng.below(cand.len())];
            apply_board(&mut s, b, w);
        }
    }
    st.games += 1;
    st.plies += len;
    st.sum_len2 += (len * len) as f64;
    st.sum_log += lg;
    st.sum_log2 += lg2;
}

fn nexus_playout(g: &Geom, rng: &mut Rng, st: &mut Stats, cap: u64) {
    let prm = Params { p1: 2, p2: 4 };
    let mut pos = Pos::start();
    let mut hist: Vec<u128> = vec![];
    let mut len = 0u64;
    let mut lg = 0f64;
    loop {
        if len >= cap {
            st.capped += 1;
            st.ends[3] += 1;
            break;
        }
        match gen(g, &pos, &hist, prm, true) {
            Gen::NoMove | Gen::IllDefined => {
                st.ends[2] += 1;
                break;
            }
            Gen::Turns(v) => {
                let bt = v.len() as f64;
                st.sum_b += bt;
                st.sum_b2 += bt;
                lg += bt.log10();
                len += 1;
                let (_, o) = v[rng.below(v.len())];
                match o {
                    Outcome::MoverWins => {
                        st.ends[0] += 1;
                        break;
                    }
                    Outcome::MoverLoses => {
                        st.ends[1] += 1;
                        break;
                    }
                    Outcome::Cont(p, k) => {
                        pos = p;
                        hist.push(k);
                    }
                }
            }
        }
    }
    st.games += 1;
    st.plies += len;
    st.sum_len2 += (len * len) as f64;
    st.sum_log += lg;
    st.sum_log2 += lg;
}

fn playout_cmd(game: &str, n: usize, games: u64, seed: u64, q: f64) {
    let g = Geom::new(n);
    let threads = 12u64.min(games);
    let cap = if game == "nexus" { 2000 } else { 20 * g.nn as u64 };
    let parts: Vec<Stats> = std::thread::scope(|s| {
        let hs: Vec<_> = (0..threads)
            .map(|t| {
                let g = g.clone();
                let game = game.to_string();
                s.spawn(move || {
                    let mut rng = Rng(seed.wrapping_mul(1_000_003).wrapping_add(t));
                    let mut st = Stats::default();
                    let k = games / threads + if t < games % threads { 1 } else { 0 };
                    for _ in 0..k {
                        match game.as_str() {
                            "go" => go_playout(&g, false, 0.0, &mut rng, &mut st, cap),
                            "ego" => go_playout(&g, true, q, &mut rng, &mut st, cap),
                            "nexus" => nexus_playout(&g, &mut rng, &mut st, cap),
                            _ => panic!("game"),
                        }
                    }
                    st
                })
            })
            .collect();
        hs.into_iter().map(|h| h.join().unwrap()).collect()
    });
    let mut st = Stats::default();
    for p in &parts {
        st.add(p);
    }
    let gm = st.games as f64;
    let mean_len = st.plies as f64 / gm;
    let sd_len = (st.sum_len2 / gm - mean_len * mean_len).max(0.0).sqrt();
    let mb = st.sum_b / st.plies as f64;
    let mb2 = st.sum_b2 / st.plies as f64;
    println!(
        "game={} n={} q={} games={} capped={} (cap {} plies)  mean length {:.2} (sd {:.2})  mean branching {:.2}  mean distinct successors {:.2}  \
         Allis log10(b^d) {:.2}  [distinct {:.2}]  mean per-game sum log10 b {:.2}  [distinct {:.2}]  ends(line,bankrupt,nomove,capped) {:?}",
        game,
        n,
        q,
        st.games,
        st.capped,
        cap,
        mean_len,
        sd_len,
        mb,
        mb2,
        mean_len * mb.log10(),
        mean_len * mb2.log10(),
        st.sum_log / gm,
        st.sum_log2 / gm,
        st.ends
    );
}

// ---------------------------------------------------------------- TS cross-check

/// Positions from random Enhanced Go playouts (ordinary moves, and a random
/// special turn with probability 0.35), printed as
/// `n toMove board hist1 hist2 ...` (boards '.', 'b', 'w'; history includes the start).
fn egodump_cmd(n: usize, count: usize, seed: u64, max_own: u32) {
    let g = Geom::new(n);
    let mut rng = Rng(seed);
    let mut printed = 0;
    let so = std::io::stdout();
    let mut so = so.lock();
    while printed < count {
        let mut s = GoState::new();
        let mut order: Vec<u64> = vec![0];
        for _ in 0..(3 * g.nn) {
            let (m, _) = s.mo();
            if m.count_ones() <= max_own && rng.unit() < 0.3 {
                let hist: Vec<String> = order.iter().map(|&k| board_str(&g, k as u32, (k >> 32) as u32)).collect();
                writeln!(so, "{} {} {} {}", n, if s.stm == 0 { "b" } else { "w" }, board_str(&g, s.b, s.w), hist.join(" ")).unwrap();
                printed += 1;
                if printed >= count {
                    break;
                }
            }
            let (ord, _) = go_moves(&g, &s, false, None);
            if m.count_ones() >= 4 && rng.unit() < 0.35 {
                if let Some((r, p)) = random_special(&g, &s, &mut rng) {
                    let (m0, o0) = s.mo();
                    let (m1, o2) = special_result(&g, m0, o0, r, p).unwrap();
                    let (b, w) = s.bw(m1, o2);
                    apply_board(&mut s, b, w);
                    order.push(bkey(b, w));
                    continue;
                }
            }
            if ord.is_empty() || rng.unit() < 0.05 {
                s.stm ^= 1;
                s.passes += 1;
                if s.passes >= 2 {
                    break;
                }
                continue;
            }
            let (_, b, w) = ord[rng.below(ord.len())];
            apply_board(&mut s, b, w);
            order.push(bkey(b, w));
        }
    }
}

/// For each position line on stdin print: ordinary-legal special-legal distinct-successor-boards.
fn egocount_cmd() {
    let stdin = std::io::stdin();
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let f: Vec<&str> = line.split_whitespace().collect();
        if f.is_empty() {
            continue;
        }
        let n: usize = f[0].parse().unwrap();
        let g = Geom::new(n);
        let (b, w) = parse_bw(f[2]);
        let mut s = GoState::new();
        s.seen.clear();
        for h in &f[3..] {
            let (hb, hw) = parse_bw(h);
            s.seen.insert(bkey(hb, hw));
        }
        s.b = b;
        s.w = w;
        s.stm = if f[1] == "b" { 0 } else { 1 };
        let (_, c) = go_moves(&g, &s, true, None);
        println!("{} {} {}", c.ordinary, c.special, c.distinct_succ);
    }
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let p = |i: usize| a[i].parse::<u64>().unwrap();
    match a.get(1).map(|s| s.as_str()) {
        Some("legal") => legal_cmd(p(2) as usize, if a.len() > 3 { p(3) } else { 1_000_000_000 }),
        Some("cycle") => cycle_cmd(p(2) as usize),
        Some("playout") => {
            let q = if a.len() > 6 { a[6].parse().unwrap() } else { 0.0 };
            playout_cmd(&a[2], p(3) as usize, p(4), p(5), q)
        }
        Some("egodump") => egodump_cmd(p(2) as usize, p(3) as usize, p(4), if a.len() > 5 { p(5) as u32 } else { 99 }),
        Some("egocount") => egocount_cmd(),
        _ => eprintln!("see the header of src/bin/complexity.rs"),
    }
}
