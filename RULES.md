# 🐾 **RULES.md — NEXUS**

*A hybrid of Go tactics, Tic-Tac-Toe geometry, and economic debt traps*

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

# **8. Ko Rule**

Nexus uses a **positional superko** rule to prevent infinite repetition:

* A player may not make a move that recreates *any previous (board, debt_difference) state*.
* Here, `debt_difference = debt_black - debt_white`.

A move is illegal if the resulting board and debt difference exactly match any previously seen state.

This prevents infinite cycles that could otherwise occur through repeated captures.

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