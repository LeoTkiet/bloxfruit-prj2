# Bản nháp Mục Algorithms — Phần Thành viên 4 (TV4: Logic Agent)

> **Trạng thái tài liệu:** Bản nháp chuẩn bị cho mục *Algorithms* trong `Report.pdf` (phần TV4: Entailment, No-Guess Deduction Loop, Hint, Uniqueness Check và Phân tích độ phức tạp; phần DPLL SAT do TV3 phụ trách — plan.md 2.3, 2.4). Đã đồng bộ tên kiểu/trường theo `Source/core/contracts/` (đã đóng băng) và quy ước trong `docs/tv4_agent_conventions.md`. Mọi số liệu thực nghiệm chưa có được giữ nguyên ở trạng thái `[chờ kết quả benchmark GĐ 3B]`.

---

## 1. Biểu diễn tri thức (Knowledge Representation)

Trong bài toán Griductive trên lưới vuông kích thước $N \times N$ với $N \in \{3, 4, 5\}$ (description.md 2.1; AI - Project 2.pdf 2.1), đặt $n = N^2$ là tổng số ô (nhân vật) trên bảng. Các hàng được đánh số từ $1$ đến $N$ (từ trên xuống dưới) và các cột được đánh chữ cái từ `A` trở đi (từ trái sang phải), ví dụ `C2` chỉ cột `C`, hàng `2` (description.md 2.1).

### 1.1. Biến mệnh đề chính và biến phụ

Với mỗi nhân vật $i \in \{1, 2, \dots, n\}$, hệ thống định nghĩa đúng một **biến mệnh đề chính (primary Boolean variable)** $C_i$ (AI - Project 2.pdf 3.1; description.md 2.2):

$$C_i = \begin{cases} \text{True}, & \text{nếu nhân vật } i \text{ là Tội phạm (CRIMINAL)}, \\ \text{False}, & \text{nếu nhân vật } i \text{ là Người vô tội (INNOCENT)}. \end{cases}$$

- Ánh xạ giữa tọa độ ô/nhân vật và chỉ số biến $i \in \{1, \dots, n\}$ phải hoàn toàn **tất định (deterministic)** (AI - Project 2.pdf 3.1; plan.md 2.2), theo thứ tự cố định row-major (`A1` $\to 1$, `B1` $\to 2$, ..., ô cuối $\to n$).
- Nếu nhóm đổi tên cặp nhãn thay cho `Criminal`/`Innocent` theo chủ đề riêng (FAQ #15), bản chất biến nhị phân $C_i$ và toàn bộ các thuật toán suy diễn bên dưới không thay đổi.
- Các **biến phụ (auxiliary variables)** phát sinh từ bộ mã hóa CNF (như biến đếm tuần tự Sequential Counter/Sinz cho manh mối đếm hoặc biến Tseitin cho ràng buộc chẵn lẻ `PARITY`) được cấp phát và quản lý **tách biệt hoàn toàn** khỏi tập biến chính $\{C_1, \dots, C_n\}$ (AI - Project 2.pdf 3.1; description.md 2.2; plan.md 2.2).

### 1.2. Cơ sở tri thức công khai $KB_t$ tại bước suy diễn $t$

Theo kiến trúc tách biệt bắt buộc giữa **Game Engine** (sở hữu thế giới dữ liệu ẩn) và **Logic Agent** (chỉ tiếp cận vùng tri thức công khai) (AI - Project 2.pdf 4.1; description.md 1.1), tại mỗi bước suy diễn $t \ge 0$, cơ sở tri thức công khai $KB_t$ được biên dịch tự động sang dạng chuẩn hội (CNF) gồm đúng hai thành phần (AI - Project 2.pdf 3.3, 4.2; description.md 2.3):

$$KB_t = \text{CNF}\!\left(\mathcal{R}_t\right) \;\wedge\; \bigwedge_{(i,\, s_i) \in \mathcal{V}_t} \text{Unit}(C_i, s_i)$$

trong đó:
- $\mathcal{R}_t$ là tập các **manh mối đã lật ngửa (revealed clues)** tính đến bước $t$. Mọi manh mối đã lật đều luôn đúng bất kể chủ nhân thẻ là `CRIMINAL` hay `INNOCENT` (AI - Project 2.pdf 2.1; description.md 2.1).
- $\mathcal{V}_t$ là tập các **phán quyết đã được chứng minh (proved verdicts)** (bao gồm các thẻ mở sẵn ban đầu ở bước $t = 0$ và các nhân vật đã được chứng minh ở các bước $0, \dots, t-1$), trong đó mỗi phán quyết được mã hóa thành một **mệnh đề đơn vị (unit clause)**: $\text{Unit}(C_i, \text{CRIMINAL}) = (C_i)$ và $\text{Unit}(C_i, \text{INNOCENT}) = (\neg C_i)$ (description.md 2.3).
- Ở thời điểm khởi đầu $t = 0$, $KB_0$ hình thành từ các thẻ mở sẵn ban đầu: game gốc có $1$ thẻ mở sẵn, hoặc nhóm có thể tùy biến thành $2, 3, 4, \dots$ thẻ mở sẵn theo từng màn chơi (FAQ #8; description.md 2.1).
- **Nguyên tắc cách ly tuyệt đối:** Trạng thái bí mật (hidden labels) và nội dung các manh mối đang úp (unrevealed clues) **tuyệt đối không xuất hiện** trong $KB_t$ (AI - Project 2.pdf 4.2; description.md 2.3).
- Khi chuyển từ bước $t$ sang $t+1$ sau khi lật thêm một thẻ hợp lệ, $KB_t$ mở rộng đơn điệu theo tập mệnh đề: $KB_{t+1} = KB_t \wedge \text{Unit}(C_{i^*}, s_{i^*}) \wedge \text{CNF}(\text{clue}_{i^*})$, đồng nghĩa với tập mô hình thỏa mãn thu hẹp dần: $\text{Mod}(KB_{t+1}) \subseteq \text{Mod}(KB_t)$.

---

## 2. Kiểm tra Hệ quả Logic (Entailment Check)

### 2.1. Phân biệt Mô hình thỏa mãn và Hệ quả logic

Điểm cốt lõi của quy tắc không đoán mò (No-Guess Rule) là phân biệt rõ giữa **một mô hình thỏa mãn (satisfying model)** và **hệ quả logic (logical entailment)** (AI - Project 2.pdf 3.4; description.md 2.5):
- Một mô hình $M \models KB_t$ chỉ cho biết một phương án gán *có thể xảy ra*, không đủ cơ sở để kết luận trạng thái bắt buộc của nhân vật.
- Một phán quyết cho nhân vật chưa giải $i$ chỉ hợp lệ khi nó đúng trong **mọi** mô hình thỏa mãn của $KB_t$, ký hiệu $KB_t \models C_i$ (chắc chắn `CRIMINAL`) hoặc $KB_t \models \neg C_i$ (chắc chắn `INNOCENT`).

### 2.2. Quy trình kiểm tra bằng phản chứng (Entailment via Refutation)

Tại bước $t$, với cơ sở tri thức $KB_t$ và một nhân vật chưa giải $i$, Logic Agent thực hiện kiểm tra như sau (AI - Project 2.pdf 3.4; description.md 2.5, 3.2; plan.md 2.4):

1. **Kiểm tra tính nhất quán của $KB_t$:** Gọi bộ giải SAT cho $KB_t$. Nếu $KB_t$ là `UNSAT` $\Rightarrow$ trả về **`INCONSISTENT`** (cơ sở tri thức tự mâu thuẫn).
2. **Kiểm tra giả thiết phủ định `CRIMINAL`:** Gọi bộ giải SAT cho $KB_t \wedge \neg C_i$. Nếu `UNSAT` $\Rightarrow$ trả về **`CRIMINAL`** (kết thúc sớm cho nhân vật $i$, không cần gọi truy vấn thứ hai).
3. **Kiểm tra giả thiết phủ định `INNOCENT`:** Nếu $KB_t \wedge \neg C_i$ là `SAT`, gọi tiếp bộ giải SAT cho $KB_t \wedge C_i$. Nếu `UNSAT` $\Rightarrow$ trả về **`INNOCENT`**.
4. **Trường hợp cả hai đều thỏa mãn:** Nếu cả $KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$ đều `SAT` $\Rightarrow$ trả về **`UNKNOWN`** (chưa bị ép buộc, tuyệt đối không đoán).

### 2.3. Chứng minh ngắn tính đúng đắn (Refutation Proof)

- **Định lý:** Với mọi công thức mệnh đề $KB_t$ và mệnh đề mục tiêu $\alpha$:
  $$KB_t \models \alpha \iff (KB_t \wedge \neg \alpha) \text{ là UNSAT}.$$
- **Chứng minh:** Theo định nghĩa ngữ nghĩa, $KB_t \models \alpha$ khi và chỉ khi với mọi phép gán chân trị $M$, hễ $M \models KB_t$ thì $M \models \alpha$. Mệnh đề phổ quát này tương đương với việc **không tồn tại** phép gán $M$ nào thỏa mãn đồng thời $M \models KB_t$ và $M \not\models \alpha$, tức không tồn tại $M$ sao cho $M \models (KB_t \wedge \neg \alpha)$. Theo định nghĩa tính không thỏa mãn, điều này tương đương $KB_t \wedge \neg \alpha$ là `UNSAT`.
- **Áp dụng:**
  - Đặt $\alpha = C_i$: $KB_t \models C_i \iff (KB_t \wedge \neg C_i) \text{ là UNSAT} \implies$ nhân vật $i$ bắt buộc là `CRIMINAL`.
  - Đặt $\alpha = \neg C_i$: $KB_t \models \neg C_i \iff (KB_t \wedge C_i) \text{ là UNSAT} \implies$ nhân vật $i$ bắt buộc là `INNOCENT`.
  - Nếu cả hai đều `SAT`, tồn tại mô hình $M_1 \models KB_t$ với $M_1(C_i) = \text{False}$ và mô hình $M_2 \models KB_t$ với $M_2(C_i) = \text{True}$, nên không trạng thái nào là hệ quả tất yếu (`UNKNOWN`).
- **Vai trò bắt buộc của bước kiểm tra $KB_t$ SAT trước tiên:** Nếu $KB_t$ vốn đã `UNSAT` (mâu thuẫn), thì theo nguyên lý bùng nổ (*ex falso quodlibet*), mọi công thức mở rộng $KB_t \wedge \neg C_i$ và $KB_t \wedge C_i$ đều đồng thời `UNSAT`. Nếu bỏ qua bước kiểm tra $KB_t$ trước, thuật toán sẽ trả về sai nhãn `CRIMINAL` ngay ở truy vấn đầu tiên thay vì phát hiện `INCONSISTENT`.

> **Ví dụ minh họa (AI - Project 2.pdf 3.4; description.md 2.5):** Với $KB = (C_A \vee C_B) \wedge (\neg C_A \vee C_B)$, phép gán $(C_A = \text{False}, C_B = \text{True})$ thỏa mãn $KB$ nên $KB$ nhất quán (`SAT`). Giả sử $\neg C_B$ cho $KB \wedge \neg C_B \equiv C_A \wedge \neg C_A$ (`UNSAT`), suy ra $KB \models C_B$ ($B$ là `CRIMINAL`). Ngược lại, cả $KB \wedge C_A$ và $KB \wedge \neg C_A$ đều `SAT`, nên $A$ có trạng thái `UNKNOWN`.

### 2.4. Tối ưu Model Caching và lập luận tính đúng đắn tuyệt đối

Khi phân loại đồng loạt tất cả nhân vật chưa giải $U_t$ ở cùng một bước $t$, cách làm ngây thơ gọi bộ giải SAT lặp đi lặp lại trên cùng $KB_t$. **Model Caching** khai thác mọi phép gán thỏa mãn $M$ thu được trong bước $t$ để loại bỏ các truy vấn dư thừa (description.md 3.2; plan.md 2.4):

- Duy trì hai bảng cờ theo từng nhân vật $j \in U_t$: `can_be_criminal[j]` (đã tìm thấy mô hình của $KB_t$ có $C_j = \text{True}$) và `can_be_innocent[j]` (đã tìm thấy mô hình của $KB_t$ có $C_j = \text{False}$), khởi tạo `False`.
- Mỗi khi một lời gọi SAT trên $KB_t$ hoặc $KB_t \wedge \ell$ (với $\ell \in \{C_i, \neg C_i\}$) trả về `SAT` kèm mô hình đầy đủ $M$, ta duyệt toàn bộ $j \in U_t$:
  - Nếu $M(C_j) = \text{True}$ $\Rightarrow$ đặt `can_be_criminal[j] <- True`.
  - Nếu $M(C_j) = \text{False}$ $\Rightarrow$ đặt `can_be_innocent[j] <- True`.
- Khi xét nhân vật $i \in U_t$: chỉ gọi `SAT(KB_t ∧ ¬C_i)` nếu `can_be_innocent[i]` đang là `False`, và chỉ gọi `SAT(KB_t ∧ C_i)` nếu `can_be_criminal[i]` đang là `False`.

**Lập luận vì sao Model Caching bảo toàn tính đúng đắn tuyệt đối (Soundness & Completeness):**
1. *Không bao giờ bỏ sót chứng nhân SAT:* Mọi mô hình $M$ trả về bởi `SAT(KB_t)` hoặc `SAT(KB_t ∧ ℓ)` đều thỏa mãn mọi mệnh đề của $KB_t$ (kể cả các mệnh đề chứa biến phụ). Nếu $M(C_j) = \text{False}$, thì chính $M$ là chứng nhân trực tiếp chứng minh $M \models (KB_t \wedge \neg C_j)$, nên $KB_t \wedge \neg C_j$ **chắc chắn `SAT`**; việc bỏ qua truy vấn `SAT(KB_t ∧ ¬C_j)` cho kết quả hoàn toàn giống như khi gọi thật. Tương tự khi $M(C_j) = \text{True}$ cho $KB_t \wedge C_j$.
2. *Không bao giờ bỏ lỡ trạng thái bị ép buộc (UNSAT):* Giả sử nhân vật $i$ thực sự bị ép là `CRIMINAL` ($KB_t \models C_i$). Khi đó mọi mô hình $M \models KB_t$ đều buộc phải có $M(C_i) = \text{True}$, nên không tồn tại mô hình nào làm `can_be_innocent[i]` trở thành `True`. Vì vậy truy vấn `SAT(KB_t ∧ ¬C_i)` vẫn chắc chắn được thực thi và trả về `UNSAT`. Tương tự đối với `INNOCENT`.
3. *Điều kiện hủy cache bắt buộc và tính đơn điệu:* Cache chứng nhân SAT chỉ hợp lệ cho đúng trạng thái $KB_t$ hiện tại; ngay khi một thẻ được lật và tri thức mở rộng sang $KB_{t+1}$, **toàn bộ cache phải bị xóa sạch** vì $\text{Mod}(KB_{t+1}) \subseteq \text{Mod}(KB_t)$ — một mô hình từng thỏa mãn $KB_t$ có thể không còn thỏa mãn manh mối mới trong $KB_{t+1}$. Ngược lại, mọi kết luận bị ép buộc ($KB_t \models C_i$ hoặc $KB_t \models \neg C_i$) đã chứng minh ở bước $t$ vẫn giữ nguyên tính đúng đắn ở bước $t+1$ nhờ tính đơn điệu (monotonicity) của hệ quả logic khi $KB$ chỉ được bổ sung thêm mệnh đề.

### 2.5. Mã giả Entailment Check (có Model Caching)

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

### 2.6. Bộ nhớ đệm theo khóa KB (`KBCache`) và tách bộ đếm SAT

Trong vòng lặp tự động giải, sau khi `DeductiveLogicAgent` suy luận ra ô ép buộc trên `PublicState` hiện tại, `GameEngine.submit_verdict(cell, verdict)` sẽ gọi ngược lại `agent.check_consistency(current_public)` và `agent.classify_character(current_public, cell)` để thẩm định độc lập tính hợp lệ của phán quyết. Nếu không đệm ở tầng KB, mỗi bước sẽ bị nhân đôi số lần gọi DPLL trên cùng một công thức $KB_t$.

Để tránh đếm gấp đôi và giữ nguyên ranh giới độc lập của `GameEngine`:
1. **Khóa KB bất biến (`make_kb_key`):** Mỗi `PublicState` được ánh xạ thành khóa `(puzzle_id, grid_size, frozenset(revealed_clues), frozenset(proved_verdicts.items()))`. Hai đối tượng `PublicState` khác nhau nhưng biểu diễn cùng một $KB_t$ sẽ cho cùng một khóa.
2. **Bộ nhớ đệm LRU giới hạn (`KBCache`, `maxsize <= 8`):** Lưu kết quả nhất quán, bảng `classification`, các mô hình đã tìm thấy và `CNFStats` của tối đa 8 trạng thái KB gần nhất. Khi `submit_verdict` gọi lại `check_consistency` hoặc `classify_character`, Agent tra `KBCache` và trả về kết quả ngay mà **không gọi `ISATSolver.solve()`**.
3. **Tách hai bộ đếm SAT (`AgentStats`):** Agent ghi nhận riêng `stats.deduction_sat_calls` (lời gọi phát sinh khi Agent tự suy luận) và `stats.validation_sat_calls` (lời gọi phát sinh khi Engine gọi lại trong `submit_verdict` để duyệt phán quyết). Nhờ `KBCache`, `stats.validation_sat_calls` luôn bằng **0** trong `run_auto_solve`. Các thống kê benchmark chỉ đếm các truy vấn thực (`cached=False`) trong `DeductionStep.sat_queries` (bao gồm cả truy vấn kiểm tra nhất quán có `cell="KB"`).

---

## 3. Vòng lặp Suy diễn Không đoán mò (No-Guess Deduction Loop)

### 3.1. Cơ chế chọn bước đi tất định và cập nhật $KB_t$

Trong chế độ giải tự động (`Auto Solve`), Logic Agent chỉ giao tiếp với Game Engine qua các thao tác công khai (lấy `PublicState` và gửi phán quyết), tuyệt đối không đọc đáp án ẩn (AI - Project 2.pdf 4.1, 4.4; description.md 3.1). Tại mỗi bước $t = 0, 1, 2, \dots$:

1. Lấy trạng thái công khai hiện hành `PublicState_t` (các thẻ đã lật, trạng thái đã chứng minh và tập ô chưa mở $U_t$). Nếu $U_t = \emptyset$, dừng ngay với trạng thái `SOLVED`.
2. Mã hóa tự động `PublicState_t` thành công thức CNF $KB_t$ kèm thống kê biến/mệnh đề (AI - Project 2.pdf 4.2).
3. Phân loại toàn bộ nhân vật chưa giải trong $U_t$ bằng thuật toán Entailment (Mục 2.5). Nếu $KB_t$ không nhất quán $\Rightarrow$ dừng với trạng thái `INCONSISTENT`.
4. Duyệt tập $U_t$ theo **thứ tự tất định row-major** tổng quát theo kích thước lưới $N \times N$ (từ hàng $1$ đến hàng $N$, trong mỗi hàng từ cột `A` đến cột thứ $N$; cụ thể `3×3`: `A1, B1, C1, A2, ..., C3`; `4×4`: `A1, ..., D4`; `5×5`: `A1, ..., E5`) và chọn nhân vật đầu tiên có nhãn bị ép buộc (`CRIMINAL` hoặc `INNOCENT`) (AI - Project 2.pdf 2.2; plan.md 2.4).
5. Gửi phán quyết `(chosen_cell, forced_status)` lên Game Engine. Khi phán quyết hợp lệ (`ACCEPTED`), Game Engine lật thẻ `chosen_cell`, tiết lộ manh mối mới và cập nhật trạng thái công khai sang bước $t + 1$ để hình thành $KB_{t+1}$ (AI - Project 2.pdf 2.2, 4.4).
6. Ghi nhận bản ghi `DeductionStep` vào `Deduction Trace`, kích hoạt callback `on_step` (nếu có) và tiếp tục sang bước $t + 1$.

> **Ghi chú về `deduction steps` và `reveal waves` (FAQ #12):** Theo giải đáp của giảng viên, một *reveal wave* là đợt lật đồng loạt toàn bộ các ô bị ép buộc ở cùng một trạng thái $KB_t$, và giảng viên **cho phép bỏ qua chỉ số `reveal waves`** trong thực nghiệm (chỉ cần báo cáo `deduction steps`). Vòng lặp chuẩn chọn và lật đúng $1$ ô ép buộc theo thứ tự row-major ở mỗi bước $t$ để bám sát luật chơi từng bước và hỗ trợ trực quan hóa từng nước đi.

### 3.2. Ba điều kiện dừng tường minh (`AutoSolveOutcome`)

Vòng lặp suy diễn chỉ kết thúc khi rơi vào đúng một trong ba trạng thái của `AutoSolveOutcome` (`SOLVED`, `AMBIGUOUS`, `INCONSISTENT`), có thể suy ra trực tiếp qua hàm `outcome_of(steps, final_state)` và được lưu tại `agent.last_outcome` (AI - Project 2.pdf 2.2, 4.4; plan.md 2.4; description.md 2.5):

1. **`SOLVED`:** Không còn nhân vật nào chưa mở (`final_state.is_solved == True`,$U_t = \emptyset$). Không chèn thêm bước kết thúc; bước cuối là bước `ACCEPTED` cuối cùng.
2. **`AMBIGUOUS` (dừng an toàn, không đoán):** Vẫn còn nhân vật chưa mở ($U_t \neq \emptyset$), $KB_t$ nhất quán, nhưng mọi nhân vật trong $U_t$ đều được phân loại là `UNKNOWN` (không có nhân vật nào bị ép buộc). Agent ghi nhận một bước kết thúc với `cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.NOT_PROVABLE`, `sat_queries` của vòng cuối, `active_clue_ids` là toàn bộ clue đã lật, đồng thời ghi cảnh báo `logging.getLogger("agent").warning(...)` (gồm `puzzle_id`, `step`, danh sách ô còn `UNKNOWN`) và **tuyệt đối không đoán mò**.
3. **`INCONSISTENT`:** Kiểm tra tính nhất quán cho thấy $KB_t$ là `UNSAT` (tập manh mối công khai và phán quyết tự mâu thuẫn). Agent ghi nhận một bước kết thúc với `cell=None`, `verdict=Status.UNKNOWN`, `verdict_code=VerdictCode.INCONSISTENT` và dừng ngay.

### 3.3. Cơ chế callback `on_step` hỗ trợ Animation (FAQ #4)

Theo (FAQ #4), chế độ `Auto Solve` trên GUI nên có chức năng **animate lại quá trình giải** thay vì nhảy thẳng đến kết quả cuối. Theo kiến trúc hướng hợp đồng (`ILogicAgent`), vòng lặp suy diễn `run_auto_solve(engine, on_step=None)` nhận tham số gọi lại tùy chọn `on_step: Callable[[DeductionStep], None] | None = None`:
- Ngay sau khi mỗi bước được tạo (kể cả bước kết thúc `AMBIGUOUS`/`INCONSISTENT`), Agent gọi `on_step(step)` trong khối `try...except` để ngoại lệ từ tầng UI không làm hỏng trạng thái của Agent.
- Lớp GUI đăng ký callback này để cập nhật thẻ vừa lật, tô sáng manh mối vừa mở, nối dòng nhật ký vào bảng Deduction Trace và chèn độ trễ (delay) tùy chỉnh theo tốc độ animation.
- Khi chạy benchmark không giao diện (`experiments/benchmark.py`), `on_step` để mặc định là `None` nên không phát sinh chi phí đồ họa.

### 3.4. Cấu trúc một bản ghi `DeductionStep` (`core/contracts/models.py`)

Mỗi bước suy diễn sinh ra một bản ghi `DeductionStep` bất biến (`@dataclass(frozen=True)`) gồm đầy đủ các trường đã chốt trong `models.py`:

| Thành phần | Kiểu dữ liệu | Mô tả & Ý nghĩa |
| --- | --- | --- |
| `step_number` | `int` | Số thứ tự bước suy diễn (`1, 2, ...`, khớp `resp.public_state.step` khi `ACCEPTED` hoặc `state.step + 1` ở bước kết thúc). |
| `active_clue_ids` | `tuple[str, ...]` | Danh sách `clue_id` của các manh mối đang lật ngửa trong $KB_t$. |
| `sat_queries` | `tuple[SATQueryLog, ...]` | Danh sách các truy vấn SAT ở bước $t$: mỗi `SATQueryLog` gồm `cell` (`"KB"` cho truy vấn nhất quán, hoặc `CellID`), `assumptions`, `is_sat`, `metrics: SATMetrics`, và cờ `cached: bool`. |
| `cell` | `Optional[CellID]` | Ô nhân vật được chọn theo thứ tự row-major (hoặc `None` ở bước kết thúc `AMBIGUOUS`/`INCONSISTENT`). |
| `verdict` | `Status` | Phán quyết `CRIMINAL` / `INNOCENT`, hoặc `Status.UNKNOWN` ở bước kết thúc không lật thẻ. |
| `verdict_code` | `VerdictCode` | `ACCEPTED` khi hợp lệ; `NOT_PROVABLE` ở bước kết thúc `AMBIGUOUS`; `INCONSISTENT` ở bước kết thúc `INCONSISTENT`; hoặc `CONTRADICTED`. |
| `revealed_clue` | `Optional[Clue]` | Manh mối mới vừa được Game Engine lật mở sau khi `ACCEPTED` (hoặc `None` nếu không lật thẻ). |
| `cnf_stats` | `Optional[CNFStats]` | Thống kê `num_primary_vars`, `num_aux_vars`, `num_clauses`, `encoding_strategy` của $KB_t$. |

### 3.5. Mã giả Vòng lặp Suy diễn Không đoán mò

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

## 4. Chức năng Gợi ý (Hint — FAQ #5)

Theo đặc tả đề bài (AI - Project 2.pdf 4.1, 4.4) và giải đáp chính thức (FAQ #5), chức năng `Hint` phải tuân thủ hai nguyên tắc:
1. **Chỉ dùng tri thức công khai:** Hoàn toàn hoạt động trên `PublicState` ($KB_t$), tuyệt đối không đọc đáp án ẩn hay manh mối đang úp trong Game Engine (AI - Project 2.pdf 4.4; description.md 2.5).
2. **Định dạng gợi ý linh hoạt (FAQ #5):** Có thể gợi ý **một nhân vật tiếp theo đang bị ép buộc** (có thể chứng minh được ngay từ $KB_t$), **hoặc** chỉ ra **tập nhân vật / manh mối công khai liên quan nên cân nhắc** để tự suy ra nhân vật đó (plan.md 2.4).

### 4.1. Cơ chế chọn mục tiêu và trích lọc manh mối liên quan

Thuật toán `GetHint` (`agent/hint_engine.py`) trả về `HintResult(cell, forced_status, relevant_clue_ids, message, is_inconsistent)` theo hai pha:
- **Pha 1 — Tìm nhân vật bị ép buộc:** Nếu bảng đã giải xong (`state.is_solved`), trả về ngay `HintResult(cell=None, forced_status=Status.UNKNOWN, ...)` với `0` truy vấn SAT. Ngược lại, tra `KBCache` / chạy Entailment (Mục 2.5):
  - Nếu $KB_t$ là `INCONSISTENT`: trả `HintResult(cell=None, forced_status=Status.UNKNOWN, message="Cơ sở tri thức mâu thuẫn (INCONSISTENT).", is_inconsistent=True)`.
  - Nếu $KB_t$ nhất quán nhưng không có ô ép buộc (`AMBIGUOUS`): trả `HintResult(cell=None, forced_status=Status.UNKNOWN, relevant_clue_ids=<clue đã lật có liên quan tới ô chưa giải>, message="Không có nhân vật nào được suy ra chắc chắn từ các manh mối hiện có (AMBIGUOUS). Hãy xem lại các manh mối: ...", is_inconsistent=False)`.
  - Nếu có ít nhất một ô bị ép buộc: chọn `chosen_cell` đầu tiên theo thứ tự row-major.
- **Pha 2 — Trích lọc tập manh mối liên quan theo phạm vi liên kết (Scope-Based BFS):**
  - Mỗi manh mối đã lật có tập ô tham chiếu `scope(clue)` tính bằng `encoder.resolve_region`.
  - Xuất phát từ `chosen_cell`, thuật toán duyệt BFS qua các **ô chưa giải** nằm trong `scope` của các manh mối đã lật để thu thập mọi manh mối có phạm vi chứa trực tiếp `chosen_cell` hoặc nối gián tiếp với `chosen_cell` qua các ô chưa giải trung gian (đồng thời loại trừ các manh mối không liên quan trên vùng rời rạc). Chi phí hoàn toàn chỉ phụ thuộc $|\mathcal{R}_t|$ và **không** cần gọi thêm SAT.
  - Hướng mở rộng tiềm năng cho phiên bản sau là tối giản phản chứng (Deletion-Based MUS) để lọc thêm các manh mối dư thừa trong cùng thành phần liên thông.

### 4.2. Mã giả Chức năng Gợi ý

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

    // Pha 1: Chọn nhân vật bị ép buộc đầu tiên theo row-major
    unresolved <- ROW_MAJOR_SORT(public_state.unsolved_cells)
    chosen <- FIRST (cell, classifications[cell]) IN unresolved
              WHERE classifications[cell] IN {CRIMINAL, INNOCENT}

    IF chosen == NONE THEN
        relevant_ids <- CLUES_TOUCHING_UNSOLVED(public_state, encoder)
        RETURN HintResult(cell = NONE, forced_status = Status.UNKNOWN,
                          relevant_clue_ids = relevant_ids,
                          message = "... (AMBIGUOUS) ...",
                          is_inconsistent = FALSE)

    // Pha 2: BFS các clue liên kết với chosen.cell qua tập ô chưa giải
    relevant_ids <- COLLECT_LINKED_CLUES(chosen.cell, public_state, encoder)
    RETURN HintResult(cell = chosen.cell, forced_status = chosen.status,
                      relevant_clue_ids = relevant_ids,
                      message = FORMAT_VIETNAMESE_HINT(chosen, relevant_ids),
                      is_inconsistent = FALSE)
```

---

## 5. Kiểm tra Tính duy nhất của Nghiệm (Uniqueness Check — FAQ #9)

### 5.1. Nguyên lý Mệnh đề chặn (Blocking Clause)

Theo đề bài (AI - Project 2.pdf 2.2, 4.4) và (FAQ #9), mọi màn chơi hợp lệ giải được bắt buộc có **duy nhất một phép gán hoàn chỉnh** thỏa mãn toàn bộ tập manh mối (trừ trường hợp màn thử nghiệm kẹt/mơ hồ do nhóm chủ động tạo để minh họa theo FAQ #13). Để kiểm chứng điều này độc lập với quá trình chơi, TV4 xây dựng mô-đun `uniqueness.py` hoạt động trên **toàn bộ tập manh mối đầy đủ (complete clue set)** của puzzle (AI - Project 2.pdf 4.4; description.md 3.2; plan.md 2.4).

Quy trình gồm hai lần gọi SAT với kỹ thuật **mệnh đề chặn (blocking clause)**:
1. Dựng một `PublicState` tổng hợp gồm toàn bộ $N^2$ nhân vật ở trạng thái `UNKNOWN` (`is_revealed=False`), `proved_verdicts={}`, và `revealed_clues=tuple(clues)`, rồi gọi `encoder.encode_kb(synthetic_state)` để biên dịch trọn vẹn bộ manh mối thành công thức CNF $F$ trên tập biến chính $V_{\text{primary}} = \{C_1, \dots, C_n\}$ và tập biến phụ $V_{\text{aux}}$ (tránh trùng chỉ số biến phụ khi mã hóa từng clue riêng lẻ).
2. **Lần giải 1:** Gọi $\text{SAT}(F)$. Nếu `UNSAT` $\Rightarrow$ kết luận `UNSAT` (`is_unique=False`).
3. **Xây dựng mệnh đề chặn $B(M)$:** Nếu lần giải 1 trả về `SAT` kèm phép gán $M$, ta tạo đúng một mệnh đề chặn chỉ trên **các biến chính** (description.md 3.2; plan.md 2.4):
   $$B(M) = \bigvee_{i=1}^{n} \ell_i, \quad \text{với } \ell_i = \begin{cases} \neg C_i, & \text{nếu } M(C_i) = \text{True}, \\ C_i, & \text{nếu } M(C_i) = \text{False}. \end{cases}$$
   Mệnh đề $B(M)$ sai khi và chỉ khi mọi biến chính $C_i$ đều nhận đúng giá trị như trong $M$; do đó $F \wedge B(M)$ loại trừ chính xác phép gán nhân vật của $M$ và giữ nguyên mọi phép gán khác trên $V_{\text{primary}}$.
   - **Lưu ý quan trọng về biến phụ:** $B(M)$ **tuyệt đối không chứa các biến phụ $V_{\text{aux}}$**. Với các bộ mã hóa một chiều như **Sequential Counter (Sinz)** cho ràng buộc lực lượng (plan.md 2.2), giá trị của các biến phụ thường không bị xác định duy nhất bởi phép gán trên biến chính; do đó nếu đưa biến phụ vào $B(M)$, hai mô hình có cùng phân loại `CRIMINAL`/`INNOCENT` cho mọi nhân vật nhưng khác giá trị biến phụ sẽ bị báo nhầm là hai nghiệm khác nhau.
4. **Lần giải 2:** Gọi $\text{SAT}(F \wedge B(M))$ và kết luận theo ba trường hợp sau.

### 5.2. Diễn giải ba kết quả đầu ra (`UniquenessResult.solution_count_status`)

| Kết quả Lần giải 1: `SAT(F)` | Kết quả Lần giải 2: `SAT(F ∧ B(M))` | `solution_count_status` | Diễn giải đối với Puzzle |
| --- | --- | --- | --- |
| `UNSAT` | *(không gọi)* | `UNSAT` (`is_unique=False`) | Tập manh mối tự mâu thuẫn, không tồn tại phép gán nào thỏa mãn. Puzzle **không hợp lệ**. |
| `SAT` (nghiệm $M$) | `UNSAT` | `UNIQUE` (`is_unique=True`) | Không tồn tại phép gán nào khác $M$ trên tập biến chính thỏa mãn $F$. Puzzle có **nghiệm duy nhất hợp lệ** (đạt FAQ #9). |
| `SAT` (nghiệm $M$) | `SAT` (nghiệm $M'$) | `MULTIPLE` (`is_unique=False`) | Tồn tại ít nhất 2 nghiệm khác nhau $M \neq M'$ trên biến chính. Puzzle **mơ hồ**, không đạt chuẩn nghiệm duy nhất (FAQ #9), chỉ dùng được cho ca kiểm thử biên `Ambiguous`. |

### 5.3. Mã giả Kiểm tra Tính duy nhất

```text
ALGORITHM CheckUniqueness(all_clues, grid_size, encoder, solver):
    // Dựng PublicState tổng hợp với mọi ô UNKNOWN, proved_verdicts rỗng
    synthetic_state <- BUILD_SYNTHETIC_PUBLIC_STATE(grid_size, revealed_clues = all_clues)
    (F, _) <- encoder.encode_kb(synthetic_state)
    cell_vars <- [(cid, encoder.map_cell_to_var(cid, grid_size)) FOR cid IN all_cell_ids(grid_size)]

    // Lần giải 1: Tìm nghiệm đầu tiên M
    res_1 <- SAT_SOLVE(F, assumptions = [])
    IF NOT res_1.is_sat THEN
        RETURN UniquenessResult(is_unique = FALSE, solution_count_status = "UNSAT",
                                first_model = NONE, second_model = NONE,
                                metrics_first = res_1.metrics, metrics_second = NONE)

    first_model <- MAP_TO_STATUS(res_1.model, cell_vars)

    // Xây dựng mệnh đề chặn B(M) CHỈ trên tập biến chính 1..N^2
    blocking_clause <- (-v IF res_1.model[v] ELSE +v FOR (_, v) IN cell_vars)

    // Lần giải 2: Kiểm tra xem còn nghiệm nào khác M trên biến chính không
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

## 6. Phân tích Độ phức tạp (Complexity Analysis)

Đặt $n = N^2$ là tổng số ô trên bảng ($n \in \{9, 16, 25\}$ tương ứng với $N \in \{3, 4, 5\}$), $k_0 \ge 1$ là số thẻ mở sẵn ban đầu ($k_0 = 1$ ở game gốc, có thể tùy biến $k_0 \in \{2, 3, 4\}$ theo FAQ #8), và $u_t$ là số ô chưa giải tại bước $t$ ($1 \le u_t \le n - k_0 < n$).

### 6.1. Số lời gọi SAT trong một bước suy diễn $t$

1. **Không dùng Model Caching (Naive Entailment):**
   - Cần $1$ lời gọi để kiểm tra tính nhất quán $\text{SAT}(KB_t)$.
   - Với mỗi nhân vật $i \in U_t$: tốn $1$ lời gọi nếu $KB_t \wedge \neg C_i$ là `UNSAT` (`CRIMINAL`, dừng sớm) và $2$ lời gọi nếu là `INNOCENT` hoặc `UNKNOWN`.
   - Tổng số lời gọi SAT ở bước $t$ (khi phân loại toàn bộ $u_t$ nhân vật chưa giải theo AI - Project 2.pdf 4.4):
     $$\text{Calls}_{\text{naive}}(t) \le 1 + 2u_t \le 2n - 1 = O(n).$$
2. **Có dùng Model Caching:**
   - Lời gọi đầu tiên $\text{SAT}(KB_t)$ trả về mô hình $M_0$, lập tức cố định **đúng $1$ cực tính thỏa mãn** (`can_be_criminal` nếu $M_0(C_i) = \text{True}$, hoặc `can_be_innocent` nếu $M_0(C_i) = \text{False}$) cho **toàn bộ** $u_t$ nhân vật chưa giải.
   - Nhờ vậy, mỗi nhân vật $i \in U_t$ chỉ còn **tối đa $1$** truy vấn cần kiểm tra (thử cực tính ngược với $M_0(C_i)$).
   - Hơn nữa, mỗi mô hình $M'$ mới thu được khi một truy vấn ngược trả `SAT` có thể đồng thời xác nhận cực tính thứ hai cho nhiều nhân vật `UNKNOWN` khác, loại bỏ hoàn toàn các lời gọi SAT cho những nhân vật đó.
   - Tổng số lời gọi SAT ở bước $t$:
     $$\text{Calls}_{\text{cache}}(t) \le 1 + u_t \le n = O(n).$$
   - Như vậy, riêng về chặn trên trường hợp xấu nhất ở mỗi bước, Model Caching cắt giảm số lời gọi SAT từ $1 + 2u_t$ xuống còn tối đa $1 + u_t$ (giảm gần **50%**); ở các bước đầu khi đa số ô là `UNKNOWN`, tỷ lệ cắt giảm thực tế còn cao hơn.

### 6.2. Tổng số lời gọi SAT cho cả màn chơi và các tác vụ khác

Giả sử màn chơi giải hết hoàn toàn sau $T = n - k_0$ bước (với $u_t = T - t$ cho $t = 0, \dots, T-1$):

- **Không dùng Model Caching (xấu nhất):**
  $$\sum_{t=0}^{T-1} \bigl(1 + 2(T - t)\bigr) = T + T(T + 1) = T^2 + 2T = O(n^2).$$
- **Có dùng Model Caching (xấu nhất):**
  $$\sum_{t=0}^{T-1} \bigl(1 + (T - t)\bigr) = T + \frac{T(T + 1)}{2} = \frac{T^2 + 3T}{2} = O(n^2).$$
- **Uniqueness Check:** Luôn cố định đúng $1$ lời gọi (nếu `UNSAT`) hoặc $2$ lời gọi SAT (nếu `UNIQUE` hoặc `MULTIPLE`), tức $O(1)$ lời gọi SAT.
- **Hint:** Tốn tối đa $1 + u_t$ lời gọi cho Pha 1 (có Model Caching); nếu bật tối giản tập manh mối (Pha 2) sẽ tốn thêm tối đa $|\mathcal{R}_t| \le n - 1$ lời gọi SAT.
- **Chi phí mỗi lời gọi DPLL SAT:** Về mặt lý thuyết, SAT là bài toán NP-complete nên một lời gọi DPLL có độ phức tạp thời gian trường hợp xấu nhất là $O\!\left(2^{|V|} \cdot |F|\right)$, trong đó $V = V_{\text{primary}} \cup V_{\text{aux}}$ là tập toàn bộ biến (kể cả biến chính và biến phụ sinh bởi chiến lược mã hóa Direct hay Sequential Counter/Sinz của TV2 — plan.md 2.2) và $|F|$ là kích thước công thức (tổng số literal trong các mệnh đề). Tuy nhiên, trong miền $n \le 25$, cấu trúc cục bộ của manh mối kết hợp với Unit Propagation và heuristic chọn biến (MOMs/JW của TV3) giúp không gian tìm kiếm thực tế được cắt tỉa mạnh.

### 6.3. Bảng tổng hợp chặn trên lý thuyết và khung đối chiếu thực nghiệm

Bảng dưới tổng hợp chặn trên số lời gọi SAT cho toàn màn chơi với giả định game gốc $k_0 = 1$ thẻ mở sẵn (khi tăng $k_0 \in \{2, 3, 4\}$ theo FAQ #8, số bước $T = n - k_0$ giảm tương ứng):

| Kích thước lưới | $n = N^2$ | Số bước tối đa $T$ ($k_0 = 1$) | Chặn trên tổng lời gọi SAT (Không cache) | Chặn trên tổng lời gọi SAT (Có Model Caching) | Tổng lời gọi SAT thực tế (Không cache) | Tổng lời gọi SAT thực tế (Có Model Caching) | Thời gian chạy thực tế |
| --- | --- | --- | --- | --- | --- | --- | --- |
| $3 \times 3$ | $9$ | $8$ | $80$ | $44$ | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] |
| $4 \times 4$ | $16$ | $15$ | $255$ | $135$ | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] |
| $5 \times 5$ | $25$ | $24$ | $624$ | $324$ | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] | [chờ kết quả benchmark GĐ 3B] |

*(So sánh đầy đủ trên bộ 10 màn chuẩn `4×3×3`, `4×4×4`, `2×5×5` — cùng tùy chọn 3 màn `extensions/` và 2 màn `edge_cases/` — qua các cấu hình Direct/Sinz và DPLL heuristics sẽ được trình bày trong mục Experiments — [chờ kết quả benchmark GĐ 3B].)*

---

## 7. Trạng thái đồng bộ với `core/contracts/` và `docs/tv4_agent_conventions.md`

Toàn bộ các điểm mở trước GĐ 0 đã được chốt trong `Source/core/contracts/models.py`, `Source/core/contracts/interfaces.py` và `docs/tv4_agent_conventions.md`:

| STT | Hạng mục liên quan | Quyết định đã chốt |
| --- | --- | --- |
| 1 | `DeductionStep` (`models.py`) | Chốt các trường `step_number`, `active_clue_ids`, `sat_queries` (`tuple[SATQueryLog, ...]`), `cell`, `verdict`, `verdict_code`, `revealed_clue`, `cnf_stats`. |
| 2 | `HintResult` (`models.py`) & UX Hint | Chốt `HintResult(cell, forced_status, relevant_clue_ids, message, is_inconsistent)` với thông điệp tiếng Việt. |
| 3 | `UniquenessResult` (`models.py`) | Chốt `is_unique`, `solution_count_status` (`"UNIQUE" | "UNSAT" | "MULTIPLE"`), `first_model`, `second_model`, `metrics_first`, `metrics_second`; mã hóa bằng `encode_kb` trên `PublicState` tổng hợp. |
| 4 | Animation `run_auto_solve` (FAQ #4) | Dùng callback `on_step: Callable[[DeductionStep], None] | None = None`, gọi cho cả bước kết thúc và bọc bảo vệ ngoại lệ; trả về `list[DeductionStep]` và lưu `last_outcome`. |
| 5 | Trạng thái dừng khi kẹt | Dùng `AutoSolveOutcome` (`SOLVED`, `AMBIGUOUS`, `INCONSISTENT`) và `outcome_of(steps, final_state)`; bước kết thúc `AMBIGUOUS` dùng `VerdictCode.NOT_PROVABLE`, `INCONSISTENT` dùng `VerdictCode.INCONSISTENT`. |
| 6 | `assumptions` & `model` (`ISATSolver`) | `assumptions: Sequence[int] = ()`; `SATResult.model` hoàn thiện mọi biến `1..num_vars` trong `DPLLSolver`. |
| 7 | Phạm vi phân loại & chọn nước đi | Phân loại toàn bộ ô chưa mở theo row-major (`classify_all`) và chọn ô bị ép buộc đầu tiên theo thứ tự row-major ở mỗi bước. |
| 8 | Đầu vào `check_uniqueness` | Kiểm tra trên toàn bộ tập `clues` qua `PublicState` tổng hợp với `proved_verdicts` rỗng. |
| 9 | Đếm SAT & `KBCache` | Đệm theo khóa KB (LRU ≤ 8) tách `deduction_sat_calls` và `validation_sat_calls` (`== 0` khi `run_auto_solve`); benchmark chỉ lấy truy vấn `cached=False` trong `DeductionStep.sat_queries`. |
