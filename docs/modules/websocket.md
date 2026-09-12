# Module: WebSocket & Event Bus (`server/ws.py`, `game/ws.py`, `game/protocol.py`)

## 1. Mục đích (Purpose)
Xử lý kết nối hai chiều thời gian thực (Full-duplex Real-time Communication) giữa trình duyệt của các người chơi và máy chủ game qua endpoint `/ws`.

---

## 2. Trách nhiệm (Responsibilities)
- Xác thực kết nối WebSocket khi bắt tay (Handshake) thông qua query params: `/ws?room=ABCD&token=XYZ`.
- Đăng ký và hủy kết nối socket vào phòng chơi tương ứng.
- Tiếp nhận các gói tin JSON từ client, phân phối cho các hàm xử lý tương ứng (`HANDLERS`).
- Phát tán (fan-out / broadcast) sự kiện tới toàn bộ người chơi trong phòng hoặc gửi tin nhắn riêng cho từng socket.

---

## 3. Danh mục Lệnh (Protocol Specification)

Được định nghĩa tập trung tại [`game/protocol.py`](file:///d:/game_bruh/game/protocol.py):

### Client to Server (`Client.*`)
| Lệnh | Payload mẫu | Ý nghĩa |
| :--- | :--- | :--- |
| `ping` | `{ "type": "ping" }` | Giữ kết nối (heartbeat mỗi 20s) |
| `start` | `{ "type": "start" }` | Chủ phòng bấm bắt đầu ván đấu |
| `guess` | `{ "type": "guess", "guess": "học sinh" }` | Người chơi gửi từ đoán |
| `next_round` | `{ "type": "next_round" }` | Chủ phòng bấm chuyển sang câu tiếp theo |
| `rematch` | `{ "type": "rematch" }` | Chủ phòng yêu cầu chơi lại ván/trận mới |
| `reaction` | `{ "type": "reaction", "emoji": "🔥" }` | Thả cảm xúc nhanh (rate-limited 0.3s) |

### Server to Client (`Server.*`)
| Lệnh | Payload chính | Ý nghĩa |
| :--- | :--- | :--- |
| `room` | `{ "type": "room", "status": ..., "players": ..., "board": ... }` | Trả về trạng thái đầy đủ khi mới vào phòng |
| `started` | `{ "type": "started", "length": ..., "spaceIndex": ... }` | Thông báo ván chơi bắt đầu |
| `guess_result` | `{ "type": "guess_result", "marks": [...], "won": bool }` | Trả kết quả tô màu cho người vừa đoán |
| `peer_update` | `{ "type": "peer_update", "players": [...] }` | Cập nhật số lượt đoán & ma trận màu (marks) an toàn của bạn chơi |
| `peer_solved` | `{ "type": "peer_solved", "player": ..., "rank": int }` | Thông báo có bạn chơi vừa đoán đúng |
| `round_finished` | `{ "type": "round_finished", "round": ..., "solution": ... }` | Kết thúc câu hiện tại trong chuỗi nhiều câu |
| `finished` | `{ "type": "finished", "ranking": [...], "solution": str }` | Kết thúc ván/trận, công bố bảng xếp hạng & đáp án |
| `reaction` | `{ "type": "reaction", "player_id": ..., "name": ..., "emoji": ... }` | Broadcast biểu cảm nhanh nổi trên màn hình |
| `pong` | `{ "type": "pong" }` | Phản hồi lệnh ping |
| `error` | `{ "type": "error", "message": str }` | Báo lỗi thao tác cho client |

---

## 4. Quản lý trạng thái kết nối (`game/ws.py` — `Broadcaster`)
- `Broadcaster._rooms`: Từ điển ánh xạ `room_id -> set[WebSocket]`.
- Được bảo vệ bởi `asyncio.Lock()` để tránh xung đột khi nhiều socket kết nối/ngắt kết nối đồng thời trong event loop.
- **Fail-safe:** Khi gửi tin nhắn qua `ws.send_json()`, nếu kết nối bị đứt (ném ngoại lệ), socket đó sẽ tự động bị loại khỏi danh sách `conns` và hủy đăng ký khỏi phòng.
