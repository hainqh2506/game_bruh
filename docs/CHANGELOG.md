# Changelog — Đoán Chữ Unlimited

Tất cả các thay đổi kỹ thuật đáng chú ý của dự án sẽ được ghi nhận tại đây theo định dạng Keep a Changelog.

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
