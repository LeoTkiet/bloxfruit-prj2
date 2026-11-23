# Quy ước nội bộ TV4 (agent/, experiments/) — chốt ngày 23/11/2026

Tài liệu này bổ sung cho `Source/core/contracts/` (đã đóng băng). Mọi quy ước ở đây nằm **trong phạm vi TV4**, không sửa `core/contracts/`, `engine/`, `logic/`, `solver/`, `gui/`.

## 1. Kết thúc vòng lặp no-guess và cảnh báo AMBIGUOUS

`VerdictCode` không có giá trị `AMBIGUOUS`, và contracts đã đóng băng. Vì vậy:

- TV4 định nghĩa trong `agent/outcome.py`:
  ```python
  class AutoSolveOutcome(str, Enum):
      SOLVED = "SOLVED"
      AMBIGUOUS = "AMBIGUOUS"          # KB_t nhất quán, chưa giải xong, không còn ô nào bị ép buộc
      INCONSISTENT = "INCONSISTENT"    # KB_t UNSAT
  ```
- `run_auto_solve` **luôn** trả về danh sách `DeductionStep`, trong đó **bước cuối là bước kết thúc** khi dừng vì AMBIGUOUS hoặc INCONSISTENT:

  | Kết cục | Bước cuối (`DeductionStep`) |
  |---|---|
  | SOLVED | Không thêm bước kết thúc. Bước cuối là bước ACCEPTED cuối cùng; `engine.get_public_state().is_solved == True`. |
  | AMBIGUOUS | `cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.NOT_PROVABLE`, `sat_queries` = các truy vấn của vòng cuối, `active_clue_ids` = toàn bộ clue đã lật. |
  | INCONSISTENT | `cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.INCONSISTENT`. |

- Hàm tiện ích `outcome_of(steps, final_state) -> AutoSolveOutcome` suy ra kết cục từ quy tắc trên. Agent cũng lưu `self.last_outcome` sau mỗi lần `run_auto_solve`.
- Cảnh báo: khi AMBIGUOUS, agent ghi `logging.getLogger("agent").warning(...)` một dòng có `puzzle_id`, `step`, danh sách ô còn UNKNOWN. **Không bao giờ đoán.**
- `get_hint` khi không có ô bị ép buộc nhưng KB nhất quán: `HintResult(cell=None, forced_status=Status.UNKNOWN, relevant_clue_ids=<clue đã lật có liên quan tới ô chưa giải>, message="Không có nhân vật nào được suy ra chắc chắn từ các manh mối hiện có (AMBIGUOUS). Hãy xem lại các manh mối: ...", is_inconsistent=False)`. Theo FAQ #5, gợi ý các clue nên cân nhắc là hợp lệ.
- `get_hint` khi KB UNSAT: `HintResult(cell=None, forced_status=Status.UNKNOWN, message="Cơ sở tri thức mâu thuẫn (INCONSISTENT).", is_inconsistent=True)`.

## 2. Cách gọi SAT (sửa lỗi đếm gấp đôi)

Vấn đề: `GameEngine.submit_verdict` tự gọi lại `agent.check_consistency` và `agent.classify_character` trên cùng `KB_t` mà vòng lặp vừa suy luận. Nếu agent chạy SAT lại thì số SAT call bị đếm gấp đôi và tốn thời gian.

Quy ước:

1. **Khóa KB (KB fingerprint):** `(puzzle_id, grid_size, frozenset(clue_id đã lật), frozenset(proved_verdicts.items()))`. Hai `PublicState` khác đối tượng nhưng cùng khóa thì cùng KB_t.
2. **Bộ nhớ đệm phân loại theo khóa KB:** mỗi khóa lưu `consistent: bool`, `classification: dict[CellID, Status]`, các model đã tìm thấy. `check_consistency` / `classify_character` / `classify_all` / `get_hint` tra đệm trước; nếu có thì **không gọi SAT**. Đệm chỉ giữ khóa KB hiện tại và khóa trước đó (LRU nhỏ, ≤ 8) để không phình bộ nhớ.
3. **Thứ tự truy vấn cho mỗi KB_t** (`entailment.py`):
   - Gọi `solve(cnf)` một lần để kiểm tra nhất quán. UNSAT → INCONSISTENT. SAT → lưu model M₀.
   - Với mỗi ô x chưa giải (thứ tự row-major), cần biết `KB ∧ x` và `KB ∧ ¬x`:
     - **Model caching:** nếu một model đã lưu có x=True thì `KB ∧ x` đã SAT, bỏ truy vấn này (ghi `SATQueryLog(cached=True)`, metrics rỗng); tương tự cho x=False.
     - Truy vấn còn lại gọi `solve(cnf, assumptions=[±var(x)])`. SAT → thêm model mới vào kho. UNSAT → ô x bị ép buộc theo cực tính ngược lại.
   - Model caching bật/tắt được bằng cờ `use_model_cache: bool = True` (cần cho RQ thực nghiệm).
4. **Đếm SAT call:** agent có hai bộ đếm tách biệt:
   - `stats.deduction_sat_calls` — truy vấn phát sinh khi agent tự suy luận (vòng lặp, hint, classify).
   - `stats.validation_sat_calls` — truy vấn phát sinh khi engine gọi lại để duyệt verdict. Với quy ước đệm ở trên, con số này phải bằng **0** trong `run_auto_solve`.
   - Benchmark chỉ báo cáo số liệu lấy từ `DeductionStep.sat_queries` (truy vấn có `cached=False`), không lấy tổng số lần gọi solver.
5. Agent nhận `ICNFEncoder` và `ISATSolver` qua constructor (DI), không import trực tiếp `logic/` hay `solver/` trong `agent/`.

## 3. Callback animation (FAQ #4)

`run_auto_solve(self, engine, on_step: Callable[[DeductionStep], None] | None = None)`. Tham số thêm là tùy chọn nên vẫn khớp `ILogicAgent`. Gọi `on_step(step)` ngay sau khi mỗi bước được tạo (kể cả bước kết thúc). Lỗi trong callback không được làm hỏng trạng thái agent.

## 4. Kiểm tra nghiệm duy nhất

`check_uniqueness(clues, grid_size)`: dựng `PublicState` tổng hợp gồm toàn bộ nhân vật **chưa lật** (status UNKNOWN), `proved_verdicts` rỗng, `revealed_clues = clues`, rồi gọi `encoder.encode_kb`. Cách này tránh trùng chỉ số biến phụ khi encode từng clue riêng. SAT → model M₁; thêm blocking clause trên **biến chính** (`¬M₁` chỉ trên `1..num_primary_vars`), solve lần 2. Kết quả `UNSAT` / `UNIQUE` / `MULTIPLE`.

> Cần báo TV2: `encode_kb` phải encode từ trường `revealed_clues`, không lấy clue từ `characters`.

## 5. Bộ puzzle

Dùng toàn bộ 10 màn chuẩn TV1 đã có (4×`3x3`, 4×`4x4`, 2×`5x5`), cộng 3 màn `extensions/` và 2 màn `edge_cases/` cho kiểm thử. Benchmark mặc định chạy 10 màn chuẩn; `extensions/` là tùy chọn (`--include-extensions`).

## 6. StubEncoder tạm thời

Trước khi có `logic.CNFEncoder` của TV2, TV4 dùng `experiments/stub_encoder.py` (chỉ để phát triển). Số liệu CNF đo bằng stub **không** đưa vào báo cáo.

## 7. StubDPLLSolver tạm thời

Khi PR solver của TV3 chưa vào `dev`, `experiments/solver_factory.make_solver()` trả `experiments/stub_solver.StubDPLLSolver` (DPLL tối giản, tất định) kèm cảnh báo. Khi `solver.DPLLSolver` có mặt, factory tự dùng solver thật với `heuristic`/`pure_literal` của cấu hình. Test của TV4 vì vậy chạy được cả trên `dev` lẫn sau khi merge TV3. Số liệu đo bằng stub **không** đưa vào báo cáo.
