# Engineering Workflow Protocol for Coding Agents

Tài liệu này định nghĩa quy trình làm việc chuẩn bắt buộc cho mọi coding agent và kỹ sư khi tham gia đóng góp mã nguồn trong repository **Đoán Chữ Unlimited**.

---

## 1. Vòng đời Tác vụ Kỹ thuật (Engineering Lifecycle)

```text
    1. Hiểu yêu cầu (Understand)
                 ↓
    2. Đọc tài liệu (Read Docs)
                 ↓
    3. Đối chiếu code thực tế (Inspect Code)
                 ↓
    4. Lập kế hoạch (Plan)
                 ↓
    5. Viết code & kiểm thử (Implement & Test)
                 ↓
    6. Rà soát tác động kiến trúc (Review Architecture Impact)
                 ↓
    7. Cập nhật tài liệu (Update Docs)
                 ↓
    8. Xác minh & Báo cáo (Final Verification & Summary)
```

---

## 2. Các bước chi tiết

### Bước 1: Trước khi viết code (Pre-Coding)
1. **Đọc tài liệu cơ bản:**
   - [`docs/README.md`](README.md): Nắm vững protocol.
   - [`docs/RULES.md`](RULES.md): Nắm vững các điều cấm kỵ và quy tắc kỹ thuật.
   - [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): Nắm rõ ranh giới module và luồng dữ liệu.
2. **Đọc tài liệu module liên quan:**
   - Nếu tác vụ liên quan đến WebSocket: đọc [`docs/modules/websocket.md`](modules/websocket.md).
   - Nếu tác vụ liên quan đến phòng chơi/state: đọc [`docs/modules/room.md`](modules/room.md).
   - Nếu tác vụ liên quan đến luật đoán chữ: đọc [`docs/modules/game.md`](modules/game.md).
3. **Đối chiếu mã nguồn thực tế (Code Inspection):**
   - Đọc các file liên quan trực tiếp để hiểu rõ hàm, class, kiểu dữ liệu hiện có.
   - Tận dụng trừu tượng sẵn có, **không tự ý phát minh lại bánh xe**.

### Bước 2: Trong khi viết code (Implementation)
- Tuân thủ ranh giới giữa `game/` (Domain thuần) và `server/` (Transport).
- Viết code tối giản, mạch lạc, giải quyết đúng mục tiêu bài toán.
- Giữ vững tính tương thích ngược với các lệnh local (`make dev`, `make test`).

### Bước 3: Sau khi viết code (Verification & Documentation)
1. **Chạy toàn bộ bộ test kiểm thử:**
   ```bash
   uv run pytest
   node --test tests/marks.test.js
   ```
   Tất cả các test phải pass 100%. Nếu có tính năng mới, phải bổ sung unit test tương ứng.
2. **Rà soát tác động (Architecture Review):**
   - Xem lại `git diff`.
   - Đối chiếu theo Cây quyết định cập nhật tài liệu (xem mục 3 bên dưới).
3. **Cập nhật tài liệu:**
   - Cập nhật các file trong `docs/` tương ứng với thay đổi.

---

## 3. Cây quyết định Cập nhật Tài liệu (Documentation Decision Tree)

Sau mỗi tác vụ code, bắt buộc phải tự đặt 5 câu hỏi sau:

```text
1. Kiến trúc hệ thống có thay đổi không?
   ├── YES ➔ Cập nhật docs/ARCHITECTURE.md và docs/modules/*.md
   └── NO  ➔ Bỏ qua

2. Có quyết định kỹ thuật / kiến trúc quan trọng mới không?
   ├── YES ➔ Thêm ADR mới vào docs/DECISIONS.md (ADR-XXX)
   └── NO  ➔ Bỏ qua

3. Có quy tắc kỹ thuật hoặc giới hạn mới nào không?
   ├── YES ➔ Cập nhật docs/RULES.md
   └── NO  ➔ Bỏ qua

4. Hành vi hệ thống, API hoặc WebSocket protocol có thay đổi không?
   ├── YES ➔ Ghi nhận vào docs/CHANGELOG.md
   └── NO  ➔ Bỏ qua

5. Thay đổi có quy mô lớn cần tài liệu thiết kế riêng không?
   ├── YES ➔ Tạo tài liệu docs/changes/YYYY-MM-DD-<ten-thay-doi>.md
   └── NO  ➔ Bỏ qua
```

---

## 4. Mẫu Báo cáo Kết thúc Tác vụ (Task Summary Template)

Khi kết thúc mỗi tác vụ, agent phải xuất báo cáo theo mẫu sau:

```markdown
## Implementation Summary

### Thay đổi kỹ thuật (Changed)
- ...

### Kiểm thử (Tests)
- uv run pytest: X passed
- node test: Y passed

### Tác động kiến trúc (Architecture Impact)
- Không có / Thay đổi tại ...

### Tài liệu đã cập nhật (Documentation Updated)
- docs/CHANGELOG.md
- docs/...

### Quyết định mới (New Decisions)
- Không có / ADR-XXX

### Bước tiếp theo (Follow-up)
- ...
```
