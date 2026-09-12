# Detailed Change Records (`docs/changes/`)

Thư mục này được sử dụng để lưu trữ các tài liệu thiết kế và ghi chép chi tiết cho **các đợt thay đổi lớn (Major Changes)** hoặc **các đợt tái cấu trúc (Refactors)** có phạm vi ảnh hưởng rộng đến nhiều module.

Các thay đổi nhỏ (như sửa lỗi nhỏ, cập nhật cấu hình) chỉ cần ghi ngắn gọn trong [`docs/CHANGELOG.md`](../CHANGELOG.md), không cần tạo file trong thư mục này.

---

## Quy ước đặt tên file

```text
YYYY-MM-DD-<ten-ngan-gon-viet-thuong-gach-noi>.md
```

Ví dụ:
- `2026-09-13-multi-round-points-system.md`
- `2026-09-20-room-state-redesign.md`

---

## Mẫu tài liệu thay đổi lớn (Change Document Template)

```markdown
# [Tên đợt thay đổi]

- **Ngày thực hiện:** YYYY-MM-DD
- **Tác giả:** [Tên người thực hiện / Agent]
- **Trạng thái:** [Draft / In Progress / Completed]

## 1. Vấn đề & Động lực (Problem & Motivation)
Mô tả lý do vì sao cần thay đổi, feedback của người dùng hoặc vấn đề hiệu năng/kiến trúc gặp phải.

## 2. Kiến trúc trước thay đổi (Previous Architecture)
Hệ thống cũ hoạt động như thế nào trước khi thay đổi?

## 3. Kiến trúc sau thay đổi (New Architecture)
Mô tả thiết kế mới, các trừu tượng mới, state machine mới.

## 4. Chi tiết thực hiện (Implementation Details)
- File thay đổi:
- Protocol / API thay đổi:

## 5. Đánh đổi & Rủi ro (Trade-offs & Risks)
Ưu điểm, nhược điểm, rủi ro tiềm ẩn.

## 6. Kế hoạch kiểm thử & Tương thích ngược (Testing & Compatibility)
- Các bài test đã chạy:
- Tương thích ngược với client cũ:

## 7. Các bước tiếp theo (Follow-up Work)
```
