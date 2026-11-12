//! n×n Nexus rules engine (n = 3, 4, 5), mirroring `nexus/game.py` (see
//! README.md, "Rules").
//!
//! Cells are indexed `i = n*row + col`; a colour's stones are an n²-bit mask
//! (u32, so n ≤ 5).  Lines are the n rows, n columns and the two main
//! diagonals.

use std::cell::Cell;

/// Board geometry for one board size.
#[derive(Clone, Debug)]
pub struct Geom {
    pub n: usize,
    pub nn: usize,
    pub full: u32,
    not_col0: u32,
    not_coll: u32,
    pub lines: Vec<u32>,
}

impl Geom {
    pub fn new(n: usize) -> Geom {
        assert!((2..=5).contains(&n), "board size must be 2..=5");
        let nn = n * n;
        let full = if nn == 32 { u32::MAX } else { (1u32 << nn) - 1 };
        let mut col0 = 0u32;
        let mut coll = 0u32;
        for r in 0..n {
            col0 |= 1 << (r * n);
            coll |= 1 << (r * n + n - 1);
        }
        let mut lines = Vec::new();
        for r in 0..n {
            lines.push((0..n).fold(0u32, |m, c| m | 1 << (r * n + c)));
        }
        for c in 0..n {
            lines.push((0..n).fold(0u32, |m, r| m | 1 << (r * n + c)));
        }
        lines.push((0..n).fold(0u32, |m, i| m | 1 << (i * n + i)));
        lines.push((0..n).fold(0u32, |m, i| m | 1 << (i * n + n - 1 - i)));
        Geom { n, nn, full, not_col0: full & !col0, not_coll: full & !coll, lines }
    }

    #[inline]
    pub fn expand(&self, g: u32) -> u32 {
        (((g << 1) & self.not_col0) | ((g >> 1) & self.not_coll) | (g << self.n) | (g >> self.n)) & self.full
    }

    #[inline]
    fn group(&self, color: u32, start: u32) -> u32 {
        let mut g = start;
        loop {
            let ng = (g | self.expand(g)) & color;
            if ng == g {
                return g;
            }
            g = ng;
        }
    }

    #[inline]
    pub fn has_line(&self, m: u32) -> bool {
        self.lines.iter().any(|&l| m & l == l)
    }

    /// Fewest further own placements needed to own a full line: every cell of
    /// a line not already holding an own stone needs one own placement.
    #[inline]
    pub fn line_distance(&self, m: u32) -> u32 {
        self.lines.iter().map(|&l| self.n as u32 - (m & l).count_ones()).min().unwrap()
    }

    /// Go placement of the mover at cell `c`: returns (mover', opponent',
    /// #captured) or None if occupied / suicide.  Mirrors `_is_legal_move`
    /// minus the ko test.
    #[inline]
    pub fn place(&self, m: u32, o: u32, c: usize) -> Option<(u32, u32, i32)> {
        let bit = 1u32 << c;
        if (m | o) & bit != 0 {
            return None;
        }
        let m2 = m | bit;
        let empty = self.full & !(m2 | o);
        let mut cap = 0u32;
        let mut nb = self.expand(bit) & o;
        while nb != 0 {
            let nbit = nb & nb.wrapping_neg();
            nb &= nb - 1;
            if cap & nbit != 0 {
                continue;
            }
            let g = self.group(o, nbit);
            if self.expand(g) & empty == 0 {
                cap |= g;
            }
        }
        if cap == 0 {
            let g = self.group(m2, bit);
            if self.expand(g) & empty == 0 {
                return None;
            }
        }
        Some((m2, o & !cap, cap.count_ones() as i32))
    }

    pub fn board_string(&self, b: u32, w: u32) -> String {
        (0..self.nn)
            .map(|i| {
                if b >> i & 1 == 1 {
                    'X'
                } else if w >> i & 1 == 1 {
                    'O'
                } else {
                    '.'
                }
            })
            .collect()
    }

    /// Cell list of a mask: digits for n = 3 (the 3×3 tree format), else
    /// comma-separated indices; "-" for the empty set.
    pub fn cells(&self, mask: u32) -> String {
        if mask == 0 {
            return "-".to_string();
        }
        let v: Vec<String> = (0..self.nn).filter(|i| mask >> i & 1 == 1).map(|i| i.to_string()).collect();
        if self.n <= 3 {
            v.concat()
        } else {
            v.join(",")
        }
    }

    pub fn turn_string(&self, t: &Turn) -> String {
        format!("{}/{}/{}", self.cells(t.unblock), t.place, self.cells(t.remove))
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Params {
    pub p1: i32,
    pub p2: i32,
}

/// A position: stones, debts, side to move (0 = Black, 1 = White).
/// The superko history is kept separately as a list of keys.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Pos {
    pub b: u32,
    pub w: u32,
    pub db: i32,
    pub dw: i32,
    pub stm: u8,
}

impl Pos {
    pub fn start() -> Pos {
        Pos { b: 0, w: 0, db: 0, dw: 0, stm: 0 }
    }
    /// Exact key of the position without history (transposition table).
    pub fn tt_key(&self) -> u128 {
        debug_assert!(self.db >= 0 && self.dw >= 0);
        (self.b as u128)
            | (self.w as u128) << 25
            | (self.stm as u128) << 50
            | (self.db as u32 as u128) << 51
            | (self.dw as u32 as u128) << 83
    }
}

/// Superko key: (board, debt_black - debt_white), exactly as game.py's
/// `get_position_key`.  Bits 0..50 hold the board.
#[inline]
pub fn ko_key(b: u32, w: u32, diff: i32) -> u128 {
    (b as u128) | (w as u128) << 25 | ((diff as i64 + (1i64 << 40)) as u128) << 50
}

/// Number of stones on the board of a superko key.
#[inline]
pub fn key_stones(k: u128) -> u32 {
    ((k as u64) & ((1u64 << 50) - 1)).count_ones()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Turn {
    /// Opponent stones removed by forced unblocking (0 = none).
    pub unblock: u32,
    /// Cell of the placed stone.
    pub place: u8,
    /// Own stones removed in a completion audit (0 = none).
    pub remove: u32,
}

#[derive(Clone, Copy, Debug)]
pub enum Outcome {
    MoverWins,
    MoverLoses,
    /// Game continues: new position and the superko key recorded for this turn.
    Cont(Pos, u128),
}

pub enum Gen {
    /// No legal placement and forced unblocking impossible: mover loses.
    NoMove,
    /// Minimal unblocking sets exist (judged with pre-unblocking debts, as in
    /// game.py) but after paying p2 no placement is legal (superko). game.py
    /// leaves this undefined; we score it as a loss for the mover and count it.
    IllDefined,
    Turns(Vec<(Turn, Outcome)>),
}

/// Iterate sub-masks of `m` with exactly `k` bits.
fn submasks_with_popcount(m: u32, k: u32, mut f: impl FnMut(u32)) {
    let mut s = m;
    loop {
        if s.count_ones() == k {
            f(s);
        }
        if s == 0 {
            break;
        }
        s = (s - 1) & m;
    }
}

struct Ctx<'a> {
    g: &'a Geom,
    stm: u8,
    hist: &'a [u128],
    prm: Params,
    full: bool,
    /// Fewest stones on any board whose key was looked up in the history.
    min_tested: Cell<u32>,
}

impl<'a> Ctx<'a> {
    #[inline]
    fn colours(&self, m: u32, o: u32) -> (u32, u32) {
        if self.stm == 0 {
            (m, o)
        } else {
            (o, m)
        }
    }
    #[inline]
    fn debts(&self, dm: i32, dq: i32) -> (i32, i32) {
        if self.stm == 0 {
            (dm, dq)
        } else {
            (dq, dm)
        }
    }
    #[inline]
    fn in_hist(&self, k: u128) -> bool {
        let s = key_stones(k);
        if s < self.min_tested.get() {
            self.min_tested.set(s);
        }
        self.hist.iter().any(|&h| h == k)
    }

    /// Any legal placement (Go legality + superko) for mover stones m vs o, debts dm/dq.
    fn has_legal(&self, m: u32, o: u32, dm: i32, dq: i32) -> bool {
        for c in 0..self.g.nn {
            if let Some((m2, o2, ncap)) = self.g.place(m, o, c) {
                let (b, w) = self.colours(m2, o2);
                let (db, dw) = self.debts(dm + ncap * self.prm.p1, dq);
                if !self.in_hist(ko_key(b, w, db - dw)) {
                    return true;
                }
            }
        }
        false
    }

    /// Append every turn consisting of a placement (after optional unblocking `ub`).
    fn placements(&self, m: u32, o: u32, dm: i32, dq: i32, ub: u32, out: &mut Vec<(Turn, Outcome)>) -> bool {
        let g = self.g;
        let n = g.n as i32;
        let mut any = false;
        let opp = self.stm ^ 1;
        for c in 0..g.nn {
            let Some((m2, o2, ncap)) = g.place(m, o, c) else { continue };
            let dm2 = dm + ncap * self.prm.p1;
            let (b, w) = self.colours(m2, o2);
            let (db, dw) = self.debts(dm2, dq);
            let key = ko_key(b, w, db - dw);
            if self.in_hist(key) {
                continue;
            }
            any = true;
            let t = |remove: u32| Turn { unblock: ub, place: c as u8, remove };
            if !g.has_line(m2) {
                out.push((t(0), Outcome::Cont(Pos { b, w, db, dw, stm: opp }, key)));
                continue;
            }
            // Completion audit.
            let net = dm2 - dq;
            let pc = m2.count_ones() as i32;
            if net <= 0 {
                out.push((t(0), Outcome::MoverWins));
            } else if pc < net {
                out.push((t(0), Outcome::MoverLoses));
            } else if net <= pc - n && !self.full {
                // Mover removes `net` stones outside some full line and keeps it: win.
                let l = *g.lines.iter().find(|&&l| m2 & l == l).unwrap();
                let mut r = 0u32;
                let mut rest = m2 & !l;
                for _ in 0..net {
                    let lb = rest & rest.wrapping_neg();
                    r |= lb;
                    rest &= rest - 1;
                }
                out.push((t(r), Outcome::MoverWins));
            } else {
                submasks_with_popcount(m2, net as u32, |r| {
                    let m3 = m2 & !r;
                    if g.has_line(m3) {
                        out.push((t(r), Outcome::MoverWins));
                    } else {
                        let (b3, w3) = self.colours(m3, o2);
                        let k3 = ko_key(b3, w3, 0);
                        out.push((t(r), Outcome::Cont(Pos { b: b3, w: w3, db: 0, dw: 0, stm: opp }, k3)));
                    }
                });
            }
        }
        any
    }
}

/// Generate all turns of the side to move.  `full = false` collapses an audit in
/// which the mover can keep a full line into a single winning turn.
pub fn gen(g: &Geom, pos: &Pos, hist: &[u128], prm: Params, full: bool) -> Gen {
    gen_t(g, pos, hist, prm, full).0
}

/// As `gen`, also returning the fewest stones on any board whose superko key
/// was looked up (u32::MAX if none): the generator's output depends on the
/// history only through those lookups.
pub fn gen_t(g: &Geom, pos: &Pos, hist: &[u128], prm: Params, full: bool) -> (Gen, u32) {
    let ctx = Ctx { g, stm: pos.stm, hist, prm, full, min_tested: Cell::new(u32::MAX) };
    let (m, o, dm, dq) = if pos.stm == 0 { (pos.b, pos.w, pos.db, pos.dw) } else { (pos.w, pos.b, pos.dw, pos.db) };
    let mut out = Vec::new();
    if ctx.placements(m, o, dm, dq, 0, &mut out) {
        return (Gen::Turns(out), ctx.min_tested.get());
    }
    // Forced unblocking: minimal sets judged with the current debts (game.py).
    if o == 0 {
        return (Gen::NoMove, ctx.min_tested.get());
    }
    for k in 1..=o.count_ones() {
        let mut sets = Vec::new();
        submasks_with_popcount(o, k, |s| {
            if ctx.has_legal(m, o & !s, dm, dq) {
                sets.push(s);
            }
        });
        if !sets.is_empty() {
            for s in sets {
                ctx.placements(m, o & !s, dm + k as i32 * prm.p2, dq, s, &mut out);
            }
            let r = if out.is_empty() { Gen::IllDefined } else { Gen::Turns(out) };
            return (r, ctx.min_tested.get());
        }
    }
    (Gen::NoMove, ctx.min_tested.get())
}

pub fn parse_board(s: &str) -> (u32, u32) {
    let mut b = 0;
    let mut w = 0;
    for (i, ch) in s.chars().enumerate() {
        match ch {
            'X' => b |= 1 << i,
            'O' => w |= 1 << i,
            _ => {}
        }
    }
    (b, w)
}

pub fn size_of_board_string(s: &str) -> usize {
    let n = (s.len() as f64).sqrt().round() as usize;
    assert_eq!(n * n, s.len(), "board string length is not a square");
    n
}
