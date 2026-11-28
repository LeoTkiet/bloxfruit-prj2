# Mục 5: Thuật toán Tác tử Suy diễn (Logic Agent — Phần TV4)

> **Tác giả:** Nguyễn Trương Bảo Nguyên — Thành viên 4 (TV4: `Source/agent/`, `Source/experiments/`)  
> **Phạm vi trong `Report.pdf`:** Nối tiếp phần Đặt bài toán (Mục 2), Mã hóa CNF (Mục 3) và DPLL SAT Solver (Mục 4); trình bày các thuật toán cốt lõi của `DeductiveLogicAgent`: Kiểm tra hệ quả logic (Entailment), tối ưu Model Caching & `KBCache`, Vòng lặp suy diễn không đoán mò (No-Guess Deduction Loop), Chức năng Gợi ý (`Hint`), Kiểm tra tính duy nhất của nghiệm (`Uniqueness Check`), và Phân tích độ phức tạp.

---

## 5.1. Ký hiệu và Cơ sở tri thức công khai $KB_t$

Nhắc lại các ký hiệu từ Mục 2 và Mục 3 trên lưới vuông $N \times N$ ($N \in \{3, 4, 5\}$, $n = N^2$ nhân vật, chỉ số theo thứ tự tất định row-major `A1, B1, ..., EN`):
- Mỗi nhân vật $i \in \{1, \dots, n\}$ gắn đúng một **biến mệnh đề chính** $C_i \in \{\text{True}, \text{False}\}$ (`True` tương ứng `CRIMINAL`, `False` tương ứng `INNOCENT`). Trường hợp đổi cặp nhãn hiển thị (FAQ #15) không làm thay đổi biểu diễn nhị phân hay thuật toán suy diễn.
- Các **biến phụ** $V_{\text{aux}}$ sinh từ bộ mã hóa CNF (Sequential Counter/Sinz, Tseitin XOR cho `PARITY`, bộ đếm cho `COMPARE_COUNTS`) được cấp phát tách biệt hoàn toàn khỏi tập biến chính $\{C_1, \dots, C_n\}$. Lưu ý: ở chế độ `direct`, ràng buộc đếm trên vùng $\lvert R\rvert > 8$ cũng được mã hóa bằng bộ đếm Sinz (`_DIRECT_CARDINALITY_THRESHOLD = 8` trong `Source/logic/cnf_encoder.py`), nên vẫn có thể phát sinh biến phụ.

Tại mỗi bước suy diễn $t \ge 0$, `DeductiveLogicAgent` chỉ tiếp cận **trạng thái công khai** `PublicState_t` (tuyệt đối cách ly khỏi nhãn ẩn và manh mối đang úp trong `GameEngine`, theo *Project 2 Spec* Mục 4.1–4.2). Cơ sở tri thức công khai $KB_t$ được biên dịch tự động sang dạng chuẩn hội (CNF):

$$KB_t = \text{CNF}\!\left(\mathcal{R}_t\right) \;\wedge\; \bigwedge_{(i,\, s_i) \in \mathcal{V}_t} \text{Unit}(C_i, s_i)$$

trong đó $\mathcal{R}_t$ là tập các **manh mối đã lật ngửa** tính đến bước $t$ (mọi manh mối đã lật luôn đúng bất kể chủ nhân là `CRIMINAL` hay `INNOCENT`), còn $\mathcal{V}_t$ là tập các **phán quyết đã chứng minh** (gồm $k_0 \ge 1$ thẻ mở sẵn ban đầu ở $KB_0$ theo FAQ #8 và các nhân vật đã suy ra ở các bước $0, \dots, t-1$), với $\text{Unit}(C_i, \text{CRIMINAL}) = (C_i)$ và $\text{Unit}(C_i, \text{INNOCENT}) = (\neg C_i)$. Khi lật thêm một thẻ hợp lệ ở bước $t$, $KB_t$ mở rộng đơn điệu và tập mô hình thỏa mãn thu hẹp dần: $\text{Mod}(KB_{t+1}) \subseteq \text{Mod}(KB_t)$.

---

## 5.2. Kiểm tra Hệ quả Logic (Entailment), Model Caching và `KBCache`

### 5.2.1. Phân biệt Mô hình thỏa mãn và Hệ quả logic

Điểm cốt lõi của quy tắc không đoán mò (**No-Guess Rule**, *Project 2 Spec* Mục 3.4) là phân biệt rõ giữa **một mô hình thỏa mãn (satisfying model)** và **hệ quả logic (logical entailment)**:
- Một mô hình $M \models KB_t$ chỉ là một phương án gán *có thể xảy ra*, không đủ cơ sở để kết luận chắc chắn trạng thái của nhân vật.
- Một phán quyết cho nhân vật chưa giải $i$ chỉ hợp lệ khi nó đúng trong **mọi** mô hình thỏa mãn của $KB_t$: $KB_t \models C_i$ (bắt buộc `CRIMINAL`) hoặc $KB_t \models \neg C_i$ (bắt buộc `INNOCENT`).

### 5.2.2. Quy trình kiểm tra bằng phản chứng (Entailment via Refutation)

Tại bước $t$, với cơ sở tri thức $KB_t$ và một nhân vật chưa giải $i$, `entailment.py` kiểm tra theo 4 bước:
1. **Kiểm tra tính nhất quán của $KB_t$:** Gọi bộ giải SAT cho $KB_t$. Nếu $KB_t$ là `UNSAT` $\Rightarrow$ trả về **`INCONSISTENT`** (cơ sở tri thức tự mâu thuẫn).
2. **Kiểm tra giả thiết phủ định `CRIMINAL`:** Gọi bộ giải SAT cho $KB_t \wedge \neg C_i$. Nếu `UNSAT` $\Rightarrow$ trả về **`CRIMINAL`** (kết thúc sớm cho nhân vật $i$, không cần truy vấn thứ hai).
3. **Kiểm tra giả thiết phủ định `INNOCENT`:** Nếu $KB_t \wedge \neg C_i$ là `SAT`, gọi tiếp bộ giải SAT cho $KB_t \wedge C_i$. Nếu `UNSAT` $\Rightarrow$ trả về **`INNOCENT`**.
4. **Cả hai nhánh đều thỏa mãn:** Nếu cả $KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$ đều `SAT` $\Rightarrow$ trả về **`UNKNOWN`** (chưa bị ép buộc, tuyệt đối không đoán).

### 5.2.3. Chứng minh tính đúng đắn (Refutation Proof)

- **Định lý:** Với mọi công thức mệnh đề $KB_t$ và mục tiêu $\alpha$:
  $$KB_t \models \alpha \iff (KB_t \wedge \neg \alpha) \text{ là UNSAT}.$$
- **Chứng minh:** Theo định nghĩa ngữ nghĩa, $KB_t \models \alpha$ khi và chỉ khi với mọi phép gán chân trị $M$, hễ $M \models KB_t$ thì $M \models \alpha$. Mệnh đề phổ quát này tương đương việc **không tồn tại** phép gán $M$ nào thỏa mãn đồng thời $M \models KB_t$ và $M \not\models \alpha$, tức không tồn tại $M \models (KB_t \wedge \neg \alpha)$, nghĩa là $KB_t \wedge \neg \alpha$ là `UNSAT`.
- **Áp dụng & vai trò bước kiểm tra nhất quán đầu tiên:**
  - Đặt $\alpha = C_i$: $KB_t \models C_i \iff (KB_t \wedge \neg C_i)\text{ là UNSAT} \implies$ `CRIMINAL`.
  - Đặt $\alpha = \neg C_i$: $KB_t \models \neg C_i \iff (KB_t \wedge C_i)\text{ là UNSAT} \implies$ `INNOCENT`.
  - Nếu cả hai đều `SAT`, tồn tại mô hình $M_1 \models KB_t$ với $M_1(C_i) = \text{False}$ và $M_2 \models KB_t$ với $M_2(C_i) = \text{True}$, suy ra `UNKNOWN`.
  - Bắt buộc kiểm tra $KB_t$ `SAT` trước: nếu $KB_t$ vốn đã `UNSAT` thì theo nguyên lý bùng nổ (*ex falso quodlibet*), mọi $KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$ đều `UNSAT`. Bỏ qua bước 1 sẽ gán nhầm nhãn `CRIMINAL` thay vì phát hiện `INCONSISTENT`.

> **Ví dụ minh họa (*Project 2 Spec* Mục 3.4):** Với $KB = (C_A \vee C_B) \wedge (\neg C_A \vee C_B)$, phép gán $(C_A = \text{False}, C_B = \text{True})$ thỏa mãn $KB$ nên $KB$ nhất quán (`SAT`). Thử $\neg C_B$ cho $KB \wedge \neg C_B \equiv C_A \wedge \neg C_A$ (`UNSAT`), suy ra $KB \models C_B$ ($B$ là `CRIMINAL`). Ngược lại, cả $KB \wedge C_A$ và $KB \wedge \neg C_A$ đều `SAT`, nên $A$ có trạng thái `UNKNOWN`.

### 5.2.4. Tối ưu Model Caching và lập luận tính đúng đắn tuyệt đối

Khi phân loại đồng loạt toàn bộ nhân vật chưa giải $U_t$ ở cùng một bước $t$, cách làm ngây thơ gọi bộ giải SAT lặp lại trên cùng $KB_t$. **Model Caching** khai thác mọi mô hình thỏa mãn $M$ thu được trong bước $t$ để bỏ qua các truy vấn dư thừa:
- Duy trì hai bảng cờ cho mỗi $j \in U_t$: `can_be_criminal[j]` (đã gặp mô hình có $C_j = \text{True}$) và `can_be_innocent[j]` (đã gặp mô hình có $C_j = \text{False}$), khởi tạo `False`.
- Mỗi khi lời gọi $\text{SAT}(KB_t)$ hoặc $\text{SAT}(KB_t \wedge \ell)$ trả về `SAT` kèm mô hình đầy đủ $M$, cập nhật cho mọi $j \in U_t$: gán `can_be_criminal[j] <- True` nếu $M(C_j)=\text{True}$, ngược lại `can_be_innocent[j] <- True`.
- Khi xét $i \in U_t$: chỉ gọi $\text{SAT}(KB_t \wedge \neg C_i)$ nếu `can_be_innocent[i]` đang là `False`, và chỉ gọi $\text{SAT}(KB_t \wedge C_i)$ nếu `can_be_criminal[i]` đang là `False`.

**Vì sao Model Caching bảo toàn tính đúng đắn tuyệt đối (Soundness & Completeness):**
1. *Không bỏ sót chứng nhân SAT:* Mọi mô hình $M$ trả về bởi $\text{SAT}(KB_t)$ hoặc $\text{SAT}(KB_t \wedge \ell)$ đều thỏa mãn toàn bộ mệnh đề của $KB_t$ (kể cả mệnh đề chứa biến phụ). Nếu $M(C_j)=\text{False}$, chính $M$ là chứng nhân chứng minh $M \models (KB_t \wedge \neg C_j)$, nên $KB_t \wedge \neg C_j$ chắc chắn `SAT`; bỏ qua truy vấn này cho kết quả giống hệt khi gọi thật. Tương tự khi $M(C_j)=\text{True}$.
2. *Không bỏ lỡ ô bị ép buộc (`UNSAT`):* Nếu $KB_t \models C_i$, mọi mô hình của $KB_t$ đều có $M(C_i)=\text{True}$, nên `can_be_innocent[i]` không bao giờ thành `True`; truy vấn $\text{SAT}(KB_t \wedge \neg C_i)$ chắc chắn vẫn được gọi và trả về `UNSAT`.
3. *Hủy cache khi chuyển bước & tính đơn điệu:* Cache chứng nhân chỉ hợp lệ trong phạm vi đúng $KB_t$; khi lật thẻ chuyển sang $KB_{t+1}$, **toàn bộ cache chứng nhân phải được tạo mới** vì $\text{Mod}(KB_{t+1}) \subseteq \text{Mod}(KB_t)$. Ngược lại, mọi kết luận ép buộc đã chứng minh ở bước $t$ vẫn đúng ở bước $t+1$ nhờ tính đơn điệu của logic mệnh đề.

### 5.2.5. Mã giả Entailment Check (có Model Caching)

```text
ALGORITHM ClassifyAllWithModelCaching(KB_t, unresolved_cells, var_map):
    // Bước 1: Kiểm tra tính nhất quán của KB_t
    base_res <- SAT_SOLVE(KB_t, assumptions = [])
    record_query(queries_log, target = NONE, assumption = [], result = base_res)

    IF NOT base_res.is_sat THEN
        RETURN (status = INCONSISTENT, classifications = EMPTY, queries = queries_log)

    // Khởi tạo cache chứng nhân từ mô hình cơ sở M_0
    FOR each cell IN unresolved_cells DO
        can_be_criminal[cell] <- FALSE
        can_be_innocent[cell] <- FALSE
    UPDATE_CACHE(base_res.model, unresolved_cells, var_map, can_be_criminal, can_be_innocent)

    // Bước 2: Phân loại từng nhân vật chưa giải theo thứ tự tất định
    classifications <- EMPTY_MAP
    FOR each cell IN unresolved_cells DO
        v <- var_map[cell]

        // Kiểm tra KB_t ∧ ¬C_v (chỉ gọi nếu chưa có mô hình nào gán C_v = False)
        IF NOT can_be_innocent[cell] THEN
            res_neg <- SAT_SOLVE(KB_t, assumptions = [-v])
            record_query(queries_log, target = cell, assumption = [-v], result = res_neg)
            IF NOT res_neg.is_sat THEN
                classifications[cell] <- CRIMINAL
                CONTINUE
            ELSE
                UPDATE_CACHE(res_neg.model, unresolved_cells, var_map, can_be_criminal, can_be_innocent)

        // Kiểm tra KB_t ∧ C_v (chỉ gọi nếu chưa có mô hình nào gán C_v = True)
        IF NOT can_be_criminal[cell] THEN
            res_pos <- SAT_SOLVE(KB_t, assumptions = [+v])
            record_query(queries_log, target = cell, assumption = [+v], result = res_pos)
            IF NOT res_pos.is_sat THEN
                classifications[cell] <- INNOCENT
                CONTINUE
            ELSE
                UPDATE_CACHE(res_pos.model, unresolved_cells, var_map, can_be_criminal, can_be_innocent)

        // Cả hai nhánh đều tồn tại mô hình thỏa mãn -> không đoán mò
        classifications[cell] <- UNKNOWN

    RETURN (status = CONSISTENT, classifications = classifications, queries = queries_log)

PROCEDURE UPDATE_CACHE(model, unresolved_cells, var_map, can_be_criminal, can_be_innocent):
    FOR each cell IN unresolved_cells DO
        v <- var_map[cell]
        IF model[v] == TRUE THEN
            can_be_criminal[cell] <- TRUE
        ELSE
            can_be_innocent[cell] <- TRUE
```

### 5.2.6. Bộ nhớ đệm theo khóa KB (`KBCache`) và tách bộ đếm SAT

Trong vòng lặp tự động giải, sau khi `DeductiveLogicAgent` chứng minh ô ép buộc trên `PublicState_t`, phương thức `GameEngine.submit_verdict(cell, verdict)` gọi ngược lại `agent.check_consistency(current_public)` và `agent.classify_character(current_public, cell)` để thẩm định độc lập phán quyết. Để tránh chạy lại DPLL gây đếm gấp đôi mà vẫn giữ nguyên ranh giới độc lập của `GameEngine`:
1. **Khóa KB bất biến (`make_kb_key`):** Ánh xạ `PublicState` thành `(puzzle_id, grid_size, frozenset(revealed_clues), frozenset(proved_verdicts.items()))` (băm trọn đối tượng `Clue`).
2. **Bộ nhớ đệm LRU giới hạn (`KBCache`, mặc định `maxsize = 8`, chỉnh qua tham số `kb_cache_size`):** Lưu trạng thái nhất quán, bảng phân loại và `CNFStats` của tối đa 8 trạng thái KB gần nhất. Khi `submit_verdict` thẩm định lại trên cùng $KB_t$, Agent trả kết quả từ `KBCache` mà **không gọi `ISATSolver.solve()`**.
3. **Tách hai bộ đếm SAT (`AgentStats`):** Phân tách `deduction_sat_calls` (từ suy diễn/hint) và `validation_sat_calls` (từ `submit_verdict`, luôn bằng **0** trong `run_auto_solve` nhờ `KBCache`). Các thống kê thực nghiệm chỉ đếm các truy vấn thực (`cached=False`) trong `DeductionStep.sat_queries` (bao gồm cả truy vấn nhất quán có `cell="KB"`).

---

## 5.3. Vòng lặp Suy diễn Không đoán mò (No-Guess Deduction Loop)

### 5.3.1. Cơ chế chọn bước đi tất định và cập nhật $KB_t$

Trong chế độ `Auto Solve`, Logic Agent chỉ làm việc qua các giao tiếp công khai của `IGameEngine` (*Project 2 Spec* Mục 4.1, 4.4). Tại mỗi bước $t = 0, 1, 2, \dots$:
1. Đọc `PublicState_t`; nếu toàn bộ ô đã mở ($U_t = \emptyset$), dừng với `SOLVED`.
2. Biên dịch `PublicState_t` sang CNF $KB_t$ kèm `CNFStats` qua `ICNFEncoder.encode_kb()`.
3. Phân loại toàn bộ ô chưa mở $U_t$ theo thứ tự row-major bằng thuật toán Entailment (Mục 5.2.5). Nếu $KB_t$ là `UNSAT` $\Rightarrow$ dừng với `INCONSISTENT`.
4. Chọn đúng **1 nhân vật bị ép buộc đầu tiên** theo thứ tự row-major (`A1, B1, ..., EN`) và gửi `(chosen_cell, forced_status)` tới `GameEngine.submit_verdict`.
5. Khi `VerdictCode.ACCEPTED`, Engine lật thẻ `chosen_cell`, tiết lộ manh mối mới và chuyển sang $KB_{t+1}$. Agent ghi nhận `DeductionStep` vào trace và kích hoạt callback `on_step(step)` (nếu có).

> **Ghi chú về `deduction_steps` và `reveal_waves` (FAQ #12):** Theo giải đáp chính thức của giảng viên, một *reveal wave* là đợt lật đồng loạt toàn bộ các ô bị ép buộc ở cùng $KB_t$, và **chỉ số `reveal_waves` được phép bỏ qua** trong thực nghiệm. Vòng lặp chuẩn chọn và lật từng nhân vật bị ép buộc theo thứ tự row-major ở mỗi bước để bám sát luật chơi và hỗ trợ animation từng nước đi.

### 5.3.2. Ba điều kiện dừng tường minh (`AutoSolveOutcome`)

Vòng lặp chỉ kết thúc với một trong ba trạng thái của `AutoSolveOutcome` (suy ra qua `outcome_of(steps, final_state)` và lưu tại `agent.last_outcome`):
1. **`SOLVED`:** Không còn ô chưa mở (`final_state.is_solved == True`). Không chèn bước kết thúc phụ; bước cuối là bước `ACCEPTED` cuối cùng.
2. **`AMBIGUOUS` (dừng an toàn, không đoán):** Vẫn còn ô chưa mở ($U_t \neq \emptyset$), $KB_t$ nhất quán, nhưng mọi ô trong $U_t$ đều là `UNKNOWN`. Agent thêm một bước kết thúc (`cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.NOT_PROVABLE`, kèm `sat_queries` vòng cuối và `active_clue_ids`), ghi log `WARNING` và **tuyệt đối không đoán mò**.
3. **`INCONSISTENT`:** $KB_t$ là `UNSAT` (thêm bước kết thúc `cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.INCONSISTENT`), hoặc Engine trả `CONTRADICTED` cho phán quyết Agent đã chứng minh là bắt buộc (bước cuối giữ `cell`/`verdict` đã gửi và `verdict_code=VerdictCode.CONTRADICTED`).

### 5.3.3. Cơ chế callback `on_step` hỗ trợ Animation (FAQ #4)

`run_auto_solve(engine, on_step=None)` nhận tham số gọi lại tùy chọn `on_step: Callable[[DeductionStep], None] | None = None` (tham số mở rộng so với hợp đồng `ILogicAgent.run_auto_solve(engine)` trong `core/contracts/interfaces.py`; giá trị mặc định `None` giữ tương thích hợp đồng):
- Ngay sau mỗi bước (kể cả bước kết thúc `AMBIGUOUS`/`INCONSISTENT`), Agent gọi `on_step(step)` trong khối `try...except` để ngoại lệ ở tầng UI không làm hỏng trạng thái Agent.
- GUI sử dụng callback này để cập nhật từng thẻ và chèn độ trễ animation; khi chạy benchmark không giao diện (`on_step=None`), không phát sinh chi phí đồ họa.

### 5.3.4. Cấu trúc bản ghi `DeductionStep` (`core/contracts/models.py`)

| Thành phần | Kiểu dữ liệu | Mô tả & Ý nghĩa |
| --- | --- | --- |
| `step_number` | `int` | Số thứ tự bước suy diễn (`1, 2, ...`, khớp `resp.public_state.step` khi `ACCEPTED` hoặc `state.step + 1` ở bước kết thúc). |
| `active_clue_ids` | `tuple[str, ...]` | Danh sách `clue_id` của các manh mối đang lật ngửa trong $KB_t$. |
| `sat_queries` | `tuple[SATQueryLog, ...]` | Danh sách truy vấn SAT ở bước $t$: `cell` (`"KB"` hoặc `CellID`), `assumptions`, `is_sat`, `metrics: SATMetrics`, `cached: bool`. |
| `cell` | `Optional[CellID]` | Ô được chọn theo row-major (`None` ở bước kết thúc `AMBIGUOUS`/`INCONSISTENT` do `UNSAT`). |
| `verdict` | `Status` | Phán quyết `CRIMINAL` / `INNOCENT`, hoặc `Status.UNKNOWN` ở bước kết thúc `AMBIGUOUS`/`INCONSISTENT` do `UNSAT`. |
| `verdict_code` | `VerdictCode` | `ACCEPTED`, `NOT_PROVABLE` (`AMBIGUOUS`), `INCONSISTENT`, hoặc `CONTRADICTED`. |
| `revealed_clue` | `Optional[Clue]` | Manh mối mới vừa được Engine lật mở sau khi `ACCEPTED` (hoặc `None`). |
| `cnf_stats` | `Optional[CNFStats]` | Thống kê `num_primary_vars`, `num_aux_vars`, `num_clauses`, `encoding_strategy` của $KB_t$. |

### 5.3.5. Mã giả Vòng lặp Suy diễn Không đoán mò

```text
ALGORITHM RunNoGuessDeductionLoop(game_engine, encoder, solver, on_step = NONE):
    trace <- EMPTY_LIST

    LOOP:
        public_state <- game_engine.get_public_state()
        IF public_state.is_solved OR public_state.unsolved_cells IS EMPTY THEN
            BREAK

        // Biên dịch KB_t từ revealed_clues + proved_verdicts (tra KBCache trước)
        active_clue_ids <- EXTRACT_IDS(public_state.revealed_clues)
        (KB_t, cnf_stats) <- encoder.encode_kb(public_state)
        unresolved <- ROW_MAJOR_SORT(public_state.unsolved_cells)

        // Phân loại toàn bộ nhân vật chưa giải (kèm Model Caching nếu bật)
        (consistent, classifications, sat_queries) <-
            ClassifyAllWithModelCaching(KB_t, unresolved, var_map)

        // Điều kiện dừng INCONSISTENT
        IF NOT consistent THEN
            step_record <- DeductionStep(step_number = public_state.step + 1,
                                         active_clue_ids = active_clue_ids,
                                         sat_queries = sat_queries,
                                         cell = NONE, verdict = Status.UNKNOWN,
                                         verdict_code = VerdictCode.INCONSISTENT,
                                         revealed_clue = NONE, cnf_stats = cnf_stats)
            APPEND(trace, step_record)
            SAFE_NOTIFY(on_step, step_record)
            BREAK

        // Chọn đúng 1 nhân vật bị ép buộc đầu tiên theo thứ tự row-major
        chosen <- FIRST (cell, classifications[cell]) IN unresolved
                  WHERE classifications[cell] IN {CRIMINAL, INNOCENT}

        // Điều kiện dừng AMBIGUOUS -> log WARNING và dừng, tuyệt đối không đoán
        IF chosen == NONE THEN
            LOG_WARNING("agent", public_state.puzzle_id, public_state.step, unresolved)
            step_record <- DeductionStep(step_number = public_state.step + 1,
                                         active_clue_ids = active_clue_ids,
                                         sat_queries = sat_queries,
                                         cell = NONE, verdict = Status.UNKNOWN,
                                         verdict_code = VerdictCode.NOT_PROVABLE,
                                         revealed_clue = NONE, cnf_stats = cnf_stats)
            APPEND(trace, step_record)
            SAFE_NOTIFY(on_step, step_record)
            BREAK

        // Gửi verdict hợp lệ lên Game Engine (KBCache đảm bảo validation_sat_calls == 0)
        resp <- game_engine.submit_verdict(chosen.cell, chosen.verdict)
        step_num <- resp.public_state.step IF resp.code == VerdictCode.ACCEPTED
                    ELSE (public_state.step + 1)
        step_record <- DeductionStep(step_number = step_num,
                                     active_clue_ids = active_clue_ids,
                                     sat_queries = sat_queries,
                                     cell = chosen.cell, verdict = chosen.verdict,
                                     verdict_code = resp.code,
                                     revealed_clue = resp.revealed_clue,
                                     cnf_stats = cnf_stats)
        APPEND(trace, step_record)
        SAFE_NOTIFY(on_step, step_record)

        IF resp.code != VerdictCode.ACCEPTED THEN
            BREAK

    self.last_outcome <- outcome_of(trace, game_engine.get_public_state())
    RETURN trace
```

---

## 5.4. Chức năng Gợi ý (Hint — FAQ #5)

Theo *Project 2 Spec* (Mục 4.1, 4.4) và FAQ #5, `get_hint(public_state)` hoạt động hoàn toàn trên `PublicState` (tuyệt đối không đọc đáp án ẩn) và trả về `HintResult(cell, forced_status, relevant_clue_ids, message, is_inconsistent)` theo hai pha:
- **Pha 1 — Tìm nhân vật bị ép buộc:** Nếu bảng đã giải xong (`state.is_solved`), trả về ngay với `0` truy vấn SAT. Ngược lại, tra `KBCache` / chạy Entailment:
  - Nếu $KB_t$ `UNSAT`: trả `HintResult(cell=None, forced_status=Status.UNKNOWN, message="Cơ sở tri thức mâu thuẫn (INCONSISTENT).", is_inconsistent=True)`.
  - Nếu $KB_t$ nhất quán nhưng không có ô ép buộc (`AMBIGUOUS`): trả `cell=None`, liệt kê các manh mối đã lật chạm tới ô chưa giải (`is_inconsistent=False`, hợp lệ theo FAQ #5).
  - Nếu có ít nhất một ô bị ép buộc: chọn `chosen_cell` đầu tiên theo row-major.
- **Pha 2 — Trích lọc manh mối liên quan (Scope-Based BFS):** Xuất phát từ `chosen_cell`, duyệt BFS qua các ô chưa giải nằm trong `scope(clue)` (tính bằng `encoder.resolve_region`) để thu thập các manh mối liên kết trực tiếp hoặc gián tiếp với `chosen_cell`, loại trừ các manh mối ở thành phần rời rạc mà không cần gọi thêm SAT. Hướng mở rộng cho tương lai là rút gọn tối thiểu theo *Deletion-Based MUS*.

```text
ALGORITHM GetHint(public_state, encoder, classify_fn):
    IF public_state.is_solved OR public_state.unsolved_cells IS EMPTY THEN
        RETURN HintResult(cell = NONE, forced_status = Status.UNKNOWN,
                          relevant_clue_ids = (), message = "Bảng đã được giải hoàn toàn.",
                          is_inconsistent = FALSE)

    (consistent, classifications) <- classify_fn(public_state)
    IF NOT consistent THEN
        RETURN HintResult(cell = NONE, forced_status = Status.UNKNOWN,
                          relevant_clue_ids = (),
                          message = "Cơ sở tri thức mâu thuẫn (INCONSISTENT).",
                          is_inconsistent = TRUE)

    unresolved <- ROW_MAJOR_SORT(public_state.unsolved_cells)
    chosen <- FIRST (cell, classifications[cell]) IN unresolved
              WHERE classifications[cell] IN {CRIMINAL, INNOCENT}

    IF chosen == NONE THEN
        relevant_ids <- CLUES_TOUCHING_UNSOLVED(public_state, encoder)
        RETURN HintResult(cell = NONE, forced_status = Status.UNKNOWN,
                          relevant_clue_ids = relevant_ids,
                          message = "... (AMBIGUOUS) ...",
                          is_inconsistent = FALSE)

    relevant_ids <- COLLECT_LINKED_CLUES(chosen.cell, public_state, encoder)
    RETURN HintResult(cell = chosen.cell, forced_status = chosen.status,
                      relevant_clue_ids = relevant_ids,
                      message = FORMAT_VIETNAMESE_HINT(chosen, relevant_ids),
                      is_inconsistent = FALSE)
```

---

## 5.5. Kiểm tra Tính duy nhất của Nghiệm (Uniqueness Check — FAQ #9)

Để kiểm chứng độc lập yêu cầu mọi màn chơi giải được có **duy nhất một nghiệm** (*Project 2 Spec* Mục 2.2, 4.4; FAQ #9), mô-đun `uniqueness.py` hoạt động trên toàn bộ tập manh mối đầy đủ của puzzle qua 2 lần gọi SAT:
1. Dựng `PublicState` tổng hợp gồm toàn bộ $N^2$ ô ở trạng thái `UNKNOWN` (`is_revealed=False`), `proved_verdicts={}`, và `revealed_clues=tuple(clues)`, rồi gọi `encoder.encode_kb(synthetic_state)` thu được công thức CNF $F$ (dùng chung một bộ cấp phát biến phụ).
2. **Lần giải 1:** Gọi $\text{SAT}(F)$. Nếu `UNSAT` $\Rightarrow$ trả về `UNSAT` (`is_unique=False`).
3. **Mệnh đề chặn $B(M)$ trên biến chính:** Từ nghiệm $M$, tạo đúng một mệnh đề chặn **chỉ trên tập biến chính $V_{\text{primary}} = \{C_1, \dots, C_n\}$**:
   $$B(M) = \bigvee_{i=1}^{n} \ell_i, \quad \text{với } \ell_i = \begin{cases} \neg C_i, & \text{nếu } M(C_i) = \text{True}, \\ C_i, & \text{nếu } M(C_i) = \text{False}. \end{cases}$$
   *(Bắt buộc không đưa biến phụ $V_{\text{aux}}$ vào $B(M)$ vì với bộ mã hóa một chiều như Sinz, cùng một phép gán biến chính có thể ứng với nhiều giá trị biến phụ khác nhau, gây báo nhầm thành nhiều nghiệm.)*
4. **Lần giải 2:** Gọi $\text{SAT}(F \wedge B(M))$ và kết luận:

| Kết quả Lần giải 1: `SAT(F)` | Kết quả Lần giải 2: `SAT(F ∧ B(M))` | `solution_count_status` | Diễn giải đối với Puzzle |
| --- | --- | --- | --- |
| `UNSAT` | *(không gọi)* | `UNSAT` (`is_unique=False`) | Tập manh mối tự mâu thuẫn, không tồn tại phép gán thỏa mãn. |
| `SAT` (nghiệm $M$) | `UNSAT` | `UNIQUE` (`is_unique=True`) | Không còn nghiệm nào khác $M$ trên biến chính — **đạt chuẩn FAQ #9**. |
| `SAT` (nghiệm $M$) | `SAT` (nghiệm $M'$) | `MULTIPLE` (`is_unique=False`) | Tồn tại $\ge 2$ nghiệm khác nhau $M \neq M'$ trên biến chính (mơ hồ). |

```text
ALGORITHM CheckUniqueness(all_clues, grid_size, encoder, solver):
    synthetic_state <- BUILD_SYNTHETIC_PUBLIC_STATE(grid_size, revealed_clues = all_clues)
    (F, _) <- encoder.encode_kb(synthetic_state)
    cell_vars <- [(cid, encoder.map_cell_to_var(cid, grid_size)) FOR cid IN all_cell_ids(grid_size)]

    res_1 <- SAT_SOLVE(F, assumptions = [])
    IF NOT res_1.is_sat THEN
        RETURN UniquenessResult(is_unique = FALSE, solution_count_status = "UNSAT",
                                first_model = NONE, second_model = NONE,
                                metrics_first = res_1.metrics, metrics_second = NONE)

    first_model <- MAP_TO_STATUS(res_1.model, cell_vars)
    blocking_clause <- (-v IF res_1.model[v] ELSE +v FOR (_, v) IN cell_vars)

    F_blocked <- CNFFormula(clauses = F.clauses + (blocking_clause,), ...)
    res_2 <- SAT_SOLVE(F_blocked, assumptions = [])

    IF NOT res_2.is_sat THEN
        RETURN UniquenessResult(is_unique = TRUE, solution_count_status = "UNIQUE",
                                first_model = first_model, second_model = NONE,
                                metrics_first = res_1.metrics, metrics_second = res_2.metrics)
    ELSE
        second_model <- MAP_TO_STATUS(res_2.model, cell_vars)
        RETURN UniquenessResult(is_unique = FALSE, solution_count_status = "MULTIPLE",
                                first_model = first_model, second_model = second_model,
                                metrics_first = res_1.metrics, metrics_second = res_2.metrics)
```

---

## 5.6. Phân tích Độ phức tạp và Đối chiếu Thực nghiệm

Đặt $n = N^2$ ($n \in \{9, 16, 25\}$), $k_0 \ge 1$ là số thẻ mở sẵn ban đầu, và $u_t$ là số ô chưa giải tại bước $t$. Giả sử màn chơi giải trọn vẹn sau $T = n - k_0$ bước ($u_t = T - t$):

- **Số lời gọi SAT ở một bước $t$:**
  - *Không Model Caching:* $\text{Calls}_{\text{naive}}(t) \le 1 + 2u_t \le 2n - 1 = O(n)$.
  - *Có Model Caching:* mô hình cơ sở $M_0$ từ $\text{SAT}(KB_t)$ cố định ngay $1$ cực tính cho toàn bộ $u_t$ ô chưa giải, nên mỗi ô chỉ còn tối đa $1$ truy vấn ngược (và các mô hình $M'$ tiếp theo tiếp tục loại bỏ truy vấn thừa), cho $\text{Calls}_{\text{cache}}(t) \le 1 + u_t \le n = O(n)$.
- **Tổng số lời gọi SAT cho cả màn chơi:**
  - *Không Model Caching (xấu nhất):* $\sum_{t=0}^{T-1}(1 + 2(T-t)) = T^2 + 2T = O(n^2)$.
  - *Có Model Caching (xấu nhất):* $\sum_{t=0}^{T-1}(1 + (T-t)) = \frac{T^2 + 3T}{2} = O(n^2)$ (giảm gần **50%** chặn trên lý thuyết).
- **Uniqueness Check:** cố định $1$ hoặc $2$ lời gọi SAT, tức $O(1)$ lời gọi.
- **Chi phí mỗi lời gọi DPLL:** trong trường hợp xấu nhất là $O\!\left(2^{|V|} \cdot |F|\right)$ với $V = V_{\text{primary}} \cup V_{\text{aux}}$ và $|F|$ là tổng số literal, nhưng với $n \le 25$, cấu trúc cục bộ của manh mối kết hợp Unit Propagation và heuristic chọn biến (`moms`/`jw`) cắt tỉa cây tìm kiếm rất mạnh.

**Bảng 5.1: Chặn trên lý thuyết ($k_0 = 1$) và số liệu thực nghiệm trung bình trên bộ 10 màn chuẩn (`direct` encoding; $k_0 = 2, 3, 5$ tương ứng $T = 7, 13, 20$, kèm chặn trên tính theo $T$ thực)**

| Kích thước lưới | $n = N^2$ | Chặn trên SAT calls (Không cache, $k_0=1$) | Chặn trên SAT calls (Model Caching, $k_0=1$) | Chặn trên với $T$ thực (Không cache / Cache) | SAT calls thực tế trung bình — Không cache (`C0`) | SAT calls thực tế trung bình — Có Model Caching (`C4` / `C6`) | Thời gian chạy thực tế trung bình `C6` (`ms`, `median`) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $3 \times 3$ (4 màn, $k_0=2, T=7$) | 9 | 80 | 44 | `63` / `35` | `54.25` (`53–56`) | `34.75` (`34–35`) / `35.00` (`35`) | `2.408` (`2.136–2.867`) |
| $4 \times 4$ (4 màn, $k_0=3, T=13$) | 16 | 255 | 135 | `195` / `104` | `169.50` (`156–187`) | `101.50` (`94–104`) / `103.00` (`100–104`) | `8.965` (`7.428–10.271`) |
| $5 \times 5$ (2 màn, $k_0=5, T=20$) | 25 | 624 | 324 | `440` / `230` | `374.00` (`351–397`) | `221.00` (`215–227`) / `222.50` (`215–230`) | `35.397` (`24.479–46.315`) |

*(Kết quả đầy đủ qua 8 cấu hình `C0`–`C7`, so sánh Direct vs. Sinz, Pure-Literal, MOMs/JW, Model Caching và các ca biên xem chi tiết tại Mục 6 — `docs/report_tv4_experiments.md`.)*
