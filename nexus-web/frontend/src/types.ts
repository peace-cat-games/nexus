export interface GameState {
  game_id: string;
  size: number;
  board: number[][];
  to_move: 'BLACK' | 'WHITE';
  debt_black: number;
  debt_white: number;
  result: 'ONGOING' | 'BLACK_WIN' | 'WHITE_WIN';
  legal_moves: [number, number][];
  p1: number;
  p2: number;
  mode: 'realtime' | 'correspondence';
  player_black_id: number | null;
  player_black_username: string | null;
  player_white_id: number | null;
  player_white_username: string | null;
}

export interface MoveResponse {
  success: boolean;
  game_state: GameState;
  unblocked_stones: [number, number][] | null;
  message: string | null;
}

export interface NewGameOptions {
  size: number;
  p1: number;
  p2: number;
  mode?: 'realtime' | 'correspondence';
}

export interface CheckMoveResponse {
  requires_debt_resolution: boolean;
  stones_to_remove: number;
  player_stones: [number, number][];
  would_be_bankrupt: boolean;
}

export interface DebtResolutionState {
  pendingMove: [number, number];
  stonesToRemove: number;
  playerStones: [number, number][];
  selectedStones: [number, number][];
  wouldBeBankrupt: boolean;
}

export interface UnblockingOptionsResponse {
  needs_unblocking: boolean;
  options: [number, number][][];
  debt_per_stone: number;
  total_debt?: number;
  impossible?: boolean;
}

export interface UnblockingState {
  options: [number, number][][];
  selectedOption: number | null;
  totalDebt: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface Seek {
  id: number;
  owner_id: number;
  owner_username: string;
  mode: 'realtime' | 'correspondence';
  board_size: number;
  p1: number;
  p2: number;
}

export interface GameListItem {
  id: string;
  player_black_id: number | null;
  player_black_username: string | null;
  player_white_id: number | null;
  player_white_username: string | null;
  mode: 'realtime' | 'correspondence';
  board_size: number;
  result: 'ongoing' | 'black_win' | 'white_win';
  created_at: string;
  updated_at: string;
}

export const EMPTY = 0;
export const BLACK = 1;
export const WHITE = 2;

export type CellValue = typeof EMPTY | typeof BLACK | typeof WHITE;
