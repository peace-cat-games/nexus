import { GameState, DebtResolutionState, UnblockingState } from '../types';
import './GameInfo.css';

interface GameInfoProps {
  gameState: GameState | null;
  error: string | null;
  debtResolution?: DebtResolutionState | null;
  onConfirmDebtResolution?: () => void;
  onCancelDebtResolution?: () => void;
  unblocking?: UnblockingState | null;
  onSelectUnblockingOption?: (index: number) => void;
  onCancelUnblocking?: () => void;
}

export function GameInfo({ gameState, error, debtResolution, onConfirmDebtResolution, onCancelDebtResolution, unblocking, onSelectUnblockingOption, onCancelUnblocking }: GameInfoProps) {
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
      ) : debtResolution ? (
        <div className="debt-resolution-panel">
          <h3>Debt Resolution</h3>
          <p className="debt-resolution-info">
            Select {debtResolution.stonesToRemove} stone{debtResolution.stonesToRemove > 1 ? 's' : ''} to remove
          </p>
          <p className="debt-resolution-progress">
            Selected: {debtResolution.selectedStones.length} / {debtResolution.stonesToRemove}
          </p>
          <div className="debt-resolution-buttons">
            <button
              className="confirm-btn"
              onClick={onConfirmDebtResolution}
              disabled={debtResolution.selectedStones.length !== debtResolution.stonesToRemove}
            >
              Confirm
            </button>
            <button className="cancel-btn" onClick={onCancelDebtResolution}>
              Cancel
            </button>
          </div>
        </div>
      ) : unblocking ? (
        <div className="unblocking-panel">
          <h3>Forced Unblocking</h3>
          <p className="unblocking-info">
            No legal moves! Choose which opponent stones to remove:
          </p>
          <p className="unblocking-debt">
            (Adds {unblocking.totalDebt} debt)
          </p>
          <div className="unblocking-options">
            {unblocking.options.map((option, index) => (
              <button
                key={index}
                className={`unblocking-option ${unblocking.selectedOption === index ? 'selected' : ''}`}
                onClick={() => onSelectUnblockingOption?.(index)}
              >
                {option.map(([r, c]) => `(${r},${c})`).join(', ')}
              </button>
            ))}
          </div>
          {unblocking.selectedOption !== null && (
            <p className="unblocking-instruction">
              Click an empty cell to make your move
            </p>
          )}
          {unblocking.selectedOption !== null && (
            <button className="cancel-btn" onClick={onCancelUnblocking}>
              Change Selection
            </button>
          )}
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

    </div>
  );
}
