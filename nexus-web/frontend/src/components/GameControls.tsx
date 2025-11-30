import { useState } from 'react';
import { NewGameOptions } from '../types';
import './GameControls.css';

interface GameControlsProps {
  onNewGame: (options: NewGameOptions) => void;
  disabled: boolean;
}

export function GameControls({ onNewGame, disabled }: GameControlsProps) {
  const [size, setSize] = useState(5);
  const [p1, setP1] = useState(2);
  const [p2, setP2] = useState(4);
  const [showOptions, setShowOptions] = useState(false);

  const handleNewGame = () => {
    onNewGame({ size, p1, p2 });
  };

  return (
    <div className="game-controls">
      <button
        className="new-game-btn"
        onClick={handleNewGame}
        disabled={disabled}
      >
        New Game
      </button>

      <button
        className="options-toggle"
        onClick={() => setShowOptions(!showOptions)}
      >
        {showOptions ? 'Hide Options' : 'Show Options'}
      </button>

      {showOptions && (
        <div className="options-panel">
          <div className="option">
            <label htmlFor="size">Board Size:</label>
            <input
              id="size"
              type="number"
              min="3"
              max="19"
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
            />
          </div>

          <div className="option">
            <label htmlFor="p1">p1 (capture debt):</label>
            <input
              id="p1"
              type="number"
              min="1"
              max="10"
              value={p1}
              onChange={(e) => setP1(Number(e.target.value))}
            />
          </div>

          <div className="option">
            <label htmlFor="p2">p2 (unblock debt):</label>
            <input
              id="p2"
              type="number"
              min="1"
              max="10"
              value={p2}
              onChange={(e) => setP2(Number(e.target.value))}
            />
          </div>
        </div>
      )}

      <div className="rules-summary">
        <h4>Quick Rules</h4>
        <ul>
          <li>Place stones to complete a line (row/col/diagonal)</li>
          <li>Capture groups with no liberties (adds debt)</li>
          <li>Complete a line with less debt to win</li>
          <li>Can't pay debt = bankruptcy = lose</li>
        </ul>
      </div>
    </div>
  );
}
