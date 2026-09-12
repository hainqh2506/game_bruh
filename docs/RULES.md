# Engineering & Coding Rules — Đoán Chữ Unlimited

Tài liệu này định nghĩa các quy chuẩn kỹ thuật bắt buộc mà mọi nhà phát triển và coding agent phải tuân thủ khi làm việc trên codebase này.

---

## 1. Cấu trúc mã nguồn & Trách nhiệm (Code Structure)

1. **Phân định ranh giới nghiêm ngặt:**
   - **`game/`** là Domain Logic thuần túy: **TUYỆT ĐỐI KHÔNG** import FastAPI, HTTP Request/Response, WebSocket connection hay bất kỳ transport layer nào vào `game/`.
   - **`server/`** là Transport & Infrastructure: Nhận request/WS từ bên ngoài, gọi logic từ `game/` hoặc `db.py`, sau đó serialize payload trả về cho client.
   - **`play/`** là Frontend nguyên bản: Sử dụng Vanilla JS và CSS thuần, không thêm các framework nặng (React/Vue) hoặc build tools phức tạp (Webpack/Vite) trừ khi có yêu cầu kiến trúc mới rõ ràng.
2. **Không tạo tầng trừu tượng thừa (No Unnecessary Layers):**
   - Tránh tạo interface/class giả lập khi chỉ có duy nhất một implementation cụ thể.
   - Ưu tiên dataclass, dict chuẩn và hàm thuần túy (pure functions).
3. **Quy ước đặt tên (Naming Conventions):**
   - File và thư mục Python: `snake_case.py`.
   - File JavaScript/CSS: `kebab-case.js` hoặc `camelCase.js` theo cấu trúc hiện tại của `play/`.
   - Hằng số cấu hình / protocol: `UPPER_CASE` (ví dụ: `Client.GUESS`, `Server.ROOM`).

---

## 2. Quy chuẩn API & WebSocket

1. **Bảo mật đáp án (Zero Solution Leak):**
   - Trong phòng chơi nhiều người, trường `solution` / `answer` **TUYỆT ĐỐI KHÔNG** được gửi trong payload public cho người chơi chưa giải xong hoặc chưa hết 6 lượt đoán.
   - Payload broadcast (`Server.PEER_UPDATE`) chỉ được gửi: `id`, `name`, `attempts`, `solved`, `disconnected`. Không bao giờ gửi nội dung từ người khác đã đoán.
2. **Xử lý lỗi API (Error Handling):**
   - API endpoints phải trả về format JSON nhất quán: `{ "error": "Mô tả lỗi tiếng Việt có dấu" }` với HTTP status code phù hợp (`400`, `403`, `404`, `429`).
   - Sử dụng helper `json_error(msg, status_code)` từ [`server/httputil.py`](file:///d:/game_bruh/server/httputil.py).
3. **Giao thức WebSocket (`/ws`):**
   - Mọi command mới giữa client và server phải được khai báo hằng số trong [`game/protocol.py`](file:///d:/game_bruh/game/protocol.py) (`Client.*` và `Server.*`).
   - Đăng ký handler tương ứng trong từ điển `HANDLERS` tại [`server/ws.py`](file:///d:/game_bruh/server/ws.py).

---

## 3. Quy chuẩn Cơ sở dữ liệu (SQLite & Warehouse)

1. **Quyền truy cập SQLite:**
   - Mọi truy vấn database phải đi qua module [`db.py`](file:///d:/game_bruh/db.py). Không viết câu lệnh raw SQL rải rác trong routes hoặc views.
2. **Pools:**
   - Database duy trì đúng 3 pool hợp lệ: `'play'` (từ dùng để giải đố), `'raw'` (từ thô chờ duyệt), `'rejected'` (từ thô tục/đã loại).
   - Khi chỉnh sửa dữ liệu, phải đảm bảo tính toàn vẹn của chỉ mục (`idx_phrases_phrase`, `idx_phrases_pool`).
3. **An toàn tiến trình (Thread/Process Safety):**
   - SQLite mở kết nối theo từng luồng hoặc dùng connection timeout ngắn hạn, tránh giữ khóa ghi (write lock) lâu.

---

## 4. Quy chuẩn Bất đồng bộ & Đồng thời (Concurrency Rules)

1. **Bộ nhớ RAM phòng chơi:**
   - [`game/room.py`](file:///d:/game_bruh/game/room.py) (`RoomHub`) sử dụng `threading.RLock()` để bảo vệ trạng thái phòng. Mọi thao tác thêm/xóa/đọc/ghi session phải nằm trong khối `with self._lock:`.
2. **Event Bus WebSocket:**
   - [`game/ws.py`](file:///d:/game_bruh/game/ws.py) (`Broadcaster`) sử dụng `asyncio.Lock()` để quản lý danh sách kết nối.
   - Không được gọi blocking I/O (như `time.sleep` hay đọc ghi file lớn) trong các hàm `async def` của WebSocket loop. Dùng `asyncio.sleep` khi cần delay.
3. **Dọn dẹp tài nguyên (Resource Cleanup):**
   - Khi client ngắt kết nối (`WebSocketDisconnect`), bắt buộc phải gọi `BUS.unregister(room.id, websocket)` và cập nhật trạng thái `disconnected = True` để giải phóng bộ nhớ.

---

## 5. Quy chuẩn Kiểm thử (Testing Rules)

1. **Bộ test hiện có:**
   - **Pytest:** `uv run pytest` kiểm tra toàn bộ API, Room lifecycle, Phrases normalization và Game Engine.
   - **Node.js Test:** `node --test tests/marks.test.js` kiểm tra thuật toán tô màu và phân tách dấu tiếng Việt ở phía client.
2. **Nguyên tắc khi viết tính năng mới:**
   - Mọi tính năng hoặc logic sửa đổi trong `game/` phải có unit test tương ứng trong `tests/test_*.py`.
   - Không được merge hoặc commit nếu có bất kỳ test nào bị fail (`100% pass rate`).

---

## 6. Quy chuẩn Bắt buộc cho Coding Agent (Mandatory Agent Rules)

1. **Đọc tài liệu trước khi code:** Phải kiểm tra [`docs/README.md`](README.md), [`docs/RULES.md`](RULES.md), [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) trước khi tiến hành viết code.
2. **Tận dụng trừu tượng sẵn có:** Tuyệt đối không tạo lại class mới nếu module đã có sẵn class phục vụ mục đích đó (ví dụ: tái sử dụng `Player`, `RoomSession`, `BUS`).
3. **Không refactor không có lý do:** Giữ nguyên các chức năng, hàm tiện ích hiện có nếu tác vụ không yêu cầu thay đổi chúng.
4. **Bảo tồn hành vi hiện có:** Không làm vỡ các tính năng cũ (như chơi đơn, Cloudflare tunnel, static build).
5. **Cập nhật tài liệu sau khi hoàn thành:** Mọi thay đổi về kiến trúc, quyết định kỹ thuật hay protocol đều phải được cập nhật vào `docs/` tương ứng.
6. **Ghi nhận quyết định kiến trúc:** Nếu thay đổi lớn về cách tổ chức hệ thống, phải ghi nhận vào [`docs/DECISIONS.md`](DECISIONS.md).
