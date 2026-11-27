# Mục 6: Thực nghiệm và Đánh giá (Phần TV4)

> **Tác giả:** Nguyễn Trương Bảo Nguyên — Thành viên 4 (TV4: `Source/agent/`, `Source/experiments/`)  
> **Phạm vi trong `Report.pdf`:** Đánh giá định lượng toàn hệ thống *Griductive Solver* hoàn chỉnh (`GameEngine + CNFEncoder + DPLLSolver + DeductiveLogicAgent`) theo đầy đủ 6 nhóm chỉ số bắt buộc (*Project 2 Spec* Mục 4.5) và các quy định FAQ chính thức (`FAQ #2, #8, #9, #12, #13`).  
> **Ghi chú hình ảnh:** 4 biểu đồ PNG 300 DPI (`rq1_scalability.png`, `rq2_direct_vs_sinz.png`, `rq3_heuristics.png`, `rq4_model_caching.png`) được sinh tại `Source/experiments/results/charts/` (thư mục kết quả không đưa lên Git) và **được gửi riêng cho Thành viên 5 (TV5)** để ghép vào `Report.pdf`; vì vậy các liên kết ảnh trong tệp này không hiển thị trên GitHub.

---

## 6.1. Mục tiêu và Câu hỏi Nghiên cứu (Research Questions)

Thực nghiệm nhằm đánh giá khách quan trên **cùng một bộ dữ liệu** ở chế độ không giao diện (headless) đối với ba tầng thiết kế cốt lõi: **mã hóa CNF** (`direct` vs. `sinz`), **bộ giải DPLL** (`lexicographic` / `moms` / `jw`, Pure-Literal Elimination), và **tối ưu ở Logic Agent** (Model Caching, `KBCache`).

| Mã RQ | Câu hỏi nghiên cứu | Thành phần đánh giá | Chỉ số trả lời chính |
| :--- | :--- | :--- | :--- |
| **RQ1** | **Khả năng mở rộng (Scalability):** Khi kích thước lưới tăng từ `3×3` (9 biến chính) lên `4×4` (16 biến chính) và `5×5` (25 biến chính), kích thước CNF, số lần gọi SAT, chi phí DPLL và thời gian giải (`total_runtime_ms`) tăng ra sao? Hệ thống có giải trọn vẹn các màn `5×5` trong ngưỡng timeout 60s không? | Toàn hệ thống | `primary_vars`, `aux_vars_final`, `cnf_clauses_final`, `sat_calls_total`, `total_decisions`, `total_backtracks`, `solver_runtime_ms`, `total_runtime_ms`, `solved_rate` |
| **RQ2** | **Chiến lược mã hóa CNF theo kích thước vùng $\lvert R\rvert$ thực (Direct vs. Sinz):** Direct Combinatorial (không biến phụ đếm, $\binom{\lvert R\rvert}{k+1}$ mệnh đề cho `AT_MOST(k)` và $\binom{\lvert R\rvert}{\lvert R\rvert-k+1}$ cho `AT_LEAST(k)`, áp dụng khi $\lvert R\rvert \le 8$; vùng lớn hơn tự chuyển sang Sinz) so với Sequential Counter / Sinz ($O(\lvert R\rvert\cdot k)$ biến phụ & mệnh đề cho `AT_MOST(k)` và $O(\lvert R\rvert\cdot(\lvert R\rvert-k))$ cho `AT_LEAST(k)`) đánh đổi thế nào về kích thước công thức, `total_propagations` và thời gian giải? | `CNFEncoder` + `DPLLSolver` | `max_region_size`, `aux_vars_final`, `cnf_clauses_final`, `total_propagations`, `total_decisions`, `total_runtime_ms` |
| **RQ3** | **Tác động của tối ưu DPLL (Pure-Literal & Heuristics):** So với DPLL cơ bản (`lexicographic`, tắt Pure-Literal), việc bật Pure-Literal Elimination và/hoặc chuyển sang heuristic `MOMs` / `Jeroslow-Wang (JW)` cắt giảm được bao nhiêu `total_decisions`, `total_backtracks` và `total_runtime_ms`? | `DPLLSolver` | `total_decisions`, `total_propagations`, `total_backtracks`, `solver_runtime_ms`, `total_runtime_ms` |
| **RQ4** | **Hiệu quả của Model Caching ở Logic Agent:** Việc tái sử dụng các mô hình thỏa mãn $M$ thu được trong cùng bước $t$ giúp cắt giảm bao nhiêu phần trăm `sat_calls_total` và `total_runtime_ms` trong khi bảo toàn 100% chuỗi phán quyết? | `DeductiveLogicAgent` | `sat_calls_total`, `sat_calls_cached_skipped`, `total_runtime_ms`, `cross_config_consistency` |
| **RQ5** | **Độ tin cậy, tính tất định & ca biên:** Các cấu hình có cho kết quả hoàn toàn tất định (`deterministic_check = PASS`) và đồng nhất chuỗi phán quyết (`cross_config_consistency = PASS`) không? Khi gặp ca mơ hồ (`AMBIGUOUS`), mâu thuẫn (`INCONSISTENT`) hoặc kẹt giữa chừng (FAQ #13), Agent có dừng an toàn mà không đoán mò không? | `GameEngine` + `DeductiveLogicAgent` | `terminal_status`, `solved_cells`, `deterministic_check`, `cross_config_consistency`, `uniqueness_status` |

---

## 6.2. Bộ Dữ liệu, Kiểm định Nghiệm duy nhất và Thiết lập Thực nghiệm

### 6.2.1. Bộ dữ liệu 15 Puzzle và Kiểm định Nghiệm duy nhất (FAQ #2, #8, #9)

Tập dữ liệu (`Source/puzzles/`) gồm **10 màn chơi chuẩn** (4 màn `3×3`, 4 màn `4×4`, 2 màn `5×5`, vượt mức tối thiểu 6 màn của FAQ #2), **3 màn mở rộng** (`extensions/`: kiểm chứng vùng nâng cao `INTERSECTION`, `COMMON_NEIGHBORS`, `CORNERS`, `BOUNDARY`, `BETWEEN`, ràng buộc chẵn lẻ `PARITY` và `COMPARE_COUNTS`), và **2 màn kiểm thử biên** (`edge_cases/`: `edge_3x3_ambiguous`, `edge_3x3_inconsistent`). Toàn bộ 15 puzzle được kiểm định độc lập bằng `Source/experiments/uniqueness_report.py` với `CNFEncoder("direct")` và `DPLLSolver()`.

**Bảng 6.1: Đặc trưng bộ 15 puzzle và kết quả kiểm định nghiệm duy nhất (`uniqueness_report.csv`)**

| `puzzle_id` | Nhóm (`dataset_group`) | Kích thước ($N \times N$) | `primary_vars` ($N^2$) | Thẻ mở sẵn ở $KB_0$ (FAQ #8) | `max_region_size` ($\max \lvert R\rvert$) | `uniqueness_status` (FAQ #9) | Khớp đáp án ẩn (`matches_hidden_solution`) | Trạng thái kết thúc (`terminal_status`) |
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

### 6.2.2. Ma trận 8 Cấu hình Thực nghiệm (`C0`–`C7`)

Để cô lập tác động của từng cải tiến (ablation study) và đánh giá tổ hợp tối ưu, `Source/experiments/configs.py` định nghĩa 8 cấu hình cốt lõi (`C0`–`C7`):

**Bảng 6.2: Ma trận 8 cấu hình thực nghiệm cốt lõi (`C0`–`C7`)**

| `config_id` | Tên cấu hình | `encoding` | `heuristic` | `pure_literal` | `model_caching` | Mục đích & Câu hỏi nghiên cứu trả lời |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`C0`** | `baseline_direct` | `direct` | `lexicographic` | `False` | `False` | **Mốc chuẩn (Baseline):** DPLL 6 yêu cầu tối thiểu + Direct encoding (**RQ1–RQ4**). |
| **`C1`** | `direct_pl` | `direct` | `lexicographic` | `True` | `False` | Cô lập tác động của **Pure-Literal Elimination** so với `C0` (**RQ3**). |
| **`C2`** | `direct_pl_moms` | `direct` | `moms` | `True` | `False` | Cô lập tác động của heuristic **MOMs** trên nền Pure-Literal (**RQ3**). |
| **`C3`** | `direct_pl_jw` | `direct` | `jw` | `True` | `False` | So sánh heuristic **Jeroslow-Wang** với **MOMs** (`C2`) và `lexicographic` (`C1`) (**RQ3**). |
| **`C4`** | `direct_cache` | `direct` | `lexicographic` | `False` | `True` | Cô lập tác động thuần túy của **Model Caching** so với `C0` (**RQ4**). |
| **`C5`** | `baseline_sinz` | `sinz` | `lexicographic` | `False` | `False` | Cô lập tác động thuần túy của **Sinz Encoding** so với Direct (`C0`) (**RQ2**). |
| **`C6`** | `opt_direct` | `direct` | `moms`\* | `True` | `True` | Tổ hợp tối ưu đầy đủ trên **Direct** (**RQ1, RQ2, RQ4**). |
| **`C7`** | `opt_sinz` | `sinz` | `moms`\* | `True` | `True` | Tổ hợp tối ưu đầy đủ trên **Sinz**; so sánh công bằng với `C6` (**RQ1, RQ2**). |

> \* *Lý do chọn `--best-heur moms` cho `C6` và `C7`:* Trên 10 màn chuẩn, `C2` (`moms`) và `C3` (`jw`) đạt cùng tỷ lệ giải `10/10` và cùng số đo tìm kiếm (`total_decisions = 285`, `total_backtracks = 530`, `total_propagations = 19445`). Tổng `total_runtime_ms_median` là `166.261 ms` (`moms`) so với `168.359 ms` (`jw`), chênh `2.098 ms` (khoảng `1.25%`), nhỏ hơn tổng độ lệch chuẩn giữa 3 lần lặp (`9.264 ms` và `12.806 ms`), nên hai heuristic được xem là tương đương về tốc độ (theo từng kích thước: `3×3` `10.296` vs `10.193 ms`, `4×4` `46.073` vs `48.904 ms`, `5×5` `109.892` vs `109.262 ms`). Nhóm chọn `moms` vì cách tính điểm đơn giản hơn: chỉ đếm tần suất (số nguyên) trên các mệnh đề ngắn nhất thay vì cộng trọng số thực $2^{-\lvert C\rvert}$ trên toàn bộ mệnh đề chưa thỏa.

### 6.2.3. Giao thức Đo lường và Môi trường Thực nghiệm

Toàn bộ thí nghiệm được thực thi bằng lệnh:
```text
python Source/experiments/benchmark.py --include-extensions --repeats 3 --timeout-s 60 --best-heur moms
```
- **Cách ly tiến trình & ngưỡng timeout:** Mỗi lượt đo `(puzzle, config, repeat_idx)` chạy trong tiến trình `multiprocessing` (`spawn`) độc lập trên Windows với `timeout = 60 giây` (`60000 ms`), khởi tạo mới `GameEngine` và `DeductiveLogicAgent` (reset sạch cache), gọi `gc.collect()` trước khi bấm giờ bằng `time.perf_counter()`. Tổng cộng `15 puzzle × 8 cấu hình × 3 lần lặp = 360` lượt đo hoàn tất trong `87.53 giây` (`benchmark_raw.csv`, tổng hợp thành `120` dòng trong `benchmark_summary.csv`).
- **Quy ước chỉ số:** Tuân thủ *Project 2 Spec* (Mục 4.5) và FAQ #12–#13:
  - `sat_calls_total` chỉ đếm các truy vấn thực (`cached=False`) trong `DeductionStep.sat_queries` (`stats.validation_sat_calls == 0` nhờ `KBCache`); `sat_calls_cached_skipped` đếm truy vấn `cached=True`.
  - Chỉ số `reveal_waves` được bỏ qua (để trống trong CSV) theo **FAQ #12**; sử dụng `deduction_steps` làm đại diện độ sâu suy diễn.
  - Tự động kiểm chứng tính bất biến qua 3 lần lặp (`deterministic_check`) và tính đồng nhất chuỗi phán quyết giữa mọi cấu hình (`cross_config_consistency`). Báo cáo thời gian bằng **trung vị (`median`)** (ms).

**Bảng 6.3: Thông số môi trường phần cứng và phần mềm thực nghiệm (`env_info.json`; tên CPU và dung lượng RAM bổ sung từ thông tin hệ thống Windows)**

| Thành phần môi trường | Chi tiết |
| :--- | :--- |
| CPU | `11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz` (8 luồng logic, `Intel64 Family 6 Model 140 Stepping 1`) |
| Bộ nhớ RAM | `15.75 GB` |
| Hệ điều hành | `Windows-11-10.0.26300-SP0` |
| Phiên bản Python | `3.12.10` (`MSC v.1943 64 bit (AMD64)`) |
| Thời điểm thực thi & Commit | `2026-11-26T16:00:38+07:00` — Commit `df66ddb` (cây mã trùng khớp `origin/dev` sau PR #3 `9d2140b`) cộng thay đổi cấu hình `REAL_ENCODER_SPEC = "logic.cnf_encoder:CNFEncoder"` trong `Source/experiments/encoder_factory.py` (được commit sau đó tại `b28094f`) |

---

## 6.3. Kết quả Tổng hợp và Khả năng Mở rộng (RQ1)

Bảng 6.4 trình bày toàn bộ 6 nhóm chỉ số bắt buộc của cấu hình nhanh nhất **`C6` (`opt_direct`)** trên đủ 10 màn chuẩn và 3 màn mở rộng; Bảng 6.5 tóm tắt xu hướng tăng trưởng theo kích thước lưới.

**Bảng 6.4: Kết quả chi tiết trên 10 màn chuẩn và 3 màn mở rộng (cấu hình `C6` — `opt_direct`)**

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

*\*Ghi chú: `reveal_waves` bỏ qua theo FAQ #12. Ở các màn `extension` (dù `encoding=direct`), `aux_vars_final > 0` phát sinh từ biến phụ Tseitin của `PARITY`, bộ đếm đơn phân của `COMPARE_COUNTS`, và bộ đếm Sinz dự phòng cho ràng buộc đếm trên vùng $\lvert R\rvert > 8$ (ví dụ `EXACTLY 5` trên vùng `BOUNDARY` 12 ô của `ext_4x4_03`).*

**Bảng 6.5: Tóm tắt khả năng mở rộng theo kích thước lưới trên bộ 10 màn chuẩn (`C6` vs. `C0`)**

| Kích thước lưới (Số màn) | `cnf_clauses_final` TB | `sat_calls_total` TB (`C0` / `C6`) | `solver_runtime_ms_median` TB (`C0` / `C6`) | `total_runtime_ms_median` TB (`C0` / `C6`) | Tỷ trọng DPLL (`solver / total`) (`C0` / `C6`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `3×3` (4 màn, $k_0=2, T=7$) | `29.0` | `54.25` / `35.00` | `0.742` / `0.559` | `2.576` / `2.408` | `28.79%` / `23.24%` |
| `4×4` (4 màn, $k_0=3, T=13$) | `99.5` | `169.50` / `103.00` | `5.792` / `3.382` | `11.824` / `8.965` | `48.98%` / `37.73%` |
| `5×5` (2 màn, $k_0=5, T=20$) | `308.0` | `374.00` / `222.50` | `38.451` / `20.852` | `53.019` / `35.397` | `72.52%` / `58.91%` |

![Hình 6.1: Khả năng mở rộng theo kích thước lưới](../Source/experiments/results/charts/rq1_scalability.png)
*Hình 6.1 (`rq1_scalability.png`): Trung bình thời gian giải (trái) và số lần gọi SAT thực tế (phải) từ `3×3` đến `5×5` trên bộ 10 màn chuẩn.*

**Phân tích định lượng (RQ1):**
- **Quy mô công thức & truy vấn SAT:** Khi lưới tăng từ `3×3` ($T=7$) lên `4×4` ($T=13$) và `5×5` ($T=20$), trung bình `cnf_clauses_final` tăng từ **`29.0`** lên **`99.5`** (`3.43×`) và **`308.0`** (`10.62×` so với `3×3`). Ở `C6`, trung bình `sat_calls_total` tăng từ **`35.00`** lên **`103.00`** (`2.94×`) và **`222.50`** (`6.36×`). Với Model Caching, số lời gọi thực tế không vượt chặn trên $\frac{T^2+3T}{2}$ (`35`, `104`, `230` tương ứng $T = 7, 13, 20$) và chạm đúng chặn này ở `3x3_01`–`3x3_04`, `4x4_01`–`4x4_03` và `5x5_01`, phù hợp tăng trưởng $O(T^2)$ (Mục 5.6).
- **Chuyển dịch nút thắt hiệu năng:** Trên lưới nhỏ `3×3`, DPLL chỉ chiếm **`23.24%`** (`0.559 / 2.408 ms` ở `C6`), phần lớn thời gian nằm ở chi phí Python (`encode_kb`, giao tiếp `GameEngine`). Khi lên `4×4` và `5×5`, tỷ trọng lõi DPLL tăng lên **`37.73%`** và **`58.91%`** (`72.52%` ở `C0`; riêng `ext_4x4_03` có `504` mệnh đề, `182` biến phụ với `48.718 / 58.702 ms = 82.99%`), cho thấy thuật toán tìm kiếm SAT trở thành yếu tố chi phối ở các bài toán lớn.
- **Khả năng đáp ứng ngưỡng 60s trên `5×5`:** Toàn bộ **8/8 cấu hình** giải trọn vẹn `10/10` màn chuẩn và `3/3` màn mở rộng (`solved_rate = 100%`, **`0` ca `TIMEOUT`**). `120/120` dòng trong `benchmark_summary.csv` đạt **`deterministic_check = PASS`** và **`cross_config_consistency = PASS`**.

---

## 6.4. So sánh Chiến lược Mã hóa CNF: Direct vs. Sinz (RQ2)

**Bảng 6.6: So sánh Direct Combinatorial và Sequential Counter (Sinz) theo kích thước vùng $\lvert R\rvert$ thực**

| Màn chơi (`dataset_group`) | `max_region_size` ($\max \lvert R\rvert$) | Cặp cấu hình | `aux_vars_final` (Direct / Sinz) | `cnf_clauses_final` (Direct / Sinz) | `total_propagations` (Direct / Sinz) | `total_decisions` (Direct / Sinz) | `total_runtime_ms` median (Direct / Sinz) | Trạng thái |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `3x3_01` (`standard`) | 8 | `C0` vs `C5` | 0 / 12 | 28 / 43 | 285 / 658 | 2 / 7 | 2.381 / 5.197 | `SOLVED` |
| `3x3_02` (`standard`) | 3 | `C0` vs `C5` | 0 / 22 | 30 / 61 | 338 / 864 | 0 / 0 | 2.450 / 3.975 | `SOLVED` |
| `3x3_03` (`standard`) | 5 | `C0` vs `C5` | 0 / 20 | 32 / 58 | 297 / 791 | 0 / 0 | 3.055 / 3.867 | `SOLVED` |
| `3x3_04` (`standard`) | 3 | `C0` vs `C5` | 0 / 16 | 26 / 48 | 292 / 745 | 1 / 7 | 2.417 / 3.419 | `SOLVED` |
| `4x4_01` (`standard`) | 5 | `C0` vs `C5` | 0 / 40 | 69 / 124 | 1807 / 4909 | 0 / 0 | 9.255 / 16.505 | `SOLVED` |
| `4x4_02` (`standard`) | 8 | `C0` vs `C5` | 0 / 98 | 164 / 238 | 1568 / 4718 | 0 / 10 | 11.268 / 16.880 | `SOLVED` |
| `4x4_03` (`standard`) | 5 | `C0` vs `C5` | 0 / 89 | 88 / 213 | 1682 / 7067 | 0 / 0 | 13.168 / 25.623 | `SOLVED` |
| `4x4_04` (`standard`) | 5 | `C0` vs `C5` | 0 / 86 | 77 / 206 | 1811 / 8989 | 102 / 104 | 13.606 / 33.945 | `SOLVED` |
| `5x5_01` (`standard`) | 8 | `C0` vs `C5` | 0 / 223 | 262 / 517 | 5465 / 23185 | 118 / 147 | 35.537 / 84.843 | `SOLVED` |
| `5x5_02` (`standard`) | 8 | `C0` vs `C5` | 0 / 244 | 354 / 558 | 6094 / 36040 | 470 / 470 | 70.501 / 199.405 | `SOLVED` |
| `5x5_01` (`standard`) | 8 | `C6` vs `C7` | 0 / 223 | 262 / 517 | 3018 / 12334 | 0 / 27 | 24.479 / 52.556 | `SOLVED` |
| `5x5_02` (`standard`) | 8 | `C6` vs `C7` | 0 / 244 | 354 / 558 | 3129 / 16404 | 102 / 95 | 46.315 / 91.803 | `SOLVED` |
| `ext_3x3_01` (`extension`) | 5 | `C6` vs `C7` | 4 / 8 | 39 / 43 | 209 / 241 | 2 / 2 | 2.893 / 2.968 | `SOLVED` |
| `ext_4x4_02` (`extension`) | 12 | `C6` vs `C7` | 23 / 33 | 137 / 150 | 1204 / 1529 | 46 / 46 | 11.275 / 12.267 | `SOLVED` |
| `ext_4x4_03` (`extension`) | 12 | `C6` vs `C7` | 182 / 186 | 504 / 508 | 5846 / 6210 | 30 / 30 | 58.702 / 61.552 | `SOLVED` |

![Hình 6.2: So sánh Direct vs. Sinz trên 10 màn chuẩn](../Source/experiments/results/charts/rq2_direct_vs_sinz.png)
*Hình 6.2 (`rq2_direct_vs_sinz.png`): So sánh `aux_vars_final` (trái) và `cnf_clauses_final` (phải) giữa Direct (`C0`) và Sinz (`C5`) trên 10 màn chuẩn.*

**Phân tích định lượng (RQ2):**
- **Trên 10 màn chuẩn ($\max \lvert R\rvert \in \{3, 5, 8\}$), Direct vượt trội Sinz về cả kích thước lẫn tốc độ:**
  - *Biến phụ & mệnh đề:* Direct sinh `0` biến phụ và tổng `1130` mệnh đề tại $KB_T$ qua 10 màn (`26–354` mệnh đề/màn), trong khi Sinz phát sinh **`850`** biến phụ (`12–244`) và **`2066`** mệnh đề (`43–558`, gấp **`1.83×`**). Nguyên nhân là với vùng nhỏ/vừa (`ROW`/`COL` $\le 5$, `NEIGHBORS` $\le 8$), hệ số đa thức $O(\lvert R\rvert\cdot k)$ của bộ đếm tuần tự Sinz sinh lượng biến phụ và mệnh đề bắc cầu lớn hơn tổ hợp trực tiếp (đặc biệt khi Sinz quy `AT_LEAST(k)` về `AT_MOST(|R|−k)` trên literal phủ định).
  - *Lan truyền đơn vị & thời gian giải:* Các biến phụ Sinz làm tổng `total_propagations` tăng **`4.48×`** ở DPLL cơ bản (`19639` ở `C0` lên `87966` ở `C5`) và **`4.10×`** ở cấu hình tối ưu (`10800` ở `C6` lên `44260` ở `C7`). Hệ quả là tổng `total_runtime_ms_median` của `C5` (`393.659 ms`) chậm hơn `C0` (`163.638 ms`) **`2.41×`**, còn `C7` (`226.451 ms`) chậm hơn `C6` (`116.285 ms`) **`1.95×`**.
- **Trường hợp vùng lớn $\lvert R\rvert = 12$ (`extensions/`) và chiến lược lai của chế độ `direct`:** `CNFEncoder` (`Source/logic/cnf_encoder.py`, hằng `_DIRECT_CARDINALITY_THRESHOLD = 8`) chỉ dùng tổ hợp trực tiếp khi $\lvert R\rvert \le 8$; với ràng buộc đếm trên vùng $\lvert R\rvert > 8$, chế độ `direct` tự chuyển sang bộ đếm tuần tự Sinz để tránh bùng nổ $\binom{\lvert R\rvert}{k+1}$ mệnh đề. Trong `ext_4x4_02`, `max_region_size = 12` thuộc clue `PARITY` (Tseitin XOR giống nhau ở cả hai chế độ). Trong `ext_4x4_03`, clue `EXACTLY 5` trên vùng `BOUNDARY` ($\lvert R\rvert = 12$) vì thế được mã hóa bằng Sinz ở **cả** `C6` lẫn `C7`, nên số mệnh đề (`504` vs `508`), biến phụ (`182` vs `186`) và thời gian (`58.702` vs `61.552 ms`) gần như trùng nhau. Đây là hệ quả của chiến lược lai, **không phải** điểm giao cắt giữa hai phương pháp; bộ dữ liệu hiện tại chưa có màn nào cho thấy Sinz thuần nhanh hơn Direct, và đánh giá trên các vùng đếm lớn hơn là hướng thực nghiệm tiếp theo.

---

## 6.5. Đánh giá Tối ưu DPLL và Model Caching (RQ3 – RQ4)

Vì cả 8 cấu hình đều giải trọn vẹn `10/10` màn chuẩn (`0 TIMEOUT`), tập giao $S_{\text{common}}$ bao gồm đủ **10/10 màn chuẩn** (`|S_common| = 10`).

**Bảng 6.7: So sánh hiệu năng các cấu hình `C0`–`C7` trên tập giao $S_{\text{common}}$ (`10/10` màn chuẩn)**

| Cấu hình | Encoding | Heuristic | Pure-Literal | Model Caching | `solved_rate` | `TIMEOUT` | Tổng `sat_calls_total` | Tổng `total_decisions` | Tổng `total_backtracks` | Tổng `total_runtime_ms_median` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C0` (Baseline) | `direct` | `lexicographic` | Tắt | Tắt | `100%` (10/10) | 0 | 1643 | 693 | 530 | 163.638 |
| `C1` (+PL) | `direct` | `lexicographic` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 516 | 530 | 197.395 |
| `C2` (+PL+MOMs) | `direct` | `moms` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 285 | 530 | 166.261 |
| `C3` (+PL+JW) | `direct` | `jw` | Bật | Tắt | `100%` (10/10) | 0 | 1643 | 285 | 530 | 168.359 |
| `C4` (+Caching) | `direct` | `lexicographic` | Tắt | Bật | `100%` (10/10) | 0 | 987 | 282 | 527 | 124.663 |
| `C5` (Sinz Base) | `sinz` | `lexicographic` | Tắt | Tắt | `100%` (10/10) | 0 | 1643 | 745 | 530 | 393.659 |
| `C6` (Opt Direct) | `direct` | `moms` | Bật | Bật | `100%` (10/10) | 0 | 997 | 122 | 528 | 116.285 |
| `C7` (Opt Sinz) | `sinz` | `moms` | Bật | Bật | `100%` (10/10) | 0 | 997 | 157 | 527 | 226.451 |

*Ghi chú: Trên 3 màn `extensions/`, tất cả cấu hình cũng đạt `3/3 SOLVED`: `sat_calls_total` giảm từ `401` (`C0`–`C3`, `C5`) xuống `229` (`C4`, `C6`, `C7`, bỏ qua `172` truy vấn = `-42.89%`); `total_decisions` giảm từ `272` (`C0`) xuống `162` (`C2`), `147` (`C3`), và `78` (`C6`/`C7`); `total_runtime_ms_median` giảm từ `137.658 ms` (`C0`) xuống `72.870 ms` (`C6`, `-47.06%`).*

![Hình 6.3: Tác động của Pure-Literal & Heuristic lên tìm kiếm DPLL](../Source/experiments/results/charts/rq3_heuristics.png)
*Hình 6.3 (`rq3_heuristics.png`): Tổng `total_decisions` (trái) và `total_backtracks` (phải) giữa `C0`, `C1`, `C2`, `C3` trên 10 màn chuẩn.*

![Hình 6.4: Hiệu quả cắt giảm số lần gọi SAT nhờ Model Caching](../Source/experiments/results/charts/rq4_model_caching.png)
*Hình 6.4 (`rq4_model_caching.png`): Số lời gọi SAT thực tế (`sat_calls_total`) giữa `C0` (không cache) và `C4` (có Model Caching) trên từng màn chuẩn.*

**Phân tích định lượng (RQ3 & RQ4):**
- **Tác động của Pure-Literal (`C1` vs. `C0` — RQ3):** Bật Pure-Literal giảm `total_decisions` từ `693` xuống `516` (**`-25.54%`**), giữ nguyên `total_backtracks = 530` (do các truy vấn phản chứng `UNSAT` vẫn phải vét hết không gian mâu thuẫn). Tuy nhiên, chi phí quét literal thuần ở mỗi nút đệ quy làm `solver_runtime_ms` tăng từ `103.033` lên `128.916 ms` (tổng `total_runtime_ms_median` tăng từ `163.638` lên `197.395 ms`, chậm hơn `20.63%`) khi dùng chung với `lexicographic`.
- **Tác động của Heuristic chọn biến (`C2`, `C3` vs. `C1` — RQ3):** Kết hợp `moms` (`C2`) hoặc `jw` (`C3`) cắt tiếp `total_decisions` từ `516` xuống còn **`285`** (`-44.77%` so với `C1`, **`-58.87%`** so với `C0`), đưa `total_runtime_ms_median` về `166.261 ms` (`C2`) và `168.359 ms` (`C3`). Trên lưới `3×3`, `C1`, `C2` và `C3` đều đạt `total_decisions = 0` (giải hoàn toàn bằng Unit Propagation + Pure-Literal), nên ở lưới nhỏ heuristic chọn biến gần như không được kích hoạt và khác biệt giữa các heuristic chỉ thể hiện ở `4×4`–`5×5`. Giữa hai heuristic, chênh lệch thời gian chỉ `2.098 ms` (khoảng `1.25%`; `166.261` vs `168.359 ms`), nằm trong biên nhiễu đo nên được xem là tương đương.
- **Tác động của Model Caching (`C4` vs. `C0` và `C6` vs. `C2` — RQ4):**
  - `C4` vs. `C0`: bỏ qua **`656`** truy vấn SAT (`1643` → **`987`**, giảm **`39.93%`**), giảm `total_decisions` từ `693` xuống `282` (`-59.31%`), giảm `total_propagations` từ `19639` xuống `10723` (`-45.40%`), và rút ngắn `total_runtime_ms_median` từ `163.638` xuống **`124.663 ms`** (nhanh hơn **`23.82%`**).
  - `C6` vs. `C2`: trên nền DPLL đã tối ưu, Model Caching tiếp tục bỏ qua **`646`** truy vấn (`1643` → **`997`**, giảm **`39.32%`**) và rút ngắn `total_runtime_ms_median` từ `166.261` xuống **`116.285 ms`** (nhanh hơn **`30.06%`**), giúp `C6` trở thành cấu hình nhanh nhất toàn bảng (nhanh hơn `C0` **`28.94%`** với `total_decisions = 122`, giảm `82.40%`), đồng thời giữ `cross_config_consistency = PASS` 100%.

---

## 6.6. Ca biên, Ca thất bại và Timeout (RQ5)

Tuân thủ nguyên tắc báo cáo trung thực mọi trường hợp không đạt `SOLVED` (*Project 2 Spec* Mục 4.5, FAQ #13), Bảng 6.8 tổng hợp đầy đủ các ca biên qua tất cả 8 cấu hình.

**Bảng 6.8: Kết quả trên 2 ca biên (`edge_cases/`) qua các cấu hình `C0`–`C7`**

| Màn chơi | Cấu hình | `terminal_status` | `solved_cells` / `total_cells` | `deduction_steps` | `sat_calls_total` (`cached_skipped`) | Thời gian tới lúc dừng (`ms`, `median`) | Hành vi No-Guess quan sát được |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `edge_3x3_ambiguous` | `C0`–`C3` | `AMBIGUOUS` | `5 / 9` | `3` | `47` (`0`) | `1.875–2.092` | Suy diễn đúng 3 bước đầu (`5/9` ô mở); tại `step = 3`, 4 ô `['A2', 'B2', 'A3', 'B3']` đều có cả $KB_3 \wedge \neg C_i$ và $KB_3 \wedge C_i$ là `SAT`. Agent log `WARNING` và dừng với `NOT_PROVABLE`, không đoán mò. |
| `edge_3x3_ambiguous` | `C4`, `C6` | `AMBIGUOUS` | `5 / 9` | `3` | `20` (`27`) | `1.422` (`C4`) / `1.518` (`C6`) | Cùng điểm dừng `step = 3` (`5/9` ô); Model Caching bỏ qua `27/47` (`57.45%`) truy vấn ngay cả khi dừng ở trạng thái mơ hồ. |
| `edge_3x3_ambiguous` | `C5` / `C7` | `AMBIGUOUS` | `5 / 9` | `3` | `47` (`0`) / `20` (`27`) | `3.625` (`C5`) / `2.107` (`C7`) | Hội tụ cùng chuỗi phán quyết và điểm dừng `step = 3` (`cross_config_consistency = PASS`). |
| `edge_3x3_inconsistent` | `C0`–`C7` | `INCONSISTENT` | `2 / 9` | `0` | `1` (`0`) | `0.228–0.302` | Kiểm tra nhất quán ban đầu `DPLL(KB_0)` trả `UNSAT` sau đúng `1` lời gọi SAT. Agent dừng tức thì với `VerdictCode.INCONSISTENT`. |

**Phân tích định lượng (RQ5):**
- **Không đoán mò (`AMBIGUOUS`) & phát hiện mâu thuẫn (`INCONSISTENT`):** Mọi cấu hình đều hội tụ chính xác tại `step = 3` trên `edge_3x3_ambiguous` (giữ nguyên 4 ô chưa ép buộc ở trạng thái úp) và dừng tức thì tại `step = 0` sau `1` lời gọi SAT trên `edge_3x3_inconsistent` (ngăn ngừa *ex falso quodlibet*).
- **Ghi nhận trung thực `TIMEOUT`:** Không ghi nhận ca `TIMEOUT` hay `ERROR` nào (`0/360` lượt chạy) trong ngưỡng `60000 ms`. Thời gian **trung vị (`median`)** dài nhất trên `120` cặp cấu hình–màn chơi là **`199.405 ms`** (`5x5_02` ở `C5`), và lượt chạy **đơn lẻ (`raw`)** chậm nhất trong toàn bộ `360` lượt đo là **`260.404 ms`** (`5x5_02`, `C5`, `repeat_idx = 1`). Cột `error_message` trong `benchmark_raw.csv` chỉ có giá trị ở `48` lượt chạy của 2 ca biên (`2 màn × 8 cấu hình × 3 lần`), là thông báo dừng mang tính thông tin (`Stopped at step 3 with no forced cell`, `KB_t UNSAT at step 0`), không phải lỗi thực thi.

---

## 6.7. Hạn chế của Hệ thống và Hướng Cải thiện

1. **Giới hạn của thuật toán DPLL thuần Python:** So với các bộ giải SAT hiện đại (CDCL với *Conflict-Driven Clause Learning*, *Two-Watched Literals*, *restarts*), DPLL cổ điển vẫn có thể khám phá lặp lại các nhánh xung đột tương đương khi kích thước vượt `5×5` hoặc khi công thức chứa nhiều biến phụ (bộ đếm Sinz cho vùng lớn, `COMPARE_COUNTS`); thể hiện ở `ext_4x4_03` (`EXACTLY 5` trên 12 ô, 3 clue `COMPARE_COUNTS` và 7 clue `PARITY`, tổng `182` biến phụ) tốn `48.718 ms` trong solver, trong khi `ext_4x4_02` dù có 11 clue `PARITY` chỉ tốn `5.219 ms`.
2. **Tái mã hóa và giải độc lập theo từng bước:** Mỗi bước $t$, hệ thống biên dịch lại `encode_kb(PublicState_t)` từ đầu; điều này giải thích vì sao chi phí ngoài solver chiếm `~77%` ở lưới `3×3`. Mã hóa gia tăng (incremental CNF) và tái sử dụng trạng thái nội bộ giữa các truy vấn `assumptions` là hướng tối ưu trực tiếp.
3. **Kích thước tập mẫu thực nghiệm:** Bộ dữ liệu 15 puzzle đủ bao phủ `3×3`–`5×5`, các mẫu Extension và ca biên, nhưng mang tính đánh giá điển hình hơn là thống kê diện rộng trên hàng trăm bản đồ sinh ngẫu nhiên.
4. **Giải thích tối giản ở `Hint`:** `HintEngine` hiện dùng duyệt liên kết vùng (Scope-Based BFS) với chi phí thấp và `0` lời gọi SAT bổ sung; phiên bản sau có thể bổ sung rút gọn theo *Deletion-Based MUS* để chỉ ra tập manh mối tối giản nhất.

---

## Phụ lục LLM (AI Appendix — Phần TV4)

**Phạm vi & nguyên tắc sử dụng:** Công cụ AI đã sử dụng: Claude Code (Anthropic) và Antigravity (Google, mô hình Gemini). Sinh viên trực tiếp phân tích đặc tả bài toán, chốt thiết kế và hợp đồng (`ILogicAgent`, `KBCache`, quy tắc *No-Guess*, ma trận thực nghiệm `C0–C7`), rà soát và hiệu chỉnh toàn bộ mã nguồn do AI gợi ý, trực tiếp chạy kiểm thử tự động (`209/209` test pass trên `pytest`) và đối soát 1-1 số liệu CSV cùng các biểu đồ.

| STT | Hạng mục TV4 | Vai trò của AI | Nội dung prompt tiêu biểu (tóm tắt) | Phần sinh viên thiết kế & kiểm chứng |
| :---: | :--- | :--- | :--- | :--- |
| 1 | Thiết kế giao thức & trường hợp biên (`ILogicAgent`, `KBCache`) | Tham khảo phương án thiết kế & phản biện trường hợp biên | *“Từ hợp đồng `core/contracts/`, đề xuất quy ước kết thúc `AMBIGUOUS`/`INCONSISTENT`, bộ đệm khóa KB tránh đếm gấp đôi khi `submit_verdict` gọi lại agent, và callback `on_step` hỗ trợ animation.”* | Chốt quy ước `AutoSolveOutcome`, thiết kế `KBCache` (LRU, mặc định 8 trạng thái), kiểm chứng `validation_sat_calls == 0` và định nghĩa luồng callback `on_step` trong `docs/tv4_agent_conventions.md`. |
| 2 | Thuật toán lõi `Source/agent/` (`Entailment`, `Model Caching`, `Hint`, `Uniqueness`) | Tham khảo thiết kế & hỗ trợ sinh khung cài đặt (được sinh viên rà soát, hiệu chỉnh và kiểm thử) | *“Hỗ trợ khung cài đặt `entailment.py` (Model Caching bật/tắt được), `logic_agent.py` (vòng lặp không đoán mò row-major), `hint_engine.py` (Scope-Based BFS), `uniqueness.py` (blocking clause chỉ trên biến chính) kèm unit test `tests/test_agent/`.”* | Kiểm duyệt logic phản chứng $KB_t \wedge \neg C_i$ / $KB_t \wedge C_i$, bảo đảm blocking clause loại trừ biến phụ Sinz/Tseitin, viết/duyệt ca test `AMBIGUOUS` và `INCONSISTENT`. |
| 3 | Khung thực nghiệm & biểu đồ (`Source/experiments/`) | Hỗ trợ sinh khung script benchmark, timeout đa tiến trình và vẽ biểu đồ | *“Hỗ trợ khung `experiments/configs.py`, `encoder_factory.py`, `solver_factory.py`, `benchmark.py` (`C0–C7`, timeout `multiprocessing` trên Windows, `deterministic_check`, `cross_config_consistency`), `uniqueness_report.py` và `plots.py`.”* | Tự thiết kế ma trận `C0–C7`, kiểm tra tính công bằng của các cấu hình, xác minh cơ chế đo `perf_counter()` và chạy test toàn bộ module `tests/test_experiments/`. |
| 4 | Tích hợp GĐ 3B, đối soát số liệu & biên tập tài liệu TV4 | Hỗ trợ tự động hóa đối chiếu chéo CSV và chuẩn hóa trình bày báo cáo | *“Tích hợp `CNFEncoder` (`direct` + `sinz`) với `DPLLSolver`, chạy `uniqueness_report.py` trên 15 puzzle, chạy `benchmark.py --include-extensions --repeats 3 --timeout-s 60 --best-heur moms`, sinh 4 PNG và đối soát 1-1 bảng báo cáo với CSV gốc.”* | Trực tiếp kiểm tra đầu ra thực nghiệm (`0` stub, `0` timeout, `120/120 PASS`), chốt chọn `--best-heur moms`, tự kiểm chứng nội dung RQ1–RQ5 và rà soát 2 tệp báo cáo TV4. |
| 5 | Rà soát độc lập báo cáo TV4 trước khi chốt PR #5 | Đối chiếu chéo số liệu, mã nguồn và chỉ ra điểm nghi vấn | *“Recheck chỉ-đọc 2 báo cáo TV4: đối chiếu 1-1 số liệu với CSV, thuật toán với `Source/agent/`, kiểm tra LaTeX và Phụ lục LLM.”* | Tự xác minh lại từng điểm AI nêu trên CSV và mã nguồn trước khi sửa; sửa 2 nhận định sai trong bản nháp (khẳng định `moms` nhanh hơn `jw` ở mọi kích thước; diễn giải "giao cắt tại $\lvert R\rvert = 12$" trong khi chế độ `direct` tự dùng Sinz khi $\lvert R\rvert > 8$). |
