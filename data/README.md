# Data

| File | Trong git? | Vai trò |
|---|---|---|
| `words.sqlite` | có | Kho từ: pool `raw` / `play` / `rejected` |
| `phrases_two_words.json` | có | Export pool Play (đọc được, ~7.3k cụm) |
| `vulgar.txt` | có | Danh sách lọc tục → `rejected` |
| `open-source/vietnamese-wordlist/Viet11K.txt` | có | Nguồn curate Play |

`play/phrases.js` và `public/` được tạo lúc `make dev` / `make build` từ SQLite, không commit.

## Pool

- **raw** — dump gốc (~59k cụm 2 từ)
- **play** — đáp án chơi (~7.3k cụm thông dụng, Viet11K, 2–5 chữ/từ)
- **rejected** — tục / loại tay

Đoán **không** cần cụm có trong Play: đúng số ô + chỗ cách + chữ Việt là được. Play chỉ để **sinh đáp án**.

## Lệnh

```bash
make curate          # dựng lại Play từ Viet11K
make filter          # chuyển tục sang rejected
uv run python main.py --add-phrase "học sinh" --pool play
```
