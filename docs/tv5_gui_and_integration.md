# Báo cáo Thành phần TV5 — Giao diện GUI, Tích hợp Hệ thống (E2E) & Đóng gói

> Tài liệu đóng góp của Thành viên 5 (TV5) để tổng hợp vào `Report.pdf` của Project 2: Griductive Solver (CSC14003).

---

## 1. Kiến trúc Giao diện Đồ họa (GUI) & Cô lập Dữ liệu Ẩn

Giao diện desktop được xây dựng bằng **Python + PyQt6** theo kiến trúc **Contract-First (Ports & Adapters)** và **MVC/Observer**:

- **Tách biệt tuyệt đối Hidden World vs. Public World:** `MainWindow`, `BoardWidget`, `CharacterCardWidget`, và `TracePanel` **chỉ** nhận đối tượng bất biến `PublicState` và `CharacterPublicInfo` thông qua hai giao diện trừu tượng `IGameEngine` và `ILogicAgent`. Mọi thẻ úp (`is_revealed = False`) không hề nhận trạng thái ẩn hay manh mối ẩn tại tầng GUI.
- **Cấu trúc module & phong cách thiết kế ("The Archival Case Board" — Detective Board ấm áp cổ điển) trong `Source/gui/`:**
  - `theme.py`: Bảng màu ấm đồng bộ theo ánh đèn bàn thám tử (gỗ óc chó `#2A1F19`, mặt bảng bần `#DCCEB7`, giấy kem lưu trữ `#FAF5EB`, đỏ sáp niêm phong `#9E2A2B` cho `CRIMINAL`, xanh xô thơm `#2F5C45` cho `INNOCENT`, nâu sẫm `#3A2D25` cho hồ sơ úp, đồng thau `#C58A2B`, mực Phổ `#27586E`, và tím mận cổ điển `#6F3D73` cho `Hint`), định nghĩa chuẩn hóa kèm `PRODUCT.md` và `DESIGN.md`.
  - `clue_formatter.py`: Tự động hiển thị manh mối dạng ngôn ngữ tự nhiên (ưu tiên `clue.text`, tự sinh cho đủ 6 mẫu cơ bản + `PARITY` + `COMPARE_COUNTS` và 9 loại vùng).
  - `card_widget.py` & `board_widget.py`: Bảng lưới $N \times N$ ($N \in \{3, 4, 5\}$) có 3 mức mật độ (`normal` / `medium` / `compact`), thẻ hồ sơ đổ bóng mềm gắn đinh ghim đồng/sáp vẽ trực tiếp bằng `QPainter`, cùng lớp phủ `_DetectiveStringOverlay` trong suốt với chuột vẽ dây điều tra cong mềm nối từ ghim của manh mối đang chọn tới các ô tham chiếu (hoặc nối các manh mối gợi ý tới ô mục tiêu khi bấm `Hint`).
  - `trace_panel.py`: Sổ nhật ký suy diễn (**Case Ledger**) gồm dải thông số kẻ chỉ liền khối (Solved, Primary+Aux Vars, CNF Clauses, SAT Calls, Decisions, Propagations, Backtracks, SAT Time), bảng `Deduction Trace`, bộ soi `Step Evidence & SAT Query Log` và tem kiểm tra **Uniqueness**.
  - `worker.py`: Luồng nền `AutoSolveWorker(QThread)` thực thi `agent.run_auto_solve(engine, on_step=...)` (và tự động dùng proxy `_StepTrackingEngineProxy` ghi snapshot trung gian nếu agent chưa hỗ trợ `on_step`), giúp giao diện phát hiệu ứng lật từng thẻ mượt mà ở 3 tốc độ (`Normal 450 ms`, `Slow 900 ms`, `Instant 0 ms`) kèm nút `Finish Fast`.
  - `main_window.py`: Thanh masthead gỗ óc chó gồm đủ 4 nút bắt buộc (**Load**, **Restart**, **Hint**, **Auto Solve**), danh sách chọn nhanh bộ màn chơi JSON, nút kiểm tra **Uniqueness**, banner phản hồi phân biệt rõ 4 mã `ACCEPTED` / `NOT_PROVABLE` / `CONTRADICTED` / `INCONSISTENT` cùng kết cục `SOLVED` / `AMBIGUOUS`.

---

## 2. Lắp ghép Hệ thống (Dependency Injection Wiring trong `Source/main.py`)

Toàn bộ việc khởi tạo lớp cụ thể được tập trung duy nhất tại hàm `wire_system()` trong `Source/main.py`:

```text
CNFEncoder (TV2) ──┐
                   ├──► DeductiveLogicAgent (TV4) ──┐
DPLLSolver (TV3) ──┘                                ├──► MainWindow (TV5)
                                                    │
GameEngine (TV1) ◄── (inject logic_agent & encoder) ┘
```

- Khi người dùng bấm **Load** màn chơi mới hoặc **Restart**, `MainWindow` tự động gọi `agent.clear_cache()` và `agent.reset_stats()` (theo đúng quy ước TV4) để số liệu SAT và bộ đệm KB không bị nhiễu giữa các phiên chơi.
- Hỗ trợ các tham số dòng lệnh (`--puzzle`, `--encoding direct|sinz`, `--heuristic lexicographic|moms|jw`, `--no-pure-literal`, `--no-model-cache`, `--strict`) phục vụ kiểm thử nhanh các cấu hình khác nhau ngay trên GUI.

---

## 3. Kiểm thử Độc lập & Kiểm thử Tích hợp (Unit & E2E)

Bộ kiểm thử tự động trong `Source/tests/test_gui/` sử dụng `pytest` + `pytest-qt` chạy hoàn toàn tự động (kể cả môi trường headless với `QT_QPA_PLATFORM=offscreen`):

1. **Kiểm thử bộ định dạng manh mối (`test_clue_formatter.py`):** bao phủ 6 mẫu manh mối lõi, `PARITY`, `COMPARE_COUNTS` và 9 loại `RegionType`.
2. **Kiểm thử đơn vị GUI độc lập (`test_gui_unit.py` với `MockGameEngine` & `MockGuiLogicAgent`):**
   - Xác minh thẻ úp không chứa bất kỳ văn bản manh mối ẩn hay nhãn ẩn nào.
   - Xác minh click thẻ ngửa gọi `get_highlighted_cells()` và bật đúng tập ô tham chiếu.
   - Xác minh gán nhãn thủ công phân biệt chính xác `ACCEPTED`, `NOT_PROVABLE`, `CONTRADICTED`, `INCONSISTENT` và không lật thẻ khi bị từ chối.
   - Xác minh 4 nút `Load`, `Restart`, `Hint`, `Auto Solve` (đủ 3 kết cục `SOLVED`, `AMBIGUOUS`, `INCONSISTENT`) và `Uniqueness`.
3. **Kiểm thử tích hợp (`test_gui_engine_integration.py`):** ghép `MainWindow` với `GameEngine` thật (TV1) trên bộ màn chơi JSON `3×3`, `4×4`, `5×5`, `edge_3x3_01_ambiguous.json` và `edge_3x3_02_inconsistent.json`.

---

## 4. Khung Biên tập Tổng hợp `Report.pdf` (6 phần bắt buộc)

Khi tổng hợp cuối kỳ từ 5 thành viên, TV5 biên tập thống nhất `Report.pdf` theo đúng 6 mục của đề bài:
1. **Kế hoạch dự án & Phân công công việc** (bảng tỷ lệ % đóng góp 5 thành viên + minh chứng Git PR/Commit).
2. **Hình thức hóa bài toán** (từ `docs/tv1_problem_formulation.md`).
3. **Mã hóa CNF & Bộ đánh giá trực tiếp** (từ `docs/tv2_cnf_encoding.md`, đủ dẫn xuất toán học cho ≥1 clue nhị phân & ≥1 clue đếm).
4. **Các thuật toán lõi** (DPLL từ `docs/tv3_dpll_solver.md`; Entailment, Uniqueness, Deduction Loop từ `docs/report_tv4_algorithms.md`; GUI & DI Wiring từ mục 1–2 ở trên).
5. **Kết quả thực nghiệm & Đánh giá** (từ `docs/report_tv4_experiments.md`, đủ 6 nhóm chỉ số, bảng, biểu đồ, báo cáo trung thực timeout/failure).
6. **Tài liệu tham khảo & Phụ lục sử dụng AI tạo sinh (LLMs)** + **Liên kết Google Drive Video Demo công khai**.
