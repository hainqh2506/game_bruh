# Module Documentation Index — Đoán Chữ Unlimited

Thư mục này chứa tài liệu chi tiết cho các module cốt lõi của hệ thống. Khi agent hoặc kỹ sư cần sửa đổi module nào, hãy đọc tài liệu module đó trước.

---

## Danh mục Module

| Tài liệu | Module tương ứng | Nội dung chính |
| :--- | :--- | :--- |
| [`game.md`](game.md) | `game/engine.py`, `game/phrases.py`, `db.py` | Thuật toán đoán chữ, chuẩn hóa dấu tiếng Việt, phân tách nguyên âm và kho từ SQLite. |
| [`room.md`](room.md) | `game/room.py`, `game/limits.py` | Phiên phòng in-memory (`RoomSession`), người chơi (`Player`), state machine và giới hạn tài nguyên. |
| [`websocket.md`](websocket.md) | `server/ws.py`, `game/ws.py`, `game/protocol.py` | Giao thức truyền tin WebSocket, bộ phát tán `BUS` (`Broadcaster`) và vòng đời kết nối. |
| [`server.md`](server.md) | `server/app.py`, `server/serve.py`, `server/routes/*` | FastAPI application, Uvicorn runner, background worker quét rác và phân phối file tĩnh. |

---

## Cấu trúc chuẩn của một Module Document

Mỗi tài liệu module phải tuân theo cấu trúc:
```text
1. Mục đích (Purpose)
2. Trách nhiệm (Responsibilities)
3. Giao diện công khai (Public Interfaces)
4. Phụ thuộc (Dependencies)
5. Quản lý trạng thái (State Management)
6. Các bất biến quan trọng (Important Invariants)
7. Điểm mở rộng (Extension Points)
8. Những điều TUYỆT ĐỐI KHÔNG LÀM (Must NOT do)
```
