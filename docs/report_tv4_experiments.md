# THIẾT KẾ THỰC NGHIỆM & BẢN NHÁP MỤC "EXPERIMENTS" — PROJECT 2: GRIDUCTIVE SOLVER (PHẦN TV4)

- **Dự án:** Project 2 — *Griductive Solver* (CSC14003 – Nhập môn Trí tuệ Nhân tạo, ĐH Khoa học Tự nhiên, ĐHQG-HCM)
- **Người phụ trách:** Nguyên — Thành viên 4 (TV4: `agent/`, `experiments/`, `tests/test_agent/`, `tests/test_experiments/`, mục *Algorithms* & *Experiments* trong `Report.pdf`) `(plan.md 2.4, schedule.md)`
- **Trạng thái hiện tại:** **Đã hoàn thành GĐ 2 (Mốc 1 + Uniqueness 15 puzzle) và GĐ 3B (Benchmark chính thức C0–C7 + 4 biểu đồ RQ1–RQ4)** trên nhánh `feat/tv4-benchmark-final` (nền `origin/dev` sau khi PR #3 `feat/tv2-logic` đã merge vào `dev` tại `9d2140b`). Toàn bộ bảng và nhận xét dưới đây sử dụng **100% số liệu thật** từ `CNFEncoder` (TV2, `direct` & `sinz`) + `DPLLSolver` (TV3) + `DeductiveLogicAgent` (TV4), không dùng bất kỳ số liệu stub nào.
- **Tài liệu nguồn đối chiếu:** `description.md`, `plan.md`, `schedule.md`, `AI - Project 2.pdf`, `docs/tv4_agent_conventions.md` và bảng FAQ chính thức của giảng viên (`FAQ #1–#15` trong `description.md 4.1`).

---

## 1. Mục tiêu và Câu hỏi Nghiên cứu

### 1.1. Mục tiêu thực nghiệm
Hệ thống thực nghiệm (`Source/experiments/benchmark.py`, `Source/experiments/plots.py`, `Source/experiments/uniqueness_report.py`) nhằm đánh giá định lượng và khách quan toàn bộ hệ thống *Griductive Solver* hoàn chỉnh (`GameEngine + ICNFEncoder + DPLLSolver + DeductiveLogicAgent`) theo đúng yêu cầu chấm điểm phần Thực nghiệm (10 điểm) và `Report.pdf` (30đ, trong đó có mục *Experiments*) `(description.md 2.7–2.8, AI - Project 2.pdf 4.5–4.6)`. Cụ thể:
1. Đo lường đầy đủ các nhóm chỉ số bắt buộc trên **cùng một bộ 10 màn chơi chuẩn** (`4×3×3`, `4×4×4`, `2×5×5`, vượt mức tối thiểu 6 màn của `FAQ #2`) cùng tùy chọn **3 màn `extensions/`** (`--include-extensions`) và **2 màn `edge_cases/`** `(docs/tv4_agent_conventions.md Mục 5)`.
2. So sánh có kiểm soát (controlled comparison) giữa các lựa chọn thiết kế cốt lõi ở ba tầng: **mã hóa CNF** (TV2), **bộ giải DPLL & heuristic** (TV3), và **tối ưu Model Caching ở Logic Agent** (TV4) `(plan.md 2.2–2.4)`.
3. Kiểm chứng độ tin cậy, tính tất định (determinism), tính tương đương kết quả giữa các cấu hình và hành vi an toàn không đoán mò (No-Guess) trên cả màn chơi hợp lệ lẫn ca biên/ca thất bại/timeout `(description.md 2.5, 2.7, FAQ #13)`.

### 1.2. Các câu hỏi nghiên cứu (Research Questions)

| Mã RQ | Câu hỏi nghiên cứu | Thành phần đánh giá chính | Chỉ số trả lời chính *(khớp Mục 4 & 5)* |
| :--- | :--- | :--- | :--- |
| **RQ1** | **Khả năng mở rộng (Scalability):** Khi kích thước lưới tăng từ `3×3` (9 biến chính) lên `4×4` (16 biến chính) và `5×5` (25 biến chính), kích thước công thức CNF, số lần gọi SAT, chi phí tìm kiếm DPLL và thời gian giải (`total_runtime_ms`) tăng theo quy luật nào? Hệ thống có giải trọn vẹn các màn `5×5` trong ngưỡng timeout đề xuất không? `(description.md 2.7, plan.md 3.1)` | Toàn hệ thống (tất cả kích thước lưới) | `primary_vars`, `aux_vars_final`, `aux_vars_max`, `cnf_clauses_final`, `sat_calls_total`, `total_decisions`, `total_backtracks`, `total_runtime_ms`, `terminal_status`, `solved_rate` *(dẫn xuất)* |
| **RQ2** | **Chiến lược mã hóa CNF đếm theo kích thước vùng $\|R\|$ thực (Direct vs. Sinz):** Theo `description.md 2.3`, các vùng cơ bản ở mọi kích thước lưới đều nhỏ (`NEIGHBORS` $\le 8$, `ROW`/`COL` $\le N \le 5$), còn vùng chỉ lớn hơn ở `EXPLICIT` nhiều ô hoặc vùng mở rộng (như `BOUNDARY` 8/12/16 ô nếu cài đặt). Giữa *Direct Combinatorial Encoding* (không biến phụ; $\binom{\|R\|}{k+1}$ mệnh đề cho `AT_MOST(k)` và $\binom{\|R\|}{\|R\|-k+1}$ cho `AT_LEAST(k)`) và *Sequential Counter / Sinz Encoding* (mã hóa `AT_MOST(k)` tốn $O(\|R\|\cdot k)$ biến phụ và mệnh đề; `AT_LEAST(k)` quy về `AT_MOST(\|R\|−k)` trên literal phủ định nên tốn $O(\|R\|\cdot(\|R\|-k))$) `(description.md 2.3, plan.md 2.2)`, sự đánh đổi về số biến phụ, số mệnh đề, `total_propagations` và thời gian giải khác nhau ra sao theo kích thước vùng thực tế $\|R\|$ (`max_region_size`) của từng clue? | `ICNFEncoder` (TV2) + `ISATSolver` (TV3) | `max_region_size`, `aux_vars_final`, `aux_vars_max`, `cnf_clauses_final`, `cnf_clauses_avg`, `total_propagations`, `total_decisions`, `solver_runtime_ms`, `total_runtime_ms` |
| **RQ3** | **Tác động của tối ưu DPLL (Pure-Literal & Heuristics):** So với DPLL cơ bản (chọn biến tất định theo chỉ số nhỏ nhất `lexicographic`, không khử literal thuần), việc bật *Pure-Literal Elimination* và/hoặc chuyển sang heuristic chọn biến `MOMs` / `Jeroslow-Wang (JW)` `(description.md 2.4, plan.md 2.3)` giúp cắt giảm bao nhiêu `total_decisions`, `total_backtracks` và `solver_runtime_ms` / `total_runtime_ms`? Ở lưới nhỏ `3×3`, chi phí tính toán heuristic có làm chậm hơn DPLL cơ bản không? | `ISATSolver` (TV3) | `total_decisions`, `total_propagations`, `total_backtracks`, `solver_runtime_ms`, `total_runtime_ms` |
| **RQ4** | **Hiệu quả của Model Caching ở tầng Logic Agent:** Khi tái sử dụng mô hình thỏa mãn $M$ thu được từ các truy vấn SAT trước trong cùng bước $t$ để bỏ qua các truy vấn $KB_t \wedge \neg C_j$ (nếu $M[j]=\text{False}$) hoặc $KB_t \wedge C_j$ (nếu $M[j]=\text{True}$) `(description.md 3.2, plan.md 2.4)`, Model Caching tiết kiệm được bao nhiêu phần trăm `sat_calls_total` và `total_runtime_ms`, trong khi vẫn giữ nguyên 100% kết quả suy diễn (`deduction_steps` và chuỗi phán quyết)? | `DeductiveLogicAgent` (TV4) | `sat_calls_total`, `sat_calls_cached_skipped`, `total_runtime_ms`, `deduction_steps`, `cross_config_consistency` *(dẫn xuất)* |
| **RQ5** | **Độ tin cậy, tính tất định & ca biên / ca thất bại:** Trên mọi màn chơi hợp lệ (`unique solution` theo `FAQ #9`), mọi cấu hình có hội tụ về cùng một chuỗi phán quyết (`cross_config_consistency = PASS`) và cùng các chỉ số tìm kiếm khi chạy lặp lại (`deterministic_check = PASS`) không `(plan.md 2.3)`? Khi gặp màn chơi mơ hồ (`AMBIGUOUS`), mâu thuẫn (`INCONSISTENT`) hoặc màn bị kẹt giữa chừng `(FAQ #13)`, Agent có dừng an toàn mà không đoán mò và ghi nhận trung thực không? | `GameEngine` (TV1) + `DeductiveLogicAgent` (TV4) | `terminal_status`, `solved_cells`, `total_cells`, `deterministic_check` *(dẫn xuất)*, `cross_config_consistency` *(dẫn xuất)*, `uniqueness_status` *(kiểm định GĐ 2)* |

---

## 2. Bộ Dữ liệu Thực nghiệm (Dataset)

### 2.1. Nguồn cung cấp và tiêu chuẩn kiểm định
- **Đơn vị cung cấp:** Toàn bộ bộ màn chơi chuẩn định dạng JSON nằm tại `Source/puzzles/` do **TV1** thiết kế và kiểm tra tính hợp lệ cấu trúc bằng `engine/puzzle_validator.py` `(plan.md 1.2, 2.1, FAQ #7)`.
- **Kiểm định nghiệm duy nhất:** Toàn bộ 15 puzzle được kiểm định bằng `agent/uniqueness.py` / `experiments/uniqueness_report.py` của **TV4** để xác nhận đúng quy tắc *unique solution* `(description.md 2.1, FAQ #9)` trên 13 màn giải được (10 màn chuẩn + 3 màn mở rộng) và phân loại đúng 2 màn ca biên (`edge_cases/`).
- **Quy tắc công bằng bắt buộc:** Mọi phép so sánh cấu hình đều chạy trên **cùng một tập puzzle** `(description.md 2.7, AI - Project 2.pdf 4.5)`.

### 2.2. Bộ 10 màn chơi chuẩn (`standard`) và 3 màn mở rộng (`extension`)
Theo quy ước bộ dữ liệu trong `docs/tv4_agent_conventions.md` (Mục 5), bộ benchmark mặc định gồm **10 màn chơi chuẩn** (phủ vượt mức tối thiểu 6 màn của `FAQ #2`):
- **4 màn `3×3`** (`Source/puzzles/3x3/`): 9 nhân vật (9 biến chính $C_1 \dots C_9$).
- **4 màn `4×4`** (`Source/puzzles/4x4/`): 16 nhân vật (16 biến chính $C_1 \dots C_{16}$).
- **2 màn `5×5`** (`Source/puzzles/5x5/`): 25 nhân vật (25 biến chính $C_1 \dots C_{25}$) — đóng vai trò *stress case* đánh giá khả năng mở rộng `(AI - Project 2.pdf 4.5, plan.md 3.1)`.

Ngoài ra có **3 màn `extensions/`** (`Source/puzzles/extensions/`, bật qua cờ `--include-extensions`, `dataset_group = extension`) kiểm chứng các biểu thức vùng nâng cao (`INTERSECTION`, `COMMON_NEIGHBORS`, `CORNERS`, `BOUNDARY`, `BETWEEN`), `PARITY` và `COMPARE_COUNTS`.

### 2.3. Tập ca biên bổ sung (`edge_cases`)
Theo `plan.md 1.2, 2.1, 2.4`, ngoài 10 màn chuẩn, TV1 cung cấp `Source/puzzles/edge_cases/` để kiểm định độ an toàn của Agent (tách nhóm `dataset_group = edge_case` khi tổng hợp thống kê để không làm lệch kết quả của 10 màn chuẩn):
- `edge_3x3_ambiguous` (`edge_3x3_01_ambiguous.json`): màn chơi thiếu thông tin ép buộc, kỳ vọng `terminal_status = AMBIGUOUS` (Agent dừng an toàn ở bước kết thúc `VerdictCode.NOT_PROVABLE`, không đoán mò).
- `edge_3x3_inconsistent` (`edge_3x3_02_inconsistent.json`): màn chơi có tập manh mối công khai mâu thuẫn (`DPLL(KB_0) = UNSAT`), kỳ vọng `terminal_status = INCONSISTENT` (`VerdictCode.INCONSISTENT`).

### 2.4. Bảng mô tả đặc trưng bộ dữ liệu (`Source/puzzles/`)

| `puzzle_id` | Nhóm (`dataset_group`) | Kích thước ($N \times N$) | `primary_vars` ($N^2$) | Thẻ mở sẵn ở $KB_0$ `(FAQ #8)` | `max_region_size` ($\max \|R\|$) | `uniqueness_status` `(FAQ #9)` | Khớp đáp án ẩn (`matches_hidden_solution`) | Trạng thái kết thúc (`terminal_status`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` | `standard` | 3×3 | 9 | 2 | 8 | `UNIQUE` (0.499 ms) | `true` | `SOLVED` |
| `3x3_02` | `standard` | 3×3 | 9 | 2 | 3 | `UNIQUE` (0.372 ms) | `true` | `SOLVED` |
| `3x3_03` | `standard` | 3×3 | 9 | 2 | 5 | `UNIQUE` (0.277 ms) | `true` | `SOLVED` |
| `3x3_04` | `standard` | 3×3 | 9 | 2 | 3 | `UNIQUE` (0.257 ms) | `true` | `SOLVED` |
| `4x4_01` | `standard` | 4×4 | 16 | 3 | 5 | `UNIQUE` (0.588 ms) | `true` | `SOLVED` |
| `4x4_02` | `standard` | 4×4 | 16 | 3 | 8 | `UNIQUE` (1.272 ms) | `true` | `SOLVED` |
| `4x4_03` | `standard` | 4×4 | 16 | 3 | 5 | `UNIQUE` (0.895 ms) | `true` | `SOLVED` |
| `4x4_04` | `standard` | 4×4 | 16 | 3 | 5 | `UNIQUE` (0.808 ms) | `true` | `SOLVED` |
| `5x5_01` | `standard` | 5×5 | 25 | 5 | 8 | `UNIQUE` (1.653 ms) | `true` | `SOLVED` |
| `5x5_02` | `standard` | 5×5 | 25 | 5 | 8 | `UNIQUE` (4.094 ms) | `true` | `SOLVED` |
| `ext_3x3_01` | `extension` | 3×3 | 9 | 2 | 5 | `UNIQUE` (0.424 ms) | `true` | `SOLVED` |
| `ext_4x4_02` | `extension` | 4×4 | 16 | 3 | 12 | `UNIQUE` (3.681 ms) | `true` | `SOLVED` |
| `ext_4x4_03` | `extension` | 4×4 | 16 | 3 | 12 | `UNIQUE` (10.743 ms) | `true` | `SOLVED` |
| `edge_3x3_ambiguous` | `edge_case` | 3×3 | 9 | 2 | 3 | `MULTIPLE` (0.312 ms) | `NA` | `AMBIGUOUS` |
| `edge_3x3_inconsistent` | `edge_case` | 3×3 | 9 | 2 | 8 | `UNSAT` (0.491 ms) | `NA` | `INCONSISTENT` |

> *Nguồn kiểm định:* `Source/experiments/results/uniqueness_report.csv` (chạy bằng `CNFEncoder("direct")` thật của TV2 và `DPLLSolver()` thật của TV3; `10/10` màn chuẩn và `3/3` màn mở rộng đạt `UNIQUE` với `matches_hidden_solution=true`).

---

## 3. Ma trận Cấu hình Thực nghiệm (Configuration Matrix)

### 3.1. Các trục biến độc lập (Independent Variables)
Dựa trên thiết kế module của TV2, TV3 và TV4 trong `plan.md 2.2–2.4`, benchmark thay đổi 4 tham số cấu hình, đồng thời giữ cố định quy tắc chọn ô ép buộc theo thứ tự hàng (row-major order) ở Logic Agent `(description.md 2.5, plan.md 2.4)`:
1. **`encoding` (TV2 – `logic/cnf_encoder.py`):**
   - `direct`: Mã hóa tổ hợp trực tiếp (*Direct Combinatorial Encoding*), tạo $\binom{|R|}{k+1}$ mệnh đề cho `AT_MOST(k, R)` và $\binom{|R|}{|R|-k+1}$ mệnh đề cho `AT_LEAST(k, R)` mà không dùng biến phụ cho ràng buộc đếm `(description.md 2.3)`.
   - `sinz`: Bộ đếm tuần tự (*Sequential Counter / Sinz Encoding*). Sinz mã hóa trực tiếp `AT_MOST(k, R)` với $O(|R|\cdot k)$ biến phụ và mệnh đề; `AT_LEAST(k, R)` được quy về `AT_MOST(|R|−k)` trên các literal phủ định nên tốn $O(|R|\cdot(|R|-k))$ biến phụ và mệnh đề (`EXACTLY(k, R)` kết hợp cả hai chiều).
2. **`pure_literal` (TV3 – `solver/heuristics.py`):**
   - `False`: Tắt khử literal thuần (chỉ dùng Unit Propagation).
   - `True`: Bật *Pure-Literal Elimination*.
3. **`heuristic` (TV3 – `solver/heuristics.py`):**
   - `lexicographic`: Chọn biến chưa gán có chỉ số nhỏ nhất (tất định cơ bản).
   - `moms`: *Maximum Occurrences in clauses of Minimum Size* (phá hòa tất định).
   - `jw`: *Jeroslow-Wang* (phá hòa tất định).
4. **`model_caching` (TV4 – `agent/entailment.py`):**
   - `False`: Luôn kiểm tra tối đa 2 truy vấn SAT ($KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$) cho mỗi ô chưa mở (tắt tối ưu tái sử dụng model).
   - `True`: Bật *Model Caching* để loại bỏ các truy vấn đã được chứng minh SAT bởi model từ các lần gọi DPLL trước trong cùng bước $t$.

### 3.2. Ma trận 8 cấu hình cốt lõi cần chạy
Tổ hợp đầy đủ (full factorial) gồm $2 \times 2 \times 3 \times 2 = 24$ cấu hình. Do thời gian GĐ 3B nén chặt (`tối 27/11 – 14:00 28/11`, `schedule.md`) và rủi ro cấu hình baseline có thể chậm ở lưới `5×5` `(plan.md 3.1)`, TV4 thiết kế **ma trận 8 cấu hình cốt lõi** theo nguyên tắc *cô lập từng yếu tố (ablation)* cộng với 2 tổ hợp tối ưu đầu cuối. Nếu tốc độ `5×5` thực tế nhanh, `benchmark.py` vẫn hỗ trợ cờ `--full-grid` để chạy mở rộng đủ tổ hợp.

| `config_id` | Tên cấu hình | `encoding` (TV2) | `heuristic` (TV3) | `pure_literal` (TV3) | `model_caching` (TV4) | Mục đích & Câu hỏi nghiên cứu trả lời |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`C0`** | `baseline_direct` | `direct` | `lexicographic` | `False` | `False` | **Mốc chuẩn (Baseline)** thỏa đúng 6 yêu cầu DPLL tối thiểu `(description.md 2.4)` và Direct encoding. Làm chuẩn đối chiếu cho mọi cải tiến (**RQ1–RQ4**). |
| **`C1`** | `direct_pl` | `direct` | `lexicographic` | `True` | `False` | Cô lập tác động của **Pure-Literal Elimination** so với `C0` (**RQ3**). |
| **`C2`** | `direct_pl_moms` | `direct` | `moms` | `True` | `False` | Cô lập tác động của heuristic **MOMs** trên nền Pure-Literal so với `C1` và `C0` (**RQ3**). |
| **`C3`** | `direct_pl_jw` | `direct` | `jw` | `True` | `False` | So sánh heuristic **Jeroslow-Wang** với **MOMs** (`C2`) và `lexicographic` (`C1`) (**RQ3**). |
| **`C4`** | `direct_cache` | `direct` | `lexicographic` | `False` | `True` | Cô lập tác động thuần túy của **Model Caching** so với `C0` trên cùng DPLL cơ bản (**RQ4**). |
| **`C5`** | `baseline_sinz` | `sinz` | `lexicographic` | `False` | `False` | Cô lập tác động thuần túy của **Sinz Encoding** so với Direct (`C0`) trên cùng DPLL cơ bản (**RQ2**). |
| **`C6`** | `opt_direct` | `direct` | `best_heur`* | `True` | `True` | Tổ hợp tối ưu đầy đủ trên **Direct** (tổng hợp tác động của DPLL tối ưu + Model Caching; so sánh với `C2`/`C3` để thấy lợi ích cộng thêm của Caching) (**RQ1, RQ2, RQ4**). |
| **`C7`** | `opt_sinz` | `sinz` | `best_heur`* | `True` | `True` | Tổ hợp tối ưu đầy đủ trên **Sinz**; so sánh công bằng Direct vs. Sinz khi đã tối ưu hết (`C6` vs `C7`) và là phương án dự phòng cho stress case `5×5` `(plan.md 3.1)` (**RQ1, RQ2**). |

> \* Ghi chú: Tham số `best_heur` của `C6` và `C7` trong bản benchmark chính thức được chọn là **`moms`** (thay vì mặc định `jw`, bằng cờ `--best-heur moms`), và giữ cố định giống nhau cho cả `C6` lẫn `C7` để phép so sánh Direct vs. Sinz công bằng. Lý do chọn từ đối chiếu thực tế `C2` (`moms`) vs `C3` (`jw`) trên bộ chuẩn: cả hai đạt cùng tỷ lệ giải `10/10` và cùng tổng số nhánh cắt tỉa (`total_decisions = 285`, `total_backtracks = 530`, `total_propagations = 19,445`), nhưng `moms` nhanh hơn `jw` ở **cả 3 kích thước lưới** (lần chạy đối chiếu ban đầu: `3×3`: `9.752` vs `12.323 ms`; `4×4`: `45.625` vs `49.243 ms`; `5×5`: `109.516` vs `115.892 ms`; tổng chuẩn `164.893` vs `177.458 ms`), do `moms` chỉ đếm tần suất trên các mệnh đề ngắn nhất bằng số nguyên thay vì tính trọng số thực $2^{-|C|}$ trên toàn bộ mệnh đề chưa thỏa. Khi có `CNFEncoder` thật của TV2 (`direct` & `sinz`), không còn cấu hình nào bị `SKIPPED_NO_ENCODER` hay rơi về `StubCNFEncoder`.

---

## 4. Danh sách Chỉ số Đo lường (Metrics)

### 4.1. Ánh xạ 6 nhóm chỉ số bắt buộc từ đề bài và chỉ số dẫn xuất
Toàn bộ 6 nhóm chỉ số bắt buộc trong `description.md 2.7` và `AI - Project 2.pdf 4.5` được ánh xạ 1-1 với tên cột trong `benchmark_raw.csv` (Mục 5.1):

| STT | Nhóm chỉ số bắt buộc (`description.md 2.7`, `AI - Project 2.pdf 4.5`) | Tên chỉ số đo trong `benchmark_raw.csv` | Nguồn dữ liệu / Cách tính | Ý nghĩa đánh giá |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Số biến chính & biến phụ** | `primary_vars`, `aux_vars_final`, `aux_vars_max` | Từ `CNFStats` của `ICNFEncoder.encode_kb()` `(plan.md 1.1, 2.2)`. `primary_vars` $= N^2$; `aux_vars_final` đo tại $KB_T$ (trạng thái cuối cùng đạt được); `aux_vars_max` là giá trị cực đại qua các bước $t=0 \dots T$ (thường bằng `aux_vars_final` vì $KB_t$ đơn điệu tăng). | Đánh giá kích thước không gian biến và chi phí biến phụ phát sinh từ Sinz Encoding và `PARITY` (Tseitin). |
| **2** | **Số lượng mệnh đề CNF** | `cnf_clauses_final`, `cnf_clauses_avg` | Từ `CNFStats` của `ICNFEncoder.encode_kb()` `(plan.md 1.1, 2.2)`. Ghi nhận tổng số mệnh đề tại $KB_T$ và trung bình số mệnh đề trên mỗi bước suy diễn $t$. | Phản ánh độ phình công thức CNF theo kích thước vùng đếm $\|R\|$ của các clue. |
| **3** | **Số lần gọi bộ giải SAT** | `sat_calls_total`, `sat_calls_cached_skipped` | Lấy trực tiếp từ `DeductionStep.sat_queries` (`docs/tv4_agent_conventions.md` Mục 2.4): `sat_calls_total` là số truy vấn có `cached=False` (gồm cả truy vấn kiểm tra nhất quán `cell="KB"` và các truy vấn $KB_t \wedge \neg C_i$, $KB_t \wedge C_i$); `sat_calls_cached_skipped` đếm các truy vấn có `cached=True`. Bộ nhớ đệm theo khóa KB (`KBCache`, LRU ≤ 8) bảo đảm `stats.validation_sat_calls == 0` trong `run_auto_solve`, và **không** gộp SAT call của `UniquenessCheck` vào đây. | Đo chi phí truy vấn Entailment và định lượng trực tiếp lợi ích của Model Caching (**RQ4**). |
| **4** | **Decisions, Propagations, Backtracks** | `total_decisions`, `total_propagations`, `total_backtracks` | Cộng dồn từ `SATMetrics` (`decisions`, `propagations`, `backtracks`) do `ISATSolver.solve()` trả về trên tất cả `sat_calls_total` lượt gọi `(description.md 2.4, plan.md 1.1, 2.3)`. | Đo hiệu quả tìm kiếm nội bộ của DPLL và hiệu quả cắt tỉa của Pure-Literal / MOMs / JW (**RQ3**). |
| **5** | **Số bước suy diễn / Làn sóng mở thẻ** | `deduction_steps` *(chính)*; `reveal_waves` *(bỏ qua / tùy chọn)* | `deduction_steps`: số bước lật thẻ thành công do Agent thực hiện từ $t=0$ đến khi kết thúc (với màn giải trọn vẹn có $k_0$ thẻ mở sẵn, `deduction_steps` $= N^2 - k_0$). | Đo độ sâu chuỗi suy diễn logic của màn chơi. |
| **6** | **Thời gian thực thi (Runtime)** | `total_runtime_ms`, `solver_runtime_ms` | `total_runtime_ms`: đo bằng `time.perf_counter()` cho toàn bộ phiên chạy `run_auto_solve` (gồm mã hóa CNF + Entailment/Caching + DPLL + cập nhật `GameEngine`, không có delay GUI). `solver_runtime_ms`: tổng `SATMetrics.runtime_ms` cộng dồn từ bộ giải DPLL `(description.md 2.4, plan.md 1.1)`. | Đánh giá tốc độ phản hồi thực tế (ms) và phân tách chi phí thời gian giữa mã hóa/Agent với lõi tìm kiếm DPLL (**RQ1–RQ4**). |

**Chỉ số ngữ cảnh bổ sung & chỉ số dẫn xuất (tách bạch rõ nguồn sinh):**
- **Cột ngữ cảnh trong `benchmark_raw.csv`:** `max_region_size` (kích thước vùng $\|R\|$ lớn nhất trong toàn bộ clue của màn chơi; là thuộc tính của màn chơi nên giống nhau ở mọi cấu hình và mọi `terminal_status`, kể cả `SKIPPED_NO_ENCODER`/`TIMEOUT`/`ERROR`; phục vụ trực tiếp **RQ2**), `terminal_status`, `solved_cells`, `total_cells`.
- **Cột dẫn xuất trong `benchmark_summary.csv` (tổng hợp qua `R` lần lặp & kiểm tra chéo):** `repeats`, `deterministic_check`, `cross_config_consistency`, `solver_runtime_ms_median` / `_mean` / `_std`, `total_runtime_ms_median` / `_mean` / `_std`.
- **Chỉ số dẫn xuất ở mức báo cáo (không phải cột trong `benchmark_raw.csv`):**
  - `solved_rate`: tỷ lệ giải thành công theo cấu hình (`số màn SOLVED / tổng số màn chuẩn`), tính từ `terminal_status`.
  - `avg_decisions_per_call` $= \text{total\_decisions} / \text{sat\_calls\_total}$ và `% giảm sat_calls` (dùng khi phân tích Bảng 5.4 và Hình E4).
- **Chỉ số kiểm định dữ liệu độc lập (GĐ 2, không thuộc lượt chạy auto-solve):** `uniqueness_status` (`UNIQUE` \| `MULTIPLE` \| `UNSAT`) thu từ `agent/uniqueness.py` trên toàn bộ tập clue của từng puzzle (ghi tại Bảng 2.4).

### 4.2. Ghi chú chính thức về `reveal_waves` (FAQ #12)
- Theo **FAQ #12** `(description.md 2.7, 4.1)`, một `reveal wave` là đợt lật đồng loạt toàn bộ các nhân vật bị ép buộc ở cùng một trạng thái $KB$, và **giảng viên đã chính thức cho phép bỏ qua chỉ số `reveal_waves`** (chỉ cần báo `deduction_steps` là đủ yêu cầu).
- Vì vòng lặp suy diễn chuẩn của nhóm lật từng nhân vật một theo thứ tự row-major `(description.md 2.5, plan.md 2.4)`, benchmark lấy **`deduction_steps`** làm chỉ số chính bắt buộc. Cột `reveal_waves` trong schema CSV có thể để rỗng (`null`) với ghi chú tuân thủ `FAQ #12`, hoặc chỉ tính bổ sung nếu nhóm muốn minh họa thêm mà không làm ảnh hưởng tiến độ GĐ 3B.

### 4.3. Quy tắc ghi nhận trung thực lỗi, timeout và ca kẹt giữa chừng (FAQ #13)
Theo yêu cầu bắt buộc của `description.md 2.7` và `AI - Project 2.pdf 4.5` (*"Report failures and timeouts rather than removing them from the results"*):
1. **Không bao giờ loại bỏ dữ liệu thất bại:** Mọi lượt chạy trả về `TIMEOUT`, `AMBIGUOUS`, `INCONSISTENT` hoặc `ERROR` phải được lưu đầy đủ vào CSV và xuất hiện trong bảng kết quả của báo cáo.
2. **Phân loại trạng thái kết thúc (`terminal_status`):**
   - `terminal_status`: `SOLVED` \| `AMBIGUOUS` \| `INCONSISTENT` \| `TIMEOUT` \| `ERROR` \| `SKIPPED_NO_ENCODER`.
   - `deduction_steps`: số bước lật thẻ `VerdictCode.ACCEPTED` trong trace (không tính bước kết thúc `NOT_PROVABLE` / `INCONSISTENT`).
   - `encoding`: `direct` \| `sinz` \| `stub` (cảnh báo khi dùng `StubCNFEncoder` tạm thời).
3. **Cách tính thống kê khi có `TIMEOUT` / `AMBIGUOUS` / `SKIPPED_NO_ENCODER`:**
   - Với `AMBIGUOUS` / `INCONSISTENT`, ghi nhận đầy đủ các chỉ số đã tích lũy đến thời điểm dừng (`solved_cells`, `deduction_steps`, `sat_calls_total`, `total_decisions`, `total_propagations`, `total_backtracks`, `total_runtime_ms`).
   - Với `TIMEOUT` (do ngắt tiến trình `multiprocessing` ngoài ngưỡng 60s) hoặc `SKIPPED_NO_ENCODER`, ghi `terminal_status`, `total_runtime_ms = timeout_limit_ms` (với `TIMEOUT`), và `error_message`; các cột chỉ số chưa thu được để rỗng (`""`).
   - Khi tổng hợp theo kích thước lưới hoặc theo cấu hình, báo cáo riêng **tỷ lệ giải thành công (`solved_rate = số màn SOLVED / tổng số màn`)** và **không gộp** ca `TIMEOUT`/`SKIPPED_NO_ENCODER` vào trung bình/trung vị runtime của các ca hoàn tất.

---

## 5. Schema CSV Đề xuất

Dữ liệu benchmark được lưu tại `Source/experiments/results/` `(plan.md 1.2)` thành 2 tệp CSV mã hóa UTF-8, dấu phẩy `,`, có dòng header:
1. **`benchmark_raw.csv`**: 1 dòng ứng với **1 lần lặp chạy** `(puzzle_id, config_id, repeat_idx)` — lưu toàn bộ dữ liệu gốc có thể tái kiểm chứng.
2. **`benchmark_summary.csv`**: 1 dòng ứng với **1 cặp `(puzzle_id, config_id)`** đã tổng hợp thống kê qua các lần lặp — dùng trực tiếp để vẽ biểu đồ và đổ vào bảng báo cáo.

### 5.1. Schema chi tiết của `benchmark_raw.csv` (31 cột)

| STT | Tên cột | Kiểu dữ liệu | Đơn vị | Nullable | Mô tả & Nguồn đối chiếu |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | `run_timestamp` | `string` (ISO-8601) | — | Không | Thời điểm chạy (vd: `2026-11-27T20:15:03+07:00`). |
| 2 | `puzzle_id` | `string` | — | Không | Mã định danh puzzle (vd: `3x3_01`, `5x5_02`, `edge_ambiguous`). |
| 3 | `dataset_group` | `enum(string)` | — | Không | `standard` (10 puzzle chuẩn), `extension` (3 màn mở rộng) hoặc `edge_case` (2 ca biên). |
| 4 | `grid_size` | `int` | ô/cạnh | Không | Kích thước cạnh lưới $N \in \{3, 4, 5\}$. |
| 5 | `initial_revealed` | `int` | thẻ | Không | Số thẻ mở sẵn ban đầu ở $KB_0$ `(FAQ #8)`. |
| 6 | `max_region_size` | `int` | ô | Không | Kích thước vùng $\|R\|$ lớn nhất trong toàn bộ clue của màn chơi (thuộc tính màn chơi, giống nhau ở mọi cấu hình/trạng thái; để trống `""` nếu màn chưa qua validate có vùng không hợp lệ; phục vụ phân tích **RQ2** theo $\|R\|$ thực). |
| 7 | `config_id` | `string` | — | Không | Mã cấu hình trong ma trận Phần 3 (`C0`..`C7`). |
| 8 | `encoding` | `enum(string)` | — | Không | Chiến lược mã hóa đếm: `direct` hoặc `sinz` `(plan.md 2.2)`. |
| 9 | `heuristic` | `enum(string)` | — | Không | Heuristic chọn biến DPLL: `lexicographic`, `moms`, `jw` `(plan.md 2.3)`. |
| 10 | `pure_literal` | `bool` | — | Không | Bật/tắt Pure-Literal Elimination (`true`/`false`) `(plan.md 2.3)`. |
| 11 | `model_caching` | `bool` | — | Không | Bật/tắt Model Caching ở Logic Agent (`true`/`false`) `(plan.md 2.4)`. |
| 12 | `repeat_idx` | `int` | lần | Không | Chỉ số lần lặp đo (`1..R`, không gồm lượt warm-up). |
| 13 | `timeout_limit_ms` | `int` | `ms` | Không | Ngưỡng timeout áp dụng (mặc định `60000`, `plan.md 3.1`). |
| 14 | `terminal_status` | `enum(string)` | — | Không | `SOLVED` \| `AMBIGUOUS` \| `INCONSISTENT` \| `TIMEOUT` \| `ERROR`. |
| 15 | `solved_cells` | `int` | ô | Không | Tổng số ô đã có nhãn xác định khi kết thúc (gồm cả thẻ mở sẵn ban đầu). |
| 16 | `total_cells` | `int` | ô | Không | Tổng số ô của lưới ($N^2$). |
| 17 | `primary_vars` | `int` | biến | Không | Số biến mệnh đề chính $N^2$ `(description.md 2.7 #1)`. |
| 18 | `aux_vars_final` | `int` | biến | Không | Số biến phụ tại $KB_T$ `(description.md 2.7 #1)`. |
| 19 | `aux_vars_max` | `int` | biến | Không | Số biến phụ cực đại qua các bước $t=0 \dots T$ `(description.md 2.7 #1)`. |
| 20 | `cnf_clauses_final` | `int` | mệnh đề | Không | Tổng số mệnh đề CNF tại $KB_T$ `(description.md 2.7 #2)`. |
| 21 | `cnf_clauses_avg` | `float` | mệnh đề/bước | Không | Trung bình số mệnh đề CNF qua các bước suy diễn $t$. |
| 22 | `sat_calls_total` | `int` | lần gọi | Không | Tổng số lời gọi `ISATSolver.solve()` thực tế `(description.md 2.7 #3)`. |
| 23 | `sat_calls_cached_skipped` | `int` | lần gọi | Không | Số truy vấn Entailment được bỏ qua nhờ Model Caching (`0` nếu tắt). |
| 24 | `total_decisions` | `int` | lần | Không | Tổng số lần phân nhánh DPLL cộng dồn `(description.md 2.7 #4)`. |
| 25 | `total_propagations` | `int` | lần | Không | Tổng số lần Unit Propagation cộng dồn `(description.md 2.7 #4)`. |
| 26 | `total_backtracks` | `int` | lần | Không | Tổng số lần quay lui DPLL cộng dồn `(description.md 2.7 #4)`. |
| 27 | `deduction_steps` | `int` | bước | Không | Tổng số bước suy diễn lật thẻ thành công `(description.md 2.7 #5)`. |
| 28 | `reveal_waves` | `int` | đợt | **Có** | Để trống (`""`) khi bỏ qua theo `FAQ #12`. |
| 29 | `solver_runtime_ms` | `float` | `ms` | Không | Tổng thời gian trong lõi DPLL (`SATMetrics.runtime_ms` cộng dồn) `(description.md 2.7 #6)`. |
| 30 | `total_runtime_ms` | `float` | `ms` | Không | Tổng thời gian giải end-to-end không kèm GUI `(description.md 2.7 #6)`. |
| 31 | `error_message` | `string` | — | Có | Chuỗi rỗng nếu bình thường; ghi rõ lý do nếu `TIMEOUT`/`ERROR`/`AMBIGUOUS`. |

### 5.2. Các cột tổng hợp & dẫn xuất trong `benchmark_summary.csv`
Giữ nguyên các cột định danh (`puzzle_id`, `dataset_group`, `grid_size`, `initial_revealed`, `max_region_size`, `config_id`, `encoding`, `heuristic`, `pure_literal`, `model_caching`, `terminal_status`, `solved_cells`, `total_cells`) và các chỉ số tất định (`primary_vars`, `aux_vars_final`, `aux_vars_max`, `cnf_clauses_final`, `cnf_clauses_avg`, `sat_calls_total`, `sat_calls_cached_skipped`, `total_decisions`, `total_propagations`, `total_backtracks`, `deduction_steps`, `reveal_waves`), bổ sung các **cột dẫn xuất** sau:
- `repeats` (`int`, dẫn xuất): số lần lặp hợp lệ đã chạy.
- `deterministic_check` (`enum`: `PASS` \| `FAIL`, dẫn xuất): kiểm tra mọi lần lặp của cùng `(puzzle_id, config_id)` có cho cùng tập chỉ số logic tất định hay không.
- `cross_config_consistency` (`enum`: `PASS` \| `FAIL` \| `NA`, dẫn xuất): kiểm tra chéo với các cấu hình khác trên cùng `puzzle_id` có cùng `terminal_status`, cùng `deduction_steps` và cùng chuỗi phán quyết từng bước hay không (`NA` nếu lượt chạy bị `TIMEOUT`/`ERROR`).
- `solver_runtime_ms_median`, `solver_runtime_ms_mean`, `solver_runtime_ms_std` (`float`, đơn vị `ms`, dẫn xuất).
- `total_runtime_ms_median`, `total_runtime_ms_mean`, `total_runtime_ms_std` (`float`, đơn vị `ms`, dẫn xuất).

### 5.3. Ví dụ một dòng hợp lệ của `benchmark_raw.csv`

> **[VÍ DỤ MINH HỌA SCHEMA — GIÁ TRỊ GIẢ ĐỊNH ĐỂ KIỂM TRA ĐỊNH DẠNG CSV, KHÔNG PHẢI SỐ LIỆU THỰC NGHIỆM THẬT]**

```csv
run_timestamp,puzzle_id,dataset_group,grid_size,initial_revealed,max_region_size,config_id,encoding,heuristic,pure_literal,model_caching,repeat_idx,timeout_limit_ms,terminal_status,solved_cells,total_cells,primary_vars,aux_vars_final,aux_vars_max,cnf_clauses_final,cnf_clauses_avg,sat_calls_total,sat_calls_cached_skipped,total_decisions,total_propagations,total_backtracks,deduction_steps,reveal_waves,solver_runtime_ms,total_runtime_ms,error_message
2026-11-27T20:15:03+07:00,3x3_01,standard,3,1,8,C6,direct,moms,true,true,1,60000,SOLVED,9,9,9,0,0,42,24.50,19,14,7,118,3,8,,4.820,6.310,
```
*(Ghi chú dòng ví dụ: `max_region_size = 8` tương ứng ô trung tâm có 8 láng giềng; `aux_vars_final = 0` và `aux_vars_max = 0`; `reveal_waves` để trống giữa `8,,4.820` thể hiện bỏ qua theo `FAQ #12`; `error_message` để trống sau dấu phẩy cuối vì `terminal_status = SOLVED`; toàn bộ con số trên chỉ là giá trị ví dụ minh họa kiểu dữ liệu.)*

---

## 6. Giao thức Đo lường (Measurement Protocol)

1. **Chế độ chạy tách biệt GUI (Headless Benchmark Mode):**
   - `experiments/benchmark.py` gọi trực tiếp `GameEngine` (TV1) + `CNFEncoder` (TV2) + `DPLLSolver` (TV3) + `DeductiveLogicAgent` (TV4), **tắt hoàn toàn callback animation / giao diện GUI** để loại bỏ độ trễ hiển thị.
   - Ở mỗi lần lặp, khởi tạo mới `GameEngine` (`load_puzzle` / `restart`) và `DeductiveLogicAgent` (reset sạch bộ nhớ đệm Model Cache) để không có trạng thái tồn dư giữa các lượt chạy.
2. **Warm-up:**
   - Trước khi bắt đầu vòng đo chính thức, thực hiện **1 lượt chạy warm-up** (ví dụ chạy `C0` trên `3x3_01`) nhằm hoàn tất nạp module Python và khởi tạo bộ nhớ ban đầu. Kết quả lượt warm-up **không được ghi** vào `benchmark_raw.csv`.
3. **Số lần lặp đo (`R`) và kiểm tra tính tất định nội cấu hình:**
   - Chạy lặp `R = 5` lần cho mỗi cặp `(puzzle_id, config_id)` trên lưới `3×3` và `4×4`; chạy `R = 3` (hoặc `5` nếu mỗi lượt `< 5,000 ms`) trên lưới `5×5`. *(Số lần lặp chính thức cho `5×5` **cần xác nhận với nhóm** khi có thời gian chạy thực tế ở GĐ 3B.)*
   - Vì hệ thống yêu cầu hoàn toàn tất định (`plan.md 2.3`, `description.md 2.4–2.5`), sau `R` lần lặp, script tự động kiểm tra tính bất biến trên tập chỉ số `(terminal_status, primary_vars, aux_vars_final, aux_vars_max, cnf_clauses_final, sat_calls_total, total_decisions, total_propagations, total_backtracks, deduction_steps)` và ghi cờ `deterministic_check = PASS/FAIL`.
4. **Kiểm tra chéo tương đương giữa các cấu hình (Cross-Configuration Equivalence Check):**
   - Để chứng minh các tối ưu (Sinz Encoding, Pure-Literal, heuristic `MOMs`/`JW`, Model Caching) **không làm thay đổi kết quả suy diễn**, `benchmark.py` đối chiếu toàn bộ các cấu hình không bị `TIMEOUT`/`ERROR` trên cùng một `puzzle_id`:
     - `terminal_status` phải trùng khớp hoàn toàn giữa mọi cấu hình;
     - `deduction_steps` phải giống hệt nhau;
     - **Chuỗi phán quyết từng bước** `[(step_t, cell_id, verdict), ...]` phải giống hệt nhau 100% (vì tập hệ quả logic $KB_t \models \pm C_i$ và quy tắc chọn ô ép buộc row-major là bất biến theo lựa chọn tối ưu).
   - Kết quả ghi vào cột dẫn xuất `cross_config_consistency = PASS | FAIL | NA` trong `benchmark_summary.csv`. Nếu xuất hiện `FAIL`, phải dừng điều tra lỗi tính đúng đắn ở `CNFEncoder` / `DPLLSolver` / `Model Caching` trước khi đưa số liệu vào báo cáo.
5. **Bộ đếm thời gian & Giảm nhiễu hệ thống:**
   - Dùng `time.perf_counter()` (độ phân giải cao, đơn điệu tăng), quy đổi sang mili-giây (`ms`), làm tròn 3 chữ số thập phân.
   - Gọi `gc.collect()` trước mỗi lượt chạy để giảm xác suất Garbage Collector kích hoạt ngẫu nhiên giữa lúc đo.
   - Toàn bộ bảng so sánh trong báo cáo phải được chạy trong **cùng một phiên đo trên cùng một máy** (cắm nguồn điện ổn định, chế độ hiệu năng chuẩn, đóng các ứng dụng nền nặng).
6. **Cách tổng hợp trung vị & trung bình:**
   - Dùng **trung vị (`median`)** làm đại diện chính cho `total_runtime_ms` và `solver_runtime_ms` vì ít bị méo bởi nhiễu tức thời của hệ điều hành.
   - Lưu và trình bày kèm **trung bình (`mean`) ± độ lệch chuẩn (`std`)** trong `benchmark_summary.csv` (và ghi chú trong bảng báo cáo nếu độ lệch lớn).
7. **Chính sách Timeout (`60 giây / lượt chạy`):**
   - Áp dụng ngưỡng `timeout_limit_ms = 60000` (60 giây/puzzle) theo phương án quản trị rủi ro trong `plan.md 3.1` và `schedule.md mục 3`.
   - Nếu lần lặp đầu tiên (`repeat_idx = 1`) vượt quá 60 giây, dừng tiến trình đó, ghi `terminal_status = TIMEOUT`, `total_runtime_ms = 60000.0`, `error_message`, và **không chạy các lần lặp còn lại** cho đúng cặp `(puzzle_id, config_id)` đó để tránh treo tổng thời gian benchmark.
   - **Cơ chế Timeout trên Windows:** Vì Windows không có `signal.SIGALRM`, `benchmark.py` chạy mỗi lượt `(puzzle, config, repeat)` trong tiến trình `multiprocessing` (`spawn`) độc lập và gọi `terminate()` khi vượt `timeout_s = 60`.
8. **Ghi nhận môi trường máy đo:**
   - Tự động xuất tệp `Source/experiments/results/env_info.json` cùng lúc chạy benchmark, gồm: CPU/processor, số nhân (`cpu_count`), hệ điều hành, phiên bản Python (`sys.version`), git commit hash, `solved_rate_standard`, ngày giờ chạy.

---

## 7. Danh sách Biểu đồ (`Source/experiments/plots.py`)

Toàn bộ biểu đồ được sinh tự động bằng `Source/experiments/plots.py` dùng `matplotlib` (non-interactive `Agg`, không gọi `plt.show()`), lưu ở định dạng PNG 300 DPI tại `Source/experiments/results/charts/` để nhúng trực tiếp vào `Report.pdf`:

| Mã / Tệp biểu đồ | Tên biểu đồ | Loại biểu đồ | Trục X / Trục Y / Nhóm dữ liệu | Câu hỏi nghiên cứu | Ghi chú trình bày |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Hình E1** (`rq1_scalability.png`) | *Khả năng mở rộng theo kích thước lưới (`3×3` → `5×5`)* | Line Chart (2 subplot đặt cạnh nhau) | **Trục X:** Kích thước lưới (`3×3`, `4×4`, `5×5`).<br>**Subplot 1 – Trục Y:** Trung bình `total_runtime_ms_median` (ms).<br>**Subplot 2 – Trục Y:** Trung bình `sat_calls_total`.<br>**Nhóm:** Các cấu hình đang chạy (`C0`..`C7`). | **RQ1** | Trực quan hóa tốc độ tăng thời gian giải và số truy vấn SAT theo kích thước bảng. |
| **Hình E2** (`rq2_direct_vs_sinz.png`) | *Kích thước công thức CNF: Direct vs. Sinz* | Grouped Bar Chart (2 subplot đặt cạnh nhau) | **Trục X:** Các màn chuẩn (`3x3_01`..`5x5_02`).<br>**Subplot 1 – Trục Y:** `aux_vars_final`.<br>**Subplot 2 – Trục Y:** `cnf_clauses_final`.<br>**Nhóm:** `Direct (C0)` vs. `Sinz (C5)`. | **RQ2** | Tự động bỏ qua kèm thông báo khi chưa có dữ liệu Sinz thật từ TV2. |
| **Hình E3** (`rq3_heuristics.png`) | *Tác động của Pure-Literal & Heuristic lên tìm kiếm DPLL* | Grouped Bar Chart (2 subplot) | **Trục X:** `C0` (Lex), `C1` (+PL), `C2` (+PL+MOMs), `C3` (+PL+JW).<br>**Trục Y:** Tổng `total_decisions` (subplot 1) và tổng `total_backtracks` (subplot 2) trên bộ chuẩn. | **RQ3** | Tách biệt hiệu ứng cắt tỉa của Pure-Literal / MOMs / JW khỏi Model Caching. |
| **Hình E4** (`rq4_model_caching.png`) | *Hiệu quả cắt giảm số lần gọi SAT nhờ Model Caching* | Side-by-side Bar Chart | **Trục X:** Các màn chuẩn.<br>**Trục Y:** `sat_calls_total` (non-cached).<br>**Nhóm:** Tắt caching (`C0`) vs. Bật caching (`C4`). | **RQ4** | So sánh trực tiếp số truy vấn SAT thực tế trên từng màn chơi. |

---

## 8. Khung Bản nháp Mục "Experiments" cho `Report.pdf`

> **Lưu ý ngôn ngữ báo cáo:** Theo quy ước chung trong `description.md 2.8, 4.2`, toàn bộ `Report.pdf` cần thống nhất **một ngôn ngữ duy nhất** (toàn bộ tiếng Việt hoặc toàn bộ tiếng Anh). Bản nháp dưới đây được soạn bằng **tiếng Việt** theo yêu cầu phiên này; nếu cả nhóm chốt viết `Report.pdf` bằng tiếng Anh thì TV4 sẽ dịch đồng bộ khung này sang tiếng Anh ở GĐ 4A (**Cần xác nhận với nhóm**).

---

### [BẮT ĐẦU BẢN NHÁP MỤC 5 — THỰC NGHIỆM VÀ ĐÁNH GIÁ]

#### 5.1. Thiết lập thực nghiệm và Môi trường đo
Để đánh giá toàn diện hiệu năng, khả năng mở rộng và tính tin cậy của hệ thống *Griductive Solver*, chúng tôi thực hiện chuỗi thực nghiệm trên bộ dữ liệu gồm **10 màn chơi chuẩn** (`4` màn `3×3`, `4` màn `4×4`, `2` màn `5×5`, vượt mức tối thiểu 6 màn của `FAQ #2`), **3 màn mở rộng** (`extensions/`: `ext_3x3_01`, `ext_4x4_02`, `ext_4x4_03`) và **2 màn kiểm thử biên** (`edge_3x3_ambiguous`, `edge_3x3_inconsistent`) — tổng cộng **15 puzzle**, chạy toàn bộ **8 cấu hình (`C0`–`C7`)** (tổng `120` cặp `(puzzle, config)`, `360` lượt đo). Tất cả cấu hình mã hóa CNF (`direct`/`sinz`), bộ giải DPLL và tối ưu ở Logic Agent đều chạy trên **cùng một tập puzzle** ở chế độ không giao diện (headless) để đảm bảo tính công bằng tuyệt đối `(AI - Project 2.pdf 4.5)`.

Mỗi cặp `(puzzle, cấu hình)` được chạy lặp **`repeats = 3`** lần trong tiến trình `multiprocessing` (`spawn`) độc lập trên Windows với giới hạn thời gian **`timeout = 60 giây`** (`60,000 ms`) cho mỗi lượt chạy `(plan.md 3.1)`. Giá trị thời gian thực thi được báo cáo bằng **trung vị (`median`)** tính bằng mili-giây (`ms`), kèm kiểm tra tự động tính tất định (`deterministic_check`) và đối chiếu chéo chuỗi phán quyết giữa các cấu hình (`cross_config_consistency`). Theo xác nhận chính thức từ giảng viên `(FAQ #12)`, chúng tôi báo cáo số bước suy diễn (`deduction_steps`) làm đại diện cho độ sâu suy luận và bỏ qua chỉ số `reveal_waves` (để trống trong CSV). Tổng thời gian chạy trọn bộ 360 lượt benchmark chính thức là `87.53 giây`.

**Bảng 5.1: Thông số môi trường phần cứng và phần mềm thực nghiệm**

| Thành phần môi trường | Chi tiết |
| :--- | :--- |
| CPU | `11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz` (8 luồng logic, `Intel64 Family 6 Model 140 Stepping 1`) |
| Bộ nhớ RAM | `15.75 GB` |
| Hệ điều hành | `Windows-11-10.0.26300-SP0` |
| Phiên bản Python | `3.12.10` (`MSC v.1943 64 bit (AMD64)`) |
| Thời điểm thực thi & Commit | `2026-11-26T16:00:38+07:00` — Commit gốc tích hợp: `df66ddb` (`origin/dev` + `origin/feat/tv2-logic`, khớp byte-to-byte với `origin/dev` sau PR #3 `9d2140b`) |

#### 5.2. Kết quả tổng hợp trên bộ 10 màn chơi chuẩn (và 3 màn mở rộng)
Bảng 5.2 tổng hợp đầy đủ các nhóm chỉ số bắt buộc (`AI - Project 2.pdf 4.5, description.md 2.7`) của hệ thống ở cấu hình tối ưu nhanh nhất **`C6` (`opt_direct`: `direct` + `moms` + `pure_literal=True` + `model_caching=True`)** trên toàn bộ 10 màn chơi chuẩn và 3 màn mở rộng (`extensions/`).

**Bảng 5.2: Kết quả thực nghiệm tổng hợp trên 10 màn chuẩn và 3 màn mở rộng (cấu hình `C6` — `opt_direct`)**

| Màn chơi (`dataset_group`) | Kích thước | `terminal_status` | `primary_vars` | `aux_vars_final` ($KB_T$) | `cnf_clauses_final` ($KB_T$) | `sat_calls_total` | `sat_calls_cached_skipped` | `total_decisions` | `total_propagations` | `total_backtracks` | `deduction_steps`* | `solver_runtime_ms` (`median`) | `total_runtime_ms` (`median`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` (`standard`) | 3×3 | `SOLVED` | 9 | 0 | 28 | 35 | 19 | 0 | 168 | 16 | 7 | 0.487 | 2.227 |
| `3x3_02` (`standard`) | 3×3 | `SOLVED` | 9 | 0 | 30 | 35 | 18 | 0 | 212 | 22 | 7 | 0.579 | 2.402 |
| `3x3_03` (`standard`) | 3×3 | `SOLVED` | 9 | 0 | 32 | 35 | 19 | 0 | 186 | 18 | 7 | 0.643 | 2.867 |
| `3x3_04` (`standard`) | 3×3 | `SOLVED` | 9 | 0 | 26 | 35 | 21 | 0 | 180 | 12 | 7 | 0.529 | 2.136 |
| `4x4_01` (`standard`) | 4×4 | `SOLVED` | 16 | 0 | 69 | 104 | 61 | 0 | 1041 | 74 | 13 | 2.471 | 7.428 |
| `4x4_02` (`standard`) | 4×4 | `SOLVED` | 16 | 0 | 164 | 104 | 52 | 0 | 963 | 61 | 13 | 3.239 | 8.792 |
| `4x4_03` (`standard`) | 4×4 | `SOLVED` | 16 | 0 | 88 | 104 | 66 | 0 | 983 | 52 | 13 | 3.944 | 10.271 |
| `4x4_04` (`standard`) | 4×4 | `SOLVED` | 16 | 0 | 77 | 100 | 87 | 20 | 920 | 30 | 13 | 3.875 | 9.368 |
| `5x5_01` (`standard`) | 5×5 | `SOLVED` | 25 | 0 | 262 | 230 | 121 | 0 | 3018 | 158 | 20 | 11.316 | 24.479 |
| `5x5_02` (`standard`) | 5×5 | `SOLVED` | 25 | 0 | 354 | 215 | 182 | 102 | 3129 | 85 | 20 | 30.388 | 46.315 |
| `ext_3x3_01` (`extension`) | 3×3 | `SOLVED` | 9 | 4 | 39 | 33 | 22 | 2 | 209 | 15 | 7 | 0.752 | 2.893 |
| `ext_4x4_02` (`extension`) | 4×4 | `SOLVED` | 16 | 23 | 137 | 97 | 79 | 46 | 1204 | 26 | 13 | 5.219 | 11.275 |
| `ext_4x4_03` (`extension`) | 4×4 | `SOLVED` | 16 | 182 | 504 | 99 | 71 | 30 | 5846 | 41 | 13 | 48.718 | 58.702 |

*\*Ghi chú: Chỉ số `reveal_waves` được bỏ qua theo hướng dẫn tại FAQ #12. Giá trị `aux_vars_final > 0` ở các màn `extension` (dù dùng `direct`) là do biến phụ Tseitin từ `PARITY` và bộ đếm đơn phân của `COMPARE_COUNTS`.*

![Hình E1: Khả năng mở rộng theo kích thước lưới](../Source/experiments/results/charts/rq1_scalability.png)
*Hình E1 (`rq1_scalability.png`): Trung bình thời gian giải (trái) và số lần gọi SAT thực tế (phải) theo kích thước lưới `3×3` → `5×5` trên bộ 10 màn chuẩn.*

**Nhận xét định lượng (RQ1 – Khả năng mở rộng):**
- **Tăng trưởng quy mô công thức CNF và truy vấn SAT:** Khi lưới tăng từ `3×3` (`primary_vars = 9`, $k_0 = 2$, $T = 7$ bước) lên `4×4` (`primary_vars = 16`, $k_0 = 3$, $T = 13$ bước) và `5×5` (`primary_vars = 25`, $k_0 = 5$, $T = 20$ bước), ở cấu hình `C6` số mệnh đề trung bình tại $KB_T$ tăng từ **`29.0`** (`26–32`) lên **`99.5`** (`69–164`) và **`308.0`** (`262–354`). Tổng số lần gọi SAT thực tế (`sat_calls_total`) tăng từ trung bình **`35.00`** (`3×3`) lên **`103.00`** (`4×4`, gấp `2.94×`) và **`222.50`** (`5×5`, gấp `6.36×` so với `3×3`), khớp chặt đường cong lý thuyết $O(T^2)$ của vòng lặp Entailment.
- **Thời gian thực thi và tỷ lệ đóng góp của DPLL (`solver_runtime_ms` / `total_runtime_ms`):** Ở cấu hình `C6`, trung bình `total_runtime_ms_median` tăng từ **`2.408 ms`** (`3×3`) lên **`8.965 ms`** (`4×4`) và **`35.397 ms`** (`5×5`; chậm nhất là `5x5_02` đạt **`46.315 ms`**). Trong đó tỷ trọng thời gian nằm trong lõi DPLL tăng mạnh theo kích thước lưới: **`23.24%`** (`2.238 / 9.632 ms`) ở `3×3`, **`37.73%`** (`13.529 / 35.859 ms`) ở `4×4`, và **`58.91%`** (`41.704 / 70.794 ms`) ở `5×5` (tổng toàn bộ 10 màn chuẩn là **`49.42%`**, tức `57.471 / 116.285 ms`). Trên lưới nhỏ `3×3`, chi phí cố định ở tầng Python (`encode_kb`, giao tiếp `GameEngine`) chiếm tới `~77%`; khi lên `5×5` (hoặc `ext_4x4_03` có `504` mệnh đề, `182` biến phụ với `48.718 / 58.702 ms = 82.99%`), lõi tìm kiếm DPLL trở thành nút thắt chính.
- **Giải trọn vẹn `5×5` trong ngưỡng timeout:** Tất cả **8/8 cấu hình** (`C0`–`C7`) đều giải trọn vẹn `10/10` màn chuẩn và `3/3` màn mở rộng (`solved_rate = 100%`, **`0` ca `TIMEOUT`** trong ngưỡng `60,000 ms`). Ngay cả cấu hình `C5` chậm nhất trên `5x5_02` cũng chỉ tốn `199.405 ms` (< `0.2s`, thấp hơn `300×` so với giới hạn 60s).
- **Tính tất định và nhất quán chéo:** `120/120` dòng trong `benchmark_summary.csv` đều đạt **`deterministic_check = PASS`** và **`cross_config_consistency = PASS`**, xác nhận mọi tối ưu không làm sai lệch bất kỳ bước phán quyết nào.

#### 5.3. So sánh chiến lược mã hóa CNF: Direct Combinatorial vs. Sequential Counter (Sinz)
Để trả lời **RQ2**, Bảng 5.3 đối chiếu hai chiến lược mã hóa ràng buộc đếm (`AT_LEAST`, `AT_MOST`, `EXACTLY`) theo kích thước vùng thực tế $\|R\|$ (`max_region_size`) trên toàn bộ 10 màn chuẩn và 3 màn mở rộng ở cả chế độ DPLL cơ bản (`C0` vs. `C5`) lẫn cấu hình tối ưu (`C6` vs. `C7`).

**Bảng 5.3: So sánh Direct Combinatorial và Sequential Counter (Sinz) theo kích thước vùng $\|R\|$ trên 10 màn chuẩn và 3 màn mở rộng**

| Màn chơi (`dataset_group`) | `max_region_size` ($\max \|R\|$) | Cấu hình so sánh | `aux_vars_final` (Direct / Sinz) | `cnf_clauses_final` (Direct / Sinz) | `total_propagations` (Direct / Sinz) | `total_decisions` (Direct / Sinz) | `total_runtime_ms` median (Direct / Sinz) | Trạng thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` (`standard`) | 8 | `C0` vs `C5` | 0 / 12 | 28 / 43 | 285 / 658 | 2 / 7 | 2.381 / 5.197 | `SOLVED` / `SOLVED` |
| `3x3_02` (`standard`) | 3 | `C0` vs `C5` | 0 / 22 | 30 / 61 | 338 / 864 | 0 / 0 | 2.450 / 3.975 | `SOLVED` / `SOLVED` |
| `3x3_03` (`standard`) | 5 | `C0` vs `C5` | 0 / 20 | 32 / 58 | 297 / 791 | 0 / 0 | 3.055 / 3.867 | `SOLVED` / `SOLVED` |
| `3x3_04` (`standard`) | 3 | `C0` vs `C5` | 0 / 16 | 26 / 48 | 292 / 745 | 1 / 7 | 2.417 / 3.419 | `SOLVED` / `SOLVED` |
| `4x4_01` (`standard`) | 5 | `C0` vs `C5` | 0 / 40 | 69 / 124 | 1807 / 4909 | 0 / 0 | 9.255 / 16.505 | `SOLVED` / `SOLVED` |
| `4x4_02` (`standard`) | 8 | `C0` vs `C5` | 0 / 98 | 164 / 238 | 1568 / 4718 | 0 / 10 | 11.268 / 16.880 | `SOLVED` / `SOLVED` |
| `4x4_03` (`standard`) | 5 | `C0` vs `C5` | 0 / 89 | 88 / 213 | 1682 / 7067 | 0 / 0 | 13.168 / 25.623 | `SOLVED` / `SOLVED` |
| `4x4_04` (`standard`) | 5 | `C0` vs `C5` | 0 / 86 | 77 / 206 | 1811 / 8989 | 102 / 104 | 13.606 / 33.945 | `SOLVED` / `SOLVED` |
| `5x5_01` (`standard`) | 8 | `C0` vs `C5` | 0 / 223 | 262 / 517 | 5465 / 23185 | 118 / 147 | 35.537 / 84.843 | `SOLVED` / `SOLVED` |
| `5x5_02` (`standard`) | 8 | `C0` vs `C5` | 0 / 244 | 354 / 558 | 6094 / 36040 | 470 / 470 | 70.501 / 199.405 | `SOLVED` / `SOLVED` |
| `5x5_01` (`standard`) | 8 | `C6` vs `C7` | 0 / 223 | 262 / 517 | 3018 / 12334 | 0 / 27 | 24.479 / 52.556 | `SOLVED` / `SOLVED` |
| `5x5_02` (`standard`) | 8 | `C6` vs `C7` | 0 / 244 | 354 / 558 | 3129 / 16404 | 102 / 95 | 46.315 / 91.803 | `SOLVED` / `SOLVED` |
| `ext_3x3_01` (`extension`) | 5 | `C6` vs `C7` | 4 / 8 | 39 / 43 | 209 / 241 | 2 / 2 | 2.893 / 2.968 | `SOLVED` / `SOLVED` |
| `ext_4x4_02` (`extension`) | 12 | `C6` vs `C7` | 23 / 33 | 137 / 150 | 1204 / 1529 | 46 / 46 | 11.275 / 12.267 | `SOLVED` / `SOLVED` |
| `ext_4x4_03` (`extension`) | 12 | `C6` vs `C7` | 182 / 186 | 504 / 508 | 5846 / 6210 | 30 / 30 | 58.702 / 61.552 | `SOLVED` / `SOLVED` |

![Hình E2: So sánh Direct vs. Sinz trên 10 màn chuẩn](../Source/experiments/results/charts/rq2_direct_vs_sinz.png)
*Hình E2 (`rq2_direct_vs_sinz.png`): So sánh `aux_vars_final` (trái) và `cnf_clauses_final` (phải) giữa Direct (`C0`) và Sinz (`C5`) trên 10 màn chuẩn.*

**Nhận xét định lượng (RQ2 – Direct vs. Sinz theo kích thước vùng $\|R\|$ thực):**
- *Cách diễn giải `max_region_size` ở `extensions/`:* Trên 10 màn chuẩn, `max_region_size` ($\le 8$) thuộc các clue đếm cơ bản (`ROW`/`COL`/`NEIGHBORS`). Ở `extensions/`, `max_region_size = 12` ở `ext_4x4_02` nằm tại clue `PARITY` (mã hóa bằng chuỗi XOR Tseitin giống nhau ở cả `direct` và `sinz`), còn `ext_4x4_03` có clue `EXACTLY` trên vùng `BOUNDARY`/`EXPLICIT` kích thước $\|R\| = 12$.
- **Trên toàn bộ 10 màn chuẩn ($\max \|R\| \in \{3, 5, 8\}$), Direct vượt trội rõ rệt Sinz về cả kích thước công thức lẫn tốc độ:**
  - *Biến phụ & mệnh đề:* Direct sinh `0` biến phụ và tổng `1,130` mệnh đề tại $KB_T$ qua 10 màn (`26–354` mệnh đề/màn), trong khi Sinz phát sinh **`850`** biến phụ (`12–244` biến phụ/màn) và **`2,066`** mệnh đề (`43–558`, nhiều hơn `1.83×`).
  - *Lan truyền đơn vị & thời gian giải:* Các biến phụ của Sinz làm tổng số `total_propagations` tăng vọt **`4.48×`** ở DPLL cơ bản (`19,639` ở `C0` lên `87,966` ở `C5`) và **`4.10×`** ở cấu hình tối ưu (`10,800` ở `C6` lên `44,260` ở `C7`). Hệ quả là tổng `total_runtime_ms_median` của `C5` (`393.659 ms`) chậm hơn `C0` (`163.638 ms`) **`2.41×`**, còn `C7` (`226.451 ms`) chậm hơn `C6` (`116.285 ms`) **`1.95×`**.
- **Quan sát vùng giao cắt khi $\|R\|$ tăng lên `12` (`ext_4x4_03`):** Ở `ext_4x4_03` (có `EXACTLY` với $\|R\| = 12$), khoảng cách số mệnh đề gần như triệt tiêu (`504` ở Direct vs. `508` ở Sinz, biến phụ `182` vs. `186`) và thời gian `C6` vs `C7` chỉ còn chênh lệch nhẹ (`58.702` vs. `61.552 ms`). Điều này xác nhận đúng phân tích lý thuyết: trong phạm vi bàn chơi tiêu chuẩn Griductive ($\|R\| \le 8$), **Direct** gọn và nhanh hơn; **Sinz** chỉ bắt đầu phát huy ưu thế tiệm cận $O(\|R\|\cdot k)$ khi mở rộng sang vùng đếm lớn ($\|R\| > 12$).

#### 5.4. Đánh giá tối ưu DPLL (Pure-Literal, MOMs/JW) và Model Caching
Để trả lời **RQ3** và **RQ4**, Bảng 5.4 tổng hợp kết quả ablation từ `C0` sang `C1`–`C7`. Vì toàn bộ `10/10` màn chuẩn đều `SOLVED` ở cả 8 cấu hình, tập giao $S_{\text{common}}$ bao gồm đủ **10/10 màn chuẩn** (`|S_common| = 10`, `TIMEOUT = 0`).

**Bảng 5.4: So sánh hiệu năng các cấu hình DPLL và Model Caching trên tập giao $S_{\text{common}}$ (`10/10` màn chuẩn)**

| Cấu hình | Encoding | Heuristic | Pure-Literal | Model Caching | `solved_rate` *(dẫn xuất)* | Số ca `TIMEOUT` | Tổng `sat_calls_total` (trên $S_{\text{common}}$) | Tổng `total_decisions` (trên $S_{\text{common}}$) | Tổng `total_backtracks` (trên $S_{\text{common}}$) | Tổng `total_runtime_ms_median` (trên $S_{\text{common}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C0` (Baseline) | `direct` | `lexicographic` | Tắt | Tắt | `100%` (10/10) | 0 | 1643 | 693 | 530 | 163.638 |
| `C1` (+PL) | `direct` | `lexicographic` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 516 | 530 | 197.395 |
| `C2` (+PL+MOMs) | `direct` | `moms` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 285 | 530 | 166.261 |
| `C3` (+PL+JW) | `direct` | `jw` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 285 | 530 | 168.359 |
| `C4` (+Caching) | `direct` | `lexicographic` | Tắt | Bật | `100%` (10/10) | 0 | 987 | 282 | 527 | 124.663 |
| `C5` (Sinz Base) | `sinz` | `lexicographic` | Tắt | Tắt | `100%` (10/10) | 0 | 1643 | 745 | 530 | 393.659 |
| `C6` (Opt Direct) | `direct` | `moms` | Bật | Bật | `100%` (10/10) | 0 | 997 | 122 | 528 | 116.285 |
| `C7` (Opt Sinz) | `sinz` | `moms` | Bật | Bật | `100%` (10/10) | 0 | 997 | 157 | 527 | 226.451 |

*\*Ghi chú Bảng 5.4: Trên 3 màn `extensions/`, kết quả cũng đạt `3/3 SOLVED` (`0 TIMEOUT`) ở cả 8 cấu hình: tổng `sat_calls_total` giảm từ `401` (`C0`–`C3`, `C5`) xuống `229` (`C4`, `C6`, `C7`, bỏ qua `172` truy vấn = `-42.89%`); tổng `total_decisions` giảm từ `272` (`C0`) xuống `162` (`C2`), `147` (`C3`) và `78` (`C6`/`C7`); tổng `total_runtime_ms_median` giảm từ `137.658 ms` (`C0`) xuống `72.870 ms` (`C6`, `-47.06%`).*

![Hình E3: Tác động của Pure-Literal & Heuristic lên tìm kiếm DPLL](../Source/experiments/results/charts/rq3_heuristics.png)
*Hình E3 (`rq3_heuristics.png`): Tổng `total_decisions` (trái) và `total_backtracks` (phải) giữa `C0`, `C1`, `C2`, `C3` trên 10 màn chuẩn.*

![Hình E4: Hiệu quả cắt giảm số lần gọi SAT nhờ Model Caching](../Source/experiments/results/charts/rq4_model_caching.png)
*Hình E4 (`rq4_model_caching.png`): Số lời gọi SAT thực tế (`sat_calls_total`) giữa không caching (`C0`) và có Model Caching (`C4`) trên từng màn chuẩn.*

**Nhận xét định lượng (RQ3 & RQ4):**
- **Tác động của Pure-Literal (`C1` vs. `C0` — RQ3):** Bật Pure-Literal Elimination giảm tổng `total_decisions` trên 10 màn chuẩn từ `693` xuống `516` (`-25.54%`), trong khi `total_backtracks` giữ nguyên (`530`, do phần lớn nhánh quay lui là các lời gọi kiểm tra phản chứng `UNSAT` bắt buộc phải vét hết nhánh mâu thuẫn). Tuy nhiên, chi phí quét literal thuần ở mỗi nút đệ quy khiến `solver_runtime_ms` tăng từ `103.033` lên `128.916 ms` (tổng `total_runtime_ms_median` tăng từ `163.638` lên `197.395 ms`, chậm hơn `20.63%`) khi không đi kèm heuristic thông minh.
- **Tác động của Heuristic chọn biến (`C2`, `C3` vs. `C1` — RQ3):** Kết hợp thêm heuristic `moms` (`C2`) hoặc `jw` (`C3`) cắt tiếp `total_decisions` từ `516` xuống còn **`285`** (`-44.77%` so với `C1`, **`-58.87%`** so với `C0`), kéo `total_runtime_ms_median` xuống `166.261 ms` (`C2`) và `168.359 ms` (`C3`) — triệt tiêu gần như toàn bộ phần chậm do Pure-Literal gây ra ở `C1`. So với `C3` (`jw`), `C2` (`moms`) đạt cùng số `decisions`/`backtracks` (`285`/`530`) nhưng nhanh hơn ở cả hai lần đo (`164.893` vs `177.458 ms` ở lượt đo `jw`, và `166.261` vs `168.359 ms` ở lượt đo `moms`) nhờ chỉ duyệt các mệnh đề có kích thước nhỏ nhất. Trên lưới `3×3`, cả `C2` và `C3` đều đạt `total_decisions = 0` (giải hoàn toàn bằng Unit Propagation + Pure-Literal), nên chi phí tính heuristic không tạo ra bất lợi đáng kể so với `C0`.
- **Tác động của Model Caching (`C4` vs. `C0` và `C6` vs. `C2` — RQ4):**
  - So với `C0`, `C4` bỏ qua được **`656`** truy vấn SAT dư thừa (`sat_calls_cached_skipped = 656`), cắt giảm `sat_calls_total` từ `1,643` xuống **`987`** (**giảm `39.93%`**), giảm `total_decisions` từ `693` xuống `282` (`-59.31%`), giảm `total_propagations` từ `19,639` xuống `10,723` (`-45.40%`), và rút ngắn `total_runtime_ms_median` từ `163.638 ms` xuống **`124.663 ms`** (**nhanh hơn `23.82%`**).
  - Trên nền DPLL đã tối ưu (`C6` vs. `C2`), Model Caching bỏ qua **`646`** truy vấn (`1,643` → **`997`**, **giảm `39.32%`**) và rút ngắn `total_runtime_ms_median` từ `166.261 ms` xuống **`116.285 ms`** (**nhanh hơn `30.06%`**), đưa `C6` thành cấu hình nhanh nhất toàn bảng (nhanh hơn `C0` **`28.94%`** với `total_decisions` chỉ còn **`122`**, giảm `82.40%` so với `C0`).
  - Trong suốt toàn bộ benchmark, `cross_config_consistency = PASS` ở `100%` cặp màn chơi — chứng minh Model Caching bảo toàn tuyệt đối chuỗi phán quyết và `deduction_steps`.

#### 5.5. Phân tích ca biên, ca thất bại, timeout và trường hợp kẹt giữa chừng
Tuân thủ nguyên tắc báo cáo trung thực mọi trường hợp không đạt `SOLVED` `(description.md 2.7, AI - Project 2.pdf 4.5, FAQ #13)`, Bảng 5.5 liệt kê toàn bộ các ca kết thúc khác `SOLVED` trên đủ 15 puzzle × 8 cấu hình (chỉ xuất hiện ở 2 màn `edge_cases/`, **không** có ca `TIMEOUT` hay `ERROR` nào ở bộ chuẩn và mở rộng).

**Bảng 5.5: Tổng hợp các ca biên (`edge_cases/`) — ghi nhận đầy đủ qua các cấu hình đại diện (`C0`, `C4`, `C5`, `C6`, `C7`)**

| Màn chơi | Cấu hình | `terminal_status` | `solved_cells` / `total_cells` | `deduction_steps` | `sat_calls_total` (`cached_skipped`) | Thời gian tới lúc dừng (`ms`, `median`) | Nguyên nhân quan sát & Phân tích hành vi No-Guess |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `edge_3x3_ambiguous` | `C0`–`C3` | `AMBIGUOUS` | `5 / 9` | `3` | `47` (`0`) | `1.875–2.092` | Suy diễn hợp lệ 3 bước đầu (`5/9` ô mở), tại `step = 3` còn 4 ô `['A2', 'B2', 'A3', 'B3']` đều cho cả $KB_3 \wedge \neg C_i$ và $KB_3 \wedge C_i$ là `SAT`. Agent ghi log `WARNING` và dừng với `VerdictCode.NOT_PROVABLE`, không đoán mò. |
| `edge_3x3_ambiguous` | `C4`, `C6` | `AMBIGUOUS` | `5 / 9` | `3` | `20` (`27`) | `1.422` (`C4`) / `1.518` (`C6`) | Cùng điểm dừng `step = 3` (`5/9` ô mở), Model Caching bỏ qua `27/47` (`57.45%`) truy vấn SAT nhờ các mô hình `SAT` ở bước kẹt. |
| `edge_3x3_ambiguous` | `C5` / `C7` | `AMBIGUOUS` | `5 / 9` | `3` | `47` (`0`) / `20` (`27`) | `3.625` (`C5`) / `2.107` (`C7`) | Hội tụ cùng chuỗi phán quyết và điểm dừng `step = 3` (`cross_config_consistency = PASS`). |
| `edge_3x3_inconsistent` | `C0`–`C7` | `INCONSISTENT` | `2 / 9` | `0` | `1` (`0`) | `0.228–0.302` | Ngay tại bước $t = 0$, kiểm tra nhất quán ban đầu `DPLL(KB_0)` trả về `UNSAT` (`sat_calls_total = 1`). Agent dừng tức thì với `VerdictCode.INCONSISTENT`, không mở thêm ô nào. |

**Nhận xét định lượng (RQ5):**
- **Ca mơ hồ / Kẹt giữa chừng (`AMBIGUOUS`):** Tại `step = 3` của `edge_3x3_ambiguous` (tương ứng trạng thái có `2` thẻ mở sẵn + `3` bước suy diễn hợp lệ = `5/9` ô đã biết), toàn bộ 4 ô còn lại (`A2, B2, A3, B3`) đều cho cả hai truy vấn $KB_3 \wedge \neg C_i$ và $KB_3 \wedge C_i$ là `SAT`. Agent ghi cảnh báo `WARNING` vào logger `"agent"` và trả về bước kết thúc `cell=None, verdict=UNKNOWN, verdict_code=NOT_PROVABLE`, tuân thủ tuyệt đối quy tắc No-Guess. Model Caching cắt giảm được `27/47` truy vấn (`57.45%`) ngay cả khi rơi vào vùng mơ hồ vì có sẵn chứng nhân `SAT` cho nhiều ô cùng lúc.
- **Ca mâu thuẫn (`INCONSISTENT`):** Trên `edge_3x3_inconsistent`, phép kiểm tra nhất quán bắt buộc ở đầu mỗi bước phát hiện `DPLL(KB_0) = UNSAT` chỉ sau đúng **`1` lời gọi SAT** (`0.228–0.302 ms`), chặn đứng nguy cơ bùng nổ logic (*ex falso quodlibet*) biến mọi ô thành `CRIMINAL`.
- **Ca quá thời gian (`TIMEOUT`):** Không ghi nhận ca `TIMEOUT` nào (`0/360` lượt chạy) trong giới hạn `60,000 ms` — thời gian chạy dài nhất toàn chiến dịch chỉ là `199.405 ms` (`5x5_02` ở `C5`).

#### 5.6. Hạn chế của hệ thống và Hướng cải thiện
1. **Giới hạn của thuật toán DPLL thuần Python:** Bộ giải hiện cài đặt DPLL cổ điển bằng Python thuần theo đúng yêu cầu tự cài đặt `(description.md 2.4)`. So với các bộ giải SAT hiện đại (CDCL – *Conflict-Driven Clause Learning*, *Two-Watched Literals*, *non-chronological backjumping*, *restarts*), DPLL có thể lặp lại việc khám phá các nhánh xung đột tương đương khi kích thước lưới mở rộng vượt `5×5` hoặc khi xuất hiện nhiều ràng buộc `PARITY` (chuỗi XOR dễ tạo nhánh sâu với DPLL, như thấy ở `ext_4x4_03` tốn `48.718 ms` trong solver).
2. **Tái mã hóa và giải độc lập theo từng bước:** Ở mỗi bước suy diễn $t$, hệ thống gọi lại `encode_kb(public_state)` từ đầu và chạy DPLL không kế thừa mệnh đề học được giữa các truy vấn trong cùng $KB_t$. Điều này giải thích vì sao ở lưới `3×3` chi phí ngoài DPLL chiếm `~77%` tổng thời gian (`2.227 ms` tổng so với `0.487 ms` trong solver ở `3x3_01`). Hướng cải thiện là mã hóa gia tăng (incremental CNF encoding) và tái sử dụng cấu trúc dữ liệu nội bộ của solver giữa các lần kiểm tra `assumptions`.
3. **Phạm vi tập dữ liệu đánh giá:** Tập chuẩn gồm 10 màn chơi đại diện cho ba kích thước `3×3`, `4×4`, `5×5` (cùng 3 màn mở rộng và 2 ca biên). Dù đủ bao phủ các mẫu clue và Extension yêu cầu, kích thước mẫu nhỏ khiến các nhận định về hiệu năng mang tính định tính–so sánh trên tập điển hình hơn là kết luận thống kê tổng quát trên hàng trăm puzzle ngẫu nhiên.
4. **Hạn chế của chức năng Gợi ý (`Hint`) ở khía cạnh giải thích tối thiểu:** `HintEngine` hiện dùng duyệt liên kết vùng (Scope-Based BFS) để gom các manh mối có liên hệ với ô bị ép buộc mà không cần gọi thêm SAT; hướng mở rộng để tinh gọn lời giải thích hơn nữa là tìm *tập con manh mối tối giản không thỏa mãn* (Deletion-Based MUS).

### [KẾT THÚC BẢN NHÁP MỤC 5]

---

## 9. Trạng thái Tích hợp & Thực thi Benchmark (cập nhật 26/11/2026)

Toàn bộ các phụ thuộc từ **TV1, TV2, TV3** đã được hợp nhất trên `origin/dev` (`9d2140b`) và kiểm chứng thực tế ở GĐ 2 (Mốc 1) + GĐ 3B:
- **TV1 (`engine/`, `puzzles/`):** `GameEngine` thật + đủ 15 puzzle (`10` standard, `3` extension, `2` edge_case) đã có mặt trên `origin/dev`; kiểm định `uniqueness_report.py` xác nhận `13/13` màn giải được đều `UNIQUE` (`matches_hidden_solution=true`).
- **TV2 (`logic/`):** `CNFEncoder` (hỗ trợ đủ `direct` & `sinz`, 6 mẫu cơ bản + `INTERSECTION`, `COMMON_NEIGHBORS`, `CORNERS`, `BETWEEN`, `PARITY`, `COMPARE_COUNTS`) đã merge vào `origin/dev` qua **PR #3** (`9d2140b`).
- **TV3 (`solver/`):** `DPLLSolver` với `lexicographic`, `moms`, `jw` và `enable_pure_literal` đã merge vào `origin/dev` (PR #1, PR #4), giải toàn bộ `5×5` trong `< 200 ms` (`0 TIMEOUT`).
- **Điểm nghẽn cứng đang chờ thành viên khác:** (1) Review/merge PR nhánh `feat/tv4-benchmark-final` vào `dev`; (2) TV5 hoàn thành GUI + `Source/main.py` cho E2E GĐ 3A (`Hint` + `Auto Solve` animated); (3) TV5 biên tập `Report.pdf` tổng, quay Video Demo Google Drive (Incognito) và cả nhóm chốt Contribution Matrix (GĐ 4B/4C).

---

## 10. Phụ lục LLM (AI Appendix — Phần TV4)

Theo yêu cầu của `plan.md` (Mục 3) và `schedule.md` (Mục 2, STT 11), bảng dưới tóm tắt các nhóm prompt chính/tiêu biểu đã dùng trong phạm vi công việc TV4 (không chứa khóa bí mật hay dữ liệu nhạy cảm):

| STT | Nhóm tác vụ TV4 | Nội dung prompt tiêu biểu (tóm tắt) | Đầu ra được kiểm chứng bởi người/test |
| :---: | :--- | :--- | :--- |
| 1 | Rà soát hợp đồng & thiết kế giao thức TV4 | *“Rà soát `core/contracts/models.py` và `interfaces.py` dưới góc độ TV4: đề xuất quy ước xử lý `AMBIGUOUS`/`INCONSISTENT`, tránh đếm gấp đôi khi `submit_verdict` gọi lại agent, và callback `on_step` cho animation.”* | `docs/tv4_contract_review_and_test_plan.md`, `docs/tv4_agent_conventions.md` |
| 2 | Cài đặt `Source/agent/` & kiểm thử đơn vị | *“Cài đặt `entailment.py` (Model Caching bật/tắt được), `kb_cache.py` (LRU ≤ 8 theo khóa KB bất biến), `logic_agent.py` (No-Guess loop row-major), `hint_engine.py` (Scope-Based BFS), `uniqueness.py` (blocking clause chỉ trên biến chính) kèm unit test `test_agent/`.”* | `Source/agent/*.py`, `Source/tests/test_agent/*.py` (toàn bộ pass trên `pytest`) |
| 3 | Xây dựng khung thực nghiệm & biểu đồ | *“Viết `experiments/configs.py`, `encoder_factory.py`, `solver_factory.py`, `benchmark.py` (C0–C7, timeout `multiprocessing` trên Windows, `deterministic_check`, `cross_config_consistency`), `uniqueness_report.py` và `plots.py` (RQ1–RQ4).”* | `Source/experiments/*.py`, `Source/tests/test_experiments/*.py` |
| 4 | Tích hợp thực nghiệm GĐ 3B & đối soát báo cáo | *“Tích hợp cục bộ `CNFEncoder` thật (Direct + Sinz) với `DPLLSolver`, chạy `uniqueness_report.py` trên 15 puzzle, chạy `benchmark.py --include-extensions --repeats 3 --timeout-s 60`, sinh 4 biểu đồ PNG, cập nhật `report_tv4_experiments.md` / `report_tv4_algorithms.md` khớp 1-1 CSV gốc và audit độc lập.”* | `uniqueness_report.csv`, `benchmark_*.csv`, `charts/*.png`, `209 passed` trên `pytest`, subagent audit 7/7 PASS |

---

## Phụ lục nhỏ: Trạng thái các điểm mở GĐ 0 (đã chốt đến 26/11/2026)

1. **Ca kẹt giữa chừng (`FAQ #13`):** Đã chốt tách 2 ca biên ở `edge_cases/` (`edge_3x3_ambiguous`, `edge_3x3_inconsistent`) và giữ 10 màn chuẩn đều `SOLVED` (`UNIQUE`).
2. **Danh sách heuristic TV3:** TV3 đã cài đủ cả `lexicographic`, `moms`, `jw` và cờ `enable_pure_literal`; benchmark GĐ 3B chọn `moms` làm `best_heur` cho `C6`/`C7`.
3. **Vùng mở rộng (Extension 1):** TV1/TV2 đã cài đủ `INTERSECTION`, `COMMON_NEIGHBORS`, `CORNERS`, `BETWEEN` (cùng `PARITY`, `COMPARE_COUNTS`), kiểm chứng trên 3 màn `extensions/`.
4. **Cơ chế Timeout trên Windows:** Đã chốt dùng `multiprocessing` (`spawn`) ở `experiments/benchmark.py` (`timeout_s = 60`).
5. **Quy ước `puzzle_id` & thẻ mở sẵn (`FAQ #8`):** Đã chốt cố định qua `3x3_01..04` (`2` thẻ), `4x4_01..04` (`3` thẻ), `5x5_01..02` (`5` thẻ), `ext_3x3_01`, `ext_4x4_02..03`, `edge_3x3_ambiguous`, `edge_3x3_inconsistent`.
6. **Ngôn ngữ thống nhất của `Report.pdf` (`description.md 4.2`):** Toàn bộ tài liệu TV4 đang viết bằng **tiếng Việt**; chờ TV5 xác nhận đồng bộ ngôn ngữ khi biên tập `Report.pdf` tổng ở GĐ 4B.
