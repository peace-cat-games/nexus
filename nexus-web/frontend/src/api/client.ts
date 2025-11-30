import { GameState, MoveResponse, NewGameOptions, CheckMoveResponse } from '../types';

const API_BASE = '/api';

export async function createGame(options: NewGameOptions): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!response.ok) {
    throw new Error(`Failed to create game: ${response.statusText}`);
  }
  return response.json();
}

export async function getGame(gameId: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${gameId}`);
  if (!response.ok) {
    throw new Error(`Failed to get game: ${response.statusText}`);
  }
  return response.json();
}

export async function makeMove(
  gameId: string,
  row: number,
  col: number,
  stonesToRemove?: [number, number][]
): Promise<MoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      row,
      col,
      stones_to_remove: stonesToRemove,
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to make move');
  }
  return response.json();
}

export async function deleteGame(gameId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/games/${gameId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete game: ${response.statusText}`);
  }
}

export async function checkMove(
  gameId: string,
  row: number,
  col: number
): Promise<CheckMoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/check-move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ row, col }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to check move');
  }
  return response.json();
}
