import { useState, useCallback, useEffect } from 'react';
import { Board, GameInfo, GameControls } from './components';
import { GameState, NewGameOptions, DebtResolutionState, UnblockingState } from './types';
import { createGame, makeMove, checkMove, getUnblockingOptions } from './api/client';
import './App.css';

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMove, setLastMove] = useState<[number, number] | null>(null);
  const [debtResolution, setDebtResolution] = useState<DebtResolutionState | null>(null);
  const [unblocking, setUnblocking] = useState<UnblockingState | null>(null);

  // Check for forced unblocking when game state changes
  useEffect(() => {
    if (!gameState || gameState.result !== 'ONGOING' || debtResolution) return;
    if (gameState.legal_moves.length > 0) {
      setUnblocking(null);
      return;
    }

    // No legal moves - check for unblocking options
    const checkUnblocking = async () => {
      try {
        const result = await getUnblockingOptions(gameState.game_id);
        if (result.needs_unblocking && result.options.length > 0) {
          setUnblocking({
            options: result.options,
            selectedOption: null,
            totalDebt: result.total_debt || 0,
          });
          setError(`No legal moves! Select which opponent stones to remove (adds ${result.total_debt} debt).`);
        } else if (result.impossible) {
          setError('No legal moves and no way to unblock - game over!');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to check unblocking options');
      }
    };
    checkUnblocking();
  }, [gameState, debtResolution]);

  const handleNewGame = useCallback(async (options: NewGameOptions) => {
    setLoading(true);
    setError(null);
    setLastMove(null);
    setDebtResolution(null);
    setUnblocking(null);
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

    // If in debt resolution mode, handle stone selection
    if (debtResolution) {
      // Check if this is the player's stone (available for selection)
      const isPlayerStone = debtResolution.playerStones.some(([r, c]) => r === row && c === col);
      if (!isPlayerStone) {
        setError('Select your own stones to remove for debt resolution');
        return;
      }

      // Toggle stone selection
      const isSelected = debtResolution.selectedStones.some(([r, c]) => r === row && c === col);
      if (isSelected) {
        setDebtResolution({
          ...debtResolution,
          selectedStones: debtResolution.selectedStones.filter(([r, c]) => !(r === row && c === col)),
        });
      } else if (debtResolution.selectedStones.length < debtResolution.stonesToRemove) {
        setDebtResolution({
          ...debtResolution,
          selectedStones: [...debtResolution.selectedStones, [row, col]],
        });
      }
      return;
    }

    // If in unblocking mode with a selected option, make the move
    if (unblocking) {
      if (unblocking.selectedOption === null) {
        setError('Select an unblocking option first, then click a move location.');
        return;
      }
      // Make the move with unblocking
      setLoading(true);
      setError(null);
      try {
        const selectedStones = unblocking.options[unblocking.selectedOption];
        const response = await makeMove(gameState.game_id, row, col, undefined, selectedStones);
        setGameState(response.game_state);
        setLastMove([row, col]);
        setUnblocking(null);

        if (response.unblocked_stones) {
          setError(`Removed opponent stones: ${response.unblocked_stones.map(([r, c]) => `(${r},${c})`).join(', ')}`);
        }

        if (response.message) {
          setError(response.message);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to make move');
      } finally {
        setLoading(false);
      }
      return;
    }

    // Check if this is a legal move
    const isLegal = gameState.legal_moves.some(([r, c]) => r === row && c === col);
    if (!isLegal) {
      setError(`Illegal move at (${row}, ${col})`);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Check if this move requires debt resolution
      const checkResult = await checkMove(gameState.game_id, row, col);

      if (checkResult.requires_debt_resolution && !checkResult.would_be_bankrupt) {
        // Enter debt resolution mode - let the player select stones
        setDebtResolution({
          pendingMove: [row, col],
          stonesToRemove: checkResult.stones_to_remove,
          playerStones: checkResult.player_stones,
          selectedStones: [],
          wouldBeBankrupt: false,
        });
        setError(`Completion! Select ${checkResult.stones_to_remove} of your stones to remove to pay debt.`);
        setLoading(false);
        return;
      }

      // Make the move (either no debt resolution, or bankruptcy)
      const response = await makeMove(gameState.game_id, row, col);
      setGameState(response.game_state);
      setLastMove([row, col]);

      if (response.unblocked_stones) {
        setError(`Removed opponent stones: ${response.unblocked_stones.map(([r, c]) => `(${r},${c})`).join(', ')}`);
      }

      if (response.message) {
        setError(response.message);
      }

      // Check for bankruptcy in the result
      if (checkResult.would_be_bankrupt && response.game_state.result !== 'ONGOING') {
        setError(`Bankruptcy! Not enough stones to pay debt.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to make move');
    } finally {
      setLoading(false);
    }
  }, [gameState, debtResolution, unblocking]);

  const handleSelectUnblockingOption = useCallback((index: number) => {
    if (!unblocking) return;
    setUnblocking({
      ...unblocking,
      selectedOption: index,
    });
    setError(`Selected option ${index + 1}. Now click a cell to make your move.`);
  }, [unblocking]);

  const handleCancelUnblocking = useCallback(() => {
    if (!unblocking) return;
    setUnblocking({
      ...unblocking,
      selectedOption: null,
    });
    setError(`No legal moves! Select which opponent stones to remove (adds ${unblocking.totalDebt} debt).`);
  }, [unblocking]);

  const handleConfirmDebtResolution = useCallback(async () => {
    if (!gameState || !debtResolution) return;
    if (debtResolution.selectedStones.length !== debtResolution.stonesToRemove) {
      setError(`Please select exactly ${debtResolution.stonesToRemove} stones to remove`);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [row, col] = debtResolution.pendingMove;
      const response = await makeMove(
        gameState.game_id,
        row,
        col,
        debtResolution.selectedStones
      );
      setGameState(response.game_state);
      setLastMove([row, col]);
      setDebtResolution(null);

      if (response.unblocked_stones) {
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
  }, [gameState, debtResolution]);

  const handleCancelDebtResolution = useCallback(() => {
    setDebtResolution(null);
    setError(null);
  }, []);

  const isGameOver = gameState?.result !== 'ONGOING';

  return (
    <div className="app">
      <header className="app-header">
        <h1>Nexus</h1>
        <p>A strategic board game combining Go and Tic-Tac-Toe</p>
      </header>

      <main className="app-main">
        <aside className="sidebar left">
          <GameControls onNewGame={handleNewGame} disabled={loading || !!debtResolution || !!unblocking} />
        </aside>

        <section className="game-area">
          {gameState ? (
            <Board
              board={gameState.board}
              size={gameState.size}
              legalMoves={debtResolution || unblocking ? [] : gameState.legal_moves}
              onCellClick={handleCellClick}
              disabled={loading || isGameOver}
              lastMove={lastMove}
              debtResolution={debtResolution}
              unblocking={unblocking}
            />
          ) : (
            <div className="empty-board-placeholder">
              <p>Click "New Game" to start playing!</p>
            </div>
          )}
        </section>

        <aside className="sidebar right">
          <GameInfo
            gameState={gameState}
            error={error}
            debtResolution={debtResolution}
            onConfirmDebtResolution={handleConfirmDebtResolution}
            onCancelDebtResolution={handleCancelDebtResolution}
            unblocking={unblocking}
            onSelectUnblockingOption={handleSelectUnblockingOption}
            onCancelUnblocking={handleCancelUnblocking}
          />
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
