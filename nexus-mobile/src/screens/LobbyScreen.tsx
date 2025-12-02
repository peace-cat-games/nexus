import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Alert,
  Modal,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import * as api from '../api/client';
import { Seek } from '../types';

export default function LobbyScreen() {
  const navigation = useNavigation<any>();
  const { user } = useAuth();
  const [seeks, setSeeks] = useState<Seek[]>([]);
  const [mySeek, setMySeek] = useState<Seek | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createMode, setCreateMode] = useState<'realtime' | 'correspondence'>('realtime');
  const [createSize, setCreateSize] = useState(5);

  const loadData = useCallback(async () => {
    try {
      const [seeksData, mySeekData] = await Promise.all([
        api.getSeeks(),
        api.getMySeek(),
      ]);
      setSeeks(seeksData);
      setMySeek(mySeekData);
    } catch (error) {
      console.error('Failed to load lobby data:', error);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadData();
      const interval = setInterval(loadData, 5000);
      return () => clearInterval(interval);
    }, [loadData])
  );

  async function handleRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  async function handleCreateSeek() {
    try {
      await api.createSeek(createMode, createSize);
      setShowCreateModal(false);
      await loadData();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create game');
    }
  }

  async function handleCancelSeek() {
    if (!mySeek) return;
    try {
      await api.cancelSeek(mySeek.id);
      setMySeek(null);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to cancel');
    }
  }

  async function handleAcceptSeek(seek: Seek) {
    try {
      const game = await api.acceptSeek(seek.id);
      navigation.navigate('Game', { gameId: game.game_id });
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to accept game');
      await loadData();
    }
  }

  function renderSeek({ item }: { item: Seek }) {
    return (
      <TouchableOpacity
        style={styles.seekCard}
        onPress={() => handleAcceptSeek(item)}
      >
        <View style={styles.seekHeader}>
          <Text style={styles.seekUsername}>{item.owner_username}</Text>
          <View style={[styles.modeBadge, item.mode === 'realtime' ? styles.realtimeBadge : styles.corrBadge]}>
            <Text style={styles.modeText}>
              {item.mode === 'realtime' ? 'Realtime' : 'Correspondence'}
            </Text>
          </View>
        </View>
        <Text style={styles.seekDetails}>
          {item.board_size}x{item.board_size} board
        </Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.container}>
      {/* My Seek Status */}
      {mySeek && (
        <View style={styles.mySeekBanner}>
          <View>
            <Text style={styles.mySeekText}>Waiting for opponent...</Text>
            <Text style={styles.mySeekDetails}>
              {mySeek.mode === 'realtime' ? 'Realtime' : 'Correspondence'} - {mySeek.board_size}x{mySeek.board_size}
            </Text>
          </View>
          <TouchableOpacity style={styles.cancelButton} onPress={handleCancelSeek}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Create Game Button */}
      {!mySeek && (
        <TouchableOpacity
          style={styles.createButton}
          onPress={() => setShowCreateModal(true)}
        >
          <Text style={styles.createButtonText}>+ Create Game</Text>
        </TouchableOpacity>
      )}

      {/* Available Seeks */}
      <Text style={styles.sectionTitle}>Available Games</Text>
      <FlatList
        data={seeks}
        renderItem={renderSeek}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor="#4a90d9"
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No games available</Text>
            <Text style={styles.emptySubtext}>Create one or wait for others</Text>
          </View>
        }
        contentContainerStyle={seeks.length === 0 ? styles.emptyList : undefined}
      />

      {/* Create Game Modal */}
      <Modal
        visible={showCreateModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowCreateModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Create Game</Text>

            <Text style={styles.modalLabel}>Mode</Text>
            <View style={styles.modeSelector}>
              <TouchableOpacity
                style={[styles.modeOption, createMode === 'realtime' && styles.modeOptionSelected]}
                onPress={() => setCreateMode('realtime')}
              >
                <Text style={[styles.modeOptionText, createMode === 'realtime' && styles.modeOptionTextSelected]}>
                  Realtime
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modeOption, createMode === 'correspondence' && styles.modeOptionSelected]}
                onPress={() => setCreateMode('correspondence')}
              >
                <Text style={[styles.modeOptionText, createMode === 'correspondence' && styles.modeOptionTextSelected]}>
                  Correspondence
                </Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.modalLabel}>Board Size</Text>
            <View style={styles.sizeSelector}>
              {[3, 5, 7, 9].map((size) => (
                <TouchableOpacity
                  key={size}
                  style={[styles.sizeOption, createSize === size && styles.sizeOptionSelected]}
                  onPress={() => setCreateSize(size)}
                >
                  <Text style={[styles.sizeOptionText, createSize === size && styles.sizeOptionTextSelected]}>
                    {size}x{size}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setShowCreateModal(false)}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalCreateButton} onPress={handleCreateSeek}>
                <Text style={styles.modalCreateText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  mySeekBanner: {
    backgroundColor: '#2a3a4e',
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  mySeekText: {
    color: '#4a90d9',
    fontSize: 16,
    fontWeight: '600',
  },
  mySeekDetails: {
    color: '#999',
    fontSize: 14,
    marginTop: 4,
  },
  cancelButton: {
    backgroundColor: '#d94a4a',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  cancelButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  createButton: {
    backgroundColor: '#4a90d9',
    margin: 16,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  createButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  sectionTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '600',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  seekCard: {
    backgroundColor: '#2a2a3e',
    marginHorizontal: 16,
    marginVertical: 6,
    padding: 16,
    borderRadius: 12,
  },
  seekHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  seekUsername: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  modeBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  realtimeBadge: {
    backgroundColor: '#4a90d9',
  },
  corrBadge: {
    backgroundColor: '#6a4ad9',
  },
  modeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  seekDetails: {
    color: '#999',
    marginTop: 8,
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
  emptyList: {
    flex: 1,
    justifyContent: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#2a2a3e',
    borderRadius: 16,
    padding: 24,
    width: '85%',
    maxWidth: 400,
  },
  modalTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 24,
  },
  modalLabel: {
    color: '#999',
    fontSize: 14,
    marginBottom: 8,
  },
  modeSelector: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  modeOption: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#3a3a4e',
    alignItems: 'center',
  },
  modeOptionSelected: {
    borderColor: '#4a90d9',
    backgroundColor: 'rgba(74, 144, 217, 0.2)',
  },
  modeOptionText: {
    color: '#999',
    fontWeight: '500',
  },
  modeOptionTextSelected: {
    color: '#4a90d9',
  },
  sizeSelector: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 24,
  },
  sizeOption: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#3a3a4e',
    alignItems: 'center',
  },
  sizeOptionSelected: {
    borderColor: '#4a90d9',
    backgroundColor: 'rgba(74, 144, 217, 0.2)',
  },
  sizeOptionText: {
    color: '#999',
    fontWeight: '500',
  },
  sizeOptionTextSelected: {
    color: '#4a90d9',
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  modalCancelButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#3a3a4e',
    alignItems: 'center',
  },
  modalCancelText: {
    color: '#999',
    fontWeight: '600',
  },
  modalCreateButton: {
    flex: 1,
    padding: 14,
    borderRadius: 8,
    backgroundColor: '#4a90d9',
    alignItems: 'center',
  },
  modalCreateText: {
    color: '#fff',
    fontWeight: '600',
  },
});
