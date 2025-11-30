import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GameInfo } from './GameInfo';
import { GameState } from '../types';

describe('GameInfo', () => {
  const mockGameState: GameState = {
    game_id: 'test-id',
    size: 5,
    board: Array(5).fill(Array(5).fill(0)),
    to_move: 'BLACK',
    debt_black: 0,
    debt_white: 0,
    result: 'ONGOING',
    legal_moves: [],
    p1: 2,
    p2: 4,
  };

  it('shows message when no game state', () => {
    render(<GameInfo gameState={null} error={null} />);
    expect(screen.getByText('Start a new game to play!')).toBeInTheDocument();
  });

  it('shows current turn', () => {
    render(<GameInfo gameState={mockGameState} error={null} />);
    expect(screen.getByText("BLACK's Turn")).toBeInTheDocument();
  });

  it('shows debt values', () => {
    const stateWithDebt: GameState = {
      ...mockGameState,
      debt_black: 5,
      debt_white: 3,
    };
    render(<GameInfo gameState={stateWithDebt} error={null} />);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows winner when game is over', () => {
    const wonState: GameState = {
      ...mockGameState,
      result: 'BLACK_WIN',
    };
    render(<GameInfo gameState={wonState} error={null} />);
    expect(screen.getByText('Black (X) Wins!')).toBeInTheDocument();
  });

  it('shows error message when provided', () => {
    render(<GameInfo gameState={mockGameState} error="Test error" />);
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('shows game parameters', () => {
    render(<GameInfo gameState={mockGameState} error={null} />);
    expect(screen.getByText('p1 = 2')).toBeInTheDocument();
    expect(screen.getByText('p2 = 4')).toBeInTheDocument();
    expect(screen.getByText('Board: 5x5')).toBeInTheDocument();
  });
});
