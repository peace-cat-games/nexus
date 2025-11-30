import { CellValue, BLACK, WHITE, EMPTY } from '../types';
import './Board.css';

interface BoardProps {
  board: number[][];
  size: number;
  legalMoves: [number, number][];
  onCellClick: (row: number, col: number) => void;
  disabled: boolean;
  lastMove?: [number, number] | null;
}

export function Board({ board, size, legalMoves, onCellClick, disabled, lastMove }: BoardProps) {
  const isLegalMove = (row: number, col: number): boolean => {
    return legalMoves.some(([r, c]) => r === row && c === col);
  };

  const isLastMove = (row: number, col: number): boolean => {
    return lastMove ? lastMove[0] === row && lastMove[1] === col : false;
  };

  const getCellClass = (value: CellValue, row: number, col: number): string => {
    const classes = ['cell'];

    if (value === BLACK) classes.push('black');
    else if (value === WHITE) classes.push('white');
    else if (isLegalMove(row, col) && !disabled) classes.push('legal');

    if (isLastMove(row, col)) classes.push('last-move');

    return classes.join(' ');
  };

  return (
    <div className="board-container">
      <div
        className="board"
        style={{
          gridTemplateColumns: `repeat(${size}, 1fr)`,
          gridTemplateRows: `repeat(${size}, 1fr)`,
        }}
      >
        {/* Grid lines */}
        <svg className="grid-lines" viewBox={`0 0 ${size} ${size}`}>
          {/* Horizontal lines */}
          {Array.from({ length: size }, (_, i) => (
            <line
              key={`h-${i}`}
              x1="0.5"
              y1={i + 0.5}
              x2={size - 0.5}
              y2={i + 0.5}
              stroke="var(--grid-color)"
              strokeWidth="0.02"
            />
          ))}
          {/* Vertical lines */}
          {Array.from({ length: size }, (_, i) => (
            <line
              key={`v-${i}`}
              x1={i + 0.5}
              y1="0.5"
              x2={i + 0.5}
              y2={size - 0.5}
              stroke="var(--grid-color)"
              strokeWidth="0.02"
            />
          ))}
        </svg>

        {/* Cells */}
        {board.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <button
              key={`${rowIdx}-${colIdx}`}
              className={getCellClass(cell as CellValue, rowIdx, colIdx)}
              onClick={() => onCellClick(rowIdx, colIdx)}
              disabled={disabled || (cell !== EMPTY && !isLegalMove(rowIdx, colIdx))}
              aria-label={`Cell ${rowIdx},${colIdx}: ${cell === BLACK ? 'Black' : cell === WHITE ? 'White' : 'Empty'}`}
            >
              {cell !== EMPTY && (
                <div className={`stone ${cell === BLACK ? 'black-stone' : 'white-stone'}`} />
              )}
            </button>
          ))
        )}
      </div>

      {/* Row labels */}
      <div className="row-labels">
        {Array.from({ length: size }, (_, i) => (
          <span key={i}>{i}</span>
        ))}
      </div>

      {/* Column labels */}
      <div className="col-labels">
        {Array.from({ length: size }, (_, i) => (
          <span key={i}>{i}</span>
        ))}
      </div>
    </div>
  );
}
