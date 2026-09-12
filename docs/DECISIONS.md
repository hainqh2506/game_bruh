# Architecture Decision Records (ADR) — Đoán Chữ Unlimited

Sổ ghi chép các quyết định kiến trúc quan trọng của dự án. Mọi thay đổi kiến trúc mang tính bước ngoặt phải được ghi nhận tại đây theo mẫu chuẩn.

---

## ADR-001: In-Memory State cho Phòng chơi Nhiều người (Multiplayer Rooms)

- **Ngày:** 2026-09-12
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Trò chơi cần hỗ trợ tính năng phòng chơi theo nhóm (Party Mode) cho 2–8 người cùng đoán chữ qua WebSocket. Các giải pháp thông thường bao gồm dùng Redis để lưu session và pub/sub, hoặc dùng database ngoài. Tuy nhiên, mục tiêu dự án là gọn nhẹ, tự chạy được trên máy cá nhân (`make dev`) hoặc deploy miễn phí trên Render mà không phải cấu hình Redis cluster hay database đám mây tốn phí.

### Quyết định (Decision)
Lưu trữ toàn bộ trạng thái phòng (`RoomSession`), người chơi (`Player`), và bộ phát sự kiện (`Broadcaster`) trực tiếp trong bộ nhớ RAM của tiến trình Python, sử dụng khóa an toàn `threading.RLock()` và `asyncio.Lock()`.

### Các giải pháp đã cân nhắc (Alternatives considered)
1. *Redis Pub/Sub + Redis Hashes:* Chuẩn công nghiệp, dễ scale ngang nhiều worker, nhưng đòi hỏi cài đặt service ngoài, phức tạp cho người dùng local và phát sinh chi phí.
2. *Lưu trạng thái vào SQLite:* Disk I/O quá lớn khi có nhiều kết nối WS gửi/nhận liên tục, khó hỗ trợ pub/sub thời gian thực.

### Hệ quả (Consequences)
- **Ưu điểm:** Tốc độ phản hồi cực nhanh (in-memory microsecond latency), mã nguồn cực kỳ gọn gàng, zero external dependencies.
- **Nhược điểm/Đánh đổi:** Trạng thái phòng sẽ mất khi tiến trình server bị tắt hoặc restart. Chỉ chạy được trên 1 worker (`WEB_CONCURRENCY=1`). Hoàn toàn chấp nhận được với quy mô party game gia đình/bạn bè.

### Các thành phần liên quan
- [`game/room.py`](file:///d:/game_bruh/game/room.py)
- [`game/ws.py`](file:///d:/game_bruh/game/ws.py)
- [`server/ws.py`](file:///d:/game_bruh/server/ws.py)

---

## ADR-002: Kiến trúc Tiến trình Đơn hợp nhất (Unified Single-Process)

- **Ngày:** 2026-09-12
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Ứng dụng gồm 3 dịch vụ: Giao diện tĩnh (HTML/JS/CSS), API quản trị/cấu hình (HTTP REST), và Máy chủ phòng chơi (WebSocket). Nếu tách thành các service riêng (frontend server riêng, API backend riêng, socket server riêng) thì việc deploy và phát triển local sẽ rất cồng kềnh.

### Quyết định (Decision)
Hợp nhất tất cả vào một ứng dụng FastAPI/Uvicorn duy nhất:
- Phục vụ static files tại `/` (mount từ thư mục `public/`).
- Phục vụ HTTP API tại `/api/*`.
- Phục vụ WebSocket phòng chơi tại `/ws`.
- Chạy background sweep task qua cơ chế `lifespan` của FastAPI.

### Các giải pháp đã cân nhắc (Alternatives considered)
1. *Tách Frontend riêng (Cloudflare Pages/Vercel) + Backend riêng (Render):* Đã thử nghiệm nhưng Cloudflare Pages không hỗ trợ WebSocket trên cùng origin, gây phức tạp về CORS và quản lý 2 repository/dịch vụ riêng.

### Hệ quả (Consequences)
- **Ưu điểm:** Chỉ cần chạy đúng một lệnh (`uv run python main.py --serve`) là toàn bộ game hoạt động. Triển khai lên Render chỉ cần 1 Web Service Free duy nhất.
- **Nhược điểm:** Tải static file và socket chia sẻ chung tài nguyên CPU của một tiến trình.

---

## ADR-003: Kho từ vựng SQLite cục bộ với Kiến trúc Ba Pool

- **Ngày:** 2026-09-11
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Game đoán cụm 2 từ tiếng Việt cần có kho từ phong phú nhưng phải loại bỏ từ tục tĩu, từ rác và từ ghép vô nghĩa. Việc gọi API bên thứ ba mỗi lượt chơi sẽ gây độ trễ và phụ thuộc mạng.

### Quyết định (Decision)
Tạo file SQLite cục bộ `data/words.sqlite` đi kèm repo với 3 pool:
1. `play`: ~7.3k từ ghép thông dụng chất lượng cao (Viet11K), độ dài mỗi từ từ 2–5 ký tự.
2. `raw`: ~59k từ vựng tổng hợp từ các từ điển mã nguồn mở.
3. `rejected`: Danh sách từ tục tĩu hoặc bị loại trừ.

### Hệ quả (Consequences)
- **Ưu điểm:** Đáp án được chọn ngẫu nhiên từ kho `play` cực nhanh, không cần internet. Dữ liệu từ vựng được version-control bằng Git.

---

## ADR-004: Khả năng Tương thích Môi trường Container Tối giản (Render)

- **Ngày:** 2026-09-12
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Khi triển khai lên Render Web Service, container Linux tối giản không cài đặt sẵn các tiện ích hệ thống như `fuser` hay `pkill`. Đồng thời, Render yêu cầu server phải lắng nghe trên `0.0.0.0` thay vì `127.0.0.1`.

### Quyết định (Decision)
- Cung cấp tham số cấu hình `--host` (mặc định bind `0.0.0.0` hoặc đọc từ biến môi trường `HOST`).
- Bọc toàn bộ các lệnh dọn dẹp port hệ thống (`fuser`, `pkill`) vào khối `try ... except OSError: pass` trong [`server/runctl.py`](file:///d:/game_bruh/server/runctl.py).

### Hệ quả (Consequences)
- **Ưu điểm:** Một mã nguồn duy nhất chạy mượt mà ở cả 2 môi trường: Local máy cá nhân (Windows/macOS) và Render Production (Linux container), không cần tạo nhánh git riêng biệt.

---

## ADR-005: Chế độ Thi đấu Nhiều vòng (Multi-Round Match) và Hệ thống Tính điểm Xếp hạng

- **Ngày:** 2026-09-13
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Cơ chế phòng nhóm ban đầu chỉ chạy 1 câu duy nhất: người giải xong sớm hoặc đoán sai cả 6 lần phải ngồi chờ thụ động rất lâu, tạo trải nghiệm cụt hứng. Người dùng đề xuất mô hình trận đấu gồm 5–10 câu chung, tính điểm theo số lượt đoán và có đồng hồ thời gian.

### Quyết định (Decision)
1. Tích hợp trực tiếp tùy chọn Số câu (`rounds`: 1, 3, 5, 10) và Thời gian (`time_limit`: 0, 120s, 180s, 300s) vào lúc tạo phòng Party. Mặc định là 5 câu và không giới hạn thời gian.
2. Thang điểm theo lượt đoán: Lần 1: 100đ, Lần 2: 50đ, Lần 3: 40đ, Lần 4: 30đ, Lần 5: 20đ, Lần 6: 10đ, hỏng: 0đ.
3. Tiêu chí phụ (Tie-breaker): Khi bằng điểm, người có tổng thời gian giải ít hơn (`total_time ASC`) sẽ xếp trên.
4. Mở rộng State Machine của `RoomSession` thêm trạng thái `round_summary` (nghỉ 5s giữa 2 câu) và sự kiện `ROUND_FINISHED` / `NEXT_ROUND`.

### Hệ quả (Consequences)
- **Ưu điểm:** Tăng tính cạnh tranh, ai cũng được chơi liên tục qua nhiều câu, có cơ hội lật kèo. Tương thích ngược 100% với các test cũ (`rounds=1`).
- **Nhược điểm:** Phức tạp hóa nhẹ luồng state machine trong `RoomSession`.

---

## ADR-006: Cơ chế Keep-Alive cho Render Free bằng Endpoint `/health` & UptimeRobot

- **Ngày:** 2026-09-13
- **Trạng thái:** Accepted

### Bối cảnh (Context)
Render Web Service gói Free tự động chuyển sang chế độ ngủ (sleep/idle) sau 15 phút không nhận được inbound HTTP request hoặc tin nhắn WebSocket. Khi người dùng truy cập lại, dịch vụ mất khoảng 50–60 giây để khởi động lại container (cold start), gây trải nghiệm chờ đợi khó chịu.

### Quyết định (Decision)
1. **Endpoint `/health` siêu nhẹ:** Bổ sung router `@app.get("/health")` trả về JSON `{ "status": "ok" }` ngay tại [`server/app.py`](file:///d:/game_bruh/server/app.py). Endpoint này phản hồi trong < 2ms, không tải trang HTML, không nạp static asset hay truy vấn cơ sở dữ liệu.
2. **Cấu hình UptimeRobot Free Monitor:**
   - URL theo dõi: `https://game-bruh.onrender.com/health`
   - Chu kỳ kiểm tra (Interval): **5 phút** (mức an toàn cao, nằm gọn dưới ngưỡng 15 phút của Render).
3. **Cấu hình Render Health Check Path:** Khai báo `/health` trên Render Dashboard để hệ thống tự động kiểm tra liveness khi deploy.
4. **WebSocket Heartbeat 2 chiều:** Duy trì ping/pong định kỳ (client ping mỗi 20s, server timeout 30s) để giữ các kết nối đang chơi không bị proxy ngắt.

### Hệ quả (Consequences)
- **Ưu điểm:**
  - Giữ Web Service Render Free luôn ở trạng thái ấm ("gần như always-on") với chi phí $0.
  - Loại bỏ hoàn toàn độ trễ cold-start khi bạn bè rủ nhau vào phòng chơi.
  - Tiêu tốn cực ít tài nguyên băng thông và CPU của Render.
- **Lưu ý thực tế:** Gói Render Free vẫn có thể restart định kỳ từ phía hạ tầng Render (khoảng 1 lần/ngày hoặc bảo trì). Vì phòng chơi được lưu in-memory (ADR-001), khi server restart người chơi chỉ cần tạo lại phòng mới, không ảnh hưởng dữ liệu cố định.


