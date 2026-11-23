# THIẾT KẾ THỰC NGHIỆM & BẢN NHÁP MỤC "EXPERIMENTS" — PROJECT 2: GRIDUCTIVE SOLVER (PHẦN TV4)

- **Dự án:** Project 2 — *Griductive Solver* (CSC14003 – Nhập môn Trí tuệ Nhân tạo, ĐH Khoa học Tự nhiên, ĐHQG-HCM)
- **Người phụ trách:** Nguyên — Thành viên 4 (TV4: `agent/`, `experiments/`, `tests/test_agent/`, mục *Algorithms* & *Experiments* trong `Report.pdf`) `(plan.md 2.4, schedule.md)`
- **Trạng thái hiện tại:** **Bản thiết kế & bản nháp trước GĐ 3B** — đã đồng bộ khung script `Source/experiments/` (`configs.py`, `encoder_factory.py`, `benchmark.py`, `plots.py`, `uniqueness_report.py`) theo `core/contracts/` và `docs/tv4_agent_conventions.md`; đang chờ `ICNFEncoder` thật của TV2 (Direct + Sinz) để chạy thực nghiệm chính thức. Mọi ô kết quả trong khung báo cáo đều giữ nguyên `[chờ kết quả benchmark GĐ 3B]`, tuyệt đối không điền số liệu tạm/giả.
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

| `puzzle_id` | Nhóm (`dataset_group`) | Kích thước ($N \times N$) | `primary_vars` ($N^2$) | Thẻ mở sẵn ở $KB_0$ `(FAQ #8)` | `max_region_size` ($\max \|R\|$) | `uniqueness_status` `(FAQ #9)` | Trạng thái kỳ vọng |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` .. `3x3_04` (4 màn) | `standard` | 3×3 | 9 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `UNIQUE` *(qua encoder thật TV2)* | `SOLVED` |
| `4x4_01` .. `4x4_04` (4 màn) | `standard` | 4×4 | 16 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `UNIQUE` *(qua encoder thật TV2)* | `SOLVED` |
| `5x5_01`, `5x5_02` (2 màn) | `standard` | 5×5 | 25 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `UNIQUE` *(qua encoder thật TV2)* | `SOLVED` |
| `ext_3x3_01`, `ext_4x4_02`, `ext_4x4_03` (3 màn) | `extension` | 3×3 / 4×4 | 9 / 16 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `UNIQUE` *(qua encoder thật TV2)* | `SOLVED` |
| `edge_3x3_ambiguous` | `edge_case` | 3×3 | 9 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `AMBIGUOUS` |
| `edge_3x3_inconsistent` | `edge_case` | 3×3 | 9 | `[chờ tổng hợp GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `UNSAT` *(qua encoder thật TV2)* | `INCONSISTENT` |

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

> \* Ghi chú: `best_heur` mặc định là `jw` (có thể đổi bằng cờ `--best-heur moms|jw|lexicographic` trong `configs.py` / `benchmark.py`) và cố định cùng một giá trị cho cả `C6` và `C7` để phép so sánh Direct vs. Sinz công bằng. Khi chưa có bộ mã hóa Sinz thật trong `logic/`, `encoder_factory.py` tự ghi nhận các cấu hình `sinz` (`C5`, `C7`) với `terminal_status = SKIPPED_NO_ENCODER` và cấu hình `direct` rơi về `StubCNFEncoder` (`encoding = "stub"`, không đưa vào báo cáo chính thức).

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
Để đánh giá toàn diện hiệu năng, khả năng mở rộng và tính tin cậy của hệ thống *Griductive Solver*, chúng tôi thực hiện chuỗi thực nghiệm trên bộ dữ liệu gồm **10 màn chơi chuẩn** (`4` màn `3×3`, `4` màn `4×4`, `2` màn `5×5`, vượt mức tối thiểu 6 màn của `FAQ #2`) cùng tùy chọn **3 màn mở rộng** (`extensions/`) và **2 màn kiểm thử biên** (`edge_3x3_ambiguous`, `edge_3x3_inconsistent`). Tất cả các cấu hình mã hóa CNF, bộ giải DPLL và tối ưu ở Logic Agent đều được chạy trên **cùng một tập puzzle** ở chế độ không giao diện (headless) để đảm bảo tính công bằng tuyệt đối `(AI - Project 2.pdf 4.5)`.

Mỗi cặp `(puzzle, cấu hình)` được chạy lặp `[chờ xác nhận: 5 hoặc 3]` lần sau `1` lượt warm-up, với giới hạn thời gian `timeout = 60 giây` cho mỗi lượt chạy `(plan.md 3.1)`. Giá trị thời gian thực thi được báo cáo bằng **trung vị (median)** tính bằng mili-giây (`ms`), kèm kiểm tra tự động tính tất định (`deterministic_check`) và đối chiếu chéo chuỗi phán quyết giữa các cấu hình (`cross_config_consistency`). Theo xác nhận chính thức từ giảng viên `(FAQ #12)`, chúng tôi báo cáo số bước suy diễn (`deduction_steps`) làm đại diện cho độ sâu suy luận và bỏ qua chỉ số `reveal_waves`.

**Bảng 5.1: Thông số môi trường phần cứng và phần mềm thực nghiệm**

| Thành phần môi trường | Chi tiết |
| :--- | :--- |
| CPU | `[chờ kết quả benchmark GĐ 3B]` |
| Bộ nhớ RAM | `[chờ kết quả benchmark GĐ 3B]` |
| Hệ điều hành | `[chờ kết quả benchmark GĐ 3B]` |
| Phiên bản Python | `[chờ kết quả benchmark GĐ 3B]` |
| Thời điểm thực thi & Commit | `[chờ kết quả benchmark GĐ 3B]` |

#### 5.2. Kết quả tổng hợp trên bộ 10 màn chơi chuẩn
Bảng 5.2 tổng hợp đầy đủ các nhóm chỉ số bắt buộc (`AI - Project 2.pdf 4.5, description.md 2.7`) của hệ thống ở cấu hình tối ưu tiêu chuẩn `[chờ chốt tên cấu hình tốt nhất giữa C6/C7 ở GĐ 3B]` trên toàn bộ 10 màn chơi chuẩn.

**Bảng 5.2: Kết quả thực nghiệm tổng hợp trên 10 màn chơi chuẩn (cấu hình `[chờ kết quả benchmark GĐ 3B]`)**

| Màn chơi | Kích thước | `terminal_status` | `primary_vars` | `aux_vars_final` ($KB_T$) | `cnf_clauses_final` ($KB_T$) | `sat_calls_total` | `total_decisions` | `total_propagations` | `total_backtracks` | `deduction_steps`* | `solver_runtime_ms` (`median`) | `total_runtime_ms` (`median`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` | 3×3 | `[chờ kết quả benchmark GĐ 3B]` | 9 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `3x3_02` | 3×3 | `[chờ kết quả benchmark GĐ 3B]` | 9 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `3x3_03` | 3×3 | `[chờ kết quả benchmark GĐ 3B]` | 9 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `3x3_04` | 3×3 | `[chờ kết quả benchmark GĐ 3B]` | 9 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `4x4_01` | 4×4 | `[chờ kết quả benchmark GĐ 3B]` | 16 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `4x4_02` | 4×4 | `[chờ kết quả benchmark GĐ 3B]` | 16 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `4x4_03` | 4×4 | `[chờ kết quả benchmark GĐ 3B]` | 16 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `4x4_04` | 4×4 | `[chờ kết quả benchmark GĐ 3B]` | 16 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_01` | 5×5 | `[chờ kết quả benchmark GĐ 3B]` | 25 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_02` | 5×5 | `[chờ kết quả benchmark GĐ 3B]` | 25 | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |

*\*Ghi chú: Chỉ số `reveal_waves` được bỏ qua theo hướng dẫn tại FAQ #12.*

**Khung nhận xét (RQ1 – Khả năng mở rộng):**
- Khi chuyển từ lưới `3×3` sang `4×4` và `5×5`, số lượng mệnh đề CNF tại $KB_T$ tăng từ `[chờ kết quả benchmark GĐ 3B]` lên `[chờ kết quả benchmark GĐ 3B]`, kéo theo tổng thời gian thực thi thay đổi từ `[chờ kết quả benchmark GĐ 3B]` ms lên `[chờ kết quả benchmark GĐ 3B]` ms.
- Tỷ lệ giữa thời gian trong lõi DPLL (`solver_runtime_ms`) và tổng thời gian giải (`total_runtime_ms`) đạt `[chờ kết quả benchmark GĐ 3B]`%, cho thấy nút thắt hiệu năng chính nằm ở `[chờ phân tích GĐ 3B: bộ giải DPLL / khâu tái mã hóa CNF]`.
- Tất cả các lần chạy lặp lại đều đạt `deterministic_check = PASS` và mọi cấu hình không timeout/skip đều đạt `cross_config_consistency = PASS` *(kỳ vọng — xác nhận bằng GĐ 3B)*, khẳng định hệ thống hoàn toàn tất định và các tối ưu không làm sai lệch chuỗi phán quyết.

#### 5.3. So sánh chiến lược mã hóa CNF: Direct Combinatorial vs. Sequential Counter (Sinz)
Để trả lời **RQ2**, chúng tôi đối chiếu hai chiến lược mã hóa ràng buộc đếm (`AT_LEAST`, `AT_MOST`, `EXACTLY`) theo kích thước vùng thực tế $\|R\|$ (`max_region_size`) trên cùng 10 màn chơi chuẩn (và tùy chọn 3 màn `extensions/`) ở cả hai chế độ: DPLL cơ bản (`C0` vs. `C5`) và cấu hình tối ưu (`C6` vs. `C7`). Nhắc lại rằng Sinz mã hóa trực tiếp `AT_MOST(k, R)` với $O(\|R\|\cdot k)$ biến phụ và mệnh đề, còn `AT_LEAST(k, R)` được quy về `AT_MOST(\|R\|−k)` trên các literal phủ định nên tốn $O(\|R\|\cdot(\|R\|-k))$.

**Bảng 5.3: So sánh Direct Combinatorial và Sequential Counter (Sinz) theo kích thước vùng $\|R\|$ trên 10 màn chơi chuẩn**

| Màn chơi | `max_region_size` ($\max \|R\|$) | Cấu hình so sánh | `aux_vars_final` (Direct / Sinz) | `cnf_clauses_final` (Direct / Sinz) | `total_propagations` (Direct / Sinz) | `total_decisions` (Direct / Sinz) | `total_runtime_ms` median (Direct / Sinz) | Ghi chú / Trạng thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `3x3_01` .. `3x3_04` | `[chờ GĐ 3B]` | `C0` vs `C5` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `4x4_01` .. `4x4_04` | `[chờ GĐ 3B]` | `C0` vs `C5` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_01` | `[chờ GĐ 3B]` | `C0` vs `C5` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_02` | `[chờ GĐ 3B]` | `C0` vs `C5` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_01` | `[chờ GĐ 3B]` | `C6` vs `C7` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `5x5_02` | `[chờ GĐ 3B]` | `C6` vs `C7` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |

*(Chèn **Hình E1** — 2 biểu đồ con so sánh biến và mệnh đề CNF Direct vs. Sinz tại đây: `[chờ biểu đồ GĐ 3B]`.)*

**Khung nhận xét (RQ2 – Direct vs. Sinz theo kích thước vùng $\|R\|$ thực):**
- *Ghi chú cách tính:* `max_region_size` lấy $\max |R|$ trên mọi clue có vùng của màn chơi. Trên 10 màn chuẩn, giá trị này trùng với $\max |R|$ của các clue đếm (`AT_LEAST`/`AT_MOST`/`EXACTLY`); ở `extensions/` nó có thể đến từ `PARITY` hoặc `COMPARE_COUNTS`, nên khi đối chiếu Direct vs. Sinz trên `extensions/` cần xem vùng lớn nhất thuộc loại clue nào.
- Theo `description.md 2.3`, ở mọi kích thước lưới (`3×3`, `4×4`, `5×5`), các vùng cơ bản đều có kích thước nhỏ (`ROW`/`COL` $\le N \le 5$, `NEIGHBORS` $\le 8$). Vì vậy sự khác biệt giữa Direct và Sinz phụ thuộc chủ yếu vào **kích thước vùng $\|R\|$ thực tế của từng clue** (`max_region_size`) và giá trị $k$, chứ không đơn thuần theo kích thước lưới $N$.
- Trên các clue có vùng nhỏ ($\|R\| \le 5$, như `ROW`/`COL`), Direct không phát sinh biến phụ đếm và số mệnh đề tổ hợp nhỏ (`[chờ kết quả benchmark GĐ 3B]`), trong khi Sinz thêm biến phụ ở cả hai chiều `AT_MOST(k)` và `AT_LEAST(k)` (`AT_MOST(\|R\|−k)` trên literal phủ định).
- Trên vùng `NEIGHBORS` ở ô trong ($\|R\| = 8$), với `EXACTLY(k, R)`, Direct sinh $\binom{8}{k+1} + \binom{8}{9-k}$ mệnh đề và **đạt đỉnh tại $k = 4$ với $56 + 56 = 112$ mệnh đề**. Khi màn chơi chứa các vùng lớn hơn (`EXPLICIT` nhiều ô hoặc `BOUNDARY` với 8/12/16 ô nếu cài đặt), số mệnh đề Direct tăng theo tổ hợp $\binom{\|R\|}{k+1} + \binom{\|R\|}{\|R\|-k+1}$, trong khi Sinz giữ mức $O(\|R\|\cdot k)$ cho `AT_MOST(k)` và $O(\|R\|\cdot(\|R\|-k))$ cho `AT_LEAST(k)`.
- Đối chiếu số liệu thực tế ở GĐ 3B (`[chờ kết quả benchmark GĐ 3B]`): xác định ngưỡng $\|R\|$ giao cắt (crossover point) nơi Sinz bắt đầu ít mệnh đề hơn hoặc nhanh hơn Direct, kèm ảnh hưởng của biến phụ Sinz lên `total_propagations` và `total_decisions`.

#### 5.4. Đánh giá tối ưu DPLL (Pure-Literal, MOMs/JW) và Model Caching
Để trả lời **RQ3** và **RQ4**, Bảng 5.4 tổng hợp kết quả nghiên cứu cắt bỏ (ablation study) từ mốc chuẩn `C0` sang các cấu hình lần lượt bổ sung Pure-Literal (`C1`), heuristic `MOMs` (`C2`), heuristic `JW` (`C3`), Model Caching (`C4`), và tổ hợp tối ưu (`C6`, `C7`). Nhằm đảm bảo so sánh công bằng, các cột tổng chỉ số (`sat_calls_total`, `total_decisions`, `total_backtracks`, `total_runtime_ms_median`) được tính **trên cùng tập giao $S_{\text{common}}$ gồm các màn mà mọi cấu hình đều `SOLVED`**, đồng thời báo riêng `solved_rate` và số ca `TIMEOUT`.

**Bảng 5.4: So sánh hiệu năng các cấu hình DPLL và Model Caching trên tập giao $S_{\text{common}}$ và số ca `TIMEOUT`**

| Cấu hình | Encoding | Heuristic | Pure-Literal | Model Caching | `solved_rate` *(dẫn xuất)* | Số ca `TIMEOUT` | Tổng `sat_calls_total` (trên $S_{\text{common}}$) | Tổng `total_decisions` (trên $S_{\text{common}}$) | Tổng `total_backtracks` (trên $S_{\text{common}}$) | Tổng `total_runtime_ms_median` (trên $S_{\text{common}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C0` (Baseline) | `direct` | `lexicographic` | Tắt | Tắt | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C1` (+PL) | `direct` | `lexicographic` | Bật | Tắt | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C2` (+PL+MOMs) | `direct` | `moms` | Bật | Tắt | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C3` (+PL+JW) | `direct` | `jw` | Bật | Tắt | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C4` (+Caching) | `direct` | `lexicographic` | Tắt | Bật | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C5` (Sinz Base) | `sinz` | `lexicographic` | Tắt | Tắt | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C6` (Opt Direct) | `direct` | `best_heur` | Bật | Bật | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |
| `C7` (Opt Sinz) | `sinz` | `best_heur` | Bật | Bật | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` | `[chờ kết quả benchmark GĐ 3B]` |

*\*Ghi chú Bảng 5.4: $S_{\text{common}}$ là tập các màn chuẩn mà toàn bộ cấu hình đang khảo sát đều đạt `SOLVED` (kích thước $|S_{\text{common}}|$ = `[chờ kết quả benchmark GĐ 3B]` / 10). Nếu có cấu hình bị `TIMEOUT`, số ca `TIMEOUT` được ghi tách riêng ở cột `Số ca TIMEOUT` và chi tiết các màn ngoài $S_{\text{common}}$ được trình bày ở Bảng 5.2, 5.3 và 5.5.*

*(Chèn **Hình E2**, **Hình E3**, **Hình E4** tại đây: `[chờ biểu đồ GĐ 3B]`.)*

**Khung nhận xét (RQ3 & RQ4):**
- **Tác động của Pure-Literal (`C1` vs. `C0`):** `[chờ kết quả benchmark GĐ 3B — nhận xét mức giảm total_decisions/total_backtracks và chi phí quét literal thuần ở mỗi nút đệ quy]`.
- **Tác động của Heuristic chọn biến (`C2`, `C3` vs. `C1`):** `[chờ kết quả benchmark GĐ 3B — so sánh MOMs với JW; làm rõ sự đánh đổi giữa thời gian tính trọng số heuristic trên lưới nhỏ 3×3 và lợi ích cắt tỉa cây tìm kiếm trên lưới 5×5]`.
- **Tác động của Model Caching (`C4` vs. `C0` và `C6` vs. `C2`/`C3`):** Model Caching bỏ qua được `[chờ kết quả benchmark GĐ 3B]` truy vấn SAT dư thừa (`sat_calls_cached_skipped`, giảm `[chờ kết quả benchmark GĐ 3B]`% `sat_calls_total`) và rút ngắn `total_runtime_ms` khoảng `[chờ kết quả benchmark GĐ 3B]`%, trong khi bảo toàn tuyệt đối chuỗi phán quyết và `deduction_steps` (`cross_config_consistency = PASS`) *(kỳ vọng — xác nhận bằng GĐ 3B)*.

#### 5.5. Phân tích ca biên, ca thất bại, timeout và trường hợp kẹt giữa chừng
Tuân thủ nguyên tắc báo cáo trung thực mọi trường hợp thất bại/timeout `(description.md 2.7, AI - Project 2.pdf 4.5)` và tùy chọn phân tích ca kẹt giữa chừng `(FAQ #13)`, Bảng 5.5 liệt kê đầy đủ các màn chơi kết thúc không ở trạng thái `SOLVED` (bao gồm cả ca biên `edge_cases/` và mọi ca `TIMEOUT`/`AMBIGUOUS` phát sinh trong quá trình chạy 10 màn chuẩn, nếu có).

**Bảng 5.5: Tổng hợp các ca biên, ca kẹt giữa chừng, timeout và thất bại**

| Màn chơi | Cấu hình | `terminal_status` | `solved_cells` / `total_cells` | `deduction_steps` | `sat_calls_total` | Thời gian tới lúc dừng (`ms`) | Nguyên nhân quan sát & Phân tích hành vi No-Guess |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `[chờ kết quả benchmark GĐ 3B]` | `[chờ GĐ 3B]` | `AMBIGUOUS` / `INCONSISTENT` / `TIMEOUT` | `[chờ GĐ 3B]` | `[chờ GĐ 3B]` | `[chờ GĐ 3B]` | `[chờ GĐ 3B]` | `[chờ phân tích thực tế GĐ 3B]` |

**Khung nhận xét (RQ5):**
- **Ca mơ hồ / Kẹt giữa chừng (`AMBIGUOUS`):** Tại bước dừng `t = [chờ GĐ 3B]`, mọi nhân vật chưa mở đều cho cả hai truy vấn $KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$ là `SAT`. Agent trả về `UNKNOWN` cho toàn bộ ô còn lại và dừng an toàn mà không lật bất kỳ thẻ ẩn nào, tuân thủ nghiêm ngặt quy tắc No-Guess *(kỳ vọng — xác nhận bằng GĐ 3B)*.
- **Ca mâu thuẫn (`INCONSISTENT`):** Ngay khi kiểm tra tính nhất quán ban đầu `DPLL(KB_t) = UNSAT`, Agent dừng tức thì và trả `INCONSISTENT` thay vì kết luận sai rằng mọi nhân vật đều đồng thời là `CRIMINAL` và `INNOCENT` *(kỳ vọng — xác nhận bằng GĐ 3B)*.
- **Ca quá thời gian (`TIMEOUT`, nếu xuất hiện):** `[chờ phân tích GĐ 3B — nêu rõ cấu hình/màn chơi nào chạm ngưỡng 60s, nguyên nhân do bùng nổ mệnh đề Direct ở vùng lớn hay cây phân nhánh sâu của DPLL cơ bản, và cách cấu hình tối ưu C6/C7 khắc phục]`.

#### 5.6. Hạn chế của hệ thống và Hướng cải thiện
1. **Giới hạn của thuật toán DPLL thuần Python:** Bộ giải hiện cài đặt DPLL cổ điển bằng Python thuần theo đúng yêu cầu tự cài đặt `(description.md 2.4)`. So với các bộ giải SAT hiện đại (CDCL – *Conflict-Driven Clause Learning*, *Two-Watched Literals*, *non-chronological backjumping*, *restarts*), DPLL có thể lặp lại việc khám phá các nhánh xung đột tương đương khi kích thước lưới mở rộng vượt `5×5` hoặc khi xuất hiện nhiều ràng buộc `PARITY` (chuỗi XOR dễ tạo nhánh sâu với DPLL).
2. **Tái mã hóa và giải độc lập theo từng bước:** Nếu ở mỗi bước suy diễn $t$, hệ thống gọi lại `encode_kb(public_state)` từ đầu và chạy DPLL không kế thừa mệnh đề học được giữa các truy vấn trong cùng $KB_t$, chi phí lặp lại có thể tăng đáng kể khi số ô lớn. Hướng cải thiện là mã hóa gia tăng (incremental CNF encoding) và tái sử dụng cấu trúc dữ liệu nội bộ của solver giữa các lần kiểm tra `assumptions`.
3. **Phạm vi tập dữ liệu đánh giá:** Tập chuẩn gồm 10 màn chơi đại diện cho ba kích thước `3×3`, `4×4`, `5×5` (cùng 3 màn mở rộng và 2 ca biên). Dù đủ bao phủ các mẫu clue và Extension yêu cầu, kích thước mẫu nhỏ khiến các nhận định về hiệu năng mang tính định tính–so sánh trên tập điển hình hơn là kết luận thống kê tổng quát trên hàng trăm puzzle ngẫu nhiên.
4. **Hạn chế của chức năng Gợi ý (`Hint`) ở khía cạnh giải thích tối thiểu:** Nếu `Hint` chỉ ra nhân vật bị ép buộc dựa trên Entailment toàn cục của $KB_t$, việc tìm *tập con manh mối nhỏ nhất* (Minimal Unsatisfiable Subset – MUS) giải thích cho người chơi vì sao nhân vật đó bị ép buộc vẫn là bài toán tốn chi phí tính toán hơn và là hướng mở rộng tiềm năng cho phiên bản sau.

### [KẾT THÚC BẢN NHÁP MỤC 5]

---

## 9. Danh sách Phụ thuộc & Mốc thời gian Thực thi Benchmark

Để chuyển từ bản thiết kế này sang chạy thực nghiệm thật tại **GĐ 3B (`16:00 ngày 27/11 – 14:00 ngày 28/11`)**, TV4 phụ thuộc trực tiếp vào đầu ra của TV1, TV2, TV3 và cần bàn giao kịp cho TV5 theo đúng `schedule.md` (Mục 1, 2, 3):

| Bên cung cấp | Đầu vào TV4 cần để chạy Benchmark | Mốc hạn chót chính (`schedule.md`) | Rủi ro nếu trễ & Phương án dự phòng của TV4 |
| :--- | :--- | :--- | :--- |
| **TV1** *(chủ trì)* + Cả nhóm | Đóng băng `core/contracts/models.py` & `interfaces.py` (chốt đầy đủ `CNFStats`, `SATMetrics`, `DeductionStep`, chữ ký `IGameEngine`, `ICNFEncoder`, `ISATSolver`, `ILogicAgent`). | **23/11** *(trước 18:00 — GĐ 0, STT 1)* | Nghẽn khởi đầu code `agent/` và khung `experiments/benchmark.py`. TV4 đọc kỹ `plan.md 1.1` trước để chốt nhanh trong buổi họp 23/11. |
| **TV1** | • `GameEngine` thật không rò rỉ đáp án ẩn + `PuzzleLoader`/`PuzzleValidator`.<br>• Bộ **10 puzzle JSON chuẩn** (`4×3×3`, `4×4×4`, `2×5×5`, vượt mức 6 màn của `FAQ #2`) + 3 màn `extensions/` + `edge_cases/` (`Ambiguous`, `Inconsistent`). | • **Đã giao ngày 23/11** (merge vào `dev`, sớm hơn hạn gốc 23:59 ngày 25/11 *(STT 2)*).<br>• Tích hợp `GameEngine` thật ở **Mốc 2 ngày 26/11** (`10:00–20:00`, *STT 8*).<br>• Duyệt `uniqueness.py` trên 15 puzzle: TV4 đã chạy thử với `StubCNFEncoder` ngày 23/11; chạy lại với encoder thật của TV2 vào **tối 26/11** (`18:00–23:59`, *STT 8*). | Nếu TV1 giao lẻ từng màn, TV4 chạy `uniqueness.py` và test benchmark theo từng lô (`3×3` → `4×4` → `5×5`) ngay khi có file JSON lên Git `(schedule.md mục 3)`. |
| **TV2** | • `ICNFEncoder` thật đủ 6 mẫu clue + ≥ 2 Extensions + trả về chính xác `CNFStats` (`primary_vars`, `aux_vars`, số mệnh đề).<br>• Hỗ trợ chuyển đổi sạch cả 2 chiến lược **`direct` và `sinz`** để chạy so sánh **RQ2**. | • Hạn chính GĐ 1: **23:59 ngày 25/11** *(STT 3, gồm đủ cả Direct & Sinz)*.<br>• Tích hợp Mốc 1: **26/11** *(08:00–18:00, STT 7)*. | **Dự phòng nếu trễ:** Nếu sáng 28/11 vẫn chưa có `sinz`, chạy trước nhóm cấu hình `direct` (`C0`–`C4`, `C6`), xuất CSV/biểu đồ nháp và ping TV2 chốt `sinz` chậm nhất **12:00 ngày 28/11** `(schedule.md mục 3)`. |
| **TV3** | • `ISATSolver` thuần Python đủ 6 yêu cầu + `assumptions` + 4 `SATMetrics` (`decisions`, `propagations`, `backtracks`, `runtime_ms`) tất định.<br>• Các cờ tối ưu `enable_pure_literal` và `heuristic` (`lexicographic` \| `moms` \| `jw`) + cơ chế kiểm tra `timeout` an toàn trên Windows.<br>• Phối hợp tối ưu nếu `5×5` quá chậm. | • Hạn chính GĐ 1: **23:59 ngày 25/11** *(STT 4, gồm đủ DPLL + `heuristics.py`)*.<br>• Tích hợp Mốc 1: **26/11** *(08:00–18:00, STT 7)*. | **Dự phòng nếu trễ / chậm `5×5`:** Nếu sáng 28/11 thiếu heuristic, chạy trước cấu hình sẵn có và chốt chậm nhất **12:00 ngày 28/11** `(schedule.md mục 3)`. Nếu `5×5` chạm ngưỡng `timeout = 60s` ở cấu hình baseline (`C0`), giữ nguyên kết quả `TIMEOUT` trung thực và phối hợp TV2 + TV3 kích hoạt ngay tổ hợp dự phòng `C7` (`Sinz + Pure-Literal + MOMs + Model Caching`) trong tối 27/11 `(plan.md 3.1, schedule.md STT 10)`. |
| **TV4 (Nguyên)** *(Tự cam kết giao đúng hạn)* | • Khung `experiments/benchmark.py` + `plots.py` + `uniqueness_report.py` chạy thông với `StubCNFEncoder`.<br>• Kết quả kiểm định `uniqueness.py` trên 15 puzzle của TV1.<br>• Chạy Benchmark đầy đủ khi TV2 giao encoder thật, xuất CSV + biểu đồ PNG 300 DPI.<br>• Hoàn thiện mục *Algorithms* & *Experiments* + Phụ lục AI bàn giao cho **TV5** biên tập `Report.pdf`. | • Khung script: **23:59 ngày 25/11** *(GĐ 1, STT 5)*.<br>• Duyệt `uniqueness.py`: **23:59 ngày 26/11** *(GĐ 2, STT 8)*.<br>• Chốt Benchmark & biểu đồ: **14:00 ngày 28/11** *(GĐ 3B, STT 10)*.<br>• Giao bản viết cho TV5: **trước 10:00 sáng ngày 29/11** *(GĐ 4B; hạn nộp chung **23:59 ngày 29/11/2026**)*. | Viết xong 100% khung báo cáo và script vẽ biểu đồ trước GĐ 3B để ngay khi có encoder thật của TV2 chỉ cần chạy sinh CSV/biểu đồ, điền bảng và viết phân tích định lượng trong tối 28/11. |

---

## Phụ lục nhỏ: Các điểm còn mở cần nhóm xác nhận trong buổi họp GĐ 0 (23/11)

1. **Ca kẹt giữa chừng (`FAQ #13`):** Nhóm giữ 10 màn chuẩn đều giải được (`SOLVED`) và tách 2 ca biên ở `edge_cases/` (`edge_3x3_ambiguous`, `edge_3x3_inconsistent`). *(Đã chốt theo bộ puzzle hiện tại.)*
2. **Danh sách heuristic TV3 cài đặt:** TV3 sẽ cài đủ cả `moms` và `jw` hay chỉ 1 heuristic? *(Cần xác nhận với nhóm — TV3).*
3. **Vùng `BOUNDARY` ở Extension 1:** `BOUNDARY` có trong `description.md 2.2` nhưng không có trong `plan.md 2.2`; xác nhận TV2 có cài `BOUNDARY` (vùng 8/12/16 ô) hay chỉ cài 4 vùng mở rộng trong `plan.md 2.2` (`INTERSECTION`, `COMMON_NEIGHBORS`, `CORNERS`, `BETWEEN`). *(Cần xác nhận với nhóm — TV2 & TV1).*
4. **Cơ chế Timeout trên Windows:** Thống nhất truyền tham số `deadline` vào `ISATSolver.solve()` để vừa dừng đúng 60 giây vừa bảo toàn số liệu tích lũy, hay bọc bằng `multiprocessing` ở `benchmark.py`? *(Cần xác nhận với nhóm — TV3 & TV4).*
5. **Quy ước tên file JSON / `puzzle_id` và số thẻ mở sẵn (`FAQ #8`):** Chốt danh sách `puzzle_id` chuẩn để khớp giữa `puzzles/`, `benchmark.py`, GUI List Map và `Report.pdf`. *(Cần xác nhận với nhóm — TV1 & TV5).*
6. **Ngôn ngữ thống nhất của `Report.pdf` (`description.md 4.2`):** Chốt toàn bộ báo cáo viết bằng **tiếng Việt** hay **tiếng Anh** để TV4 đồng bộ ngôn ngữ bản nháp mục *Experiments* trước ngày 28/11. *(Cần xác nhận với nhóm — TV5 & cả nhóm).*
