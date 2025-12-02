import './RulesPage.css';

export function RulesPage() {
  return (
    <div className="rules-page">
      <article className="rules-content">
        <h1>Nexus Rules</h1>
        <p className="subtitle">A hybrid of Go tactics, Tic-Tac-Toe geometry, and economic debt traps</p>

        <section>
          <h2>1. Overview</h2>
          <p>
            Nexus is a two-player deterministic strategy game mixing:
          </p>
          <ul>
            <li><strong>Go-style fighting and capture mechanics</strong></li>
            <li><strong>Tic-Tac-Toe's line-completion objective</strong></li>
            <li><strong>A debt economy where captures create future liabilities</strong></li>
          </ul>
          <p>The result is a game where:</p>
          <ul>
            <li>Capturing may be brilliant—or catastrophic.</li>
            <li>Completing a line may win instantly—or explode your own position.</li>
            <li>Debt rules determine whether you survive a completion audit.</li>
            <li>Bankruptcy is a normal tactical outcome.</li>
          </ul>
        </section>

        <section>
          <h2>2. The Board</h2>
          <ul>
            <li>An <strong>n × n</strong> grid of intersections.</li>
            <li>Two players: <strong>Black</strong> (plays first) and <strong>White</strong>.</li>
            <li>Stones are placed on intersections, not inside squares.</li>
          </ul>
        </section>

        <section>
          <h2>3. Groups, Liberties, and Go Legality</h2>
          <p>Nexus uses standard Go mechanics:</p>

          <h3>3.1 Groups</h3>
          <p>A group is a maximal set of same-colored stones connected orthogonally (up, down, left, right).</p>

          <h3>3.2 Liberties</h3>
          <p>A liberty is any orthogonally adjacent empty point to a group.</p>

          <h3>3.3 Captures</h3>
          <p>When a stone is placed:</p>
          <ol>
            <li>All adjacent opponent groups with <strong>zero liberties</strong> are captured and removed.</li>
            <li>After captures, if the new stone's own group has <strong>zero liberties</strong>, the move is illegal <em>unless</em> it captured enemy stones.</li>
          </ol>
        </section>

        <section>
          <h2>4. Debt Mechanics</h2>
          <p>Nexus introduces <strong>debt</strong>:</p>
          <ul>
            <li>Capturing enemy stones <strong>costs debt</strong>.</li>
            <li>Debt is only resolved when a <strong>Completion event</strong> occurs.</li>
          </ul>

          <div className="parameters">
            <p><strong>Default parameters:</strong></p>
            <ul>
              <li><code>p₁ = 2</code> — debt per captured stone</li>
              <li><code>p₂ = 4</code> — debt per stone removed in Forced Unblocking</li>
            </ul>
          </div>

          <h3>4.1 Capture Debt</h3>
          <p>If a player captures <code>k</code> enemy stones in a move:</p>
          <pre>debt_player += k × p₁</pre>
          <p>For default p₁ = 2:</p>
          <ul>
            <li>Capturing a 3-stone group → <strong>+6 debt</strong></li>
            <li>Capturing anything large is extremely dangerous!</li>
          </ul>
        </section>

        <section>
          <h2>5. Lines & Completion</h2>

          <h3>5.1 Lines</h3>
          <p>A line is any of the following:</p>
          <ul>
            <li>Any full <strong>row</strong> (n stones by the same player)</li>
            <li>Any full <strong>column</strong></li>
            <li>The <strong>main diagonal</strong> (top-left to bottom-right)</li>
            <li>The <strong>anti-diagonal</strong> (top-right to bottom-left)</li>
          </ul>
          <p>There are <strong>2n + 2</strong> lines total.</p>

          <h3>5.2 Completion Event</h3>
          <p>
            After a move (and captures), if the player who just moved owns <strong>at least one full line</strong>,
            a <strong>Completion Event</strong> begins.
          </p>
        </section>

        <section>
          <h2>6. The Debt Audit at Completion</h2>
          <p>Let:</p>
          <ul>
            <li>P = player who formed the line</li>
            <li>Q = opponent</li>
            <li>D_P, D_Q = their debts</li>
            <li><code>net = D_P - D_Q</code></li>
          </ul>

          <div className="case">
            <h3>Case 1 — net ≤ 0: Instant Win</h3>
            <p>P's total debt is not higher than Q's.</p>
            <p className="result">→ <strong>P wins immediately.</strong></p>
          </div>

          <div className="case">
            <h3>Case 2 — net &gt; 0: P must pay</h3>
            <p>P must pay "excess" debt by removing <code>net</code> of their own stones:</p>
            <ol>
              <li>Let <code>k = net</code>.</li>
              <li>P must remove <strong>exactly k of their own stones</strong>.</li>
              <li>If P has fewer than k stones → <strong className="loss">P loses by bankruptcy.</strong></li>
              <li>
                If P has at least k stones:
                <ul>
                  <li>P chooses which stones to remove.</li>
                  <li>Remove all k stones.</li>
                  <li>After removal:
                    <ul>
                      <li>If at least one full line remains → <strong className="win">P wins immediately.</strong></li>
                      <li>If no full line remains:
                        <ul>
                          <li>Debt is settled; <strong>both debts reset to 0</strong>.</li>
                          <li>Game continues.</li>
                          <li>Turn passes to Q.</li>
                        </ul>
                      </li>
                    </ul>
                  </li>
                </ul>
              </li>
            </ol>
          </div>
        </section>

        <section>
          <h2>7. Forced Unblocking</h2>
          <p>Before placing a stone normally:</p>

          <h3>7.1 If legal moves exist → play normally.</h3>

          <h3>7.2 If no legal placement exists: Forced Unblocking</h3>
          <p>The player must:</p>
          <ul>
            <li>Remove the <strong>minimum number</strong> of opponent stones that makes at least one legal placement possible.</li>
          </ul>
          <p>Let <code>k = number removed</code>:</p>
          <pre>debt_player += k × p₂</pre>
          <p>Using default p₂ = 4, removing even one stone is very costly.</p>
          <p>After removal:</p>
          <ul>
            <li>If a legal placement exists → player plays normally.</li>
            <li>If no legal placement exists even after removing all opponent stones → <strong className="loss">loss</strong>.</li>
          </ul>
        </section>

        <section>
          <h2>8. Ko Rule</h2>
          <p>Nexus uses a <strong>positional superko</strong> rule to prevent infinite repetition:</p>
          <ul>
            <li>A player may not make a move that recreates <em>any previous (board, debt_difference) state</em>.</li>
            <li>Here, <code>debt_difference = debt_black - debt_white</code>.</li>
          </ul>
          <p>A move is illegal if the resulting board and debt difference exactly match any previously seen state.</p>
        </section>

        <section>
          <h2>9. End of Game</h2>
          <p>A player wins if:</p>
          <ul>
            <li>They complete a line and survive the audit,</li>
            <li>Their opponent cannot financially survive the audit,</li>
            <li>Their opponent cannot move and forced unblocking is impossible.</li>
          </ul>
          <p>Nexus does <strong>not</strong> require full board filling. Many games end abruptly after large captures.</p>
        </section>

        <section>
          <h2>10. Default Parameters</h2>
          <ul>
            <li><strong>p₁ = 2</strong> (debt per captured stone)</li>
            <li><strong>p₂ = 4</strong> (debt per forced unblock stone)</li>
          </ul>
          <p>Recommended board sizes: 3×3, 5×5, 7×7, 9×9.</p>
        </section>
      </article>
    </div>
  );
}
