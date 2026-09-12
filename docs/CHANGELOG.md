# Changelog — Đoán Chữ Unlimited

Tất cả các thay đổi kỹ thuật đáng chú ý của dự án sẽ được ghi nhận tại đây theo định dạng Keep a Changelog.

## 2026-09-13

### Added
- Tính năng Thả cảm xúc nhanh (Floating Emoji Reactions):
  - Thanh emoji 6 biểu cảm (`👏`, `🔥`, `🤣`, `💀`, `😱`, `❤️`) xuất hiện mượt mà khi đang trong trận đấu.
  - Hiệu ứng floating emoji bay bổng từ dưới màn hình lên với chuyển động tự nhiên và tên người thả, tự biến mất sau 1.9s.
  - Cơ chế rate-limit (0.3s) ở cả client và server chống spam, kèm huy hiệu emoji hiển thị tức thời bên cạnh tên người chơi trong danh sách phòng.
  - Lệnh WebSocket hai chiều mới: `Client.REACTION` và `Server.REACTION`.
- Tính năng Soi ma trận màu của đối thủ (Live Progress Mini-board Spectating):
  - Nút "👁️ Soi" / "Đóng" bên cạnh mỗi đối thủ trong danh sách phòng khi đang thi đấu.
  - Bảng ma trận 6 dòng x N ô hiển thị trực quan các màu (xanh lá, vàng, xanh dương, xám, khoảng trống) theo từng lượt đoán của đối thủ theo thời gian thực.
  - Bảo mật tuyệt đối (100% cheat-proof): `Player.public()` chỉ trả về mảng màu `marks`, tuyệt đối giấu kín các chữ cái đoán (`guesses`).
- Chế độ thi đấu phòng nhiều người Nhiều vòng (Multi-round Match):
  - Tùy chọn số câu (1, 3, 5, 10 câu - mặc định 5) và thời gian (Không giới hạn - mặc định, 120s, 180s, 300s) ngay khi tạo phòng.
  - Thang điểm theo số lượt đoán: lần 1 được 100đ, lần 2: 50đ, lần 3: 40đ, lần 4: 30đ, lần 5: 20đ, lần 6: 10đ, hỏng: 0đ.
  - Cơ chế tie-breaker khi bằng điểm: người có tổng thời gian giải ít hơn xếp trên.
  - Trạng thái `round_summary` (nghỉ 5s giữa 2 câu) và đếm ngược tự chuyển câu tiếp theo.
  - Màn hình vinh danh chung cuộc (Victory Podium Top 1 🥇, Top 2 🥈, Top 3 🥉).
  - Lệnh WebSocket mới: `Client.NEXT_ROUND` và `Server.ROUND_FINISHED`.
- Bổ sung endpoint siêu nhẹ `GET /health` (`{"status": "ok"}`) phục vụ Health Check trên Render và cơ chế Keep-Alive chống sleep container thông qua UptimeRobot Free (chu kỳ 5 phút).
- Ghi nhận quyết định kiến trúc ADR-005 và ADR-006 vào `docs/DECISIONS.md`.
- Ghi nhận tài liệu thiết kế chi tiết tại `docs/changes/2026-09-13-multi-round-match-scoring.md`.

### Changed
- Tối ưu hóa toàn diện giao diện Mobile:
  - Nâng `font-size: 16px` cho các ô input và select để ngăn chặn hoàn toàn hiện tượng tự động zoom khó chịu trên iOS Safari.
  - Chuyển hàng cấu hình phòng (Số câu & Thời gian) sang dạng Grid 2 cột dễ nhìn, dễ thao tác trên màn hình nhỏ.
  - Tăng chiều cao vùng chạm (touch target ≥ 42px - 44px) và bật `touch-action: manipulation` loại bỏ 300ms độ trễ chạm.
  - Thu gọn kích thước bảng kết quả Endgame Modal và ảnh canvas để các nút thao tác luôn nằm trọn trong màn hình mà không cần cuộn.

### Fixed
- Sửa lỗi hiển thị 2 nút "Đóng" nằm cạnh nhau trong modal kết thúc câu ở chế độ phòng.
- Sửa lỗi mất kết nối và không nhận diện lại người chơi khi đóng/mở lại tab hoặc trình duyệt ẩn danh:
  - Lưu trữ token phòng đa tầng (`localStorage` + `sessionStorage`) theo mã phòng.
  - Bổ sung cơ chế tự động re-claim cho người chơi bị ngắt kết nối ("mất máy") khi vào lại bằng đúng tên.
- Sửa lỗi không hiển thị link từ điển VDict khi người chơi đoán sai hoặc hết 6 lượt.
- Ẩn triệt để thông tin liên hệ tĩnh ("Contact us") thừa ở chân modal kết quả.
- Bổ sung trạng thái `round_summary` vào kiểm tra `inGame` trong `syncPlayfield()` để tránh ẩn nhầm bàn cờ và danh sách người chơi giữa 2 câu.

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
