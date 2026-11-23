# Checklist Duyệt Contracts (GĐ 0) & Kế Hoạch Kiểm Thử Của TV4 (`tests/test_agent/`)

- **Dự án:** Project 2 — Griductive Solver (CSC14003 – Nhập môn Trí tuệ Nhân tạo)
- **Người chuẩn bị:** Nguyên — Thành viên 4 (TV4: `agent/`, `experiments/`, `tests/test_agent/`, mục *Algorithms* & *Experiments* trong `Report.pdf`) *(schedule.md)*
- **Mục đích tài liệu:** Mang vào buổi họp chốt và đóng băng `core/contracts/` (`models.py`, `interfaces.py`) trước **18:00 ngày 23/11/2026** *(schedule.md)*, đồng thời chốt trước kế hoạch kiểm thử đơn vị và đặc tả 3 stub để TV4 lập trình song song ngay sau khi hợp đồng đóng băng.
- **Tài liệu căn cứ:** `description.md`, `plan.md`, `schedule.md`, `AI - Project 2.pdf`, và bảng FAQ chính thức 15 câu của giảng viên *(description.md 4.1)*.
- **Phạm vi:** Chỉ là tài liệu kỹ thuật phục vụ rà soát và thiết kế kiểm thử — **không chứa mã Python** và **không tự ý ban hành `core/contracts/`** (do TV1 chủ trì và cả nhóm duyệt chốt) *(plan.md 1.1)*.

---

## Bảng "Phải chốt hôm nay" (Họp GĐ 0 — trước 18:00 ngày 23/11)

> Bảng tóm tắt **14 quyết định trọng yếu** (sắp theo mức độ chặn tiến độ) để cả nhóm chốt nhanh trong cuộc họp đóng băng `core/contracts/`. Các mã `Q01`–`Q14` được tham chiếu xuyên suốt phần Checklist và Test Plan bên dưới.

| # | Câu hỏi cần chốt | Đề xuất của TV4 | Người quyết | Mức chặn |
|---|---|---|---|---|
| `Q01` | Sửa lỗi mutable default `assumptions: list[int] = []` trong `ISATSolver.solve()` | Đổi thành `assumptions: Sequence[int] \| None = None` hoặc `tuple[int, ...] = ()` | TV3, TV1 | **Chặn GĐ 1** |
| `Q02` | Cách `classify_character`/`classify_all` báo `INCONSISTENT` khi `Status` chưa có giá trị này | Chốt 1 trong 2: thêm `Status.INCONSISTENT` vào enum `Status` hoặc ném `InconsistentKBError` | TV1, TV4 | **Chặn GĐ 1** |
| `Q03` | Bổ sung `VerdictResponse` (kiểu trả về của `submit_verdict`) vào `models.py` | Thêm frozen dataclass `VerdictResponse(code, public_state, revealed_clue, message)` | TV1, TV4, TV5 | **Chặn GĐ 1** |
| `Q04` | Chuẩn hóa `CellID` và thứ tự **row-major** (tránh bẫy sort chuỗi `'A2' < 'B1'`) | Giữ `CellID` viết hoa + cung cấp sẵn `cell_sort_key_row_major` & `all_cells_row_major` trong `models.py` | TV1, TV2, TV4 | **Chặn GĐ 1** |
| `Q05` | Chốt tên trường `SATResult.model` (thay `assignment`) và kiểu bất biến (không dùng `dict` trong `frozen=True`) | Chốt tên `model: Mapping[int, bool] \| None` (bọc `types.MappingProxyType`, đủ mọi biến chính) | TV3, TV1, TV4 | **Chặn GĐ 1** |
| `Q06` | Định danh `Clue` (`clue_id`) và cấu trúc `revealed_clues` trong `PublicState` | Mỗi `Clue` có `clue_id: str` duy nhất (hoặc thống nhất dùng `owner_cell: CellID` làm ID) | TV1, TV2, TV4, TV5 | **Chặn GĐ 1** |
| `Q07` | Chốt các trường của `DeductionStep`, `HintResult`, `UniquenessResult` (Mục 2) & bản ghi bước dừng `AMBIGUOUS`/`INCONSISTENT` | Duyệt bảng Mục 2 (`frozen=True`, dùng `MappingProxyType`, `verdict=None` khi không lật thẻ; ghi 1 step cuối khi dừng bất thường) | TV1, TV4, TV5 | **Chặn GĐ 1** |
| `Q08` | Hợp đồng `on_step` cho animation (`FAQ #4`): callback, generator hay thêm `step_once` cho `QTimer` | Giữ `on_step: Callable[[DeductionStep], None] \| None = None` trên `run_auto_solve`; bổ sung `step_once(engine)` nếu TV5 nối trực tiếp `QTimer` | TV5, TV4 | **Chặn GĐ 1** |
| `Q09` | Bổ sung `encode_clues(clues, size, known_verdicts=None)` vào `ICNFEncoder` & lưu `num_primary_vars` trong `CNFFormula` | Thêm `encode_clues` tránh đụng ID biến phụ; lưu `num_primary_vars` để blocking clause ở `Uniqueness` chỉ phủ biến chính `1..N²` | TV2, TV4 | **Chặn GĐ 1** |
| `Q10` | Hành vi `classify_all` / `classify_character` / `get_hint` với ô đã giải hoặc bảng đã giải xong | `classify_all` chỉ trả các ô chưa giải (rỗng khi xong); `get_hint` trả `ALREADY_SOLVED` với `0` SAT calls | TV1, TV4 | **Chặn GĐ 1** |
| `Q11` | Tránh gọi vòng lặp đôi `Auto Solve -> submit_verdict -> Agent` làm gấp đôi `SAT calls`/`Runtime` | Tách bạch luồng chơi tay (Engine gọi Agent thẩm định) và Auto Solve (hoặc có cờ/kênh xác nhận không gọi lặp DPLL) | TV1, TV4 | **Chặn GĐ 2** |
| `Q12` | Kiểu trả về của `IGameEngine.list_maps()` (`FAQ #6`) cho GUI và Benchmark 6 màn chuẩn | Trả `list[MapInfo]` (`map_id`, `title`, `size`, `path`, `is_official_benchmark`) thay vì chỉ `list[str]` | TV1, TV4, TV5 | **Chặn GĐ 2** |
| `Q13` | `check_uniqueness` có tính kèm `initial_verdicts` (`FAQ #8`) và có bắt buộc `UNIQUE` cho màn kẹt (`FAQ #13`) không | Hỗ trợ tham số tùy chọn `known_verdicts=None`; xác nhận thêm với nhóm/thầy cho bộ 6 map chính thức | TV1, TV4 *(hỏi thầy nếu cần)* | **Chặn GĐ 2** |
| `Q14` | Tên tham số cấu hình Direct/Sinz (`CNFEncoder`), Pure-Literal/Heuristics/Timeout (`DPLLSolver`) & vai trò `IDirectEvaluator` với TV4 | Chốt tên cờ cấu hình trước 26/11; TV4 không gọi `IDirectEvaluator` trong `DeductiveLogicAgent` | TV2, TV3, TV4 | **Để sau** |

---

## Mục lục

1. [Bảng "Phải chốt hôm nay" (Họp GĐ 0 — trước 18:00 ngày 23/11)](#bảng-phải-chốt-hôm-nay-họp-gđ-0--trước-1800-ngày-2311)
2. [Checklist duyệt Contracts (`interfaces.py` & `models.py`)](#1-checklist-duyệt-contracts-interfacespy--modelspy)
   - [1.1. Các giao diện (`core/contracts/interfaces.py`)](#11-các-giao-diện-corecontractsinterfacespy)
   - [1.2. Các mô hình dữ liệu (`core/contracts/models.py`)](#12-các-mô-hình-dữ-liệu-corecontractsmodelspy)
3. [Đề xuất cấu trúc trường dữ liệu cho `DeductionStep`, `HintResult` và `UniquenessResult`](#2-đề-xuất-cấu-trúc-trường-dữ-liệu-cho-deductionstep-hintresult-và-uniquenessresult)
4. [Kế hoạch kiểm thử (`tests/test_agent/`)](#3-kế-hoạch-kiểm-thử-teststest_agent)
5. [Đặc tả hành vi cho ba Stub phát triển song song của TV4](#4-đặc-tả-hành-vi-cho-ba-stub-phát-triển-song-song-của-tv4)

---

## 1. Checklist duyệt Contracts (`interfaces.py` & `models.py`)

> **Quy ước sử dụng trong buổi họp:** Đánh dấu `[x]` vào từng mục khi TV1 và cả nhóm thống nhất xong chữ ký, kiểu dữ liệu, hành vi biên và ràng buộc bất biến. Mọi điểm chưa được đề bài nêu rõ được đánh dấu **"Cần xác nhận với nhóm/thầy"**.

### 1.1. Các giao diện (`core/contracts/interfaces.py`)

#### [ ] 1.1.1. `ILogicAgent` *(TV4 cung cấp; TV1 dùng để thẩm định nước đi, TV5 dùng cho GUI `Hint` & `Auto Solve` — plan.md 1.1)*

- **TV4 cần gì / cung cấp gì:**
  - Bộ phương thức cốt lõi theo `plan.md 1.1`:
    - `check_consistency(state: PublicState) -> bool`
    - `classify_character(state: PublicState, cell: CellID) -> Status` *(cần làm rõ xử lý `INCONSISTENT` — xem `Q02`)*
    - `classify_all(state: PublicState) -> dict[CellID, Status]`
    - `get_hint(state: PublicState) -> HintResult`
    - `run_auto_solve(engine: IGameEngine, on_step: Callable[[DeductionStep], None] | None = None) -> list[DeductionStep]`
    - `check_uniqueness(clues: Sequence[Clue], size: int) -> UniquenessResult` *(cần chốt xem có nhận thêm `known_verdicts` hay không — xem `Q13`)*
  - Hỗ trợ tham số cấu hình (ở lớp triển khai cụ thể `DeductiveLogicAgent`, tiêm qua constructor) để bật/tắt Model Caching và đặt `timeout_sec` phục vụ Benchmark GĐ 3B *(plan.md 2.4, 3.1)*.
- **Vì sao (gắn với đề bài & FAQ):**
  - Tác tử phải phân loại mọi nhân vật chưa giải thành `CRIMINAL`, `INNOCENT` hoặc `UNKNOWN`, chỉ chọn nước đi bị ép buộc, tuyệt đối không đoán mò, phát hiện trạng thái `AMBIGUOUS` và `INCONSISTENT`, xuất Deduction Trace, hỗ trợ Hint công khai và kiểm tra Uniqueness độc lập *(AI - Project 2.pdf 4.4, description.md 2.5, plan.md 2.4)*.
  - `on_step` callback trên `run_auto_solve` là móc nối trực tiếp để GUI **animate quá trình giải từng bước** theo khuyến nghị của giảng viên *(FAQ #4, plan.md 1.1, 2.4)*.
- **Câu hỏi cần chốt với nhóm:**
  1. **Xử lý `INCONSISTENT` trong `classify_character` và `classify_all` (`Q02`):** Theo `plan.md 1.1`, `Status` chỉ có `(CRIMINAL, INNOCENT, UNKNOWN)` trong khi `INCONSISTENT` lại nằm trong `VerdictCode`; nhưng `AI - Project 2.pdf 3.4` & `description.md 2.5` yêu cầu trả `INCONSISTENT` khi $KB_t$ tự mâu thuẫn. Nhóm chọn phương án nào: (a) thêm `INCONSISTENT` vào `Status`, (b) cho `classify_*` ném ngoại lệ `InconsistentKBError` (và `GameEngine` bắt ngoại lệ đó để trả `VerdictCode.INCONSISTENT`), hay (c) tạo kiểu kết quả riêng? *(Cần xác nhận với nhóm)*
  2. **Hợp đồng cho `on_step` / cơ chế animate (`Q08`, `FAQ #4`):**
     - Nhóm chọn cơ chế nào để GUI phát animation mượt: (a) callback `on_step(step: DeductionStep) -> None` (hoặc trả `bool` với `False` để hủy giữa chừng khi người dùng bấm Restart/đổi map), (b) generator `iter_auto_solve(engine) -> Iterator[DeductionStep]`, hay (c) bổ sung phương thức `step_once(engine) -> DeductionStep` để TV5 nối trực tiếp với `QTimer` (tránh đa luồng UI)?
     - `on_step` có được gọi cho cả bước kết thúc không lật thẻ (khi dừng ở `AMBIGUOUS` hoặc `INCONSISTENT`) không? *(Cần xác nhận với nhóm, đặc biệt TV5)*
  3. **Hành vi `classify_character` / `classify_all` đối với ô đã mở sẵn (`Q10`):** Nếu caller gọi `classify_character` cho một ô đã nằm trong `proved_verdicts`, Agent trả về trạng thái đã biết đó hay báo lỗi? `classify_all` chỉ trả về các ô **chưa giải** *(đúng câu chữ "Classify every unresolved character" — AI - Project 2.pdf 4.4)* hay trả cả $N^2$ ô? *(Cần xác nhận với nhóm, đặc biệt TV1)*
  4. **Đầu vào của `check_uniqueness(clues, size)` (`Q13`):** Khi puzzle có $\ge 1$ thẻ (thường 1–4) mở sẵn ban đầu (`FAQ #8`), tính duy nhất của puzzle được kiểm tra trên **chỉ toàn bộ tập clues** (`all_clues`) hay **toàn bộ tập clues cộng thêm các trạng thái mở sẵn ban đầu** (`initial_verdicts`)? *(Cần xác nhận với nhóm/thầy vì `AI - Project 2.pdf 4.4` ghi "for the complete clue set" còn `FAQ #8` cho phép mở sẵn "2, 3, 4, v.v." thẻ)*

---

#### [ ] 1.1.2. `ICNFEncoder` & `IDirectEvaluator` *(TV2 cung cấp; TV4 dùng `ICNFEncoder` trong Agent & Uniqueness, TV1 dùng cho Highlight — plan.md 1.1)*

- **TV4 cần gì:**
  - `map_cell_to_var(cell: CellID, size: int) -> int` *(lưu ý `plan.md 1.1` ghi `map_cell_to_var(cell) -> int` chưa nêu rõ `size` truyền ở đâu — qua constructor hay tham số hàm)* và hàm ánh xạ ngược `map_var_to_cell(var_id: int, size: int) -> CellID` để TV4 dịch `SATResult.model` và blocking clause giữa biến số nguyên và `CellID`.
  - `encode_kb(public_state: PublicState) -> tuple[CNFFormula, CNFStats]` tự động biên dịch $KB_t = \text{CNF}(\text{revealed clues}) \wedge \text{UnitClauses}(\text{proved verdicts})$, tách biệt biến chính ($1 \dots N^2$) và biến phụ ($\ge N^2 + 1$).
  - **Bổ sung quan trọng cho `uniqueness.py` (`Q09`):** Cần một phương thức mã hóa trọn gói danh sách manh mối cho `check_uniqueness`, ví dụ `encode_clues(clues: Sequence[Clue], size: int, known_verdicts: Mapping[CellID, Status] | None = None) -> tuple[CNFFormula, CNFStats]`, để TV2 quản lý bộ cấp phát biến phụ liên tục không bị trùng ID giữa các clue.
  - Khả năng cấu hình chiến lược mã hóa lực lượng (**Direct Combinatorial** vs **Sequential Counter / Sinz**) ở tầng lớp triển khai cụ thể `CNFEncoder` để TV4 chạy thực nghiệm so sánh ở GĐ 3B *(plan.md 2.2, 2.4, schedule.md)*.
  - Về `IDirectEvaluator`: TV4 không cần dùng trong vòng lặp suy diễn chính (chỉ dùng `ICNFEncoder` + `ISATSolver`), nhưng cần chốt rõ phạm vi sử dụng với TV2 để tránh phụ thuộc thừa.
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài cấm viết tay CNF, bắt buộc ánh xạ biến tất định, tách biệt biến phụ với biến chính, và báo cáo đầy đủ số biến chính, biến phụ, số mệnh đề *(AI - Project 2.pdf 3.1, 3.3, 4.2, description.md 2.2, 2.3)*.
  - Nếu `uniqueness.py` phải gọi lặp `encode_clue(clue)` từng lần một mà `ICNFEncoder` reset bộ đếm biến phụ về $N^2 + 1$ ở mỗi lần gọi, các biến phụ của clue sau sẽ đụng biến phụ của clue trước (đặc biệt với Sinz encoding và Extension `PARITY` dùng Tseitin XOR), làm hỏng công thức CNF!
  - Benchmark GĐ 3B bắt buộc so sánh Direct vs Sinz trên cùng bộ 6 puzzle chuẩn *(plan.md 2.4, schedule.md)*.
- **Câu hỏi cần chốt với nhóm:**
  1. **Quản lý biến phụ khi mã hóa nhiều clue cho `check_uniqueness` (`Q09`):** TV2 có đồng ý bổ sung `encode_clues(clues, size, known_verdicts=None) -> tuple[CNFFormula, CNFStats]` vào `ICNFEncoder` không?
  2. **Tham số `size` và ánh xạ hai chiều:** `ICNFEncoder` là stateless (nhận `size` ở từng hàm như `map_cell_to_var(cell, size)`) hay stateful (khởi tạo gắn với một `size` cố định)? Có cung cấp cả `map_var_to_cell` (hoặc bảng ánh xạ trong `CNFFormula`) để TV4 không tự viết lại logic quy đổi tọa độ không?
  3. **Quy ước chỉ số biến chính (`Q04`):** Khẳng định biến chính luôn đánh số liên tục `1..N²` theo đúng thứ tự **row-major** (`A1 -> 1`, `B1 -> 2`, ..., `E5 -> 25`), literal dương `+i` biểu diễn `CRIMINAL` (`True`), literal âm `-i` biểu diễn `INNOCENT` (`False`), và biến phụ bắt đầu từ `N² + 1` *(description.md 2.2, plan.md 2.2)*.
  4. **Trường hợp clue trùng lặp / mâu thuẫn / tham số không hợp lệ:** Khi `encode_kb` gặp `PublicState` có mâu thuẫn logic (ví dụ vừa chứng minh `A1=CRIMINAL` vừa có clue `FACT(A1=INNOCENT)`), TV2 vẫn sinh công thức CNF bình thường để DPLL trả `UNSAT` (⇒ `INCONSISTENT`), hay ném ngoại lệ? *(TV4 cần TV2 **sinh CNF bình thường** cho mâu thuẫn logic, chỉ ném `ValueError` cho lỗi cấu trúc/vượt biên như $k < 0$ hoặc $k > |R|$ — cần chốt rõ với TV2!)*
  5. **Cơ chế chuyển đổi Direct vs Sinz cho Benchmark GĐ 3B (`Q14`):** TV2 chốt tên tham số cấu hình (ví dụ `cardinality_encoding: Literal["direct", "sinz"]`) trên constructor của `CNFEncoder` để TV4 viết khung `experiments/benchmark.py` ngay trong GĐ 1.
  6. **Vai trò của `IDirectEvaluator` đối với TV4 (`Q14`):** TV4 có cần gọi `IDirectEvaluator` hay không, và nếu có thì dùng để làm gì (ví dụ: chỉ TV2 dùng trong `tests/test_logic/` để kiểm chứng tương đương CNF theo `plan.md 2.2`, hay TV4 còn cần gọi trong `experiments/benchmark.py` / `uniqueness.py` để xác minh độc lập nghiệm cuối của 6 puzzle thỏa mãn mọi clue gốc)? *(TV4 đề xuất không tiêm `IDirectEvaluator` vào `DeductiveLogicAgent`; nếu cần xác minh chéo nghiệm cuối thì chỉ dùng tùy chọn ở script kiểm định/benchmark — cần xác nhận với TV2 & TV1.)*

---

#### [ ] 1.1.3. `ISATSolver` *(TV3 cung cấp; TV4 dùng trong `entailment.py` & `uniqueness.py`, TV2 dùng để cross-check — plan.md 1.1)*

- **TV4 cần gì:**
  - Chữ ký `solve(cnf: CNFFormula, assumptions: Sequence[int] | None = None) -> SATResult` (hoặc `assumptions: tuple[int, ...] = ()`).
  - **Sửa lỗi mutable default argument trong `plan.md 1.1` (`Q01`):** Bản nháp trong `plan.md 1.1` đang ghi `solve(cnf: CNFFormula, assumptions: list[int] = []) -> SATResult`. Trong Python, đặt `list` rỗng làm giá trị mặc định là lỗi **mutable default** — mọi lời gọi không truyền `assumptions` sẽ dùng chung cùng một instance `list`; bất kỳ thao tác thay đổi nào sẽ rò rỉ sang các lần gọi sau và gây bug cực kỳ khó lần. **Đề xuất chốt:** đổi sang `assumptions: tuple[int, ...] = ()` hoặc `assumptions: Sequence[int] | None = None`.
  - Hỗ trợ truyền `assumptions` (ví dụ `(-var_i,)` hoặc `(+var_i,)`) **không làm biến đổi (non-mutating)** đối tượng `CNFFormula` gốc và tránh sao chép nặng toàn bộ tập mệnh đề mỗi lượt gọi *(plan.md 2.3)*.
  - Kết quả trả về `SATResult` luôn đầy đủ `is_sat`, `model` (complete assignment khi SAT), và `metrics: SATMetrics` (4 chỉ số bắt buộc).
  - Hỗ trợ cờ cấu hình ở lớp triển khai `DPLLSolver` (`enable_pure_literal`, `heuristic` gồm `'lexicographic'`, `'moms'`, `'jw'`) và hỗ trợ `timeout_ms` / `timeout_sec` (tùy chọn) cho stress case 5×5 *(plan.md 2.3, 3.1)*.
- **Vì sao (gắn với đề bài & FAQ):**
  - Entailment via Refutation gọi liên tiếp hàng chục truy vấn $KB_t \land \neg C_i$ và $KB_t \land C_i$ trên cùng một $KB_t$ *(description.md 2.5, 3.2, AI - Project 2.pdf 3.4, 4.3)*.
  - Model Caching ở TV4 phụ thuộc trực tiếp vào `model` hoàn chỉnh của `SATResult`; Benchmark GĐ 3B phụ thuộc vào 4 chỉ số `SATMetrics` và khả năng bật/tắt Pure-Literal + Heuristics *(description.md 2.4, 2.7, plan.md 2.3, 2.4)*.
- **Câu hỏi cần chốt với nhóm:**
  1. **Sửa chữ ký `assumptions` (`Q01`):** TV3 và cả nhóm đồng ý bỏ mutable default `= []`, thay bằng `assumptions: Sequence[int] | None = None` (hoặc `tuple[int, ...] = ()`) chứ?
  2. **Hành vi biên của `assumptions`:**
     - Nếu `assumptions` chứa hai literal đối nghịch nhau như `(+3, -3)` thì trả `SATResult(is_sat=False, model=None, ...)` (không crash)?
     - Nếu `cnf.clauses` rỗng (công thức thỏa mãn tầm thường) nhưng có `assumptions=(+1,)` thì có gán đúng `model[1] = True` và hoàn thiện mọi biến `1..num_total_vars` không?
     - Nếu `cnf` chứa mệnh đề rỗng `()` (tức $KB$ đã mâu thuẫn ngay từ đầu) thì trả ngay `UNSAT` không lỗi chỉ số?
  3. **Đảm bảo tính bất biến của `cnf`:** TV3 cam kết `solve()` không bao giờ mutate `cnf` (hay các clause bên trong `cnf`), cho phép TV4 gọi `solve(cnf, assumptions=...)` nhiều lần liên tiếp trên cùng một `CNFFormula`?
  4. **Cơ chế Timeout cho màn 5×5 (`Q14`, `plan.md 3.1`):** `solve()` có nhận thêm tham số tùy chọn `timeout_ms: float | None = None` (và phản ánh trạng thái timeout trong `SATResult` hoặc ném `SolverTimeoutError`) hay TV4 tự kiểm soát timeout ở cấp puzzle trong `benchmark.py`? *(Cần xác nhận với nhóm, đặc biệt TV3)*
  5. **Tên tham số cấu hình heuristic cho Benchmark GĐ 3B (`Q14`):** Chốt tên tham số trên `DPLLSolver(...)` (ví dụ `enable_pure_literal: bool`, `heuristic: Literal["lexicographic", "moms", "jw"]`) để TV4 chuẩn bị sẵn bảng ma trận thí nghiệm.

---

#### [ ] 1.1.4. `IGameEngine` *(TV1 cung cấp; TV4 dùng trong `run_auto_solve` & Benchmark, TV5 dùng cho GUI — plan.md 1.1)*

- **TV4 cần gì:**
  - Các phương thức theo `plan.md 1.1`:
    - `load_puzzle(path: str | Path) -> PublicState`
    - `load_map(map_id: str) -> PublicState` *(cho List Map theo FAQ #6)*
    - `list_maps() -> list[...]` *(cần chốt kiểu phần tử trả về — xem `Q12`)*
    - `get_public_state() -> PublicState`
    - `submit_verdict(cell: CellID, status: Status) -> VerdictResponse` *(lưu ý: `VerdictResponse` xuất hiện ở chữ ký này trong `plan.md 1.1` nhưng chưa có tên trong dòng `models.py` — xem `Q03`)*
    - `restart() -> PublicState`
    - `get_highlighted_cells(cell: CellID) -> list[CellID]` *(chủ yếu cho GUI TV5)*
    - `get_all_clues_for_uniqueness() -> list[Clue]`
  - Ranh giới cách ly tuyệt đối: `get_public_state()` không rò rỉ đáp án ẩn hay manh mối úp; khi `submit_verdict` bị từ chối (`NOT_PROVABLE` hoặc `CONTRADICTED`), trạng thái bảng giữ nguyên và không lật thẻ *(AI - Project 2.pdf 2.2, 4.1, description.md 2.1)*.
- **Vì sao (gắn với đề bài & FAQ):**
  - `run_auto_solve(engine, on_step)` của TV4 phải tương tác với thế giới ẩn duy nhất qua `get_public_state()` và `submit_verdict()` *(AI - Project 2.pdf 4.1, 4.4, plan.md 2.4)*.
  - `FAQ #6` cho phép thay nút `Load` bằng **danh sách màn chơi (list map)** kèm `Restart`; nếu `list_maps()` trả về đủ thông tin chuẩn của 6 màn chơi (`2×3×3`, `2×4×4`, `2×5×5` theo `FAQ #2`), `experiments/benchmark.py` của TV4 có thể nạp tự động cùng một nguồn dữ liệu với GUI mà không cần hard-code đường dẫn.
  - `get_all_clues_for_uniqueness()` phục vụ pipeline kiểm tra tính duy nhất độc lập (`FAQ #9`, `description.md 3.2 luồng C`).
- **Câu hỏi cần chốt với nhóm:**
  1. **Tránh vòng gọi lặp đôi (Circular / Double Call) giữa `GameEngine.submit_verdict` và `LogicAgent.run_auto_solve` (`Q11`):** Theo `plan.md 2.1`, khi chơi thủ công, `GameEngine.submit_verdict(cell, status)` gọi `ILogicAgent` để thẩm định xem nước đi có bị ép buộc hay không. Vậy khi `run_auto_solve(engine)` của TV4 tự gọi `engine.submit_verdict(cell, status)`, `GameEngine` sẽ gọi lại `ILogicAgent` thêm một lần nữa (gấp đôi số lần gọi SAT trong Benchmark!) hay có cơ chế tách bạch/cache? Đây là điểm **cực kỳ quan trọng** ảnh hưởng trực tiếp tới số liệu `SAT calls` và `Runtime` của Benchmark GĐ 3B! *(Cần xác nhận với nhóm, đặc biệt TV1 & TV4)*
  2. **Định nghĩa `VerdictResponse` (`Q03`):** `plan.md 1.1` nhắc tới `VerdictResponse` làm kiểu trả về của `submit_verdict` nhưng chưa liệt kê trong `models.py`. TV4 đề xuất `VerdictResponse` chứa: `code: VerdictCode`, `public_state: PublicState`, `revealed_clue: Clue | None`, `message: str`. Nhóm có thống nhất đưa `VerdictResponse` vào `models.py` không?
  3. **Kiểu trả về của `list_maps()` (`Q12`, `FAQ #6`):** Trả về `list[str]` (chỉ `map_id`) hay `list[MapInfo]` (gồm `map_id`, `title`, `size`, `path`, `is_official_benchmark`)? TV4 khuyến nghị `list[MapInfo]` để `benchmark.py` dễ phân tách 6 màn chuẩn (`FAQ #2`) với các màn `edge_cases/`.
  4. **Quy ước an toàn cho `get_all_clues_for_uniqueness()` (`Q13`):** Chốt quy tắc kiến trúc rằng **chỉ** công cụ kiểm định puzzle / `uniqueness.py` được phép gọi hàm này; `DeductiveLogicAgent` trong luồng giải (`classify_*`, `get_hint`, `run_auto_solve`) tuyệt đối **không được gọi**. Đồng thời xác nhận hàm này có trả về bản sao độc lập (immutable/copy) và có cần kèm `initial_verdicts` hay kích thước lưới `size` không?
  5. **Phản hồi khi nộp verdict cho ô đã mở hoặc khi chưa load puzzle:** `submit_verdict` trên ô đã giải rồi hoặc gọi `get_public_state()` trước khi `load_puzzle`/`load_map` sẽ trả mã lỗi nào hay ném ngoại lệ gì? *(Cần xác nhận với nhóm, đặc biệt TV1)*

---

### 1.2. Các mô hình dữ liệu (`core/contracts/models.py`)

> **Quy ước bất biến chung đề xuất cho mọi `@dataclass(frozen=True)` trong `models.py`:** Không dùng field kiểu `dict` thuần bên trong `frozen=True` dataclass (vì người gọi vẫn có thể mutate nội dung `dict` và sẽ lỗi `TypeError: unhashable type` khi hash). TV4 đề xuất dùng thống nhất **`Mapping[K, V]` bọc bằng `types.MappingProxyType`** khi khởi tạo (bất biến và tra cứu $O(1)$ cho Model Caching); nếu nhóm cần các dataclass này hỗ trợ `hash()` trực tiếp thì chuyển thống nhất sang **`tuple[tuple[K, V], ...]`**.

#### [ ] 1.2.1. `CellID` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Định danh ô duy nhất, hashable (dùng được làm key của `Mapping`/`dict`), bất biến, chuẩn hóa theo tọa độ cột chữ cái + hàng số (ví dụ `'A1'`, `'C2'`, `'E5'`).
  - Một quy ước **thứ tự row-major** dùng chung toàn dự án: hàng 1 (`A1, B1, C1, ...`) → hàng 2 (`A2, B2, C2, ...`) → ... → hàng N (`..., E5`).
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài quy định hàng đánh số `1..N` từ trên xuống dưới, cột đánh chữ `A..` từ trái sang phải (`C2` = cột C, hàng 2), và chọn nhân vật tất định theo **row-major order** *(AI - Project 2.pdf 2.1, 2.2, description.md 2.1, 2.5, plan.md 2.4)*.
  - **Cảnh báo bẫy kỹ thuật:** Nếu `CellID` chỉ là `str` thuần (`'A1'`, `'B1'`, `'A2'`), thì `sorted(cells)` mặc định của Python sẽ sắp theo thứ tự từ điển thành `'A1', 'A2', 'B1'` — tức là **column-major**, SAI hoàn toàn so với row-major (`'A1', 'B1', 'A2'`) và lệch với `VariableMapper` của TV2!
- **Câu hỏi cần chốt với nhóm (`Q04`):**
  1. `CellID` được định nghĩa là `TypeAlias` / `NewType('CellID', str)` (luôn viết hoa `'A1'..'E5'`) hay một frozen dataclass `(col: str, row: int)` có định nghĩa sẵn thứ tự so sánh `(row, col)`?
  2. Nếu giữ `CellID = str` cho gọn khi serialize JSON, TV1 có cung cấp sẵn các hàm tiện ích chuẩn ngay trong `core/contracts/models.py` như `parse_cell_id(cell) -> tuple[int, int]`, `cell_sort_key_row_major(cell) -> tuple[int, int]`, và `all_cells_row_major(size: int) -> tuple[CellID, ...]` để cả 5 thành viên dùng thống nhất không?

---

#### [ ] 1.2.2. `Status` *(plan.md 1.1)*

- **TV4 cần gì:**
  - `Enum` biểu diễn trạng thái phân loại logic của một nhân vật: tối thiểu `CRIMINAL`, `INNOCENT`, `UNKNOWN` *(plan.md 1.1)*.
  - Tách biệt rõ tên giá trị logic nội bộ (`CRIMINAL`/`INNOCENT`) với tên hiển thị chủ đề trên GUI (nếu nhóm đổi tên đối tượng theo `FAQ #15`).
- **Vì sao (gắn với đề bài & FAQ):**
  - Mọi yêu cầu logic cốt lõi (`C_i = True` nếu Criminal, `False` nếu Innocent; phân loại `CRIMINAL` / `INNOCENT` / `UNKNOWN`) đều bám cặp nhãn nhị phân này *(AI - Project 2.pdf 3.1, 3.4, 4.4)*. `FAQ #15` cho phép đổi tên cặp đối tượng miễn không đổi bản chất logic.
- **Câu hỏi cần chốt với nhóm (`Q02`):**
  1. Nhóm có giữ nguyên tên enum `Status.CRIMINAL`, `Status.INNOCENT`, `Status.UNKNOWN` ở tầng `core/contracts/` (kể cả khi GUI đổi tên chủ đề theo `FAQ #15`) không?
  2. Có thêm thành viên `Status.INCONSISTENT` vào enum `Status` (để `classify_character` trả trực tiếp theo đúng mô tả mục `3.4` trong `AI - Project 2.pdf`) hay tách riêng ra khỏi `Status` (giữ `Status` sạch chỉ 3 giá trị và xử lý `INCONSISTENT` bằng cơ chế khác)? *(Cần xác nhận với nhóm)*

---

#### [ ] 1.2.3. `VerdictCode` *(và `VerdictResponse` — plan.md 1.1)*

- **TV4 cần gì:**
  - `VerdictCode` là `Enum` gồm đúng 4 mã chuẩn trong `plan.md 1.1`: `ACCEPTED`, `NOT_PROVABLE`, `CONTRADICTED`, `INCONSISTENT`.
  - Đồng thời chốt cấu trúc `VerdictResponse` (kiểu trả về của `IGameEngine.submit_verdict`) để `run_auto_solve` nhận ngay mã kết quả, `PublicState` mới và manh mối vừa lật mở (nếu `ACCEPTED`).
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài bắt buộc phân biệt `NOT_PROVABLE` (không có trạng thái nào bị ép) với `CONTRADICTED` (trạng thái ngược lại mới bị ép) khi từ chối nước đi, giữ nguyên trạng thái bàn chơi, và nhận diện `INCONSISTENT` khi $KB_t$ mâu thuẫn *(AI - Project 2.pdf 2.2, 3.4, 4.1, description.md 2.1)*.
- **Câu hỏi cần chốt với nhóm (`Q03`):**
  1. Có cần thêm mã nào khác vào `VerdictCode` (ví dụ `ALREADY_SOLVED` nếu người chơi/caller nộp lại verdict cho ô đã mở) hay giữ đúng 4 mã trong `plan.md 1.1`?
  2. Nhóm đồng ý bổ sung `VerdictResponse` vào `core/contracts/models.py` với các trường `(code, public_state, revealed_clue, message)` không?

---

#### [ ] 1.2.4. `PublicState` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Một đối tượng **bất biến thực sự** (`@dataclass(frozen=True)`, các tập hợp dùng `tuple` và các ánh xạ dùng `Mapping` bọc `types.MappingProxyType` — không dùng `dict` thuần) đại diện đầy đủ và **duy nhất** cho tri thức công khai tại thời điểm $t$:
    - Kích thước lưới `size: int` ($N \in \{3, 4, 5\}$, hoặc tổng quát $N \ge 1$ cho unit test nhỏ $2 \times 2$).
    - Danh sách ô / thông tin công khai của từng nhân vật (`CellID`, tên hiển thị, nghề nghiệp — tuyệt đối **không** có trường trạng thái ẩn).
    - Bản đồ các phán quyết đã chứng minh / mở sẵn: `proved_verdicts: Mapping[CellID, Status]` *(bọc `types.MappingProxyType`)* chỉ gồm `CRIMINAL`/`INNOCENT`, hỗ trợ **$\ge 1$ thẻ (thường 1–4)** mở sẵn ban đầu theo `FAQ #8`.
    - Danh sách/bản đồ các manh mối **đã lật ngửa**: `revealed_clues: tuple[Clue, ...]` hoặc `Mapping[CellID, Clue]` *(bọc `types.MappingProxyType`)*.
    - Các trường tiện ích (tùy chọn nhưng rất sạch): `unresolved_cells` (hoặc suy ra được từ `all_cells - proved_verdicts.keys()`), `puzzle_id` / `step_index` (nếu có).
- **Vì sao (gắn với đề bài & FAQ):**
  - Ranh giới cách ly dữ liệu ẩn là yêu cầu kiến trúc bắt buộc số 1 *(AI - Project 2.pdf 4.1, 4.2, description.md 1.1, 2.3, plan.md 2.1 DoD #1)*: Logic Agent và Hint chỉ được nhận `PublicState`, tuyệt đối không được tiếp cận hidden status hay unrevealed clues.
  - Tính bất biến của `PublicState` đảm bảo TV4 không thể vô tình sửa trạng thái bên trong `GameEngine`, đồng thời cho phép dùng làm mốc kiểm tra hợp lệ khi vô hiệu hóa Model Cache giữa $KB_t$ và $KB_{t+1}$.
- **Câu hỏi cần chốt với nhóm (`Q06`):**
  1. **Kiểm định chống rò rỉ dữ liệu ẩn:** TV1 xác nhận `PublicState` tuyệt đối không chứa bất kỳ trường nào liên quan đến đáp án ẩn, manh mối đang úp, hay tham chiếu ngược tới `GameEngine`?
  2. **Cấu trúc `revealed_clues` và ID của `Clue` (`Q06`):** Mỗi `Clue` có trường `clue_id: str` duy nhất (hay dùng chính `owner_cell: CellID` làm ID manh mối vì mỗi ô có đúng 1 clue theo `description.md 2.1`)? Việc này ảnh hưởng trực tiếp tới `DeductionStep.active_clue_ids` và `HintResult.relevant_clue_ids`.
  3. **Hỗ trợ kích thước nhỏ cho unit test:** `PublicState` và `ICNFEncoder` có cho phép $N = 1$ hoặc $N = 2$ (ngoài $N \in \{3, 4, 5\}$) để unit test chạy gọn nhẹ, hay giới hạn cứng $N \in \{3, 4, 5\}$? *(Cần xác nhận với nhóm, đặc biệt TV1 & TV2)*
  4. **Trạng thái kết thúc:** `PublicState` có cung cấp cờ/thuộc tính `is_solved` (khi mọi ô đều đã nằm trong `proved_verdicts`) không?

---

#### [ ] 1.2.5. `CNFFormula` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Chứa tập mệnh đề CNF dạng bất biến (`clauses: tuple[tuple[int, ...], ...]`), với quy ước DIMACS integer literals (`+v` cho $C_v$, `-v` cho $\neg C_v$, không chứa số `0` làm kết thúc mệnh đề như file DIMACS text).
  - Chứa siêu dữ liệu biến tối thiểu:
    - `num_primary_vars: int` (bằng $N^2$, biểu diễn các biến chính $1 \dots N^2$).
    - `num_aux_vars: int` (hoặc `num_total_vars: int`, với `num_total_vars = num_primary_vars + num_aux_vars`).
    - (Khuyến nghị) `var_to_cell` / `cell_to_var` hoặc quy ước row-major cố định gắn với `size`.
- **Vì sao (gắn với đề bài & FAQ):**
  - `uniqueness.py` **bắt buộc** biết chính xác đâu là tập biến chính $1 \dots N^2$ để tạo mệnh đề chặn (blocking clause) chỉ trên biến chính, loại trừ biến phụ *(description.md 2.2, 3.2 luồng C, plan.md 2.4)*.
  - Nếu `clauses` là `tuple[tuple[int, ...], ...]`, việc TV4 chèn thêm blocking clause ở `uniqueness.py` (tạo `CNFFormula` mới với `clauses + (blocking_clause,)`) sẽ hoàn toàn an toàn, không làm hỏng công thức gốc.
- **Câu hỏi cần chốt với nhóm (`Q09`):**
  1. `CNFFormula.clauses` chốt dùng `tuple[tuple[int, ...], ...]` (bất biến, tránh bug mutate khi gọi `solve()` nhiều lần) được không?
  2. `CNFFormula` có lưu rõ `num_primary_vars` và `num_aux_vars` (hoặc `num_total_vars`) ngay trên đối tượng để `ISATSolver` biết phạm vi biến cần hoàn thiện model và `uniqueness.py` biết phạm vi biến chính cho blocking clause không?
  3. Mệnh đề rỗng (biểu diễn xung đột trực tiếp, ví dụ từ một clue vô nghiệm ngay khi mã hóa) được biểu diễn là `()` nằm trong `clauses` (tức `clauses = ((),)`), còn công thức rỗng (luôn đúng / tautology) là `clauses = ()` — cả TV2, TV3, TV4 có thống nhất quy ước này không?

---

#### [ ] 1.2.6. `CNFStats` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Thống kê chính xác tại mỗi lần mã hóa `encode_kb` / `encode_clues`:
    - `num_primary_vars: int`
    - `num_aux_vars: int`
    - `num_clauses: int`
    - (Khuyến nghị bổ sung) `encoding_strategy: str` (ví dụ `"direct"` / `"sinz"`) để log sạch vào CSV Benchmark GĐ 3B.
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài yêu cầu trực tiếp báo cáo 2 nhóm chỉ số đầu tiên trong thực nghiệm: (1) số biến chính & biến phụ, (2) số lượng mệnh đề CNF *(AI - Project 2.pdf 3.3, 4.2, 4.5, description.md 2.3, 2.7)*.
- **Câu hỏi cần chốt với nhóm:**
  1. `num_primary_vars` luôn tính bằng tổng số ô trên bảng ($N^2$) hay chỉ đếm số biến chính thực sự xuất hiện trong ít nhất một mệnh đề của $KB_t$? *(Khuyến nghị: luôn là $N^2$ theo `description.md 2.2` "Với mỗi nhân vật thứ i trên bảng (i = 1..N²), định nghĩa đúng một biến Boolean chính $C_i$", hoặc tách thêm trường nếu muốn — cần chốt đồng nhất giữa TV2 & TV4 cho báo cáo!)*
  2. Trong `benchmark.py` (GĐ 3B), các chỉ số `num_aux_vars` và `num_clauses` báo cáo cho mỗi puzzle là lấy ở **trạng thái cuối / đỉnh lớn nhất** ($KB_{\max}$), **trung bình các bước**, hay **toàn bộ tập clue đầy đủ**? *(Cần xác nhận với nhóm để TV2 & TV4 trình bày nhất quán trong Report.pdf)*

---

#### [ ] 1.2.7. `SATResult` *(plan.md 1.1)*

- **TV4 cần gì:**
  - `is_sat: bool`: `True` nếu công thức thỏa mãn, `False` nếu `UNSAT`.
  - `model: Mapping[int, bool] | None` *(bọc `types.MappingProxyType` trong frozen dataclass — không dùng `dict` thuần; nếu nhóm cần `SATResult` hashable thì dùng `tuple[tuple[int, bool], ...] | None`)*: phép gán **đầy đủ (complete assignment)** cho mọi biến khi `is_sat=True` (bắt buộc phủ đủ tất cả biến chính `1..num_primary_vars`, kể cả các biến không xuất hiện trong mệnh đề nào), và `None` khi `is_sat=False`.
  - `metrics: SATMetrics`: gói 4 chỉ số hiệu năng của đúng lượt gọi đó.
  - (Tùy chọn) `timed_out: bool = False`: nếu TV3 hỗ trợ timeout bên trong DPLL *(xem `Q14`)*.
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài bắt buộc DPLL trả về `SAT` kèm **complete assignment** hoặc `UNSAT` *(AI - Project 2.pdf 4.3, description.md 2.4)*.
  - **Phục vụ trực tiếp Model Caching:** Mỗi `model` trả về khi `is_sat=True` cho phép TV4 biết ngay với mọi biến chính $j$: nếu `model[j] == False` thì $KB_t \land \neg C_j$ chắc chắn `SAT`; nếu `model[j] == True` thì $KB_t \land C_j$ chắc chắn `SAT` — bỏ qua lệnh gọi DPLL thừa mà vẫn bảo toàn 100% tính đúng đắn toán học *(description.md 3.2 luồng A, plan.md 2.4)*.
  - **Phục vụ trực tiếp Uniqueness Check:** Cần đọc đủ giá trị $M[1 \dots N^2]$ để dựng blocking clause $\bigvee_{v=1}^{N^2} (\neg C_v \text{ nếu } M[v]=\text{True else } C_v)$ *(description.md 3.2 luồng C)*.
  - Dùng `Mapping[int, bool]` bọc `types.MappingProxyType` tránh lỗi `frozen=True` nhưng vẫn bị mutate nội dung `dict` (và ghi chú rõ nếu cần hashable thì dùng `tuple[tuple[int, bool], ...]`).
- **Câu hỏi cần chốt với nhóm (`Q05`):**
  1. **Kiểu dữ liệu bất biến của `model`:** Chốt dùng `Mapping[int, bool] | None` (bọc `types.MappingProxyType`, key là `var_id` từ `1..N²` hoặc `1..num_total_vars`, value là `True`/`False`) thay vì `dict` thuần hay `list[int]` kiểu DIMACS để vừa bất biến vừa tra cứu $O(1)$ khi làm Model Caching được không? *(Nếu nhóm cần `SATResult` hashable thì chuyển thống nhất sang `tuple[tuple[int, bool], ...] | None`.)*
  2. **Biến tự do (don't-care variables):** Khi DPLL rút gọn xong toàn bộ mệnh đề trước khi gán hết biến, TV3 có cam kết điền giá trị tất định (ví dụ mặc định `False`) cho mọi biến chính chưa gán trong `1..num_primary_vars` để `model` luôn là complete assignment không?
  3. **Tên trường:** `plan.md 1.1` ghi là `model`, còn `description.md 3.2` ghi là `assignment`. Nhóm chốt dùng đúng một tên duy nhất (`model`) trong `core/contracts/models.py`!

---

#### [ ] 1.2.8. `SATMetrics` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Đúng 4 chỉ số bắt buộc của mỗi lượt gọi `solve()`:
    - `decisions: int` (số lần phân nhánh chọn biến)
    - `propagations: int` (số lần lan truyền đơn vị)
    - `backtracks: int` (số lần gặp xung đột và quay lui)
    - `runtime_ms: float` (thời gian thực thi tính bằng mili-giây, đo bằng `time.perf_counter()`).
- **Vì sao (gắn với đề bài & FAQ):**
  - Đây là yêu cầu tối thiểu số 6 của DPLL *(AI - Project 2.pdf 4.3, description.md 2.4)* và nhóm chỉ số bắt buộc số 4 & số 6 của Thực nghiệm *(AI - Project 2.pdf 4.5, description.md 2.7)*.
  - TV4 cần cộng dồn chính xác `decisions`, `propagations`, `backtracks`, `runtime_ms` qua toàn bộ các truy vấn SAT trong một bước suy diễn (`DeductionStep`) và trong cả một màn chơi (`experiments/benchmark.py`).
- **Câu hỏi cần chốt với nhóm:**
  1. **Đơn vị thời gian:** Chốt dùng `runtime_ms: float` (mili-giây, dùng `perf_counter()`) thống nhất giữa TV3, TV4 và TV5?
  2. **Định nghĩa đếm `propagations` và `backtracks`:** Khi `assumptions` được đưa vào đầu `solve()`, việc gán trực tiếp các `assumptions` có tính vào `propagations` hay chỉ tính các mệnh đề đơn vị bị ép sinh ra sau đó? Khi xung đột ngay ở gốc (chưa có decision nào), `backtracks` là `0` hay `1`? *(Cần TV3 chốt rõ định nghĩa để giải thích nhất quán giữa mục DPLL của TV3 và mục Experiments của TV4 trong Report.pdf)*
  3. **Tính tất định:** Xác nhận 3 chỉ số `decisions`, `propagations`, `backtracks` luôn hoàn toàn giống nhau giữa các lần chạy lặp lại trên cùng công thức và cùng cấu hình *(plan.md 2.3 DoD #2)*.

---

#### [ ] 1.2.9. `DeductionStep` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Một bản ghi (frozen dataclass) đầy đủ thông tin cho từng bước suy diễn $t$, chứa toàn bộ thành phần vết suy diễn theo yêu cầu đề bài (số bước, ID manh mối hoạt động, danh sách truy vấn SAT kèm metrics, phán quyết rút ra, manh mối mới lật mở) và trạng thái bước để TV5 animate trực tiếp trên GUI *(chi tiết trường đề xuất xem [Mục 2.1](#21-đề-xuất-cấu-trúc-deductionstep))*.
- **Vì sao (gắn với đề bài & FAQ):**
  - Đề bài yêu cầu rõ: *"Produce a deduction trace containing the step number, active clue identifiers, SAT queries, verdict, and newly revealed clue"* *(AI - Project 2.pdf 4.4, description.md 2.5, plan.md 2.4)*.
  - Đồng thời đây là payload truyền qua `on_step(step)` cho GUI animation *(FAQ #4, plan.md 1.1, 2.5)* và nguồn dữ liệu cho Benchmark *(plan.md 2.4)*.
- **Câu hỏi cần chốt với nhóm (`Q07`, `Q08`):**
  1. TV5 có cần thêm trường nào trong `DeductionStep` để vẽ `trace_panel.py` và animate trên `board_widget.py` mà không phải gọi ngược vào `GameEngine` không (ví dụ `public_state_after` hay chỉ cần `target_cell`, `verdict`, `newly_revealed_clue`, `cnf_stats`)?
  2. Bước kết thúc bất thường (`AMBIGUOUS` hoặc `INCONSISTENT`, không lật được thẻ mới) có được ghi thành 1 `DeductionStep` cuối cùng trong danh sách trả về của `run_auto_solve` (với `target_cell=None`, `verdict=None`, `terminal_state="AMBIGUOUS"|"INCONSISTENT"`) để GUI hiển thị nguyên nhân dừng không?
  3. Nhóm có cần giữ thêm trường tùy chọn hỗ trợ thống kê `reveal_waves` (như `forced_candidates`) không, dù giảng viên đã cho phép bỏ qua `reveal_waves` theo `FAQ #12`?

---

#### [ ] 1.2.10. `HintResult` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Một đối tượng bất biến biểu diễn kết quả gợi ý công khai, đủ linh hoạt để hỗ trợ cả hai cách gợi ý theo `FAQ #5`: (a) chỉ ra **nhân vật tiếp theo có thể chứng minh được** (`target_cell`), và/hoặc (b) chỉ ra **tập nhân vật/manh mối liên quan nên cân nhắc** (`relevant_clue_ids`, `relevant_cells`), kèm lý do khi không có gợi ý *(chi tiết trường đề xuất xem [Mục 2.2](#22-đề-xuất-cấu-trúc-hintresult))*.
- **Vì sao (gắn với đề bài & FAQ):**
  - `FAQ #5` nêu rõ: *"Hoặc là hint người tiếp theo có thể đoán được, hoặc là hint những người nên cân nhắc để đoán ra người tiếp theo"* *(description.md 4.1)*; `AI - Project 2.pdf 4.1 & 4.4` yêu cầu Hint chỉ ra manh mối liên quan và/hoặc nhân vật chứng minh được tiếp theo và **tuyệt đối không đọc hidden solution**.
- **Câu hỏi cần chốt với nhóm (`Q07`, `Q10`):**
  1. **Mức độ lộ thông tin của Hint trên GUI:** Khi người chơi bấm nút `Hint`, TV5 muốn: (a) chỉ highlight `target_cell` + các manh mối liên quan (không lộ ngay `CRIMINAL`/`INNOCENT` để người chơi tự suy luận), hay (b) hiển thị luôn cả `suggested_status`? *(Nếu `HintResult` chứa đủ `target_cell`, `suggested_status`, `relevant_clue_ids`, `relevant_cells`, GUI có toàn quyền chọn mức hiển thị — cần chốt với TV5!)*
  2. **Mức độ chi tiết của `relevant_clue_ids`:** Với lưới 3×3–5×5, TV4 lấy các manh mối đang ngửa có tham chiếu tới `target_cell` (hoặc toàn bộ active clues nếu suy luận gián tiếp nhiều bước, hoặc tìm tập con tối thiểu tối giản — minimal unsatisfiable subset đơn giản). Nhóm chốt mức độ nào là đủ trong khung thời gian 7 ngày? *(Cần xác nhận với nhóm)*

---

#### [ ] 1.2.11. `UniquenessResult` *(plan.md 1.1)*

- **TV4 cần gì:**
  - Một đối tượng bất biến phân biệt rạch ròi đúng **3 nhánh kết quả** (`NO_SOLUTION`, `UNIQUE`, `MULTIPLE_SOLUTIONS`), lưu tối đa 2 nghiệm đại diện $M, M'$ dạng `Mapping[CellID, Status] | None` *(bọc `types.MappingProxyType`)* để TV1 debug puzzle khi bị mơ hồ và thống kê CNF/SAT *(chi tiết trường đề xuất xem [Mục 2.3](#23-đề-xuất-cấu-trúc-uniquenessresult))*.
- **Vì sao (gắn với đề bài & FAQ):**
  - Mọi màn chơi hợp lệ bắt buộc có nghiệm duy nhất *(AI - Project 2.pdf 2.2, 4.4, FAQ #9)*. TV1 phụ thuộc trực tiếp vào `uniqueness.py` của TV4 ở tối 26/11 để nghiệm thu đủ 6 puzzle chuẩn *(schedule.md, plan.md 2.1 DoD #2, 2.4)*.
- **Câu hỏi cần chốt với nhóm (`Q07`, `Q13`):**
  1. `first_model` và `second_model` trong `UniquenessResult` nên dùng key là `CellID` với value là `Status` (`Mapping[CellID, Status] | None`, bọc `types.MappingProxyType`) cho dễ đọc khi TV1 kiểm tra puzzle, hay giữ dạng raw `Mapping[int, bool] | None`? *(TV4 khuyến nghị `Mapping[CellID, Status] | None` bọc `MappingProxyType` kèm `differing_cells: tuple[CellID, ...]` — hoặc `tuple[tuple[CellID, Status], ...] | None` nếu nhóm cần hashable.)*
  2. Trong trường hợp màn demo kẹt giữa chừng (nếu nhóm chủ động thiết kế 1 màn kẹt để làm failure case theo `FAQ #13`), màn đó có cần thỏa `UNIQUE` trên toàn bộ clues hay được phép là `MULTIPLE_SOLUTIONS`? *(Cần xác nhận với nhóm để TV1 & TV4 kiểm định nhất quán tối 26/11)*

---

## 2. Đề xuất cấu trúc trường dữ liệu cho `DeductionStep`, `HintResult` và `UniquenessResult`

> **Lưu ý:** Toàn bộ các bảng dưới đây là **đề xuất của TV4** để đưa vào buổi họp GĐ 0 (trước 18:00 ngày 23/11) cho **TV1 và cả nhóm duyệt, chỉnh sửa và chốt** vào `core/contracts/models.py` (`Q07`). Tất cả khai báo dạng `@dataclass(frozen=True)`; các trường ánh xạ dùng thống nhất **`Mapping[K, V]` bọc `types.MappingProxyType`** (không dùng `dict` thuần để tránh bị mutate nội dung trong frozen dataclass; nếu nhóm cần hỗ trợ `hash()`, chuyển thống nhất sang `tuple[tuple[K, V], ...]`).

### 2.1. Đề xuất cấu trúc `DeductionStep`

Để ghi lại đầy đủ chi tiết truy vấn SAT mà không làm phình cấu trúc, TV4 đề xuất kèm một bản ghi con `SATQueryRecord` (đề xuất để nhóm duyệt) chứa: `purpose: str` (`"consistency"` | `"check_criminal"` | `"check_innocent"`), `target_cell: CellID | None`, `assumptions: tuple[int, ...]`, `is_sat: bool`, `from_cache: bool`, `metrics: SATMetrics | None` (`None` khi `from_cache=True`).

| Tên trường | Kiểu đề xuất | Ý nghĩa & Liên kết yêu cầu |
|---|---|---|
| `step_number` | `int` | Số thứ tự bước suy diễn $t$ (bắt đầu từ `1`) *(AI - Project 2.pdf 4.4, description.md 2.5)*. |
| `active_clue_ids` | `tuple[str, ...]` | Danh sách ID các manh mối đang lật ngửa (hoạt động) trong $KB_t$ tại bước $t$ *(AI - Project 2.pdf 4.4)*. |
| `sat_queries` | `tuple[SATQueryRecord, ...]` | Danh sách đầy đủ các truy vấn SAT (kèm `assumptions`, kết quả, `SATMetrics`, cờ `from_cache`) đã thực hiện ở bước $t$ *(AI - Project 2.pdf 4.4, plan.md 2.4)*. |
| `target_cell` | `CellID \| None` | Ô nhân vật được chọn để đưa phán quyết (theo thứ tự row-major); `None` nếu bước này dừng do `AMBIGUOUS`, `INCONSISTENT` hoặc `TIMEOUT` *(plan.md 2.4)*. |
| `verdict` | `Status \| None` | Phán quyết rút ra cho `target_cell` (`Status.CRIMINAL` hoặc `Status.INNOCENT`); **chỉ dùng `None`** khi không có phán quyết (dừng do `AMBIGUOUS`, `INCONSISTENT` hoặc `TIMEOUT`) — không dùng `Status.UNKNOWN` cho nghĩa này *(AI - Project 2.pdf 4.4)*. |
| `verdict_code` | `VerdictCode \| None` | Mã phản hồi từ `IGameEngine.submit_verdict` (`ACCEPTED`, `INCONSISTENT`, ...); `None` nếu không gọi `submit_verdict` (ví dụ dừng do `AMBIGUOUS`). |
| `newly_revealed_clue` | `Clue \| None` | Manh mối mới vừa được lật mở sau khi `verdict` được chấp nhận; `None` nếu bước này không lật thẻ mới *(AI - Project 2.pdf 4.4, description.md 2.5)*. |
| `cnf_stats` | `CNFStats \| None` | Thống kê số biến chính, biến phụ và số mệnh đề của $KB_t$ tại bước $t$ (phục vụ GUI trace panel & Benchmark) *(plan.md 2.4, 2.5)*. |
| `sat_calls_count` | `int` | Tổng số lệnh gọi `ISATSolver.solve()` thực tế trong bước $t$ (không tính các lần bỏ qua nhờ Model Caching) *(description.md 2.7)*. |
| `cache_hits_count` | `int` | Số lượng truy vấn phản chứng được rút gọn nhờ Model Caching trong bước $t$ (bằng `0` khi tắt caching) *(plan.md 2.4)*. |
| `forced_candidates` | `tuple[CellID, ...]` | *(Tùy chọn)* Danh sách tất cả các ô bị ép buộc tại $KB_t$ theo thứ tự row-major; hữu ích cho hiển thị GUI hoặc tính `reveal_waves` tùy chọn *(FAQ #12)*. |
| `terminal_state` | `str` *(hoặc Enum `SolveStatus`)* | Trạng thái sau bước $t$: `"IN_PROGRESS"`, `"SOLVED"`, `"AMBIGUOUS"`, `"INCONSISTENT"`, hoặc `"TIMEOUT"`; giúp GUI animation biết điểm dừng và thông báo kết quả *(FAQ #4, plan.md 2.4)*. |

### 2.2. Đề xuất cấu trúc `HintResult`

| Tên trường | Kiểu đề xuất | Ý nghĩa & Liên kết yêu cầu |
|---|---|---|
| `available` | `bool` | `True` nếu tìm được gợi ý hợp lệ từ $KB_t$; `False` nếu bảng đã giải xong, bị `AMBIGUOUS` (không có ô ép buộc) hoặc `INCONSISTENT`. |
| `reason_code` | `str` *(hoặc Enum `HintReason`)* | Mã phân loại: `"FORCED_CELL_FOUND"`, `"NO_FORCED_CELL"`, `"ALREADY_SOLVED"`, `"INCONSISTENT"` để GUI xử lý giao diện nhất quán. |
| `target_cell` | `CellID \| None` | Nhân vật bị ép buộc tiếp theo (chọn tất định theo row-major) mà người chơi có thể chứng minh được ngay; `None` nếu `available=False` *(FAQ #5, AI - Project 2.pdf 4.4)*. |
| `suggested_status` | `Status \| None` | Trạng thái bị ép buộc (`CRIMINAL` / `INNOCENT`) của `target_cell` suy ra từ $KB_t$ công khai; GUI có thể chọn hiển thị hoặc ẩn đi tùy chế độ gợi ý *(FAQ #5)*. |
| `relevant_clue_ids` | `tuple[str, ...]` | Danh sách ID các manh mối **đã lật ngửa** liên quan tới việc chứng minh `target_cell`, giúp GUI highlight vùng gợi ý *(FAQ #5, AI - Project 2.pdf 4.1, plan.md 2.5)*. |
| `relevant_cells` | `tuple[CellID, ...]` | Danh sách các ô/nhân vật nên cân nhắc (ví dụ các ô nằm trong vùng của `relevant_clue_ids`) để suy ra `target_cell` *(FAQ #5)*. |
| `message` | `str` | Thông điệp ngắn gọn (chỉ dựa trên thông tin công khai) giải thích gợi ý cho người chơi. |
| `sat_calls` | `int` | *(Tùy chọn)* Số lần gọi SAT để tạo gợi ý, phục vụ theo dõi hiệu năng phản hồi trên GUI. |

### 2.3. Đề xuất cấu trúc `UniquenessResult`

| Tên trường | Kiểu đề xuất | Ý nghĩa & Liên kết yêu cầu |
|---|---|---|
| `status` | `str` *(hoặc Enum `UniquenessStatus`)* | Phân loại đúng 3 nhánh bắt buộc: `"NO_SOLUTION"` (vô nghiệm), `"UNIQUE"` (nghiệm duy nhất), `"MULTIPLE_SOLUTIONS"` ($\ge 2$ nghiệm), kèm tùy chọn `"TIMEOUT"` *(plan.md 2.4 — nhiệm vụ, FAQ #9)*. |
| `is_unique` | `bool` | Cờ tiện dụng: `True` khi và chỉ khi `status == "UNIQUE"`, ngược lại `False` *(FAQ #9)*. |
| `solutions_found` | `int` | Số nghiệm phân biệt trên biến chính đã tìm thấy: `0` (vô nghiệm), `1` (duy nhất), hoặc `2` (đã tìm thấy ít nhất 2 nghiệm khác nhau và dừng sớm). |
| `first_model` | `Mapping[CellID, Status] \| None` *(bọc `types.MappingProxyType`)* | Nghiệm đầu tiên $M$ bất biến ánh xạ trên toàn bộ $N^2$ ô (`None` nếu `NO_SOLUTION`); nếu cần hashable thì đổi sang `tuple[tuple[CellID, Status], ...] \| None` *(description.md 3.2 luồng C)*. |
| `second_model` | `Mapping[CellID, Status] \| None` *(bọc `types.MappingProxyType`)* | Nghiệm thứ hai $M' \neq M$ bất biến tìm được sau khi thêm blocking clause (`None` nếu `NO_SOLUTION` hoặc `UNIQUE`), giúp TV1 sửa map mơ hồ *(description.md 3.2 luồng C)*. |
| `differing_cells` | `tuple[CellID, ...]` | Danh sách các ô (theo thứ tự row-major) có trạng thái khác nhau giữa `first_model` và `second_model` (rỗng nếu không phải `MULTIPLE_SOLUTIONS`). |
| `cnf_stats` | `CNFStats \| None` | Thống kê số biến chính, biến phụ và số mệnh đề của toàn bộ tập manh mối đầu vào. |
| `first_solve_metrics` | `SATMetrics \| None` | Chỉ số `SATMetrics` của lần gọi `DPLL(F)`. |
| `second_solve_metrics` | `SATMetrics \| None` | Chỉ số `SATMetrics` của lần gọi `DPLL(F ∧ B)` (`None` nếu lần gọi đầu trả `UNSAT`). |

---

## 3. Kế hoạch kiểm thử (`tests/test_agent/`)

Kế hoạch gồm **30 test case** độc lập, chia thành 5 nhóm (`entailment`: 7, `loop`: 9, `hint`: 5, `uniqueness`: 5, `caching`: 4), chạy hoàn toàn bằng **3 stub nội bộ** ngay trong GĐ 1 (tối 23/11 – 25/11) trước khi ghép module thật ở GĐ 2 *(plan.md 2.4, schedule.md)*.

### Bảng ma trận kiểm thử (30 Test Cases)

| ID | Nhóm | Mô tả tình huống | Kỳ vọng | Stub cần có |
|---|---|---|---|---|
| `TC-ENT-01` | `entailment` | **Ví dụ chuẩn trong đề (`AI - Project 2.pdf 3.4`):** $KB = (C_A \lor C_B) \land (\neg C_A \lor C_B)$ trên 2 ô chưa giải `A1`, `B1`. | `check_consistency` = `True`; `classify_character(B1)` = `CRIMINAL` ($KB \land \neg C_{B1}$ UNSAT); `classify_character(A1)` = `UNKNOWN` (cả hai nhánh SAT). | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-02` | `entailment` | **Ép buộc `INNOCENT`:** `A1` đã chứng minh `INNOCENT` và có clue `SAME(A1, B1)` (hoặc `EXACTLY(0, Row 1)`). | `check_consistency` = `True`; `classify_character(B1)` = `INNOCENT` ($KB \land \neg C_{B1}$ SAT, $KB \land C_{B1}$ UNSAT). | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-03` | `entailment` | **Phân biệt Satisfying Model vs Logical Consequence (`description.md 2.5`):** $KB = (C_{A1} \lor C_{B1})$ — tồn tại model $C_{A1}=\text{True}, C_{B1}=\text{False}$ nhưng không có biến nào đúng trong mọi model. | `classify_all` trả `UNKNOWN` cho cả `A1` và `B1`; tuyệt đối không lấy giá trị của một model làm verdict. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-04` | `entailment` | **KB mâu thuẫn (`INCONSISTENT` — DoD `plan.md 2.4`):** $KB_t$ chứa hai ràng buộc trái ngược nhau (vd: `A1=CRIMINAL` và clue `FACT(A1=INNOCENT)`). | `check_consistency(state)` = `False`; `classify_character` / `classify_all` báo đúng `INCONSISTENT` (không trả nhầm `CRIMINAL` chỉ vì $KB \land \neg C_i$ UNSAT). *(Phụ thuộc quyết định `Q02`)* | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-05` | `entailment` | **KB không có thông tin ép buộc (công thức rỗng / tautology):** Chỉ mở sẵn 1 thẻ với clue không ràng buộc các ô còn lại. | `check_consistency` = `True`; mọi ô chưa giải đều trả `UNKNOWN`. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-06` | `entailment` | **Suy luận chuỗi nhiều mệnh đề (multi-hop):** `A1=CRIMINAL`, `SAME(A1, B1)`, `DIFFERENT(B1, C1)`, `EXACTLY(2, {A1, B1, C1, A2})`. | `classify_all` suy ra đồng thời `B1=CRIMINAL`, `C1=INNOCENT`, `A2=INNOCENT` trong cùng một trạng thái $KB_t$. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-ENT-07` | `entailment` | **Ô đã được chứng minh sẵn / bảng đã giải hết:** Gọi `classify_all` khi một phần hoặc toàn bộ $N^2$ ô đã có mặt trong `proved_verdicts`. | Chỉ xét các ô chưa giải (trả dict rỗng khi đã giải hết), không gọi `ISATSolver.solve()` cho các ô đã chứng minh. *(Phụ thuộc quyết định `Q10`)* | `StubEncoder`, `BruteForceStubSolver` |
| `TC-LOOP-01` | `loop` | **Giải trọn vẹn puzzle 3×3 hợp lệ (Happy path):** Bắt đầu với 1 thẻ mở sẵn ($KB_0$), mỗi thẻ lật ra mở khóa bước kế tiếp cho tới khi đủ 9/9 ô. | Kết thúc ở trạng thái `SOLVED`; trả về đủ 8 `DeductionStep` hợp lệ (`step_number` = `1..8`, đủ `active_clue_ids`, `sat_queries`, `verdict`, `newly_revealed_clue`); toàn bộ bảng khớp đáp án. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-02` | `loop` | **Khởi tạo nhiều thẻ mở sẵn (`FAQ #8`):** Puzzle 3×3 mở sẵn 3 thẻ ngay ở $KB_0$. | Vòng lặp chỉ cần chạy đúng 6 bước cho 6 ô còn lại; `active_clue_ids` ở bước 1 đã chứa đủ 3 clue ban đầu; kết thúc `SOLVED`. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-03` | `loop` | **Thứ tự chọn tất định row-major (`description.md 2.5`, `plan.md 2.4`):** Tại $KB_t$, đồng thời 3 ô `C1`, `A2`, `B1` cùng bị ép buộc. | Agent bắt buộc chọn `B1` trước (không chọn `A2` theo thứ tự chữ cái `'A2' < 'B1'`); chạy lại 3 lần cho trace hoàn toàn đồng nhất. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-04` | `loop` | **Trạng thái mơ hồ — Ambiguous puzzle (DoD `plan.md 2.4`, `FAQ #13`):** Puzzle giải được 2 bước đầu, tới bước 3 mọi ô còn lại đều `UNKNOWN`. | Agent **dừng ngay**, không đoán mò, không gọi `submit_verdict` ở bước 3 (kiểm qua `submitted_verdicts`); ghi nhận trạng thái dừng `AMBIGUOUS` với `target_cell=None`, `verdict=None`. *(Phụ thuộc quyết định `Q07`)* | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-05` | `loop` | **Trạng thái mâu thuẫn ngay từ $KB_0$ (DoD `plan.md 2.4`):** Puzzle lỗi có manh mối mâu thuẫn ngay lúc khởi tạo. | Agent phát hiện `INCONSISTENT` ở bước 1, dừng ngay lập tức, không gọi `submit_verdict` lần nào (`submitted_verdicts` rỗng). *(Phụ thuộc quyết định `Q02`, `Q07`)* | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-06` | `loop` | **Mâu thuẫn phát sinh giữa chừng sau khi lật thẻ mới:** $KB_0$ nhất quán và mở được ô `B1`, nhưng manh mối vừa lật của `B1` mâu thuẫn với $KB_1$. | Bước 1 thành công (`ACCEPTED`), bước 2 phát hiện `INCONSISTENT` ngay khi kiểm tra $KB_1$ và dừng vòng lặp an toàn. *(Phụ thuộc quyết định `Q02`, `Q07`)* | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-07` | `loop` | **Callback `on_step` cho Animation (`FAQ #4`):** Truyền một spy callback vào `run_auto_solve(engine, on_step=spy)` trên màn giải 4 bước; và thử thêm trường hợp `on_step=None`. | Với `spy`: được gọi đúng thứ tự sau từng bước với đúng `DeductionStep` tương ứng; với `on_step=None`: chạy trọn vẹn không lỗi. *(Phụ thuộc quyết định `Q08`)* | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-08` | `loop` | **Cách ly dữ liệu ẩn trong vòng lặp giải (`AI - Project 2.pdf 4.1`):** Gắn bẫy trong `MockGameEngine` gồm `@property` ném `AssertionError` cho các trường ẩn (`hidden_solution`, `unrevealed_clues`), spy `__getattr__` ghi/chặn truy cập thuộc tính không thuộc `IGameEngine`, và cờ giám sát `get_all_clues_for_uniqueness()`. | `run_auto_solve` hoàn tất đúng, chỉ gọi `get_public_state()` và `submit_verdict()`, không kích hoạt property bẫy, không đụng `__getattr__` cho dữ liệu ẩn, và `uniqueness_accessor_called == False`. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-LOOP-09` | `loop` | **Phòng vệ chống lặp vô hạn khi verdict bị từ chối bất ngờ:** Cấu hình `MockGameEngine` trả `VerdictCode.NOT_PROVABLE` (hoặc `CONTRADICTED`) cho nước đi hợp lệ mà Agent gửi lên tại bước $t$. | Agent phát hiện trạng thái không tiến triển sau khi bị từ chối, dừng vòng lặp an toàn thay vì lặp vô tận trên cùng một ô và ghi nhận mã/trạng thái dừng rõ ràng. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-HINT-01` | `hint` | **Gợi ý nhân vật bị ép buộc (`FAQ #5`):** Tại $KB_t$ có nhiều ô bị ép buộc (`C1`, `B1`, `A2`). | `get_hint(public_state)` trả `available=True`, `reason_code="FORCED_CELL_FOUND"`, `target_cell="B1"` (row-major), `suggested_status` đúng, `relevant_clue_ids` chỉ gồm các clue đã lật ngửa. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-HINT-02` | `hint` | **Không đọc hidden solution (`plan.md 2.4` — nhiệm vụ, `AI - Project 2.pdf 4.4`):** Gọi `get_hint` trên 2 `PublicState` giống hệt nhau trích ra từ 2 `MockGameEngine` cố tình có đáp án ẩn khác nhau ở các ô chưa mở. | Kết quả `HintResult` giống nhau 100%, không truy cập `MockGameEngine` hay bất kỳ trường ẩn nào (`uniqueness_accessor_called == False`); không bao giờ gợi ý ô chưa bị ép buộc dù đáp án ẩn đã xác định. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-HINT-03` | `hint` | **Hint ở trạng thái Ambiguous:** Mọi ô chưa mở trong `PublicState` đều `UNKNOWN`. | Trả `available=False`, `target_cell=None`, `suggested_status=None`, `reason_code="NO_FORCED_CELL"`; tuyệt đối không đoán mò. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-HINT-04` | `hint` | **Hint khi bảng đã giải xong:** Toàn bộ $N^2$ ô đã có mặt trong `proved_verdicts`. | Trả `available=False`, `target_cell=None`, `reason_code="ALREADY_SOLVED"`, số lần gọi SAT = `0`. *(Phụ thuộc quyết định `Q07`, `Q10`)* | `StubEncoder`, `BruteForceStubSolver` |
| `TC-HINT-05` | `hint` | **Hint khi $KB_t$ bị `INCONSISTENT`:** `PublicState` chứa tập manh mối tự mâu thuẫn. | Trả `available=False`, `target_cell=None`, `reason_code="INCONSISTENT"` thay vì trả về một ô giả tạo. *(Phụ thuộc quyết định `Q02`, `Q07`)* | `StubEncoder`, `BruteForceStubSolver` |
| `TC-UNIQ-01` | `uniqueness` | **Nhánh 1 — Vô nghiệm (`plan.md 2.4` — nhiệm vụ):** Toàn bộ tập clues của puzzle tự mâu thuẫn (`A1=CRIMINAL` và `A1=INNOCENT`). | `status="NO_SOLUTION"`, `is_unique=False`, `solutions_found=0`, `first_model=None`, `second_model=None`; chỉ gọi `ISATSolver.solve()` đúng **1 lần**. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-UNIQ-02` | `uniqueness` | **Nhánh 2 — Nghiệm duy nhất (`plan.md 2.4` — nhiệm vụ, `FAQ #9`):** Tập clues xác định duy nhất 1 nghiệm $M$ trên lưới 2×2 và 3×3. | `status="UNIQUE"`, `is_unique=True`, `solutions_found=1`, `first_model` khớp $M$, `second_model=None`, `differing_cells=()` ; gọi `solve()` đúng **2 lần** (lần 1 SAT, lần 2 với blocking clause UNSAT). | `StubEncoder`, `BruteForceStubSolver` |
| `TC-UNIQ-03` | `uniqueness` | **Nhánh 3 — Có $\ge 2$ nghiệm (`plan.md 2.4` — nhiệm vụ):** Tập clues thiếu ràng buộc (vd: `DIFFERENT(A1, B1)` trên lưới 2×2 có ít nhất 2 nghiệm khác nhau). | `status="MULTIPLE_SOLUTIONS"`, `is_unique=False`, `solutions_found=2`, `first_model != second_model`, `differing_cells` chứa đúng các ô khác nhau giữa 2 nghiệm. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-UNIQ-04` | `uniqueness` | **Blocking clause loại trừ biến phụ:** `StubEncoder` tạo công thức có nghiệm biến chính duy nhất nhưng chèn thêm 1 biến phụ tự do $a_1 = N^2 + 1$ có thể nhận cả `True` và `False`. | Blocking clause chỉ phủ định trên $N^2$ biến chính `1..N²` (không chứa biến phụ $a_1$) ⇒ lần giải 2 trả `UNSAT` ⇒ kết luận đúng `status="UNIQUE"`. | `StubEncoder` *(chế độ thêm biến phụ)*, `BruteForceStubSolver` |
| `TC-UNIQ-05` | `uniqueness` | **Không gây hiệu ứng phụ (No side-effects):** Kiểm tra tập clues đầu vào và công thức `CNFFormula` gốc trước và sau khi gọi `check_uniqueness`. | Danh sách clues đầu vào không bị chỉnh sửa; `first_solve_metrics` và `second_solve_metrics` đều được ghi nhận đầy đủ khi lần 1 SAT. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-CACHE-01` | `caching` | **Tương đương ngữ nghĩa (Bật vs Tắt Model Caching):** Chạy `classify_all` và `run_auto_solve` trên các kịch bản Solvable, Ambiguous, Inconsistent với `use_model_caching=False` và `use_model_caching=True`. | Kết quả phân loại mọi ô, thứ tự bước giải, phán quyết và trạng thái kết thúc giống nhau 100% giữa hai chế độ. | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-CACHE-02` | `caching` | **Giảm số lần gọi SAT (`description.md 3.2`, `plan.md 2.4`):** Trạng thái $KB_t$ 3×3 có 8 ô chưa giải, phần lớn là `UNKNOWN` (ví dụ chỉ có 1 clue yếu). | Tổng số lệnh gọi `ISATSolver.solve()` khi bật Model Caching **nhỏ hơn nghiêm ngặt** so với khi tắt caching, và `cache_hits_count > 0` được ghi nhận chính xác trong `DeductionStep`. | `StubEncoder`, `BruteForceStubSolver` |
| `TC-CACHE-03` | `caching` | **Vô hiệu hóa cache khi $KB_t \to KB_{t+1}$ (Cache Invalidation):** Ở bước 1 ô `C2` là `UNKNOWN` (có model $M_0$ gán `C2=False` và $M_1$ gán `C2=True`); sang bước 2 một thẻ mới lật mở ép buộc `C2=CRIMINAL`. | Agent xóa/làm mới cache khi chuyển sang $KB_2$, gọi lại kiểm tra và suy ra đúng `C2=CRIMINAL` (không dùng nhầm model $M_0$ cũ để kết luận sai `C2=UNKNOWN`). | `StubEncoder`, `BruteForceStubSolver`, `MockGameEngine` |
| `TC-CACHE-04` | `caching` | **Cô lập cache giữa các lời gọi độc lập & khi `UNSAT`:** Gọi `classify_all` trên hai `PublicState` khác nhau liên tiếp (trong đó có 1 trạng thái `INCONSISTENT`). | Không rò rỉ model cache từ `PublicState` trước sang `PublicState` sau; khi `DPLL(KB)` trả `UNSAT` (`model=None`), không lưu dữ liệu lỗi vào cache và trả `INCONSISTENT` sạch. | `StubEncoder`, `BruteForceStubSolver` |

### Đối chiếu độ phủ DoD & Nhiệm vụ cốt lõi của TV4 (`plan.md 2.4`)

| Hạng mục yêu cầu (`plan.md 2.4`) | Phân loại nguồn | Các test case phủ trực tiếp |
|---|---|---|
| Ambiguous luôn trả `UNKNOWN` và dừng an toàn (không đoán mò) | **DoD #1 (`plan.md 2.4`)** | `TC-ENT-01`, `TC-ENT-03`, `TC-ENT-05`, `TC-LOOP-04`, `TC-HINT-03` |
| Inconsistent luôn phát hiện `INCONSISTENT` | **DoD #1 (`plan.md 2.4`)** | `TC-ENT-04`, `TC-LOOP-05`, `TC-LOOP-06`, `TC-HINT-05`, `TC-CACHE-04` |
| `Hint` không đọc hidden solution | **Nhiệm vụ (`plan.md 2.4`)** | `TC-HINT-02` |
| Hành vi `Hint` (chọn ô ép buộc row-major, Ambiguous, đã giải xong, Inconsistent) | **Nhiệm vụ (`plan.md 2.4`, `FAQ #5`)** | `TC-HINT-01`, `TC-HINT-03`, `TC-HINT-04`, `TC-HINT-05` |
| `Uniqueness` phủ đủ 3 nhánh: vô nghiệm / duy nhất / $\ge 2$ nghiệm & loại trừ biến phụ | **Nhiệm vụ (`plan.md 2.4`, `FAQ #9`)** | `TC-UNIQ-01`, `TC-UNIQ-02`, `TC-UNIQ-03`, `TC-UNIQ-04`, `TC-UNIQ-05` |
| Cách ly dữ liệu ẩn & phòng vệ vòng lặp (`on_step` `FAQ #4`, nhiều thẻ mở sẵn `FAQ #8`, Model Caching) | **Nhiệm vụ (`plan.md 2.4`)** | `TC-LOOP-02`, `TC-LOOP-07`, `TC-LOOP-08`, `TC-LOOP-09`, `TC-CACHE-01` → `TC-CACHE-04` |

*(Ghi chú: DoD #2 của TV4 — xuất đầy đủ chỉ số benchmark và biểu đồ cho 6 puzzle chuẩn `2×3×3`, `2×4×4`, `2×5×5` — không thuộc unit test với stub và sẽ được nghiệm thu tại GĐ 3B: `[chờ kết quả benchmark GĐ 3B]`.)*

---

## 4. Đặc tả hành vi cho ba Stub phát triển song song của TV4

Ngay sau khi `core/contracts/` được đóng băng ở GĐ 0 (trước 18:00 ngày 23/11), TV4 sẽ xây dựng 3 stub đặt trong `tests/test_agent/` (chỉ dùng cho kiểm thử độc lập ở GĐ 1, tuyệt đối không đưa vào mã sản phẩm `agent/`). Dưới đây là đặc tả hành vi chi tiết (chưa viết mã).

### 4.1. `StubEncoder` *(triển khai giả lập `ICNFEncoder`)*

- **Mục đích:** Thay thế tạm thời `logic/cnf_encoder.py` của TV2 trong GĐ 1 để TV4 phát triển và kiểm thử đầy đủ `entailment.py`, `logic_agent.py`, `hint_engine.py`, `uniqueness.py` mà không cần chờ TV2.
- **Nguyên tắc thiết kế tối giản (tránh viết lại encoder của TV2):**
  - **Ưu tiên chế độ bảng kịch bản `clue_id -> clauses`:** Khi khởi tạo, `StubEncoder` nhận một bảng ánh xạ trực tiếp từ mỗi `clue_id` (hoặc khóa kịch bản) sang danh sách mệnh đề CNF đã chuẩn bị sẵn cho test case đó. **Không tự cài đặt lại bộ biên dịch đủ 6 mẫu clue** (`FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST`) của TV2 để tránh trùng lặp công việc và tránh tự sinh lỗi biên dịch trong tầng test.
  - Chỉ tự động sinh các mệnh đề đơn vị `[+v]` (cho `CRIMINAL`) / `[-v]` (cho `INNOCENT`) tương ứng với `proved_verdicts` trong `PublicState`.
  - Hỗ trợ tùy chọn **`inject_free_aux_vars: int = 0`** (cố tình cấp phát thêm biến phụ tự do $\ge N^2 + 1$ không bị ràng buộc chặt) để kiểm thử riêng `TC-UNIQ-04` (xác minh blocking clause không chặn nhầm biến phụ).
  - Hỗ trợ tùy chọn **`force_inconsistent: bool = False`** (chèn cặp mệnh đề đối nghịch `[+1], [-1]`) để tạo nhanh tình huống $KB$ mâu thuẫn mà không cần dựng bảng kịch bản phức tạp.
- **Hành vi các phương thức:**
  - `map_cell_to_var` / `map_var_to_cell`: ánh xạ hai chiều tất định theo đúng thứ tự **row-major** (`A1 -> 1`, `B1 -> 2`, ..., khớp chuẩn `Q04`).
  - `resolve_region`: trả kết quả từ bảng tra kịch bản tối giản (nếu test cần kiểm tra `relevant_cells` ở `Hint`), không tự cài bộ phân giải vùng đầy đủ của TV2.
  - `encode_kb(public_state)`: tra `clauses` theo `clue_id` của từng `revealed_clue` trong `public_state`, ghép thêm mệnh đề đơn vị của `proved_verdicts`, và trả về `(CNFFormula, CNFStats)` bất biến với `num_primary_vars = size * size`, `num_aux_vars` và `num_clauses` chính xác. Tuyệt đối không đọc bất cứ thông tin nào ngoài `public_state`.
  - `encode_clues(clues, size, known_verdicts=None)` *(theo hợp đồng `Q09`)*: tra bảng `clue_id -> clauses` cho toàn bộ danh sách `clues`, ghép thêm biến phụ (nếu `inject_free_aux_vars > 0`) và `known_verdicts` (nếu có).
- **Móc kiểm tra (Instrumentation):** Đếm số lần gọi `encode_kb` và lưu lại `PublicState` đầu vào gần nhất để test xác nhận Agent không gọi mã hóa dư thừa.
- **Điều kiện thay thế:** Gỡ bỏ trong integration test ở **GĐ 2 – Mốc 1 (26/11)** khi ghép `CNFEncoder` thật của TV2 *(schedule.md)*.

---

### 4.2. `BruteForceStubSolver` *(triển khai giả lập `ISATSolver`)*

- **Mục đích:** Thay thế tạm thời `solver/dpll_solver.py` của TV3 trong GĐ 1 bằng một oracle vét cạn chính xác tuyệt đối 100% trên bài toán nhỏ, giúp TV4 tin cậy hoàn toàn vào kết quả SAT/UNSAT khi debug thuật toán Entailment, Model Caching và Uniqueness.
- **Dữ liệu khởi tạo / Cấu hình:**
  - Giới hạn an toàn: chỉ chạy vét cạn trên các công thức có tổng số biến nhỏ (ví dụ $\le 14$ biến — tối đa $2^{14} = 16\,384$ phép gán; nếu vượt ngưỡng thì ném lỗi bảo vệ để tránh treo pytest).
  - Tùy chọn thứ tự duyệt phép gán (tất định từ `False` trước `True`, hoặc ngược lại) để dễ kiểm thử hành vi Model Caching trong `TC-CACHE-02` và `TC-CACHE-03`.
- **Hành vi `solve(cnf, assumptions=None)`:**
  - **Không bao giờ mutate** `cnf` hay `assumptions` đầu vào (trước và sau khi gọi có thể kiểm tra bình đẳng cấu trúc).
  - Nếu `assumptions` chứa hai literal đối nghịch (`+v` và `-v`) hoặc `cnf.clauses` chứa mệnh đề rỗng `()`, trả ngay `SATResult(is_sat=False, model=None, metrics=...)`.
  - Gán cố định các biến trong `assumptions`, sau đó duyệt vét cạn tất định toàn bộ tổ hợp giá trị `True`/`False` cho các biến còn lại từ `1..num_total_vars`.
  - Với phép gán đầu tiên thỏa mãn toàn bộ mệnh đề trong `cnf.clauses`: dừng sớm và trả về `SATResult(is_sat=True, model=MappingProxyType(complete_assignment), metrics=...)` (đảm bảo `model` bất biến và đủ toàn bộ biến `1..num_total_vars`).
  - Nếu không có phép gán nào thỏa mãn: trả `SATResult(is_sat=False, model=None, metrics=...)`.
  - Điền `SATMetrics` hợp lệ về kiểu (`decisions`, `propagations`, `backtracks` đặt giá trị giả lập không âm nhất quán, `runtime_ms` đo thật bằng `perf_counter()`).
- **Móc kiểm tra (Spy / Instrumentation):**
  - Ghi nhận bộ đếm `call_count` (tổng số lần `solve()` được gọi) và danh sách `call_history` (lưu `assumptions`, `num_clauses`, `is_sat` của từng lượt gọi) cùng phương thức `reset_stats()`.
  - Nhờ móc này, nhóm test `caching` (`TC-CACHE-02`) và `uniqueness` (`TC-UNIQ-01`, `TC-UNIQ-02`) khẳng định chính xác số lần gọi SAT thực tế.
- **Điều kiện thay thế:** Gỡ bỏ trong integration test ở **GĐ 2 – Mốc 1 (26/11)** khi ghép `DPLLSolver` thật của TV3 *(schedule.md)*.

---

### 4.3. `MockGameEngine` *(triển khai giả lập `IGameEngine`)*

- **Mục đích:** Thay thế tạm thời `engine/game_engine.py` của TV1 trong GĐ 1 để kiểm thử toàn bộ vòng lặp suy diễn tự động (`run_auto_solve`), callback animation (`on_step`), ranh giới cách ly dữ liệu ẩn và các ca biên (`Ambiguous`, `Inconsistent`, nhiều thẻ mở sẵn).
- **Dữ liệu khởi tạo / Cấu hình kịch bản:**
  - Cho phép khởi tạo trực tiếp từ bộ kịch bản dựng sẵn trong bộ nhớ (không cần đọc file JSON thật) gồm:
    - Kích thước lưới `size`, đáp án ẩn `hidden_solution: Mapping[CellID, Status]`, toàn bộ manh mối `all_clues: Mapping[CellID, Clue]`, và tập thẻ mở sẵn ban đầu `initial_revealed: tuple[CellID, ...]` (hỗ trợ **$\ge 1$ thẻ, thường 1–4**, theo `FAQ #8`).
    - **Hai chế độ thẩm định khi nhận `submit_verdict`:**
      1. *Chế độ mặc định (đối chiếu `hidden_solution`):* Chấp nhận khi `status == hidden_solution[cell]`. **Lưu ý quan trọng:** ở chế độ này, nếu Agent **đoán mò nhưng vô tình trúng** `hidden_solution`, `MockGameEngine` vẫn sẽ trả `ACCEPTED`! Vì vậy, các bài test chống đoán mò (như `TC-LOOP-04`) **bắt buộc phải kiểm chứng trực tiếp qua danh sách `submitted_verdicts`** (khẳng định không có nước đi đoán nào được gửi lên), **không** chỉ dựa vào mã `ACCEPTED`.
      2. *Chế độ tùy chọn tự kiểm entailment (strict no-guess mode):* Nhận thêm một bộ kiểm tra nội bộ (dùng `StubEncoder` + `BruteForceStubSolver`, hoặc danh sách các ô hợp lệ tại từng trạng thái $KB_t$) để trả đúng `VerdictCode.NOT_PROVABLE` nếu Agent gửi nước đi đoán dù trùng `hidden_solution`. Ngoài ra hỗ trợ kịch bản cưỡng bức trả `NOT_PROVABLE` / `CONTRADICTED` tại một ô chỉ định để test chống lặp vô hạn ở `TC-LOOP-09`.
- **Hành vi các phương thức:**
  - `get_public_state()`: luôn tạo và trả về một `PublicState` **bất biến** mới chỉ chứa các thẻ đã mở (gồm `initial_revealed` và các thẻ đã được `ACCEPTED`) cùng manh mối tương ứng; **tuyệt đối không** đính kèm `hidden_solution` hay manh mối đang úp.
  - `submit_verdict(cell, status)`:
    - Ghi nhận `(cell, status)` vào `submitted_verdicts`.
    - Nếu chấp nhận (`ACCEPTED`): cập nhật danh sách thẻ đã mở nội bộ, trả về `VerdictResponse` chứa `VerdictCode.ACCEPTED`, `PublicState` mới và đúng `newly_revealed_clue` của ô `cell`.
    - Nếu từ chối (`NOT_PROVABLE` hoặc `CONTRADICTED`): **giữ nguyên hoàn toàn** trạng thái bàn chơi, không lật thẻ, `revealed_clue=None`.
  - `restart()`: khôi phục trạng thái về đúng `initial_revealed` ban đầu và trả về `PublicState` khởi tạo.
  - `list_maps()` / `load_map(map_id)` / `load_puzzle(path)`: cung cấp các màn giả lập định danh sẵn (ví dụ `"mock_3x3_solvable"`, `"mock_3x3_multi_init"`, `"mock_3x3_ambiguous"`, `"mock_3x3_inconsistent"`).
  - `get_all_clues_for_uniqueness()`: trả về danh sách toàn bộ `all_clues`, đồng thời **bật cờ giám sát** `uniqueness_accessor_called = True`.
- **Móc kiểm tra an toàn (Leak & Spy Assertions):**
  - **Chống truy cập dữ liệu ẩn (`TC-LOOP-08`):** Cung cấp `@property` bẫy cho các tên thuộc tính ẩn (`hidden_solution`, `unrevealed_clues`, ...) ném `AssertionError` ngay nếu bị đọc từ bên ngoài, kết hợp spy `__getattr__` ghi nhận/chặn mọi truy cập thuộc tính ngoài giao diện `IGameEngine` (dữ liệu nội bộ thật được cất trong cấu trúc riêng biệt không phơi bày).
  - Ghi lại `submitted_verdicts: list[tuple[CellID, Status]]` để xác minh thứ tự row-major (`TC-LOOP-03`) và xác minh Agent **không gửi verdict đoán mò** ở trạng thái `AMBIGUOUS` (`TC-LOOP-04`) hay `INCONSISTENT` (`TC-LOOP-05`).
  - Dùng cờ `uniqueness_accessor_called` để khẳng định trong `TC-LOOP-08` và `TC-HINT-02` rằng vòng lặp giải và hàm `Hint` **không bao giờ** gọi `get_all_clues_for_uniqueness()`.
- **Điều kiện thay thế:** Gỡ bỏ trong kiểm thử E2E ở **GĐ 3A (27/11)** khi ghép `GameEngine` thật của TV1 và 6 puzzle JSON chuẩn *(schedule.md)*.
