import { useState, useCallback } from 'react';
import { Board, GameInfo, GameControls } from './components';
import { GameState, NewGameOptions } from './types';
import { createGame, makeMove } from './api/client';
import './App.css';

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMove, setLastMove] = useState<[number, number] | null>(null);

  const handleNewGame = useCallback(async (options: NewGameOptions) => {
    setLoading(true);
    setError(null);
    setLastMove(null);
    try {
      const state = await createGame(options);
      setGameState(state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCellClick = useCallback(async (row: number, col: number) => {
    if (!gameState || gameState.result !== 'ONGOING') return;

    // Check if this is a legal move
    const isLegal = gameState.legal_moves.some(([r, c]) => r === row && c === col);
    if (!isLegal) {
      setError(`Illegal move at (${row}, ${col})`);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await makeMove(gameState.game_id, row, col);
      setGameState(response.game_state);
      setLastMove([row, col]);

      if (response.unblocked_stones) {
        // Show notification about forced unblocking
        setError(`Forced unblocking removed stones: ${response.unblocked_stones.map(([r, c]) => `(${r},${c})`).join(', ')}`);
      }

      if (response.message) {
        setError(response.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to make move');
    } finally {
      setLoading(false);
    }
  }, [gameState]);

  const isGameOver = gameState?.result !== 'ONGOING';

  return (
    <div className="app">
      <header className="app-header">
        <h1>Nexus</h1>
        <p>A strategic board game combining Go and Tic-Tac-Toe</p>
      </header>

      <main className="app-main">
        <aside className="sidebar left">
          <GameControls onNewGame={handleNewGame} disabled={loading} />
        </aside>

        <section className="game-area">
          {gameState ? (
            <Board
              board={gameState.board}
              size={gameState.size}
              legalMoves={gameState.legal_moves}
              onCellClick={handleCellClick}
              disabled={loading || isGameOver}
              lastMove={lastMove}
            />
          ) : (
            <div className="empty-board-placeholder">
              <p>Click "New Game" to start playing!</p>
            </div>
          )}
        </section>

        <aside className="sidebar right">
          <GameInfo gameState={gameState} error={error} />
        </aside>
      </main>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
        </div>
      )}
    </div>
  );
}

export default App;
