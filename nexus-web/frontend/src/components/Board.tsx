import { CellValue, BLACK, WHITE, EMPTY, DebtResolutionState } from '../types';
import './Board.css';

interface BoardProps {
  board: number[][];
  size: number;
  legalMoves: [number, number][];
  onCellClick: (row: number, col: number) => void;
  disabled: boolean;
  lastMove?: [number, number] | null;
  debtResolution?: DebtResolutionState | null;
}

export function Board({ board, size, legalMoves, onCellClick, disabled, lastMove, debtResolution }: BoardProps) {
  const isLegalMove = (row: number, col: number): boolean => {
    return legalMoves.some(([r, c]) => r === row && c === col);
  };

  const isLastMove = (row: number, col: number): boolean => {
    return lastMove ? lastMove[0] === row && lastMove[1] === col : false;
  };

  const isSelectableForDebt = (row: number, col: number): boolean => {
    if (!debtResolution) return false;
    return debtResolution.playerStones.some(([r, c]) => r === row && c === col);
  };

  const isSelectedForDebt = (row: number, col: number): boolean => {
    if (!debtResolution) return false;
    return debtResolution.selectedStones.some(([r, c]) => r === row && c === col);
  };

  const isPendingMove = (row: number, col: number): boolean => {
    if (!debtResolution) return false;
    const [r, c] = debtResolution.pendingMove;
    return r === row && c === col;
  };

  const getCellClass = (value: CellValue, row: number, col: number): string => {
    const classes = ['cell'];

    if (value === BLACK) classes.push('black');
    else if (value === WHITE) classes.push('white');
    else if (isLegalMove(row, col) && !disabled) classes.push('legal');

    if (isLastMove(row, col)) classes.push('last-move');

    // Debt resolution mode
    if (debtResolution) {
      if (isPendingMove(row, col)) classes.push('pending-move');
      if (isSelectableForDebt(row, col)) classes.push('selectable-for-debt');
      if (isSelectedForDebt(row, col)) classes.push('selected-for-debt');
    }

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
          row.map((cell, colIdx) => {
            const isClickable = debtResolution
              ? isSelectableForDebt(rowIdx, colIdx)
              : (cell === EMPTY && isLegalMove(rowIdx, colIdx));

            return (
              <button
                key={`${rowIdx}-${colIdx}`}
                className={getCellClass(cell as CellValue, rowIdx, colIdx)}
                onClick={() => onCellClick(rowIdx, colIdx)}
                disabled={disabled || !isClickable}
                aria-label={`Cell ${rowIdx},${colIdx}: ${cell === BLACK ? 'Black' : cell === WHITE ? 'White' : 'Empty'}${isSelectedForDebt(rowIdx, colIdx) ? ' (selected for removal)' : ''}`}
              >
                {cell !== EMPTY && (
                  <div className={`stone ${cell === BLACK ? 'black-stone' : 'white-stone'}`} />
                )}
                {isPendingMove(rowIdx, colIdx) && (
                  <div className="pending-stone" />
                )}
              </button>
            );
          })
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
