# Nguồn bên thứ ba

Repo này **không** phải sản phẩm của doanchu.vn. UI/Telex lấy từ client công khai; kho từ lấy từ wordlist mã nguồn mở.

## Giao diện & Telex

- Site gốc: https://doanchu.vn/ (Đoán Chữ V3)
- Snapshot trong `source/client/` (HTML/CSS/JS đã public trên trình duyệt)
- Bản unlimited (`play/mock.js`, `play/marks.js`, server Python) là code mới

## Kho từ

### Vietnamese wordlist (Viet11K)

- https://github.com/duyet/vietnamese-wordlist
- Giấy phép: GPL-2.0 (`data/open-source/vietnamese-wordlist/LICENSE`)
- Dùng để **lọc Play**: cụm 2 từ, mỗi từ 2–5 chữ

### Nối từ (noitu)

- https://github.com/minhqnd/noitu
- Giấy phép: MIT
- Đã import vào pool **Raw** trong `data/words.sqlite`; không giữ clone git trong repo

Pool Raw còn chứa dump từ Viet22K/39K/74K (cùng bộ wordlist trên). File `.txt` lớn không commit; dữ liệu nằm trong SQLite.
