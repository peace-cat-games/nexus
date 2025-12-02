import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';

export default function RulesScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Nexus Rules</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Overview</Text>
        <Text style={styles.text}>
          Nexus is a two-player strategy game played on an n×n grid. It combines Go-style captures with Tic-Tac-Toe line completion and an economic debt system.
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Basic Play</Text>
        <Text style={styles.text}>
          • Players alternate placing stones (Black moves first){'\n'}
          • Stones are placed on grid intersections{'\n'}
          • The goal is to complete a full line (row, column, or main diagonal)
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Captures & Debt</Text>
        <Text style={styles.text}>
          • Groups with no liberties (empty adjacent points) are captured{'\n'}
          • Capturing stones adds debt to the capturing player{'\n'}
          • Each captured stone = 2 debt (p1 parameter){'\n'}
          • Suicide moves are illegal unless they capture opponent stones
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Line Completion</Text>
        <Text style={styles.text}>
          When you complete a line:{'\n\n'}
          1. Calculate net debt = your debt - opponent's debt{'\n\n'}
          2. If net debt ≤ 0: You win instantly!{'\n\n'}
          3. If net debt {'>'} 0: You must remove that many of your own stones:{'\n'}
             • If you can't (not enough stones): Bankruptcy = you lose{'\n'}
             • After removal, if line still complete: You win{'\n'}
             • If line broken: Game continues, debts reset to 0
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Forced Unblocking</Text>
        <Text style={styles.text}>
          If you have no legal moves:{'\n\n'}
          • You must remove minimum opponent stones to create a legal move{'\n'}
          • Each removed stone adds 4 debt (p2 parameter){'\n'}
          • If unblocking is impossible: You lose
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Ko Rule</Text>
        <Text style={styles.text}>
          Repeating a previous board position + debt difference is forbidden. This prevents infinite capture loops.
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Parameters</Text>
        <Text style={styles.text}>
          • Board size: 3×3, 5×5, 7×7, or 9×9{'\n'}
          • p1 = 2: Debt per captured stone{'\n'}
          • p2 = 4: Debt per forced unblock stone
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Tips</Text>
        <Text style={styles.text}>
          • Capturing is a double-edged sword - it adds debt{'\n'}
          • Sometimes letting opponent capture is advantageous{'\n'}
          • Plan your line completions carefully{'\n'}
          • Watch your debt vs opponent's debt
        </Text>
      </View>
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
    paddingBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 24,
    textAlign: 'center',
  },
  section: {
    backgroundColor: '#2a2a3e',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#4a90d9',
    marginBottom: 12,
  },
  text: {
    fontSize: 15,
    color: '#ccc',
    lineHeight: 24,
  },
});
