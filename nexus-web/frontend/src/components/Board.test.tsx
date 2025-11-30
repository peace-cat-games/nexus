import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Board } from './Board';
import { EMPTY, BLACK, WHITE } from '../types';

describe('Board', () => {
  const defaultProps = {
    board: [
      [EMPTY, EMPTY, EMPTY],
      [EMPTY, BLACK, EMPTY],
      [EMPTY, EMPTY, WHITE],
    ],
    size: 3,
    legalMoves: [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1]] as [number, number][],
    onCellClick: vi.fn(),
    disabled: false,
  };

  it('renders the correct number of cells', () => {
    render(<Board {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(9);
  });

  it('shows stones in correct positions', () => {
    render(<Board {...defaultProps} />);
    // Check that there are 2 stones rendered (1 black, 1 white)
    const stones = document.querySelectorAll('.stone');
    expect(stones).toHaveLength(2);
    expect(document.querySelector('.black-stone')).toBeInTheDocument();
    expect(document.querySelector('.white-stone')).toBeInTheDocument();
  });

  it('calls onCellClick when a cell is clicked', () => {
    const onCellClick = vi.fn();
    render(<Board {...defaultProps} onCellClick={onCellClick} />);

    const cell = screen.getByLabelText('Cell 0,0: Empty');
    fireEvent.click(cell);

    expect(onCellClick).toHaveBeenCalledWith(0, 0);
  });

  it('highlights legal moves', () => {
    render(<Board {...defaultProps} />);
    const legalCell = screen.getByLabelText('Cell 0,0: Empty');
    expect(legalCell).toHaveClass('legal');
  });

  it('disables cells when disabled prop is true', () => {
    render(<Board {...defaultProps} disabled={true} />);
    const cells = screen.getAllByRole('button');
    cells.forEach(cell => {
      expect(cell).toBeDisabled();
    });
  });

  it('highlights last move when provided', () => {
    render(<Board {...defaultProps} lastMove={[1, 1]} />);
    const lastMoveCell = screen.getByLabelText('Cell 1,1: Black');
    expect(lastMoveCell).toHaveClass('last-move');
  });
});
