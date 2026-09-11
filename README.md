# Đoán Chữ Unlimited

Bản chơi **không giới hạn 1 từ/ngày** của trò đoán cụm tiếng Việt 2 từ (kiểu Wordle + dấu).

Máy bạn chạy server (và tuỳ chọn Cloudflare Quick Tunnel). Không cần tài khoản Cloudflare để cho bạn bè vào.

Không liên kết với [doanchu.vn](https://doanchu.vn/). Xem [THIRD_PARTY.md](THIRD_PARTY.md).

## Cần có

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/) — chỉ khi `make dev` / `--tunnel`
- Node.js — chỉ khi `make test`

Clone xong **không** cần import wordlist: `data/words.sqlite` đã có đủ 3 pool.

```bash
git clone <url>
cd doan_chu
uv sync
make test          # optional
make dev           # debug + tunnel + reload
```

Link public nằm ở `run/LINK.txt`. Local: http://127.0.0.1:18765/

Tắt: `make stop` hoặc Ctrl+C.

## Lệnh Make

| Lệnh | Việc |
|---|---|
| `make dev` | Debug + Quick Tunnel + reload. Cổng `18765` |
| `make serve` | Chỉ localhost, có debug |
| `make stop` | Tắt python + cloudflared |
| `make build` | Build `public/` |
| `make test` | Test màu xanh lá / vàng / xanh dương / xám |
| `make curate` | Dựng lại pool Play từ Viet11K |
| `make filter` | Lọc tục → rejected |
| `make link` | In link tunnel hiện tại |

Cổng khác: `make dev PORT=18766`

## Cách chơi

Cụm **hai từ**, 6 lần thử. Mỗi ô một chữ (kể cả dấu). Khoảng trắng cố định.

| Màu | Nghĩa |
|---|---|
| Xanh lá | Đúng chữ + đúng dấu, đúng vị trí |
| Vàng | Đúng chữ + đúng dấu, sai vị trí |
| Xanh dương | Cùng nguyên âm gốc, sai dấu (`á` vs `à`) |
| Xám | Không có trong đáp án |

`a ≠ ă ≠ â`, `e ≠ ê`, `o ≠ ô ≠ ơ`, `u ≠ ư`. `d ≠ đ`.

### Mò nguyên âm

Đoán **không** cần cụm có nghĩa. Đủ ô, đúng chỗ cách, chữ Việt là được.

Ví dụ ván `3 + 3`: lần 1 gõ `aei ăâê` hoặc `aăâ oôơ` để loại nguyên âm (xám = không có, xanh dương = đúng gốc sai dấu).

Đáp án vẫn lấy ngẫu nhiên từ kho **Play** (~7.3k cụm thông dụng).

### Cài đặt

Thanh **Cài đặt** đóng sẵn. Bấm để mở → số từ → độ dài từng từ (hoặc “bất kỳ”) → **Sinh câu hỏi**. **Ván mới** giữ đúng bộ lọc đó.

## Kho từ (SQLite)

Ba pool trong `data/words.sqlite` (xem [data/README.md](data/README.md)):

| Pool | Dùng để |
|---|---|
| **Play** | Đáp án (~7.345 cụm Viet11K, mỗi từ 2–5 chữ) |
| **Raw** | Dump gốc (~59k) |
| **Đã loại** | Tục / bỏ tay |

Tab **Kho từ** (khi `DOANCHU_DEBUG=1`, mặc định với `make dev`): tìm, thêm, xoá, chuyển pool.

```bash
uv run python main.py --add-phrase "học sinh" --pool play
uv run python main.py --remove-phrase "cụm xấu" --pool play
make filter
make curate
```

Danh sách tục: `data/vulgar.txt`.

## Sửa code (reload)

`make dev` watch `play/mock.js`, `marks.js`, `debug.js`, `debug.css`, `settings.css`, `reload.js`. Lưu file → trang tự F5, **URL tunnel không đổi**.

Sửa `main.py` / `db.py` thì phải chạy lại `make dev` (đổi link tunnel).

Đừng chạy `make dev` lần nữa chỉ để sửa frontend.

## Cấu trúc

```
play/           mock, tô màu, cài đặt, debug UI
source/client/  snapshot HTML/CSS/JS gốc (build UI)
data/           words.sqlite, Viet11K, vulgar.txt
tests/          node:test tô màu
functions/      Cloudflare Pages /api/config
```

`public/` là output, gitignore.

## Python CLI

```bash
uv run python main.py --serve --port 18765
uv run python main.py --tunnel
uv run python main.py --stop
uv run python main.py --build-play
uv run python main.py --deploy          # Cloudflare Pages (cần wrangler login)
uv run python main.py --fetch-client    # maintainer: tải lại snapshot doanchu.vn
```

Không tham số → in help. Không tự scrape site gốc.

## Deploy Cloudflare Pages (tuỳ chọn)

Cần login Cloudflare. Local chơi thì **không** cần.

1. Secrets GitHub: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
2. Push `main` → workflow `.github/workflows/cloudflare-pages.yml`
3. Hoặc: `npx wrangler login` rồi `uv run python main.py --deploy`

`DOANCHU_DEBUG=0` trên Pages (không mở tab Kho từ cho khách).

## Gỡ lỗi thường gặp

**“Từ không hợp lệ” khi mò nguyên âm** — hard-refresh (Ctrl+Shift+R). `mock.js` phải load như file riêng, không còn `VALID.has(guess)`.

**Link trycloudflare không mở** — DNS LAN đôi khi cache NXDOMAIN vài phút. Thử http://127.0.0.1:18765/ hoặc đợi / DoH. Mỗi lần `make dev` ra URL mới.

**Cổng đang dùng** — `make stop` rồi `make dev`.
