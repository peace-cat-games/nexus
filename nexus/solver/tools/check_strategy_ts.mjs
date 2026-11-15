// Independent checker for Nexus strategy trees, using only the Peace Cat
// Games TypeScript engine (peace-cat-games/games/nexus/engine, used
// read-only): the engine the site plays, with its draw rule.
//
// It mirrors tools/check_strategy.py, which uses game.py, but every legality
// question goes to the site's engine: `turnStatus` (place, unblock or
// blocked, and the unblocking options), `preview` (whether a placement is
// legal after a given unblocking, whether it completes a line, how many
// stones the audit takes and which stones can pay) and `playTurn` (which
// applies a whole turn, ends the game when the opponent is left blocked, and
// applies the quiet-turn draw: 2n^2 consecutive turns without a capture).
// The turns of a position are every (unblocking option, legal placement,
// payment) combination those functions allow; a payment is any set of
// exactly `owed` of the mover's stones.
//
// For each tree it replays every line from a fresh game and requires:
//   * the forced opening (header `first=`, if any) is legal;
//   * at each node of the claimed winner: exactly one child, a legal turn;
//   * at each node of the loser: the children are exactly all legal turns;
//   * every leaf is a finished game won by the claimed winner (a draw fails),
//     and no internal node is a finished game.
//
// usage: node --experimental-strip-types check_strategy_ts.mjs ENGINE_DIR [--no-draw | --quiet-limit K] TREE...
//   --no-draw        turn the quiet-turn draw off (the original engine had none)
//   --quiet-limit K  draw after K capture-free turns instead of 2n^2 (for testing)
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const argv = process.argv.slice(2);
const dir = argv.shift();
const noDraw = argv.includes("--no-draw");
const qi = argv.indexOf("--quiet-limit");
const quietLimit = qi >= 0 ? Number(argv[qi + 1]) : null;
const files = argv.filter((a, i) => a !== "--no-draw" && (qi < 0 || (i !== qi && i !== qi + 1)));
const { newGame, turnStatus, preview, playTurn } = await import(pathToFileURL(join(dir, "index.ts")).href);
const options = noDraw ? { quietTurnLimit: Infinity } : quietLimit !== null ? { quietTurnLimit: quietLimit } : {};
const mode = noDraw ? ", no draw rule" : quietLimit !== null ? `, draw after ${quietLimit} quiet turns` : "";

function* combos(arr, k, start = 0, acc = []) {
  if (acc.length === k) {
    yield acc.slice();
    return;
  }
  for (let i = start; i <= arr.length - (k - acc.length); i++) {
    acc.push(arr[i]);
    yield* combos(arr, k, i + 1, acc);
    acc.pop();
  }
}

class CheckError extends Error {}

function check(path) {
  const header = {};
  const nodes = [];
  for (const line of readFileSync(path, "utf8").split("\n")) {
    if (line.startsWith("#")) {
      for (const tok of line.slice(1).trim().split(/\s+/)) {
        const i = tok.indexOf("=");
        if (i > 0) header[tok.slice(0, i)] = tok.slice(i + 1);
      }
      continue;
    }
    const f = line.trim().split(/\s+/);
    if (f.length === 2) nodes.push([f[0], Number(f[1])]);
  }
  const n = Number(header.n ?? 3);
  const p1 = Number(header.p1);
  const p2 = Number(header.p2);
  const winner = header.winner === "BLACK" ? "black" : "white";
  const sep = n <= 3 ? "" : ",";
  const cells = (x) => (x && x.length ? [...x].sort((a, b) => a - b).join(sep) : "-");
  const key = (t) => `${cells(t.unblock)}/${t.place}/${cells(t.pay)}`;
  const parseCells = (x) => (x === "-" ? undefined : n <= 3 ? [...x].map(Number) : x.split(",").map(Number));
  const parse = (s) => {
    const [a, m, b] = s.split("/");
    return { unblock: parseCells(a), place: Number(m), pay: parseCells(b) };
  };
  const first = header.first && header.first !== "any"
    ? header.first.match(/(?:-|\d+(?:,\d+)*)\/\d+\/(?:-|\d+(?:,\d+)*)/g)
    : [];
  const stats = { nodes: nodes.length, winnerNodes: 0, loserNodes: 0, leaves: 0, maxLen: 0, maxQuiet: 0, reasons: {} };
  let pos = 0;
  const next = () => {
    if (pos >= nodes.length) throw new CheckError("tree file truncated");
    return nodes[pos++];
  };

  function turnsOf(s) {
    const st = turnStatus(s);
    if (st.kind === "over") throw new CheckError("internal node is a finished game");
    if (st.kind === "blocked") throw new CheckError("blocked position left unfinished by playTurn");
    const sets = st.kind === "place" ? [undefined] : st.options;
    const out = new Map();
    for (const unblock of sets) {
      for (let p = 0; p < s.board.length; p++) {
        const r = preview(s, unblock, p);
        if (!r.ok) continue;
        const v = r.preview;
        const pays = v.completes && v.owed > 0 && !v.bankrupt ? [...combos(v.own, v.owed)] : [undefined];
        for (const pay of pays) {
          const t = { unblock, place: p, pay };
          const k = key(t);
          if (out.has(k)) throw new CheckError(`turn ${k} enumerated twice`);
          out.set(k, t);
        }
      }
    }
    if (out.size === 0) throw new CheckError("unblocking options but no legal placement (undefined case)");
    return out;
  }

  function apply(s, t) {
    const r = playTurn(s, { unblock: t.unblock, place: t.place, pay: t.pay }, options);
    if (!r.ok) throw new CheckError(`engine refused ${key(t)}: ${r.error.code}`);
    stats.maxQuiet = Math.max(stats.maxQuiet, r.state.quietTurns ?? 0);
    return r.state;
  }

  function verify(s, nchild, depth) {
    if (s.outcome) throw new CheckError("internal node is a finished game");
    const turns = turnsOf(s);
    if (s.toMove === winner) {
      stats.winnerNodes++;
      if (nchild !== 1) throw new CheckError(`winner node with ${nchild} children`);
      const [t, c] = next();
      const k = key(parse(t));
      if (!turns.has(k)) throw new CheckError(`winner turn ${t} is not legal in the site engine`);
      child(s, turns.get(k), c, depth);
    } else {
      stats.loserNodes++;
      if (nchild !== turns.size) {
        throw new CheckError(`loser node: tree has ${nchild} replies, the site engine allows ${turns.size} at ${s.board.join("")} debts ${s.debtBlack}/${s.debtWhite}`);
      }
      const want = new Set(turns.keys());
      for (let i = 0; i < nchild; i++) {
        const [t, c] = next();
        const k = key(parse(t));
        if (!want.has(k)) throw new CheckError(`loser reply ${t} missing from the site engine's list or duplicated`);
        want.delete(k);
        child(s, turns.get(k), c, depth);
      }
    }
  }

  function child(s, t, c, depth) {
    const ns = apply(s, t);
    if (!ns.outcome) return verify(ns, c, depth + 1);
    if (ns.outcome.winner !== winner) {
      throw new CheckError(`line ends ${ns.outcome.winner ? "in a loss" : "in a draw"} (${ns.outcome.reason}) for the claimed winner after ${key(t)}`);
    }
    if (c !== 0) throw new CheckError("finished game has children");
    stats.leaves++;
    stats.reasons[ns.outcome.reason] = (stats.reasons[ns.outcome.reason] ?? 0) + 1;
    stats.maxLen = Math.max(stats.maxLen, depth + 1);
  }

  const [root, rc] = next();
  if (root !== "root") throw new CheckError("first node must be root");
  let s = newGame({ size: n, p1, p2 });
  let count = rc;
  for (const ft of first) {
    if (count !== 1) throw new CheckError("forced opening node must have one child");
    const [t, c] = next();
    if (t !== ft) throw new CheckError(`tree does not start with the forced opening ${ft}`);
    const turns = turnsOf(s);
    const k = key(parse(t));
    if (!turns.has(k)) throw new CheckError(`opening turn ${t} is not legal`);
    s = apply(s, turns.get(k));
    if (s.outcome) throw new CheckError("opening ends the game");
    count = c;
  }
  verify(s, count, first.length);
  if (pos !== nodes.length) throw new CheckError("trailing nodes in tree file");
  return { n, p1, p2, winner, first: first.join(",") || "any", stats };
}

let failed = 0;
for (const f of files) {
  try {
    const r = check(f);
    console.log(`VERIFIED (site engine${mode}): ${r.winner} wins ${r.n}x${r.n} Nexus (p1=${r.p1}, p2=${r.p2}) after [${r.first}]: ${f}`);
    console.log(JSON.stringify(r.stats));
  } catch (e) {
    if (!(e instanceof CheckError)) throw e;
    failed++;
    console.log(`CHECK FAILED: ${f}: ${e.message}`);
  }
}
process.exit(failed ? 1 : 0);
