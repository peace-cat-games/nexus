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
}

export const EMPTY = 0;
export const BLACK = 1;
export const WHITE = 2;

export type CellValue = typeof EMPTY | typeof BLACK | typeof WHITE;
