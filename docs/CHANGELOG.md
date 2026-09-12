# Changelog — Đoán Chữ Unlimited

Tất cả các thay đổi kỹ thuật đáng chú ý của dự án sẽ được ghi nhận tại đây theo định dạng Keep a Changelog.

## 2026-09-13

### Added
- Chế độ thi đấu phòng nhiều người Nhiều vòng (Multi-round Match):
  - Tùy chọn số câu (1, 3, 5, 10 câu - mặc định 5) và thời gian (Không giới hạn - mặc định, 120s, 180s, 300s) ngay khi tạo phòng.
  - Thang điểm theo số lượt đoán: lần 1 được 100đ, lần 2: 50đ, lần 3: 40đ, lần 4: 30đ, lần 5: 20đ, lần 6: 10đ, hỏng: 0đ.
  - Cơ chế tie-breaker khi bằng điểm: người có tổng thời gian giải ít hơn xếp trên.
  - Trạng thái `round_summary` (nghỉ 5s giữa 2 câu) và đếm ngược tự chuyển câu tiếp theo.
  - Màn hình vinh danh chung cuộc (Victory Podium Top 1 🥇, Top 2 🥈, Top 3 🥉).
  - Lệnh WebSocket mới: `Client.NEXT_ROUND` và `Server.ROUND_FINISHED`.
- Ghi nhận quyết định kiến trúc ADR-005 vào `docs/DECISIONS.md`.
- Ghi nhận tài liệu thiết kế chi tiết tại `docs/changes/2026-09-13-multi-round-match-scoring.md`.

---

## 2026-09-12 (Tối)

### Added
- Khởi tạo quy chuẩn tài liệu kỹ thuật tự duy trì theo chuẩn Agent Harness tại thư mục `docs/`.
- Tài liệu hóa toàn bộ kiến trúc, ranh giới runtime, quy tắc kỹ thuật và các quyết định kiến trúc (ADR-001 đến ADR-004).
- Tạo nhánh `develop` để chuẩn bị phát triển tính năng Trận đấu nhiều vòng (Multi-round Match) và tính điểm xếp hạng.

### Changed
- Cập nhật [`main.py`](file:///d:/game_bruh/main.py) và [`server/serve.py`](file:///d:/game_bruh/server/serve.py) hỗ trợ tham số `--host` (mặc định `0.0.0.0` hoặc biến môi trường `HOST`) phục vụ triển khai trên Render.
- Tự động chuẩn hóa hiển thị URL local `127.0.0.1:{port}` khi host là `0.0.0.0` để tương thích tốt với trình duyệt desktop.

### Fixed
- Bọc các lệnh gọi hệ thống `fuser` và `pkill` trong khối `try ... except OSError: pass` tại [`server/runctl.py`](file:///d:/game_bruh/server/runctl.py) để tránh lỗi `FileNotFoundError` khi chạy trên container Linux tối giản của Render.

---

## 2026-09-12 (Sáng & Chiều)

### Added
- Chế độ phòng chơi nhiều người qua WebSocket thời gian thực (`/ws`):
  - Lobby tạo phòng mã 4 ký tự ngẫu nhiên.
  - Quản lý phiên phòng in-memory (`RoomHub`, `RoomSession`, `Player`) có khóa `threading.RLock`.
  - Bộ phát tán sự kiện in-memory `BUS` (`Broadcaster`) theo phòng.
  - Cơ chế quét phòng hết hạn tự động mỗi 10 giây qua background task trong FastAPI lifespan.
- Cơ chế bảo vệ giới hạn tài nguyên máy chủ (`Limits`):
  - Khống chế số lượng phòng (`DOANCHU_MAX_ROOMS`), số người mỗi phòng (`DOANCHU_MAX_PLAYERS`), tổng người chơi (`DOANCHU_MAX_PARTY`) và slot chơi đơn (`DOANCHU_MAX_SOLO`).

### Architecture
- Thiết kế hệ thống phòng chơi in-memory không phụ thuộc cơ sở dữ liệu ngoài (như Redis), chạy trọn vẹn trong một tiến trình FastAPI/Uvicorn duy nhất.

---

## 2026-09-11

### Added
- Kho từ vựng SQLite (`data/words.sqlite`) phân chia 3 pool: `play` (~7.3k từ thông dụng Viet11K), `raw` (~59k từ thô) và `rejected` (từ thô tục/đã loại).
- Thuật toán `mark_guess` so khớp dấu tiếng Việt (xanh lá, vàng, xanh dương, xám) tương đương logic client `play/marks.js`.
- Giao diện chơi đơn (Solo Play) tại `play/` với bàn phím ảo, hỗ trợ mò nguyên âm không cần từ có nghĩa.
- Tích hợp Cloudflare Quick Tunnel (`cloudflared`) tự động lấy link public không cần tài khoản.
