import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import Board from '../components/Board';
import * as api from '../api/client';
import { GameState, CheckMoveResult, UnblockingOptions } from '../types';

type GameMode = 'normal' | 'debt_resolution' | 'unblocking_selection';

export default function GameScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const { gameId } = route.params as { gameId: string };
  const { user } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);

  const [gameState, setGameState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Game interaction state
  const [mode, setMode] = useState<GameMode>('normal');
  const [pendingMove, setPendingMove] = useState<[number, number] | null>(null);
  const [debtInfo, setDebtInfo] = useState<CheckMoveResult | null>(null);
  const [selectedStones, setSelectedStones] = useState<number[][]>([]);
  const [unblockingOptions, setUnblockingOptions] = useState<UnblockingOptions | null>(null);

  // Load game state
  const loadGame = useCallback(async () => {
    try {
      const data = await api.getGame(gameId);
      setGameState(data);
      setError(null);

      // Check for forced unblocking
      if (data.result === 'ONGOING' && data.legal_moves.length === 0 && isMyTurn(data)) {
        const options = await api.getUnblockingOptions(gameId);
        if (options.needs_unblocking && !options.impossible) {
          setUnblockingOptions(options);
          setMode('unblocking_selection');
        }
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load game');
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  // WebSocket connection
  useEffect(() => {
    loadGame();

    // Connect to WebSocket for realtime updates
    wsRef.current = api.createGameWebSocket(
      gameId,
      (data) => {
        if (data.type === 'game_update' && data.game_state) {
          setGameState(data.game_state);
        }
      },
      () => console.log('WebSocket error'),
      () => console.log('WebSocket closed')
    );

    return () => {
      wsRef.current?.close();
    };
  }, [gameId, loadGame]);

  // Periodic refresh for correspondence games
  useEffect(() => {
    if (gameState?.mode === 'correspondence') {
      const interval = setInterval(loadGame, 10000);
      return () => clearInterval(interval);
    }
  }, [gameState?.mode, loadGame]);

  function isMyTurn(state: GameState = gameState!): boolean {
    if (!state || !user) return false;
    if (state.to_move === 'BLACK' && state.player_black_id === user.id) return true;
    if (state.to_move === 'WHITE' && state.player_white_id === user.id) return true;
    return false;
  }

  function getMyColor(): 'BLACK' | 'WHITE' | null {
    if (!gameState || !user) return null;
    if (gameState.player_black_id === user.id) return 'BLACK';
    if (gameState.player_white_id === user.id) return 'WHITE';
    return null;
  }

  async function handleCellPress(row: number, col: number) {
    if (!gameState || gameState.result !== 'ONGOING') return;

    // Handle different modes
    if (mode === 'debt_resolution') {
      handleDebtStoneSelection(row, col);
      return;
    }

    if (mode === 'unblocking_selection') {
      // In unblocking mode, we select an option, then make a move
      // First click selects unblocking option, subsequent clicks are the move
      return;
    }

    // Normal mode - check if legal move
    if (!isMyTurn()) {
      Alert.alert('Not your turn', 'Wait for your opponent to move.');
      return;
    }

    const isLegal = gameState.legal_moves.some(
      (m) => m[0] === row && m[1] === col
    );

    if (!isLegal) {
      return;
    }

    // Check if move triggers debt resolution
    try {
      const checkResult = await api.checkMove(gameId, row, col);
      if (checkResult.requires_debt_resolution && checkResult.stones_to_remove > 0) {
        setPendingMove([row, col]);
        setDebtInfo(checkResult);
        setSelectedStones([]);
        setMode('debt_resolution');

        if (checkResult.would_be_bankrupt) {
          Alert.alert(
            'Warning',
            `This move will cause bankruptcy! You need ${checkResult.stones_to_remove} stones but only have ${checkResult.player_stones.length}.`,
            [
              { text: 'Cancel', style: 'cancel', onPress: () => resetMode() },
              { text: 'Play Anyway', onPress: () => makeMove(row, col) },
            ]
          );
        }
        return;
      }

      // Make the move directly
      await makeMove(row, col);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to make move');
    }
  }

  function handleDebtStoneSelection(row: number, col: number) {
    if (!debtInfo) return;

    const stone = [row, col];
    const isPlayerStone = debtInfo.player_stones.some(
      (s) => s[0] === row && s[1] === col
    );

    if (!isPlayerStone) return;

    const isSelected = selectedStones.some(
      (s) => s[0] === row && s[1] === col
    );

    if (isSelected) {
      setSelectedStones(selectedStones.filter((s) => !(s[0] === row && s[1] === col)));
    } else if (selectedStones.length < debtInfo.stones_to_remove) {
      setSelectedStones([...selectedStones, stone]);
    }
  }

  function selectUnblockingOption(option: number[][]) {
    setSelectedStones(option);
  }

  async function confirmUnblocking() {
    if (!selectedStones.length || !unblockingOptions) return;

    // After unblocking, we need to select a move
    // For simplicity, auto-refresh and let user pick
    try {
      // The move will be made with unblocking stones
      // For now, we store the selection and wait for move
      setMode('normal');
      Alert.alert('Select Move', 'Now select where to place your stone.');
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  }

  async function confirmDebtResolution() {
    if (!pendingMove || !debtInfo) return;
    if (selectedStones.length !== debtInfo.stones_to_remove) {
      Alert.alert('Error', `Select exactly ${debtInfo.stones_to_remove} stones to remove.`);
      return;
    }

    await makeMove(pendingMove[0], pendingMove[1], selectedStones);
  }

  async function makeMove(
    row: number,
    col: number,
    stonesToRemove?: number[][],
    unblockingStones?: number[][]
  ) {
    try {
      const unblockers = mode === 'unblocking_selection' ? selectedStones : unblockingStones;
      const result = await api.makeMove(gameId, row, col, stonesToRemove, unblockers);

      if (result.success) {
        setGameState(result.game_state);
      } else {
        Alert.alert('Move Failed', result.message || 'Unknown error');
      }

      resetMode();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to make move');
      resetMode();
    }
  }

  function resetMode() {
    setMode('normal');
    setPendingMove(null);
    setDebtInfo(null);
    setSelectedStones([]);
    setUnblockingOptions(null);
  }

  function getStatusText(): string {
    if (!gameState) return 'Loading...';

    if (gameState.result === 'BLACK_WIN') return 'Black wins!';
    if (gameState.result === 'WHITE_WIN') return 'White wins!';

    if (mode === 'debt_resolution') {
      return `Select ${debtInfo?.stones_to_remove} stones to remove`;
    }

    if (mode === 'unblocking_selection') {
      return 'Select unblocking option';
    }

    return isMyTurn() ? 'Your turn' : "Opponent's turn";
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4a90d9" />
      </View>
    );
  }

  if (error || !gameState) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error || 'Failed to load game'}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadGame}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const myColor = getMyColor();
  const isOver = gameState.result !== 'ONGOING';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Game Info Header */}
      <View style={styles.header}>
        <View style={styles.playerInfo}>
          <View style={[styles.colorIndicator, styles.blackIndicator]} />
          <Text style={styles.playerName}>
            {gameState.player_black_username || 'Black'}
            {myColor === 'BLACK' && ' (You)'}
          </Text>
          <Text style={styles.debtText}>Debt: {gameState.debt_black}</Text>
        </View>

        <Text style={styles.vs}>vs</Text>

        <View style={styles.playerInfo}>
          <View style={[styles.colorIndicator, styles.whiteIndicator]} />
          <Text style={styles.playerName}>
            {gameState.player_white_username || 'White'}
            {myColor === 'WHITE' && ' (You)'}
          </Text>
          <Text style={styles.debtText}>Debt: {gameState.debt_white}</Text>
        </View>
      </View>

      {/* Status */}
      <View style={[styles.statusBar, isOver && styles.statusBarOver]}>
        <Text style={styles.statusText}>{getStatusText()}</Text>
      </View>

      {/* Board */}
      <View style={styles.boardContainer}>
        <Board
          size={gameState.size}
          board={gameState.board}
          legalMoves={mode === 'normal' && isMyTurn() ? gameState.legal_moves : []}
          onCellPress={handleCellPress}
          selectedStones={selectedStones}
          selectableStones={
            mode === 'debt_resolution' ? debtInfo?.player_stones : undefined
          }
          disabled={isOver || !isMyTurn() || mode !== 'normal'}
        />
      </View>

      {/* Unblocking Options */}
      {mode === 'unblocking_selection' && unblockingOptions && (
        <View style={styles.optionsContainer}>
          <Text style={styles.optionsTitle}>
            Select stones to remove (costs {unblockingOptions.total_debt} debt):
          </Text>
          {unblockingOptions.options.map((option, i) => (
            <TouchableOpacity
              key={i}
              style={[
                styles.optionButton,
                JSON.stringify(selectedStones) === JSON.stringify(option) &&
                  styles.optionButtonSelected,
              ]}
              onPress={() => selectUnblockingOption(option)}
            >
              <Text style={styles.optionText}>
                Option {i + 1}: {option.map((s) => `(${s[0]},${s[1]})`).join(', ')}
              </Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            style={[styles.confirmButton, !selectedStones.length && styles.confirmButtonDisabled]}
            onPress={confirmUnblocking}
            disabled={!selectedStones.length}
          >
            <Text style={styles.confirmButtonText}>Confirm Selection</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Debt Resolution */}
      {mode === 'debt_resolution' && debtInfo && (
        <View style={styles.debtContainer}>
          <Text style={styles.debtTitle}>
            Debt Resolution: Remove {debtInfo.stones_to_remove} stones
          </Text>
          <Text style={styles.debtSubtitle}>
            Selected: {selectedStones.length} / {debtInfo.stones_to_remove}
          </Text>
          <View style={styles.debtButtons}>
            <TouchableOpacity style={styles.cancelButton} onPress={resetMode}>
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.confirmButton,
                selectedStones.length !== debtInfo.stones_to_remove &&
                  styles.confirmButtonDisabled,
              ]}
              onPress={confirmDebtResolution}
              disabled={selectedStones.length !== debtInfo.stones_to_remove}
            >
              <Text style={styles.confirmButtonText}>Confirm Move</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Game Over Actions */}
      {isOver && (
        <View style={styles.gameOverContainer}>
          <Text style={styles.gameOverText}>
            {gameState.result === 'BLACK_WIN' ? 'Black' : 'White'} wins!
            {((gameState.result === 'BLACK_WIN' && myColor === 'BLACK') ||
              (gameState.result === 'WHITE_WIN' && myColor === 'WHITE')) &&
              ' Congratulations!'}
          </Text>
          <TouchableOpacity
            style={styles.newGameButton}
            onPress={() => navigation.navigate('Lobby')}
          >
            <Text style={styles.newGameButtonText}>Back to Lobby</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  content: {
    padding: 16,
    alignItems: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a2e',
    padding: 24,
  },
  errorText: {
    color: '#d94a4a',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#4a90d9',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 16,
  },
  playerInfo: {
    alignItems: 'center',
    flex: 1,
  },
  colorIndicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
    marginBottom: 4,
  },
  blackIndicator: {
    backgroundColor: '#1a1a1a',
    borderWidth: 2,
    borderColor: '#666',
  },
  whiteIndicator: {
    backgroundColor: '#f5f5f5',
  },
  playerName: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  debtText: {
    color: '#d94a4a',
    fontSize: 12,
    marginTop: 2,
  },
  vs: {
    color: '#666',
    fontSize: 16,
    marginHorizontal: 16,
  },
  statusBar: {
    backgroundColor: '#2a2a3e',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 16,
  },
  statusBarOver: {
    backgroundColor: '#3a3a4e',
  },
  statusText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  boardContainer: {
    marginVertical: 16,
    paddingLeft: 20,
    paddingBottom: 20,
  },
  optionsContainer: {
    width: '100%',
    backgroundColor: '#2a2a3e',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  optionsTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  optionButton: {
    backgroundColor: '#3a3a4e',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  optionButtonSelected: {
    backgroundColor: '#4a90d9',
  },
  optionText: {
    color: '#fff',
    fontSize: 14,
  },
  confirmButton: {
    backgroundColor: '#4ad94a',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  confirmButtonDisabled: {
    opacity: 0.5,
  },
  confirmButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  debtContainer: {
    width: '100%',
    backgroundColor: '#2a2a3e',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  debtTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  debtSubtitle: {
    color: '#999',
    fontSize: 14,
    marginBottom: 16,
  },
  debtButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#3a3a4e',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  gameOverContainer: {
    width: '100%',
    alignItems: 'center',
    marginTop: 24,
  },
  gameOverText: {
    color: '#4ad94a',
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  newGameButton: {
    backgroundColor: '#4a90d9',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 8,
  },
  newGameButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
