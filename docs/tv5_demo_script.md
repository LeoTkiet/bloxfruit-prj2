# Kịch bản Quay Video Demo — Project 2: Griductive Solver (TV5)

> **Thời lượng mục tiêu:** 6–8 phút (yêu cầu: 5–10 phút)  
> **Thang điểm:** 10 điểm (5đ Giao diện GUI + 5đ Các chức năng đã cài đặt)  
> **Yêu cầu bắt buộc:** Có thuyết minh hoặc phụ đề (Tiếng Việt / Tiếng Anh); đăng **Google Drive** ở chế độ công khai (*Anyone with the link*), kiểm tra bằng cửa sổ ẩn danh (**Incognito**); **TUYỆT ĐỐI KHÔNG dùng YouTube**.

---

## Timeline Kịch bản Chi tiết

### Phần 1 — Giới thiệu & Khởi động ứng dụng (0:00 – 0:45)
- Giới thiệu tên đề tài **Project 2: Griductive Solver**, nguyên tắc **No-Guess Rule** và kiến trúc phân tách **Game Engine (Hidden World)** ↔ **Logic Agent (Public World)** ↔ **GUI**.
- **Liệt kê ngắn các thuật toán lõi đã cài đặt (theo FAQ #14):**
  - **Mã hóa CNF tự động (TV2):** hỗ trợ 6 mẫu manh mối lõi + phần mở rộng (`PARITY` qua chuỗi XOR Tseitin, `COMPARE_COUNTS`, vùng nâng cao), kèm 2 chiến lược mã hóa lực lượng **Direct Combinatorial** và **Sequential Counter (Sinz)**.
  - **Bộ giải DPLL SAT thuần Python (TV3):** Unit Propagation, Conflict Detection, phân nhánh đệ quy/quay lui tất định, kết hợp **Pure-Literal Elimination** và các heuristic chọn biến (**Lexicographic**, **MOMs**, **Jeroslow-Wang**).
  - **Tác tử Suy diễn Logic (TV4):** kiểm tra **Entailment via Refutation** ($KB_t \land \neg C_i$, $KB_t \land C_i$), tối ưu **Model Caching** & KB cache, kiểm chứng tính duy nhất bằng **Blocking Clause (Uniqueness Check)** và gợi ý tối giản (`Hint`).
- Mở terminal trong thư mục `Source/`, chạy lệnh `python main.py --strict` để chứng minh hệ thống lắp ghép đủ 5 module thật và khởi động mượt, không lỗi.

### Phần 2 — Trình diễn Giao diện Đồ họa GUI (0:45 – 2:15) *[5 điểm GUI]*
- Giới thiệu bố cục 2 cột:
  - **Lưới chơi $N \times N$:** tọa độ cột `A..E`, hàng `1..5`, tên nhân vật, nghề nghiệp, màu phân biệt rõ `CRIMINAL` (đỏ), `INNOCENT` (xanh lá), thẻ úp `UNSOLVED` (mặt lưng tối, không lộ clue ẩn).
  - **Thanh công cụ:** chọn nhanh puzzle + 4 nút chuẩn **Load**, **Restart**, **Hint**, **Auto Solve** + tốc độ phát + **Uniqueness**.
  - **Trace Panel:** bảng `Deduction Trace`, `Step Inspector`, và 8 ô thống kê trực tiếp (Solved, Primary+Aux Vars, CNF Clauses, SAT Calls, Decisions, Propagations, Backtracks, Runtime).
- **Trình diễn Highlight manh mối:** click vào một thẻ đã lật ngửa (ví dụ `A1` trên `3x3_01_precinct_basics.json`) -> các ô tham chiếu (`B1`, `C2`) sáng viền hổ phách + nhãn `REF`. Click lại để tắt.

### Phần 3 — Chơi Thủ công & Phản hồi Lỗi An toàn (2:15 – 4:00) *[Chức năng]*
- **Thử phán quyết `NOT_PROVABLE`:** chọn một ô chưa đủ dữ kiện (ví dụ `C1`) và bấm `Mark CRIMINAL` -> banner vàng cam hiện **NOT PROVABLE (No Guessing Allowed)**, thẻ vẫn úp, không lộ manh mối.
- **Thử phán quyết `CONTRADICTED`:** chọn một ô ép buộc là `CRIMINAL` (ví dụ `B1`) nhưng cố tình bấm `Mark INNOCENT` -> banner đỏ hiện **CONTRADICTED**, thẻ vẫn úp, không lộ manh mối.
- **Sử dụng nút `Hint`:** bấm `Hint` -> thẻ mục tiêu bật viền tím `HINT`, thẻ manh mối liên quan bật viền `CLUE`, banner giải thích rõ nhân vật đang bị ép buộc hoàn toàn từ tri thức công khai.
- **Gán nhãn đúng (`ACCEPTED`):** bấm `Mark CRIMINAL` cho ô được gợi ý -> thẻ lật ngửa, hiện màu đỏ và tiết lộ manh mối mới, Trace Panel cập nhật ngay.
- Bấm **Restart** để đưa màn chơi về bước 0.

### Phần 4 — Trình diễn Auto Solve trên Nhiều Màn chơi & Stress Case (4:00 – 6:30) *[Chức năng]*
1. **Màn `3×3` (`3x3_01_precinct_basics.json`):** chọn tốc độ `Slow (900 ms)` hoặc `Normal (450 ms)` -> bấm **Auto Solve** -> quan sát từng thẻ lật theo thứ tự suy diễn logic, Trace Panel ghi nhận từng bước & chỉ số SAT -> kết thúc `SOLVED`. Click một dòng trong Trace để mở `Step Inspector`. Bấm **Uniqueness** chứng minh `UNIQUE ✓`.
2. **Màn `4×4` có Extension (`extensions/ext_4x4_02_parity_intersections.json`):** dùng nút **Load** chọn file JSON -> cho thấy giao diện tự đổi sang lưới `4×4`, hiển thị các manh mối nâng cao (`PARITY`, `INTERSECTION`) -> chạy **Auto Solve** -> `SOLVED`.
3. **Stress Case `5×5` (`5x5/5x5_01_grand_precinct.json`):** nạp màn `5×5`, cho thấy lưới 25 thẻ hiển thị gọn gàng -> chọn tốc độ `Instant (0 ms)` -> chạy **Auto Solve** -> `SOLVED`, chỉ rõ thời gian chạy và số lần gọi SAT.

### Phần 5 — Kiểm thử Biên: Không đoán mò & Phát hiện Mâu thuẫn (6:30 – 7:30)
1. Nạp `edge_cases/edge_3x3_01_ambiguous.json` -> bấm **Auto Solve** -> Agent giải các ô ép buộc được rồi **dừng an toàn ở trạng thái `AMBIGUOUS`** (tuyệt đối không đoán mò).
2. Nạp `edge_cases/edge_3x3_02_inconsistent.json` -> bấm **Auto Solve** -> hệ thống phát hiện ngay `INCONSISTENT` (KB UNSAT) và cảnh báo rõ ràng.

---

## Checklist Trước khi Nộp Video
- [ ] Thời lượng video nằm trong khoảng **5–10 phút**.
- [ ] Âm thanh thuyết minh rõ ràng (hoặc có phụ đề tiếng Việt/Anh dễ đọc).
- [ ] Độ phân giải tối thiểu **1080p**, đọc rõ chữ trên thẻ và Trace Panel.
- [ ] Đã tải lên **Google Drive** (không dùng YouTube) và bật chia sẻ *Anyone with the link (Viewer)*.
- [ ] Đã tự kiểm tra mở link trên trình duyệt **ẩn danh (Incognito)** xem phát video bình thường.
- [ ] Đã dán link Google Drive vào trang đầu / mục phụ lục của `Report.pdf`.
