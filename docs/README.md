# Đoán Chữ Unlimited — Documentation Protocol

Chào mừng bạn (con người hoặc AI coding agent) đến với hệ thống tài liệu kỹ thuật của **Đoán Chữ Unlimited**.

Hệ thống tài liệu này được thiết kế theo tư duy **Agent Harness / Persistent Engineering Memory**: Tài liệu là một phần bắt buộc của quy trình công nghệ phần mềm, phản ánh chính xác 100% hiện trạng mã nguồn, không viết lý thuyết viển vông.

---

## 1. Cấu trúc thư mục tài liệu

```text
docs/
├── README.md               # Bản đồ điều hướng & quy chuẩn tài liệu (file này)
├── ARCHITECTURE.md         # Kiến trúc hệ thống hiện tại, luồng dữ liệu & ranh giới runtime
├── RULES.md                # Các quy tắc kỹ thuật bắt buộc agent/developer phải tuân thủ
├── DECISIONS.md            # Sổ ghi chép quyết định kiến trúc (Architecture Decision Records - ADR)
├── CHANGELOG.md            # Nhật ký thay đổi kỹ thuật
├── WORKFLOW.md             # Quy trình làm việc bắt buộc của agent trước và sau khi viết code
├── modules/                # Chi tiết kiến trúc theo từng module phức tạp
│   ├── README.md           # Chỉ mục tài liệu module
│   ├── game.md             # Bộ luật engine, xử lý dấu tiếng Việt & kho từ
│   ├── room.md             # Quản lý phòng chơi, state machine & lifecycle
│   ├── websocket.md        # Giao thức WebSocket, fan-out event bus & kết nối
│   └── server.md           # FastAPI HTTP app, background worker, static server
└── changes/                # Tài liệu thiết kế chi tiết cho các đợt thay đổi lớn
    └── README.md           # Hướng dẫn ghi chép thay đổi lớn
```

---

## 2. Bản đồ đọc tài liệu (Reading Protocol)

Không cần đọc toàn bộ thư mục `docs/` trong mọi tác vụ nhằm tối ưu context window. Hãy tuân thủ phân tầng sau:

```text
               ┌───────────────────────────────────────┐
               │              AGENT TASK               │
               └──────────────────┬────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LUÔN LUÔN ĐỌC TRƯỚC KHI CODE (MANDATORY BASELINE):                  │
│   1. docs/README.md                                                 │
│   2. docs/RULES.md                                                  │
│   3. docs/ARCHITECTURE.md                                           │
└─────────────────────────────────┬───────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│ ĐỌC CÓ ĐIỀU KIỆN (THEO PHẠM VI TASK):                               │
│   - Sửa luật đoán chữ / từ vựng   ➔ docs/modules/game.md            │
│   - Sửa logic phòng / chơi nhóm   ➔ docs/modules/room.md            │
│   - Sửa lệnh WS / sync real-time  ➔ docs/modules/websocket.md       │
│   - Sửa HTTP route / deploy / PID ➔ docs/modules/server.md          │
│   - Có quyết định kiến trúc mới   ➔ docs/DECISIONS.md               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│ KIỂM TRA MÃ NGUỒN THỰC TẾ (Source Code is Ground Truth)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Quy chuẩn cập nhật sau khi sửa code (Post-Execution Protocol)

Sau khi hoàn thành tác vụ code và chạy test thành công, agent **BẮT BUỘC** trả lời Cây quyết định (Decision Tree):

1. **Kiến trúc có thay đổi không?**
   - *Có:* Cập nhật [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) và module liên quan trong [`docs/modules/`](modules/).
   - Nếu là quyết định quan trọng (ví dụ: đổi state machine, thêm tầng lưu trữ): Thêm ADR mới vào [`docs/DECISIONS.md`](DECISIONS.md).
2. **Quy tắc kỹ thuật có thay đổi không?**
   - *Có:* Cập nhật [`docs/RULES.md`](RULES.md).
3. **Hành vi hệ thống hoặc API/WS có thay đổi không?**
   - *Có:* Cập nhật [`docs/CHANGELOG.md`](CHANGELOG.md).
4. **Có phải là thay đổi kiến trúc quy mô lớn không?**
   - *Có:* Tạo tài liệu thay đổi trong [`docs/changes/YYYY-MM-DD-<ten-thay-doi>.md`](changes/).

---

## 4. Nguyên tắc cốt lõi của Documentation

- **Mã nguồn là sự thật tối cao (Code is Ground Truth):** Nếu tài liệu mâu thuẫn với code, phải đối chiếu, xác minh và sửa lại tài liệu (hoặc fix code nếu code vi phạm kiến trúc).
- **Không viết tài liệu hình thức (No Documentation Theater):** Mọi điều ghi trong `docs/` đều phải mang tính kỹ thuật, có căn cứ thực tế và phục vụ cho việc vận hành/phát triển.
- **Tách bạch Rõ ràng giữa Hiện tại và Lịch sử:**
  - `ARCHITECTURE.md`: Mô tả hệ thống **ngay lúc này**.
  - `DECISIONS.md`: Giải thích **tại sao** đưa ra quyết định đó.
  - `CHANGELOG.md` & `changes/`: Ghi nhận những gì **đã thay đổi theo thời gian**.
