---

# 🐾 **RULES.md — NEXUS**

*A hybrid of Go tactics, Tic-Tac-Toe geometry, and economic debt traps*

---

# **1. Overview**

Nexus is a two-player deterministic strategy game mixing:

* **Go-style fighting and capture mechanics**
* **Tic-Tac-Toe’s line-completion objective**
* **A debt economy where captures create future liabilities**

The result is a game where:

* Capturing may be brilliant—or catastrophic.
* Completing a line may win instantly—or explode your own position.
* Debt rules determine whether you survive a completion audit.
* Bankruptcy is a normal tactical outcome.

Nexus is **original**: no known abstract game uses Go liberties, line completion, and symmetric economic audits.

---

# **2. The Board**

* An **n × n** grid of intersections.
* Two players: **Black** (plays first) and **White**.
* Stones are placed on intersections, not inside squares.

---

# **3. Groups, Liberties, and Go Legality**

Nexus uses standard **Go mechanics**:

### **3.1 Groups**

A group is a maximal set of same-colored stones connected orthogonally.

### **3.2 Liberties**

A liberty is any orthogonally adjacent empty point.

### **3.3 Captures**

When a stone is placed:

1. All adjacent opponent groups with **zero liberties** are captured and removed.
2. After captures, if the new stone’s own group has **zero liberties**,
   the move is illegal **unless** it captured enemy stones.

---

# **4. Debt Mechanics (defaults: p₁ = 2, p₂ = 4)**

Nexus introduces **debt**:

* Capturing enemy stones **costs debt**.
* Debt is only resolved when a **Completion event** occurs.

Let:

* **p₁ = 2** (default): debt per captured stone
* **p₂ = 4** (default): debt per stone removed in Forced Unblocking

Track two integers:

* `debt_black ≥ 0`
* `debt_white ≥ 0`

### **4.1 Capture Debt**

If a player captures `k` enemy stones in a move:

```
debt_player += k * p₁
```

For default p₁ = 2:

* Capturing a 3-stone group → **+6 debt**
* Capturing anything large is extremely dangerous.

---

# **5. Lines & Completion**

### **5.1 Lines**

A *line* is any of the following:

* Any full **row** (n stones by the same player)
* Any full **column**
* The **main diagonal**
* The **anti-diagonal**

There are **2n + 2** lines total.

### **5.2 Completion Event**

After a move (and captures),
if the player who just moved owns **at least one full line**,
a **Completion Event** begins.

---

# **6. The Debt Audit at Completion**

Let:

* P = player who formed the line
* Q = opponent
* `D_P`, `D_Q` = their debts
* Compute `net = D_P - D_Q`

### **Case 1 — net ≤ 0: Instant Win**

P’s total debt is not higher than Q’s.

→ **P wins immediately.**
Debts do not matter anymore.

---

### **Case 2 — net > 0: P must pay**

P must pay “excess” debt by removing `net` of their own stones:

1. Let `k = net`.
2. P must remove **exactly k of their own stones**.
3. If P has fewer than k stones → **P loses by bankruptcy.**
4. If P has at least k stones:

   * P chooses which stones to remove.
   * Remove all k stones.
   * After removal:

     * If at least one full line remains → **P wins immediately.**
     * If no full line remains:

       * Debt is settled; **both debts reset to 0**.
       * Game continues.
       * Turn passes to Q.

---

# **7. Forced Unblocking **

Before placing a stone normally:

### **7.1 If legal moves exist → play normally.**

### **7.2 If no legal placement exists: Forced Unblocking**

The player must:

* Remove the **minimum number** of opponent stones
  that makes at least one legal placement possible.

Let `k = number removed`:

```
debt_player += k * p₂
```

Using default p₂ = 4, removing even one stone is very costly.

After removal:

* If a legal placement exists → player plays normally.
* If no legal placement exists even after removing all opponent stones → **loss**.

---

# **8. Ko & Repetition**

### **8.1 Nexus has no Ko rule by default.**

Position repetition **is allowed**.
This is intentional:

* Nexus already has strong debt-based anti-cycling pressure.
* The debt economy ensures that “infinite Go fights” eventually become fatal.
* Forced Unblocking ensures boards cannot enter certain Go-style “two-eyes-only” deadlocks.

### **8.2 Optional Superko (advanced variant)**

If desired, an optional rule can be adopted:

* **Positional superko:** A player may not recreate *any previous board+turn+debt state.*

This is optional and not part of the base rules.
For AI and human play, **default = no superko**.

---

# **9. End of Game**

A player wins if:

* They complete a line and survive the audit,
* Their opponent cannot financially survive the audit,
* Their opponent cannot move and forced unblocking is impossible.

Nexus does **not** require full board filling.
Many games end abruptly after large captures.

---

# **10. Default Parameters**

* **p₁ = 2**
* **p₂ = 4**
* Recommended boards: 3×3, 5×5, 7×7, 9×9.

---

# 🐾 **APPENDIX A — NEW PUZZLES (p₁=2, p₂=4)**

These puzzles highlight the defaults.

---

## **PUZZLE A1 — The p₁=2 Capture Bomb**

```
Board 3×3
Turn: Black
Debt: B=0, W=0
p₁=2

B W .
B W .
. . .
```

Black can capture both white stones in column 2.

### **Question:**

Should Black do it?

### **Answer:**

**No.**

Capturing 2 stones → **+4 debt**.

White immediately plays on row 1 to complete the top row:

```
B B B
. . .
. . .
```

Audit:

* D_B = 4
* D_W = 0
* net = 4 → Black must remove 4 stones → impossible → **Black bankrupts**.

---

## **PUZZLE A2 — Forced Unblocking with p₂=4**

```
Turn: White
Debt: W=0, B=0
p₂=4

Board:
B W B
W B W
B W .
```

White has **no legal placement move**.

### **Question:**

Which minimal unblock removes must White choose, and what happens?

### **Answer:**

White must remove 1 Black stone (cost = 4 debt).
Removing (2,2) or (1,1) opens a liberty.

So:

* Remove one Black stone → debt_white = 4
* White now must place a stone normally
* Strong players avoid this position entirely because p₂=4 is painful.

---

## **PUZZLE A3 — Debt Advantage Instant Win**

White prepares a completion, Black has captured heavily:

```
Debts: B=10, W=2
p₁=2

White to move can complete a column.
```

Completion audit:

* net = D_W - D_B = 2 - 10 = -8 → ≤ 0
  → **White wins instantly**

White’s line makes Black’s giant capture spree fatal.

---

## **PUZZLE A4 — Bankruptcy by Overcapture**

Black captures a 3-stone group on a 5×5 board:

* k = 3
* p₁ = 2
* debt added = 6

Black’s debt is now 7 while White has 0.

White completes a diagonal:

Audit:

* net = D_W - D_B = 0 - 7 = -7 → ≤ 0
  White **wins** immediately.

Large captures are extremely risky under p₁ = 2.

---

# **APPENDIX B — OPTIONAL ADVANCED PUZZLE: DEBT LADDER**

A multi-step forcing sequence where a series of captures (each worth +2 debt per stone) becomes unavoidable, then White executes a clean Completion to annihilate Black.

(Not included here but can be produced on request.)

