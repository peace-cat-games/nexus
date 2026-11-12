//! 3x3 Nexus rules engine, mirroring `nexus/game.py` (see README.md, "Rules").
//!
//! Cells are indexed `i = 3*row + col`; a colour's stones are a 9-bit mask.

pub const FULL: u16 = 0x1FF;
const COL0: u16 = 0b001_001_001;
const COL2: u16 = 0b100_100_100;
/// Rows, columns, main diagonal, anti-diagonal.
pub const LINES: [u16; 8] = [0x007, 0x038, 0x1C0, 0x049, 0x092, 0x124, 0x111, 0x054];

#[derive(Clone, Copy, Debug)]
pub struct Params {
    pub p1: i32,
    pub p2: i32,
}

/// A position: stones, debts, side to move (0 = Black, 1 = White).
/// The superko history is kept separately as a list of keys.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Pos {
    pub b: u16,
    pub w: u16,
    pub db: i32,
    pub dw: i32,
    pub stm: u8,
}

impl Pos {
    pub fn start() -> Pos {
        Pos { b: 0, w: 0, db: 0, dw: 0, stm: 0 }
    }
    /// Compact key for the transposition table (history NOT included).
    pub fn tt_key(&self) -> u64 {
        debug_assert!(self.db >= 0 && self.dw >= 0 && self.db < 1 << 20 && self.dw < 1 << 20);
        (self.b as u64)
            | (self.w as u64) << 9
            | (self.stm as u64) << 18
            | (self.db as u64) << 19
            | (self.dw as u64) << 40
    }
    pub fn board_string(&self) -> String {
        (0..9)
            .map(|i| {
                if self.b >> i & 1 == 1 {
                    'X'
                } else if self.w >> i & 1 == 1 {
                    'O'
                } else {
                    '.'
                }
            })
            .collect()
    }
}

/// Superko key: (board, debt_black - debt_white), exactly as game.py's `get_position_key`.
#[inline]
pub fn ko_key(b: u16, w: u16, diff: i32) -> u64 {
    (b as u64) | (w as u64) << 9 | ((diff as i64 + (1i64 << 40)) as u64) << 18
}

#[inline]
fn expand(g: u16) -> u16 {
    (((g << 1) & !COL0) | ((g >> 1) & !COL2) | (g << 3) | (g >> 3)) & FULL
}

#[inline]
fn group(color: u16, start: u16) -> u16 {
    let mut g = start;
    loop {
        let ng = (g | expand(g)) & color;
        if ng == g {
            return g;
        }
        g = ng;
    }
}

#[inline]
pub fn has_line(m: u16) -> bool {
    LINES.iter().any(|&l| m & l == l)
}

/// Go placement of the mover at cell `c`: returns (mover', opponent', #captured)
/// or None if occupied / suicide.  Mirrors `_is_legal_move` minus the ko test.
#[inline]
fn place(m: u16, o: u16, c: usize) -> Option<(u16, u16, i32)> {
    let bit = 1u16 << c;
    if (m | o) & bit != 0 {
        return None;
    }
    let m2 = m | bit;
    let empty = FULL & !(m2 | o);
    let mut cap = 0u16;
    let mut nb = expand(bit) & o;
    while nb != 0 {
        let nbit = nb & nb.wrapping_neg();
        nb &= nb - 1;
        if cap & nbit != 0 {
            continue;
        }
        let g = group(o, nbit);
        if expand(g) & empty == 0 {
            cap |= g;
        }
    }
    if cap == 0 {
        let g = group(m2, bit);
        if expand(g) & empty == 0 {
            return None;
        }
    }
    Some((m2, o & !cap, cap.count_ones() as i32))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Turn {
    /// Opponent stones removed by forced unblocking (0 = none).
    pub unblock: u16,
    /// Cell of the placed stone.
    pub place: u8,
    /// Own stones removed in a completion audit (0 = none).
    pub remove: u16,
}

#[derive(Clone, Copy, Debug)]
pub enum Outcome {
    MoverWins,
    MoverLoses,
    /// Game continues: new position and the superko key recorded for this turn.
    Cont(Pos, u64),
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

pub fn cells(mask: u16) -> String {
    if mask == 0 {
        return "-".to_string();
    }
    (0..9).filter(|i| mask >> i & 1 == 1).map(|i| char::from(b'0' + i as u8)).collect()
}

pub fn turn_string(t: &Turn) -> String {
    format!("{}/{}/{}", cells(t.unblock), t.place, cells(t.remove))
}

#[inline]
fn in_hist(hist: &[u64], k: u64) -> bool {
    hist.iter().any(|&h| h == k)
}

/// Iterate sub-masks of `m` with exactly `k` bits.
fn submasks_with_popcount(m: u16, k: u32, mut f: impl FnMut(u16)) {
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
    stm: u8,
    hist: &'a [u64],
    prm: Params,
    full: bool,
}

impl<'a> Ctx<'a> {
    #[inline]
    fn colours(&self, m: u16, o: u16) -> (u16, u16) {
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

    /// Any legal placement (Go legality + superko) for mover stones m vs o, debts dm/dq.
    fn has_legal(&self, m: u16, o: u16, dm: i32, dq: i32) -> bool {
        for c in 0..9 {
            if let Some((m2, o2, ncap)) = place(m, o, c) {
                let (b, w) = self.colours(m2, o2);
                let (db, dw) = self.debts(dm + ncap * self.prm.p1, dq);
                if !in_hist(self.hist, ko_key(b, w, db - dw)) {
                    return true;
                }
            }
        }
        false
    }

    /// Append every turn consisting of a placement (after optional unblocking `ub`).
    fn placements(&self, m: u16, o: u16, dm: i32, dq: i32, ub: u16, out: &mut Vec<(Turn, Outcome)>) -> bool {
        let mut any = false;
        let opp = self.stm ^ 1;
        for c in 0..9 {
            let Some((m2, o2, ncap)) = place(m, o, c) else { continue };
            let dm2 = dm + ncap * self.prm.p1;
            let (b, w) = self.colours(m2, o2);
            let (db, dw) = self.debts(dm2, dq);
            let key = ko_key(b, w, db - dw);
            if in_hist(self.hist, key) {
                continue;
            }
            any = true;
            let t = |remove: u16| Turn { unblock: ub, place: c as u8, remove };
            if !has_line(m2) {
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
            } else if net <= pc - 3 && !self.full {
                // Mover removes `net` stones outside some full line and keeps it: win.
                let l = *LINES.iter().find(|&&l| m2 & l == l).unwrap();
                let mut r = 0u16;
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
                    if has_line(m3) {
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
pub fn gen(pos: &Pos, hist: &[u64], prm: Params, full: bool) -> Gen {
    let ctx = Ctx { stm: pos.stm, hist, prm, full };
    let (m, o, dm, dq) = if pos.stm == 0 { (pos.b, pos.w, pos.db, pos.dw) } else { (pos.w, pos.b, pos.dw, pos.db) };
    let mut out = Vec::new();
    if ctx.placements(m, o, dm, dq, 0, &mut out) {
        return Gen::Turns(out);
    }
    // Forced unblocking: minimal sets judged with the current debts (game.py).
    if o == 0 {
        return Gen::NoMove;
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
            return if out.is_empty() { Gen::IllDefined } else { Gen::Turns(out) };
        }
    }
    Gen::NoMove
}

pub fn parse_board(s: &str) -> (u16, u16) {
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
