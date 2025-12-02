import React from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Text,
} from 'react-native';
import Svg, { Line, Circle } from 'react-native-svg';

interface BoardProps {
  size: number;
  board: number[][];
  legalMoves: number[][];
  onCellPress: (row: number, col: number) => void;
  selectedStones?: number[][];
  selectableStones?: number[][];
  highlightLastMove?: [number, number] | null;
  disabled?: boolean;
}

const EMPTY = 0;
const BLACK = 1;
const WHITE = 2;

export default function Board({
  size,
  board,
  legalMoves,
  onCellPress,
  selectedStones = [],
  selectableStones,
  highlightLastMove,
  disabled = false,
}: BoardProps) {
  const screenWidth = Dimensions.get('window').width;
  const boardSize = Math.min(screenWidth - 32, 400);
  const cellSize = boardSize / size;
  const padding = cellSize / 2;
  const stoneRadius = cellSize * 0.42;

  const isLegalMove = (row: number, col: number) => {
    return legalMoves.some((m) => m[0] === row && m[1] === col);
  };

  const isSelected = (row: number, col: number) => {
    return selectedStones.some((s) => s[0] === row && s[1] === col);
  };

  const isSelectable = (row: number, col: number) => {
    if (!selectableStones) return false;
    return selectableStones.some((s) => s[0] === row && s[1] === col);
  };

  const isLastMove = (row: number, col: number) => {
    return highlightLastMove?.[0] === row && highlightLastMove?.[1] === col;
  };

  // Generate grid lines
  const gridLines = [];
  for (let i = 0; i < size; i++) {
    // Horizontal lines
    gridLines.push(
      <Line
        key={`h${i}`}
        x1={padding}
        y1={padding + i * cellSize}
        x2={padding + (size - 1) * cellSize}
        y2={padding + i * cellSize}
        stroke="#666"
        strokeWidth={1}
      />
    );
    // Vertical lines
    gridLines.push(
      <Line
        key={`v${i}`}
        x1={padding + i * cellSize}
        y1={padding}
        x2={padding + i * cellSize}
        y2={padding + (size - 1) * cellSize}
        stroke="#666"
        strokeWidth={1}
      />
    );
  }

  // Star points (for standard board sizes)
  const starPoints: [number, number][] = [];
  if (size >= 5) {
    const center = Math.floor(size / 2);
    starPoints.push([center, center]);
    if (size >= 7) {
      starPoints.push([2, 2], [2, size - 3], [size - 3, 2], [size - 3, size - 3]);
    }
  }

  return (
    <View style={[styles.container, { width: boardSize, height: boardSize }]}>
      {/* Grid background */}
      <View style={[styles.gridBackground, { width: boardSize, height: boardSize }]}>
        <Svg width={boardSize} height={boardSize}>
          {gridLines}
          {/* Star points */}
          {starPoints.map(([r, c], i) => (
            <Circle
              key={`star${i}`}
              cx={padding + c * cellSize}
              cy={padding + r * cellSize}
              r={3}
              fill="#666"
            />
          ))}
        </Svg>
      </View>

      {/* Interactive layer */}
      <View style={styles.interactiveLayer}>
        {board.map((row, rowIndex) =>
          row.map((cell, colIndex) => {
            const isLegal = isLegalMove(rowIndex, colIndex);
            const selected = isSelected(rowIndex, colIndex);
            const selectable = isSelectable(rowIndex, colIndex);
            const lastMove = isLastMove(rowIndex, colIndex);

            return (
              <TouchableOpacity
                key={`${rowIndex}-${colIndex}`}
                style={[
                  styles.cell,
                  {
                    width: cellSize,
                    height: cellSize,
                    left: colIndex * cellSize,
                    top: rowIndex * cellSize,
                  },
                ]}
                onPress={() => !disabled && onCellPress(rowIndex, colIndex)}
                disabled={disabled && !selectable}
                activeOpacity={0.7}
              >
                {/* Legal move indicator */}
                {cell === EMPTY && isLegal && !disabled && (
                  <View
                    style={[
                      styles.legalMoveIndicator,
                      {
                        width: stoneRadius * 0.6,
                        height: stoneRadius * 0.6,
                        borderRadius: stoneRadius * 0.3,
                      },
                    ]}
                  />
                )}

                {/* Stone */}
                {cell !== EMPTY && (
                  <View
                    style={[
                      styles.stone,
                      cell === BLACK ? styles.blackStone : styles.whiteStone,
                      {
                        width: stoneRadius * 2,
                        height: stoneRadius * 2,
                        borderRadius: stoneRadius,
                      },
                      lastMove && styles.lastMoveHighlight,
                      selected && styles.selectedStone,
                      selectable && styles.selectableStone,
                    ]}
                  />
                )}
              </TouchableOpacity>
            );
          })
        )}
      </View>

      {/* Row labels */}
      <View style={[styles.rowLabels, { height: boardSize }]}>
        {Array.from({ length: size }, (_, i) => (
          <Text key={i} style={[styles.label, { height: cellSize, lineHeight: cellSize }]}>
            {i}
          </Text>
        ))}
      </View>

      {/* Column labels */}
      <View style={[styles.colLabels, { width: boardSize }]}>
        {Array.from({ length: size }, (_, i) => (
          <Text key={i} style={[styles.label, { width: cellSize }]}>
            {i}
          </Text>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    backgroundColor: '#DEB887',
    borderRadius: 4,
  },
  gridBackground: {
    position: 'absolute',
  },
  interactiveLayer: {
    position: 'absolute',
    width: '100%',
    height: '100%',
  },
  cell: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stone: {
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 2,
    elevation: 3,
  },
  blackStone: {
    backgroundColor: '#1a1a1a',
  },
  whiteStone: {
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#ccc',
  },
  legalMoveIndicator: {
    backgroundColor: 'rgba(76, 175, 80, 0.5)',
  },
  lastMoveHighlight: {
    borderWidth: 3,
    borderColor: '#FFD700',
  },
  selectedStone: {
    borderWidth: 3,
    borderColor: '#FF4444',
  },
  selectableStone: {
    borderWidth: 2,
    borderColor: '#4444FF',
    opacity: 0.8,
  },
  rowLabels: {
    position: 'absolute',
    left: -20,
    top: 0,
    justifyContent: 'flex-start',
  },
  colLabels: {
    position: 'absolute',
    bottom: -20,
    left: 0,
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  label: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
});
