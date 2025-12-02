import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  GameState,
  GameListItem,
  Seek,
  User,
  MoveResponse,
  DebtResolutionInfo,
  UnblockingOptions,
  CheckMoveResult,
  AuthToken,
} from '../types';

const TOKEN_KEY = 'nexus_auth_token';

// Default to localhost - change this for production
let API_BASE_URL = 'http://10.0.2.2:8000'; // Android emulator localhost
// For iOS simulator, use: 'http://localhost:8000'
// For physical device, use your computer's IP address

export function setApiBaseUrl(url: string) {
  API_BASE_URL = url;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

// Token management
let authToken: string | null = null;

export async function loadToken(): Promise<string | null> {
  try {
    authToken = await AsyncStorage.getItem(TOKEN_KEY);
    return authToken;
  } catch {
    return null;
  }
}

export async function saveToken(token: string): Promise<void> {
  authToken = token;
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  authToken = null;
  await AsyncStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  return authToken;
}

// HTTP helpers
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auth API
export async function register(
  username: string,
  email: string,
  password: string
): Promise<AuthToken> {
  const data = await request<AuthToken>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
  await saveToken(data.access_token);
  return data;
}

export async function login(
  username: string,
  password: string
): Promise<AuthToken> {
  const data = await request<AuthToken>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  await saveToken(data.access_token);
  return data;
}

export async function logout(): Promise<void> {
  await clearToken();
}

export async function getMe(): Promise<User> {
  return request<User>('/api/auth/me');
}

// Game API
export async function createGame(
  size: number = 5,
  mode: string = 'realtime',
  p1: number = 2,
  p2: number = 4
): Promise<GameState> {
  return request<GameState>('/api/nexus/games', {
    method: 'POST',
    body: JSON.stringify({ size, mode, p1, p2 }),
  });
}

export async function getGame(gameId: string): Promise<GameState> {
  return request<GameState>(`/api/nexus/games/${gameId}`);
}

export async function makeMove(
  gameId: string,
  row: number,
  col: number,
  stonesToRemove?: number[][],
  unblockingStones?: number[][]
): Promise<MoveResponse> {
  return request<MoveResponse>(`/api/nexus/games/${gameId}/move`, {
    method: 'POST',
    body: JSON.stringify({
      row,
      col,
      stones_to_remove: stonesToRemove,
      unblocking_stones: unblockingStones,
    }),
  });
}

export async function checkMove(
  gameId: string,
  row: number,
  col: number
): Promise<CheckMoveResult> {
  return request<CheckMoveResult>(`/api/nexus/games/${gameId}/check-move`, {
    method: 'POST',
    body: JSON.stringify({ row, col }),
  });
}

export async function getDebtResolution(
  gameId: string
): Promise<DebtResolutionInfo> {
  return request<DebtResolutionInfo>(`/api/nexus/games/${gameId}/debt-resolution`);
}

export async function getUnblockingOptions(
  gameId: string
): Promise<UnblockingOptions> {
  return request<UnblockingOptions>(`/api/nexus/games/${gameId}/unblocking-options`);
}

export async function deleteGame(gameId: string): Promise<void> {
  await request(`/api/nexus/games/${gameId}`, { method: 'DELETE' });
}

// User games
export async function getMyGames(): Promise<GameListItem[]> {
  return request<GameListItem[]>('/api/me/games');
}

// Seeks API
export async function getSeeks(): Promise<Seek[]> {
  return request<Seek[]>('/api/nexus/seeks');
}

export async function createSeek(
  mode: string,
  boardSize: number = 5,
  p1: number = 2,
  p2: number = 4
): Promise<Seek> {
  return request<Seek>('/api/nexus/seeks', {
    method: 'POST',
    body: JSON.stringify({ mode, board_size: boardSize, p1, p2 }),
  });
}

export async function getMySeek(): Promise<Seek | null> {
  return request<Seek | null>('/api/nexus/seeks/mine');
}

export async function cancelSeek(seekId: number): Promise<void> {
  await request(`/api/nexus/seeks/${seekId}`, { method: 'DELETE' });
}

export async function acceptSeek(seekId: number): Promise<GameState> {
  return request<GameState>(`/api/nexus/seeks/${seekId}/accept`, {
    method: 'POST',
  });
}

// WebSocket connection
export function createGameWebSocket(
  gameId: string,
  onMessage: (data: any) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket {
  const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
  const ws = new WebSocket(`${wsUrl}/ws/game/${gameId}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('WebSocket message parse error:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}
