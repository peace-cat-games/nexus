// Count the legal turns of Enhanced Go positions with the owner's own
// TypeScript engine (peace-cat-games/games/enhanced-go/engine, used read-only).
// Input lines (from `complexity egodump`): n toMove board hist1 hist2 ...
// Output per line: ordinaryLegal specialLegal distinctSuccessorBoards
// (passing is always legal and is not counted here).
// usage: node --experimental-strip-types ego_ts_count.mjs ENGINE_DIR < positions
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const dir = process.argv[2];
const { fromPosition, playTurn } = await import(pathToFileURL(join(dir, "game.ts")).href);

function* combos(arr, k, start = 0, acc = []) {
  if (acc.length === k) { yield acc.slice(); return; }
  for (let i = start; i <= arr.length - (k - acc.length); i++) {
    acc.push(arr[i]); yield* combos(arr, k, i + 1, acc); acc.pop();
  }
}

const out = [];
for (const line of readFileSync(0, "utf8").split("\n")) {
  const f = line.trim().split(/\s+/);
  if (f.length < 3) continue;
  const n = Number(f[0]);
  const toMove = f[1];
  const parse = (s) => [...s].map((c) => (c === "." ? null : c));
  const board = parse(f[2]);
  const state = { ...fromPosition(board, n, toMove), positions: f.slice(3) };
  const boards = new Set();
  let ord = 0, spec = 0;
  for (let p = 0; p < n * n; p++) {
    const r = playTurn(state, { kind: "place", point: p });
    if (r.ok) { ord++; boards.add(r.value.state.board.map((c) => c ?? ".").join("")); }
  }
  const own = [], empty = [];
  board.forEach((c, i) => { if (c === toMove) own.push(i); else if (c === null) empty.push(i); });
  for (let k = 2; k * k <= own.length; k++) {
    for (const rem of combos(own, k * k)) {
      const avail = [...empty, ...rem].sort((a, b) => a - b);
      for (const pl of combos(avail, k)) {
        const r = playTurn(state, { kind: "special", remove: rem, place: pl });
        if (r.ok) { spec++; boards.add(r.value.state.board.map((c) => c ?? ".").join("")); }
      }
    }
  }
  out.push(`${ord} ${spec} ${boards.size}`);
}
console.log(out.join("\n"));
