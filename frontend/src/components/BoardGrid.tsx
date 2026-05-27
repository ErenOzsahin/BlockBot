import type { MoveResponse } from "../api/analyze";

interface Props {
  board: number[][];
  bestMove?: MoveResponse | null;
  pieceShape?: number[][] | null;
}

function rotateShape(shape: number[][], times: number): number[][] {
  let s = shape.map((r) => [...r]);
  for (let t = 0; t < times % 4; t++) {
    s = s[0].map((_, col) => s.map((row) => row[col]).reverse());
  }
  return s;
}

export function BoardGrid({ board, bestMove, pieceShape }: Props) {
  const hintCells = new Set<string>();
  if (bestMove && pieceShape) {
    const rotated = rotateShape(pieceShape, bestMove.rotation);
    for (let i = 0; i < rotated.length; i++) {
      for (let j = 0; j < rotated[i].length; j++) {
        if (rotated[i][j]) {
          hintCells.add(`${bestMove.row + i},${bestMove.col + j}`);
        }
      }
    }
  }

  return (
    <div className="board-grid" role="grid" aria-label="8x8 tahta">
      {board.map((row, ri) =>
        row.map((cell, ci) => {
          const isHint = hintCells.has(`${ri},${ci}`);
          const filled = cell === 1;
          return (
            <div
              key={`${ri}-${ci}`}
              className={`cell ${filled ? "filled" : "empty"} ${isHint ? "hint" : ""}`}
            />
          );
        })
      )}
    </div>
  );
}
