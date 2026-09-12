# Module: Game Engine & Phrases (`game/engine.py`, `game/phrases.py`, `db.py`)

## 1. Mục đích (Purpose)
Chịu trách nhiệm thực thi toàn bộ luật chơi đoán chữ tiếng Việt: thẩm định từ hợp lệ, phân tích cấu trúc ký tự/dấu thanh, so khớp đoán chữ và chọn từ ngẫu nhiên từ kho từ SQLite.

---

## 2. Trách nhiệm (Responsibilities)
- **Chuẩn hóa Unicode:** Luôn chuẩn hóa xâu ký tự về dạng Unicode NFC (`unicodedata.normalize("NFC", ...)`).
- **Phân tách dấu thanh (`decompose`):** Bóc tách ký tự tiếng Việt thành chữ cái gốc và dấu (`acute` sắc, `grave` huyền, `hook` hỏi, `tilde` ngã, `dot` nặng).
- **Thuật toán tô màu (`mark_guess`):** So sánh `guess` với `answer` và trả về mảng màu:
  - `green`: Đúng ký tự + đúng dấu thanh + đúng vị trí.
  - `yellow`: Đúng ký tự + đúng dấu thanh nhưng khác vị trí.
  - `blue`: Cùng nguyên âm gốc (ví dụ `a/á/à`), khác dấu thanh.
  - `null` hoặc chuỗi rỗng: Dành cho khoảng trắng ngăn cách giữa 2 từ.
  - `"gray"`: Không có trong từ.
- **Thẩm định độ hợp lệ (`is_playable`):** Người chơi được phép đoán các chuỗi ký tự Việt không có nghĩa để "mò nguyên âm", miễn là đủ số ký tự và đúng vị trí dấu cách.

---

## 3. Giao diện công khai (Public Interfaces)
- `decompose(ch: str) -> dict[str, str]`: Bóc tách ký tự thành `{ "b": base_char, "t": tone }`.
- `mark_guess(guess: str, answer: str) -> list[str | None]`: Đánh giá kết quả một lượt đoán.
- `is_playable(guess: str, answer: str) -> bool`: Kiểm tra từ đoán có đúng khuôn mẫu độ dài và dấu cách không.
- `pick_answer(settings: dict[str, Any]) -> str`: Chọn một từ ngẫu nhiên từ kho `play` theo cấu hình độ dài từ.
- `puzzle_meta(phrase: str) -> dict[str, Any]`: Trả về metadata của câu đố (độ dài tổng, vị trí dấu cách) mà không làm lộ đáp án.

---

## 4. Quản lý trạng thái & Bất biến (Invariants)
- **Stateless:** Toàn bộ các hàm trong `engine.py` và `phrases.py` là hàm thuần túy (pure functions), không lưu trữ trạng thái.
- **Tiêu thụ ký tự duy nhất:** Trong một lượt đoán, mỗi ký tự trong đáp án chỉ được dùng để so khớp một lần duy nhất. Ưu tiên xanh lá trước, vàng sau, xanh dương tiếp theo, cuối cùng là xám.

---

## 5. Những điều TUYỆT ĐỐI KHÔNG LÀM (Must NOT do)
- **Không import web/server:** Không bao giờ import `FastAPI`, `WebSocket`, `Request` hay bất kỳ thành phần server nào vào module này.
- **Không làm lộ đáp án:** Hàm `puzzle_meta` chỉ được trả về độ dài và vị trí dấu cách, không bao giờ được chứa đáp án.
