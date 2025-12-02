import {
  GameState,
  MoveResponse,
  NewGameOptions,
  CheckMoveResponse,
  UnblockingOptionsResponse,
  User,
  AuthToken,
  Seek,
  GameListItem,
} from '../types';

const API_BASE = '/api';

// Token management
let authToken: string | null = localStorage.getItem('token');

export function setToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

export function getToken(): string | null {
  return authToken;
}

function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

// Auth API
export async function register(username: string, email: string, password: string): Promise<AuthToken> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export async function login(username: string, password: string): Promise<AuthToken> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
}

export function logout() {
  setToken(null);
}

export async function getMe(): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Not authenticated');
  }
  return response.json();
}

// Game API
export async function createGame(options: NewGameOptions): Promise<GameState> {
  const response = await fetch(`${API_BASE}/nexus/games`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(options),
  });
  if (!response.ok) {
    throw new Error(`Failed to create game: ${response.statusText}`);
  }
  return response.json();
}

export async function getGame(gameId: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/nexus/games/${gameId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to get game: ${response.statusText}`);
  }
  return response.json();
}

export async function makeMove(
  gameId: string,
  row: number,
  col: number,
  stonesToRemove?: [number, number][],
  unblockingStones?: [number, number][]
): Promise<MoveResponse> {
  const response = await fetch(`${API_BASE}/nexus/games/${gameId}/move`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      row,
      col,
      stones_to_remove: stonesToRemove,
      unblocking_stones: unblockingStones,
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to make move');
  }
  return response.json();
}

export async function getUnblockingOptions(gameId: string): Promise<UnblockingOptionsResponse> {
  const response = await fetch(`${API_BASE}/nexus/games/${gameId}/unblocking-options`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get unblocking options');
  }
  return response.json();
}

export async function deleteGame(gameId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/nexus/games/${gameId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
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
  const response = await fetch(`${API_BASE}/nexus/games/${gameId}/check-move`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ row, col }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to check move');
  }
  return response.json();
}

// Lobby API
export async function getMyGames(): Promise<GameListItem[]> {
  const response = await fetch(`${API_BASE}/me/games`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to get games');
  }
  return response.json();
}

export async function createSeek(
  mode: 'realtime' | 'correspondence',
  boardSize: number,
  p1: number = 2,
  p2: number = 4
): Promise<Seek> {
  const response = await fetch(`${API_BASE}/nexus/seeks`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ mode, board_size: boardSize, p1, p2 }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create seek');
  }
  return response.json();
}

export async function getSeeks(): Promise<Seek[]> {
  const response = await fetch(`${API_BASE}/nexus/seeks`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to get seeks');
  }
  return response.json();
}

export async function getMySeek(): Promise<Seek | null> {
  const response = await fetch(`${API_BASE}/nexus/seeks/mine`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to get seek');
  }
  return response.json();
}

export async function cancelSeek(seekId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/nexus/seeks/${seekId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to cancel seek');
  }
}

export async function acceptSeek(seekId: number): Promise<GameState> {
  const response = await fetch(`${API_BASE}/nexus/seeks/${seekId}/accept`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to accept seek');
  }
  return response.json();
}

// WebSocket
export function connectToGame(gameId: string, onMessage: (data: unknown) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/game/${gameId}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      console.error('Failed to parse WebSocket message');
    }
  };

  return ws;
}
