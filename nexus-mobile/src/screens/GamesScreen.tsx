import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import * as api from '../api/client';
import { GameListItem } from '../types';

export default function GamesScreen() {
  const navigation = useNavigation<any>();
  const { user } = useAuth();
  const [games, setGames] = useState<GameListItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadGames = useCallback(async () => {
    try {
      const data = await api.getMyGames();
      setGames(data);
    } catch (error) {
      console.error('Failed to load games:', error);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadGames();
    }, [loadGames])
  );

  async function handleRefresh() {
    setRefreshing(true);
    await loadGames();
    setRefreshing(false);
  }

  function getOpponent(game: GameListItem): string {
    if (game.player_black_id === user?.id) {
      return game.player_white_username || 'Waiting...';
    }
    return game.player_black_username || 'Waiting...';
  }

  function getMyColor(game: GameListItem): 'BLACK' | 'WHITE' {
    return game.player_black_id === user?.id ? 'BLACK' : 'WHITE';
  }

  function getResultText(game: GameListItem): string {
    if (game.result === 'ongoing') return 'In Progress';
    const myColor = getMyColor(game);
    const iWon =
      (game.result === 'black_win' && myColor === 'BLACK') ||
      (game.result === 'white_win' && myColor === 'WHITE');
    return iWon ? 'Victory' : 'Defeat';
  }

  function getResultStyle(game: GameListItem) {
    if (game.result === 'ongoing') return styles.resultOngoing;
    const myColor = getMyColor(game);
    const iWon =
      (game.result === 'black_win' && myColor === 'BLACK') ||
      (game.result === 'white_win' && myColor === 'WHITE');
    return iWon ? styles.resultWin : styles.resultLoss;
  }

  const ongoingGames = games.filter((g) => g.result === 'ongoing');
  const finishedGames = games.filter((g) => g.result !== 'ongoing');

  function renderGame({ item }: { item: GameListItem }) {
    const myColor = getMyColor(item);

    return (
      <TouchableOpacity
        style={styles.gameCard}
        onPress={() => navigation.navigate('Game', { gameId: item.id })}
      >
        <View style={styles.gameHeader}>
          <View style={styles.opponentInfo}>
            <Text style={styles.vsText}>vs</Text>
            <Text style={styles.opponentName}>{getOpponent(item)}</Text>
          </View>
          <View style={[styles.resultBadge, getResultStyle(item)]}>
            <Text style={styles.resultText}>{getResultText(item)}</Text>
          </View>
        </View>

        <View style={styles.gameDetails}>
          <View style={styles.detailItem}>
            <View style={[styles.colorDot, myColor === 'BLACK' ? styles.blackDot : styles.whiteDot]} />
            <Text style={styles.detailText}>Playing as {myColor}</Text>
          </View>
          <Text style={styles.detailText}>{item.board_size}x{item.board_size}</Text>
          <View style={[styles.modeBadge, item.mode === 'realtime' ? styles.realtimeBadge : styles.corrBadge]}>
            <Text style={styles.modeText}>
              {item.mode === 'realtime' ? 'RT' : 'Corr'}
            </Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  }

  function renderSection(title: string, data: GameListItem[]) {
    if (data.length === 0) return null;
    return (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {data.map((game) => (
          <View key={game.id}>{renderGame({ item: game })}</View>
        ))}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={[]}
        renderItem={() => null}
        ListHeaderComponent={
          <>
            {renderSection('Your Turn', ongoingGames)}
            {renderSection('Completed', finishedGames)}
            {games.length === 0 && (
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>No games yet</Text>
                <Text style={styles.emptySubtext}>Go to Play to start a game</Text>
              </View>
            )}
          </>
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor="#4a90d9"
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '600',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  gameCard: {
    backgroundColor: '#2a2a3e',
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 12,
  },
  gameHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  opponentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  vsText: {
    color: '#666',
    fontSize: 14,
  },
  opponentName: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  resultBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  resultOngoing: {
    backgroundColor: '#4a90d9',
  },
  resultWin: {
    backgroundColor: '#4ad94a',
  },
  resultLoss: {
    backgroundColor: '#d94a4a',
  },
  resultText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  gameDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  colorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  blackDot: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#666',
  },
  whiteDot: {
    backgroundColor: '#f5f5f5',
  },
  detailText: {
    color: '#999',
    fontSize: 14,
  },
  modeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  realtimeBadge: {
    backgroundColor: 'rgba(74, 144, 217, 0.3)',
  },
  corrBadge: {
    backgroundColor: 'rgba(106, 74, 217, 0.3)',
  },
  modeText: {
    color: '#999',
    fontSize: 12,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    color: '#666',
    fontSize: 18,
  },
  emptySubtext: {
    color: '#555',
    fontSize: 14,
    marginTop: 8,
  },
});
