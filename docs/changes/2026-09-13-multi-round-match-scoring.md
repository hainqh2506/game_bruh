# Multi-Round Match Series with Cumulative Scoring & Timer

- **Ngày thực hiện:** 2026-09-13
- **Tác giả:** Antigravity Coding Agent
- **Trạng thái:** Completed

## 1. Vấn đề & Động lực (Problem & Motivation)
Trong chế độ "Chơi cùng bạn" (Party Mode) ban đầu, mỗi ván đấu chỉ gồm 1 câu duy nhất. Những người chơi giải được sớm hoặc đoán sai cả 6 lần phải ngồi đợi thụ động những người còn lại, gây nhàm chán. Người dùng phản hồi và yêu cầu chuyển sang mô hình thi đấu theo trận (Match Series 3–5–10 câu) kèm tính điểm theo số lượt đoán và đồng hồ thời gian.

## 2. Kiến trúc trước thay đổi (Previous Architecture)
- Phòng chơi chỉ có 1 câu đố. Trạng thái gồm `lobby` ➔ `playing` ➔ `finished`.
- Không có thuộc tính số vòng hay điểm số. Bảng xếp hạng chỉ so sánh `solved_at` của câu đó.
- Chủ phòng phải bấm Rematch sau mỗi câu.

## 3. Kiến trúc sau thay đổi (New Architecture)
- Hỗ trợ chọn số câu (`rounds`: 1, 3, 5, 10 — mặc định 5) và thời gian (`time_limit`: 0 = không giới hạn, 120s, 180s, 300s).
- Thang điểm: 100đ, 50đ, 40đ, 30đ, 20đ, 10đ, tạch 0đ.
- Bằng điểm: Tiêu chí phụ (tie-breaker) là tổng thời gian giải ít hơn (`total_time ASC`).
- Mở rộng state machine với trạng thái `round_summary` (nghỉ 5s xem đáp án & điểm) trước khi bước sang câu tiếp theo.
- Sự kiện mới: `Server.ROUND_FINISHED`, `Client.NEXT_ROUND`.
- Màn hình vinh danh chung cuộc (Victory Podium Top 1 🥇, Top 2 🥈, Top 3 🥉).

## 4. Chi tiết thực hiện (Implementation Details)
- `game/protocol.py`: Thêm `Client.NEXT_ROUND` và `Server.ROUND_FINISHED`.
- `game/engine.py`: Chuẩn hóa `rounds` và `time_limit` trong `normalize_settings()`.
- `game/room.py`: Cập nhật `Player` (điểm, thời gian), `RoomSession` (state machine nhiều vòng, scoring, ranking tie-break, next_round, sweep_stale time limit, re-claim người chơi mất máy).
- `server/routes/rooms.py`: Nhận `rounds` và `time_limit` từ body lúc tạo phòng.
- `server/ws.py`: Broadcast `round_finished`, xử lý handler `Client.NEXT_ROUND`.
- `play/room.js` & `play/room.css`: 
  - Thêm dropdown chọn số câu, thời gian, đồng hồ đếm ngược, badge điểm số, banner kết thúc vòng và bảng vinh danh chung cuộc.
  - Lưu trữ token phòng đa tầng (`localStorage` + `sessionStorage`) để không bị mất phòng khi tải lại trang/đóng tab.
  - Tối ưu hóa toàn diện cho Mobile (chống auto-zoom iOS 16px, touch targets ≥ 42px, grid 2 cột, layout co giãn gọn gàng).
- `play/mock.js` & `play/settings.css`:
  - Loại bỏ nút Đóng trùng lặp ở modal kết thúc câu.
  - Luôn hiển thị link tra cứu từ điển VDict cho cả trường hợp đoán đúng và đoán sai.
  - Dọn dẹp khối contact thừa trong modal.
- `tests/test_room.py`: Bổ sung unit tests cho tính điểm, chuyển vòng, tie-breaker, trần thời gian và re-claim mất máy (46 tests).

## 5. Đánh đổi & Rủi ro (Trade-offs & Risks)
- Không có rủi ro về tương thích ngược: Các phòng tạo không truyền `rounds` tự động chạy 1 round như cũ.
- Trạng thái vẫn duy trì in-memory an toàn theo ADR-001.

## 6. Kế hoạch kiểm thử (Testing)
- Pytest: 46/46 tests passed 100%.
- Node.js tests: 13/13 tests passed 100%.
- Build play bundle: Chạy thành công, bundle cập nhật đồng bộ vào `public/`.
