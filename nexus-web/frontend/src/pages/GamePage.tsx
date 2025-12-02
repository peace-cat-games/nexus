import { useState, useCallback, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Board, GameInfo } from '../components';
import { GameState, DebtResolutionState, UnblockingState } from '../types';
import { getGame, makeMove, checkMove, getUnblockingOptions, connectToGame } from '../api/client';
import { useAuth } from '../context/AuthContext';
import './GamePage.css';

export function GamePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastMove, setLastMove] = useState<[number, number] | null>(null);
  const [debtResolution, setDebtResolution] = useState<DebtResolutionState | null>(null);
  const [unblocking, setUnblocking] = useState<UnblockingState | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  // Load game state
  const loadGame = useCallback(async () => {
    if (!gameId) return;
    try {
      const state = await getGame(gameId);
      setGameState(state);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load game');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  useEffect(() => {
    loadGame();
  }, [loadGame]);

  // Set up WebSocket for real-time games
  useEffect(() => {
    if (!gameId || !gameState) return;

    // For real-time games, use WebSocket
    if (gameState.mode === 'realtime') {
      wsRef.current = connectToGame(gameId, (data: unknown) => {
        if (data && typeof data === 'object' && 'type' in data) {
          const msg = data as { type: string; game_state?: GameState };
          if (msg.type === 'game_update' && msg.game_state) {
            setGameState(msg.game_state);
          }
        }
      });

      return () => {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      };
    }

    // For correspondence games, poll every 10 seconds
    if (gameState.mode === 'correspondence' && gameState.result === 'ONGOING') {
      pollIntervalRef.current = window.setInterval(() => {
        loadGame();
      }, 10000);

      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
      };
    }
    // Only re-run when mode or result changes, not on every gameState update
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId, gameState?.mode, gameState?.result, loadGame]);

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

  // Determine if it's the current user's turn
  const isMyTurn = useCallback(() => {
    if (!gameState || !user) return false;
    if (gameState.to_move === 'BLACK' && gameState.player_black_id === user.id) return true;
    if (gameState.to_move === 'WHITE' && gameState.player_white_id === user.id) return true;
    return false;
  }, [gameState, user]);

  // Get which color the user is playing
  const myColor = useCallback(() => {
    if (!gameState || !user) return null;
    if (gameState.player_black_id === user.id) return 'BLACK';
    if (gameState.player_white_id === user.id) return 'WHITE';
    return null;
  }, [gameState, user]);

  const handleCellClick = useCallback(async (row: number, col: number) => {
    if (!gameState || gameState.result !== 'ONGOING') return;
    if (!isMyTurn()) {
      setError("It's not your turn");
      return;
    }

    // If in debt resolution mode, handle stone selection
    if (debtResolution) {
      const isPlayerStone = debtResolution.playerStones.some(([r, c]) => r === row && c === col);
      if (!isPlayerStone) {
        setError('Select your own stones to remove for debt resolution');
        return;
      }

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
      setLoading(true);
      setError(null);
      try {
        const selectedStones = unblocking.options[unblocking.selectedOption];
        const response = await makeMove(gameState.game_id, row, col, undefined, selectedStones);
        setGameState(response.game_state);
        setLastMove([row, col]);
        setUnblocking(null);

        // Broadcast update via WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'game_update',
            game_state: response.game_state,
          }));
        }

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
      const checkResult = await checkMove(gameState.game_id, row, col);

      if (checkResult.requires_debt_resolution && !checkResult.would_be_bankrupt) {
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

      const response = await makeMove(gameState.game_id, row, col);
      setGameState(response.game_state);
      setLastMove([row, col]);

      // Broadcast update via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'game_update',
          game_state: response.game_state,
        }));
      }

      if (response.unblocked_stones) {
        setError(`Removed opponent stones: ${response.unblocked_stones.map(([r, c]) => `(${r},${c})`).join(', ')}`);
      }
      if (response.message) {
        setError(response.message);
      }
      if (checkResult.would_be_bankrupt && response.game_state.result !== 'ONGOING') {
        setError(`Bankruptcy! Not enough stones to pay debt.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to make move');
    } finally {
      setLoading(false);
    }
  }, [gameState, debtResolution, unblocking, isMyTurn]);

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

      // Broadcast update via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'game_update',
          game_state: response.game_state,
        }));
      }

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

  if (loading && !gameState) {
    return (
      <div className="game-page">
        <div className="loading-message">Loading game...</div>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="game-page">
        <div className="error-page">
          <h2>Game Not Found</h2>
          <p>{error || 'The game could not be loaded.'}</p>
          <button onClick={() => navigate('/play')} className="btn btn-primary">
            Back to Lobby
          </button>
        </div>
      </div>
    );
  }

  const isGameOver = gameState.result !== 'ONGOING';
  const color = myColor();
  const canPlay = isMyTurn() && !isGameOver;

  return (
    <div className="game-page">
      <div className="game-header">
        <div className="players">
          <span className={`player black ${gameState.to_move === 'BLACK' ? 'active' : ''} ${color === 'BLACK' ? 'you' : ''}`}>
            {gameState.player_black_username || 'Black'}
          </span>
          <span className="vs">vs</span>
          <span className={`player white ${gameState.to_move === 'WHITE' ? 'active' : ''} ${color === 'WHITE' ? 'you' : ''}`}>
            {gameState.player_white_username || 'White'}
          </span>
        </div>
        <div className="game-mode">{gameState.mode}</div>
      </div>

      <main className="game-main">
        <section className="game-area">
          <Board
            board={gameState.board}
            size={gameState.size}
            legalMoves={canPlay && !debtResolution && !unblocking ? gameState.legal_moves : []}
            onCellClick={handleCellClick}
            disabled={loading || isGameOver || !canPlay}
            lastMove={lastMove}
            debtResolution={debtResolution}
            unblocking={unblocking}
          />
        </section>

        <aside className="game-sidebar">
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
          {!canPlay && !isGameOver && (
            <div className="waiting-message">
              {gameState.player_black_id && gameState.player_white_id
                ? "Waiting for opponent's move..."
                : 'Waiting for opponent to join...'}
            </div>
          )}
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
