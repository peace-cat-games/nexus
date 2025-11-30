import { GameState } from '../types';
import './GameInfo.css';

interface GameInfoProps {
  gameState: GameState | null;
  error: string | null;
}

export function GameInfo({ gameState, error }: GameInfoProps) {
  if (!gameState) {
    return (
      <div className="game-info">
        <p className="info-message">Start a new game to play!</p>
      </div>
    );
  }

  const isGameOver = gameState.result !== 'ONGOING';
  const currentPlayer = gameState.to_move;
  const currentSymbol = currentPlayer === 'BLACK' ? 'X' : 'O';

  return (
    <div className="game-info">
      {error && <div className="error-message">{error}</div>}

      {isGameOver ? (
        <div className="result-banner">
          <h2>
            {gameState.result === 'BLACK_WIN' ? 'Black (X) Wins!' : 'White (O) Wins!'}
          </h2>
        </div>
      ) : (
        <div className="turn-indicator">
          <span className={`player-badge ${currentPlayer.toLowerCase()}`}>
            {currentSymbol}
          </span>
          <span>{currentPlayer}'s Turn</span>
        </div>
      )}

      <div className="debt-display">
        <div className="debt-item">
          <span className="player-badge black">X</span>
          <span className="debt-label">Debt:</span>
          <span className="debt-value">{gameState.debt_black}</span>
        </div>
        <div className="debt-item">
          <span className="player-badge white">O</span>
          <span className="debt-label">Debt:</span>
          <span className="debt-value">{gameState.debt_white}</span>
        </div>
      </div>

      <div className="game-params">
        <span>p1 = {gameState.p1}</span>
        <span>p2 = {gameState.p2}</span>
        <span>Board: {gameState.size}x{gameState.size}</span>
      </div>

      {!isGameOver && gameState.legal_moves.length === 0 && (
        <div className="warning-message">
          No legal moves! Forced unblocking required.
        </div>
      )}
    </div>
  );
}
