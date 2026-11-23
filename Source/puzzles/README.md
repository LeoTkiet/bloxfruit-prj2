# Griductive Puzzle Dataset & JSON Schema (Owned by TV1)

This directory contains the official Griductive puzzle dataset for development, testing, GUI demonstration, and benchmarking.

## Dataset Summary (15 Puzzles)

| Folder | Count | Description |
| :--- | :---: | :--- |
| `3x3/` | 4 | Core 3×3 puzzles covering all 6 core clue templates and 4 core regions (easy → hard). |
| `4x4/` | 4 | Core 4×4 puzzles with progressive multi-wave deductions and richer region constraints. |
| `5x5/` | 2 | 5×5 stress-case puzzles (25 characters) for scalability & CNF/DPLL heuristic benchmarks. |
| `extensions/` | 3 | Puzzles exercising Extension 1 (Advanced Regions), Extension 2 (`PARITY`), and Extension 3 (`COMPARE_COUNTS`). |
| `edge_cases/` | 2 | Adversarial test cases: `AMBIGUOUS` (must return `UNKNOWN`, never guess) and `INCONSISTENT` (`KB_0` is UNSAT). |

Every solvable puzzle in `3x3/`, `4x4/`, `5x5/`, and `extensions/` is mathematically verified to satisfy:
1. **Truthfulness**: Every clue (initial and hidden) evaluates to `True` under the puzzle's hidden solution.
2. **Uniqueness**: The full clue set admits **exactly one** complete Criminal/Innocent assignment.
3. **No-Guess Solvability**: Starting from `initial_revealed`, strict logical entailment progressively proves all $N^2$ characters without ever guessing.
4. **Alphabetical Characters**: Display names are ordered alphabetically in row-major order (`A1, B1, ..., EN`).

## JSON Schema Specification

```json
{
  "puzzle_id": "3x3_01",
  "name": "3x3 Puzzle 1 - Precinct Basics",
  "difficulty": "easy",
  "grid_size": 3,
  "initial_revealed": ["A1", "C3"],
  "tags": ["3x3", "core"],
  "expected_status": "SOLVABLE",
  "characters": [
    {
      "cell_id": "A1",
      "name": "Abel",
      "profession": "Astronaut",
      "status": "INNOCENT",
      "clue": {
        "clue_id": "clue_A1",
        "type": "EXACTLY",
        "region": { "type": "ROW", "row": 1 },
        "count": 1,
        "text": "Exactly 1 Criminal in row 1."
      }
    }
  ]
}
```

### Supported Region Types (`region.type`)

| Type | Required Fields | Meaning |
| :--- | :--- | :--- |
| `ROW` | `row` (int `1..N`) | All cells in row `row`. |
| `COL` | `col` (str `"A".."Z"`) | All cells in column `col`. |
| `NEIGHBORS` | `center` (`CellID`) | Up to 8 orthogonal/diagonal neighbors of `center` (excluding `center`). |
| `EXPLICIT` | `cells` (`list[CellID]`) | Explicit list of distinct cells. |
| `CORNERS` *(Ext 1)* | *(none)* | The 4 corner cells of the $N \times N$ grid. |
| `BOUNDARY` *(Ext 1)* | *(none)* | All outer perimeter cells of the $N \times N$ grid. |
| `COMMON_NEIGHBORS` *(Ext 1)* | `cells` (`[c1, c2]`) | Cells neighboring both `c1` and `c2`. |
| `BETWEEN` *(Ext 1)* | `cells` (`[c1, c2]`) | Cells strictly between `c1` and `c2` along a shared row or column. |
| `INTERSECTION` *(Ext 1)* | `sub_regions` (`list[Region]`) | Intersection of 2 or more regions. |

### Supported Clue Types (`clue.type`)

| Type | Required Fields | Logical Content |
| :--- | :--- | :--- |
| `FACT` | `target`, `target_status` (`CRIMINAL`\|`INNOCENT`) | $C_i$ or $\neg C_i$ |
| `SAME` | `targets` (`[c1, c2]`) | $C_i \leftrightarrow C_j$ |
| `DIFFERENT` | `targets` (`[c1, c2]`) | $C_i \oplus C_j$ |
| `EXACTLY` (or alias `NO`) | `region`, `count` (`0 <= k <= |R|`) | $\sum_{i \in R} C_i = k$ (`NO` normalizes to `EXACTLY`, `count=0`) |
| `AT_LEAST` | `region`, `count` | $\sum_{i \in R} C_i \ge k$ |
| `AT_MOST` | `region`, `count` | $\sum_{i \in R} C_i \le k$ |
| `PARITY` *(Ext 2)* | `region`, `parity` (`EVEN`\|`ODD`) | $\sum_{i \in R} C_i \equiv p \pmod 2$ |
| `COMPARE_COUNTS` *(Ext 3)* | `region`, `region_b`, `compare_op` (`EQ`\|`LT`\|`GT`\|`LE`\|`GE`) | $\sum_{i \in R_1} C_i \;\text{op}\; \sum_{j \in R_2} C_j$ |

## Validating Puzzles via CLI

```bash
python -m engine.puzzle_validator Source/puzzles
```
