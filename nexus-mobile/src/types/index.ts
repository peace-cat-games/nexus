// Game types
export interface GameState {
  game_id: string;
  size: number;
  board: number[][];
  to_move: 'BLACK' | 'WHITE';
  debt_black: number;
  debt_white: number;
  result: 'ONGOING' | 'BLACK_WIN' | 'WHITE_WIN';
  legal_moves: number[][];
  p1: number;
  p2: number;
  mode: 'realtime' | 'correspondence';
  player_black_id: number | null;
  player_black_username: string | null;
  player_white_id: number | null;
  player_white_username: string | null;
}

export interface GameListItem {
  id: string;
  player_black_id: number | null;
  player_black_username: string | null;
  player_white_id: number | null;
  player_white_username: string | null;
  mode: string;
  board_size: number;
  result: string;
  created_at: string;
  updated_at: string;
}

export interface Seek {
  id: number;
  owner_id: number;
  owner_username: string;
  mode: string;
  board_size: number;
  p1: number;
  p2: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface MoveResponse {
  success: boolean;
  game_state: GameState;
  unblocked_stones: number[][] | null;
  message: string | null;
}

export interface DebtResolutionInfo {
  player_debt: number;
  opponent_debt: number;
  net_debt: number;
  stones_to_remove: number;
  player_stones: number[][];
  can_pay: boolean;
}

export interface UnblockingOptions {
  needs_unblocking: boolean;
  options: number[][][];
  debt_per_stone: number;
  total_debt?: number;
  impossible?: boolean;
}

export interface CheckMoveResult {
  requires_debt_resolution: boolean;
  stones_to_remove: number;
  player_stones: number[][];
  would_be_bankrupt: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
