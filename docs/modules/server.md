# Module: Server & Infrastructure (`server/app.py`, `server/serve.py`, `server/routes/*`)

## 1. Mục đích (Purpose)
Chịu trách nhiệm khởi tạo ứng dụng web ASGI (FastAPI), phục vụ các API REST, quản lý các tác vụ nền (lifespan background tasks), đóng gói tài nguyên tĩnh từ `play/` sang `public/`, và chạy Uvicorn server.

---

## 2. Trách nhiệm (Responsibilities)
- **FastAPI App Composition (`server/app.py`):**
  - Tích hợp các router: `/api/config`, `/api/rooms`, `/api/phrases`, `/api/presence`, `/api/reload`.
  - Đăng ký route WebSocket: `app.add_api_websocket_route("/ws", room_socket)`.
  - Mount thư mục tĩnh `public/` tại `/` với middleware chống cache (`NoCacheStatic`).
- **Background Sweeper (`lifespan`):**
  - Chạy vòng lặp vô hạn `asyncio.sleep(10)` để gọi `HUB.sweep_stale()`.
  - Tự động broadcast thông báo nếu có phòng bị hủy hoặc người chơi ngắt kết nối quá lâu.
- **Server Runner (`server/serve.py`):**
  - Tự động gọi `build_play()` trước khi mở server để đồng bộ frontend.
  - Lắng nghe trên `host` (mặc định `0.0.0.0`) và `port` (mặc định `18765` hoặc `$PORT` từ Render).
  - Tích hợp file watcher reload nóng cho frontend (`play/*.js`, `play/*.css`).
  - Quản lý Cloudflare Quick Tunnel (`cloudflared`) nếu người dùng truyền cờ `--tunnel`.

---

## 3. Danh mục API Endpoints

| Method | Path | Quyền | Mục đích |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Public | Phục vụ file `index.html` của game |
| `GET` | `/api/config` | Public | Lấy trạng thái server, giới hạn phòng, chế độ debug |
| `POST` | `/api/rooms` | Public | Tạo phòng mới |
| `POST` | `/api/rooms/{id}/join` | Public | Tham gia phòng chơi |
| `GET` | `/api/rooms/{id}` | Public | Lấy thông tin phòng |
| `GET` | `/api/phrases` | Debug only | Tìm kiếm từ vựng trong SQLite |
| `POST` | `/api/phrases` | Debug only | Thêm từ mới vào database |
| `DELETE` | `/api/phrases` | Debug only | Xóa từ vựng khỏi database |
| `GET` | `/api/presence` | Public | Thống kê số lượng người chơi đang online |
| `GET` | `/api/reload` | Dev only | Server-Sent Events (SSE) để trình duyệt tự F5 khi sửa code |

---

## 4. Quản lý tiến trình & Dừng server (`server/runctl.py`)
- Ghi trạng thái tiến trình (PID, URL, cổng) vào file `run/status.json` và `run/LINK.txt`.
- Hàm `stop_run()` dùng để tắt các tiến trình cũ khi chạy lại server. Bọc an toàn các lệnh hệ thống để tương thích tốt với container Linux tối giản (như Render).
