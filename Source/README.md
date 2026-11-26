# Griductive Solver — CSC14003 (Introduction to Artificial Intelligence)

No-Guess Grid-Deduction AI Solver built with **Propositional Logic**, automatic **CNF Encoding**, a pure-Python **DPLL SAT Solver**, a **Deductive Logic Agent**, and a **PyQt6 Desktop GUI**.

---

## 1. Prerequisites & Installation

- **Python:** 3.10 – 3.12 (recommended)

Create a clean virtual environment and install dependencies from `Source/requirements.txt`:

```bash
# From the repository root (or inside Source/)
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r Source/requirements.txt
```

---

## 2. Running the GUI Application

Launch from inside `Source/`:

```bash
cd Source
python main.py
```

Or from the repository root:

```bash
python Source/main.py
```

### Optional CLI Arguments

| Flag | Values | Default | Description |
|---|---|---|---|
| `--puzzle <path>` | Path to `.json` | First puzzle in `puzzles/` | Load a specific puzzle on startup |
| `--encoding` | `direct`, `sinz` | `direct` | Cardinality CNF encoding strategy |
| `--heuristic` | `lexicographic`, `moms`, `jw` | `moms` | DPLL variable selection heuristic |
| `--no-pure-literal` | flag | enabled | Disable Pure-Literal Elimination |
| `--no-model-cache` | flag | enabled | Disable Agent Model Caching |
| `--strict` | flag | disabled | Require all 5 production modules to be present |

Example:

```bash
python Source/main.py --puzzle Source/puzzles/5x5/5x5_01_grand_precinct.json --encoding sinz --heuristic moms
```

---

## 3. GUI Controls & Keyboard Shortcuts

- **Click a face-down card** to select it, then click **Mark CRIMINAL** (`C`) or **Mark INNOCENT** (`I`).
  - Only **logically entailed** verdicts are accepted (`ACCEPTED`).
  - Unprovable guesses (`NOT_PROVABLE`) and wrong guesses (`CONTRADICTED`) are rejected cleanly with distinct banners without flipping the card or leaking hidden clues.
- **Click any revealed card** to highlight all cells referenced or counted by its clue (`REF` indicator). Click again or press `Esc` to clear.
- **Load:** Open any Griductive JSON puzzle file (or pick quickly from the top dropdown).
- **Restart (`R`):** Reset the active puzzle to step 0 and clear agent caches/metrics.
- **Hint (`H`):** Ask the Logic Agent for a provable next character and highlight its supporting clues (strictly from public knowledge).
- **Auto Solve:** Run the no-guess Deductive Logic Agent with configurable playback speed (`Normal 450 ms`, `Slow 900 ms`, `Instant 0 ms`) while inspecting live **Deduction Trace**, **CNF Stats**, and **SAT Metrics**.
- **Uniqueness:** Verify whether the full puzzle clue set admits a unique solution (`UNIQUE` / `MULTIPLE` / `UNSAT`).

---

## 4. Running Automated Tests

Run the entire `pytest` suite from the repository root:

```bash
# Headless GUI tests work automatically with QT_QPA_PLATFORM=offscreen
# PowerShell:
$env:QT_QPA_PLATFORM="offscreen"; pytest

# Bash:
# QT_QPA_PLATFORM=offscreen pytest
```

Run only GUI tests:

```bash
$env:QT_QPA_PLATFORM="offscreen"; pytest Source/tests/test_gui
```

---

## 5. Running Experiments & Benchmarks (TV4)

Once all modules are integrated on `dev`/`main`:

```bash
python Source/experiments/benchmark.py --include-extensions --repeats 3 --timeout-s 60 --best-heur moms
```

Or run as a module from the repository root:

```bash
# PowerShell:
$env:PYTHONPATH="Source"; python -m experiments.benchmark --include-extensions

# Bash:
# PYTHONPATH=Source python -m experiments.benchmark --include-extensions
```

---

## 6. Project Architecture & Directory Layout

```text
Source/
├── main.py              # [TV5] Entry point & Dependency Injection wiring
├── requirements.txt     # [TV5] Python dependencies
├── README.md            # [TV5] Setup & usage guide
├── core/contracts/      # [Frozen] Shared immutable models & Protocol interfaces
├── engine/              # [TV1] GameEngine (Hidden World isolation) & JSON loader/validator
├── puzzles/             # [TV1] 15 verified puzzles (3x3, 4x4, 5x5, extensions, edge_cases)
├── logic/               # [TV2] VariableMapper, RegionResolver, CNFEncoder, DirectEvaluator
├── solver/              # [TV3] Pure-Python DPLL SAT Solver, heuristics, DIMACS I/O
├── agent/               # [TV4] DeductiveLogicAgent (Entailment, Hint, Uniqueness, Trace)
├── experiments/         # [TV4] Benchmark harness & plotting scripts
├── gui/                 # [TV5] PyQt6 GUI (board, cards, trace panel, worker, theme)
└── tests/               # Independent unit & integration tests per module
```
