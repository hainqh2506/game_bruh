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
| `make test` | Test màu (JS + Python) và phòng in-memory |
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

### Phòng nhiều người

Trên **cùng link** `make dev` / tunnel (không phải Cloudflare Pages — Pages không chạy WebSocket):

1. Chọn **Cùng bạn** (không trộn với ván chơi đơn)
2. **Tạo phòng** → mã 4 ký tự + copy `/?room=ABCD` — hoặc bạn bè nhập mã
3. Chủ phòng bấm **Bắt đầu** (cần 2–8 người)
4. Cùng một đáp án, đoán đồng thời, 6 lần. Người khác chỉ thấy tên / số lần đoán / đã xong — không thấy bảng màu.
5. Ai đúng trước thắng (`solved_at`). Người còn lại đoán tiếp để xếp hạng. **Chơi lại** giữ cùng nhóm, đáp án mới.

**Chơi đơn** là mode riêng, bảng hiện ngay. Refresh trong phòng giữ token (`sessionStorage`) và khôi phục bảng của mình.

### Trần máy chủ (tránh sập host nhỏ)

Phòng nằm **trong RAM** của process Python. GitHub Pages / Cloudflare Pages chỉ được **chơi đơn** (file tĩnh, không WebSocket). Party vẫn cần máy chạy `make dev` / `--tunnel`, hoặc VPS nhỏ — không host 24/7 trên GitHub Actions.

Copy [`.env.example`](.env.example) → `.env` rồi sửa (file `.env` không commit). `make dev` tự đọc `.env`.

| Biến | Mặc định | Nghĩa |
|---|---|---|
| `DOANCHU_MAX_SOLO` | 40 | Slot chơi đơn đồng thời trên process này |
| `DOANCHU_MAX_ROOMS` | 12 | Số phòng cùng lúc |
| `DOANCHU_MAX_PLAYERS` | 8 | Người / phòng (2–8) |
| `DOANCHU_MAX_PARTY` | 40 | Tổng người trong mọi phòng |
| `DOANCHU_ROOM_TTL` | 2700 | Xóa phòng idle (giây) |

```bash
cp .env.example .env
# sửa số trong .env
make dev
```

Lobby hiện `phòng đang dùng / trần`. Hết slot thì tạo phòng / chơi đơn báo lỗi, không nhận thêm.

Muốn solo không tốn máy bạn: deploy Pages (`make` / workflow) rồi gửi link Pages; tunnel chỉ để party.

### Cài đặt

Thanh **Cài đặt** đóng sẵn. Bấm để mở → số từ → độ dài từng từ (hoặc “bất kỳ”) → **Sinh câu hỏi**. **Ván mới** giữ đúng bộ lọc đó.

## Kho từ (SQLite)

Ba pool trong `data/words.sqlite` (xem [data/README.md](data/README.md)):

| Pool | Dùng để |
|---|---|
| **Play** | Đáp án (~7.345 cụm Viet11K, mỗi từ 2–5 chữ) |
| **Raw** | Dump gốc (~59k) |
| **Đã loại** | Tục / bỏ tay |

Tab **Kho từ** (khi `DOANCHU_DEBUG=1`, mặc định với `make dev`): tìm, thêm từng cụm, chọn hàng loạt, nhập/xuất file `.txt`. Raw = chờ duyệt; Play = đáp án. **Loại** đưa vào Đã loại (lấy lại được); chỉ **Xóa hẳn** ở tab đó mới mất.

```bash
uv run python main.py --add-phrase "học sinh" --pool play
uv run python main.py --remove-phrase "cụm xấu" --pool play
make filter
make curate
```

Danh sách tục: `data/vulgar.txt`.

## Sửa code (reload)

`make dev` watch `play/*.js`, `*.css`. Lưu file → trang tự F5, **URL tunnel không đổi**.

Sửa `main.py` / `db.py` / `game/` / `server/` thì phải chạy lại `make dev` (đổi link tunnel).

Đừng chạy `make dev` lần nữa chỉ để sửa frontend.

## Cấu trúc

```
play/           mock, tô màu, phòng, cài đặt, debug UI
game/           luật chơi: engine, RoomHub, protocol (không FastAPI)
server/         HTTP/WS: routes, build public/, serve + tunnel
tools/          import kho từ, (snapshot client nằm CLI)
main.py         CLI
source/client/  snapshot HTML/CSS/JS gốc (build UI)
data/           words.sqlite, Viet11K, vulgar.txt
tests/          node:test tô màu; pytest engine/phòng
functions/      Cloudflare Pages /api/config
```

Thêm API: tạo `server/routes/<ten>.py` rồi `include_router` trong `server/app.py`.
Thêm lệnh WS: hằng số ở `game/protocol.py` + handler trong `server/ws.py` `HANDLERS`.
Thêm file JS/CSS: ghi vào `PLAY_SCRIPTS` / `PLAY_STYLES` trong `server/build.py`.

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
2. Actions → **Deploy Cloudflare Pages** → Run workflow (không chạy khi `git push`)
3. Hoặc: `npx wrangler login` rồi `uv run python main.py --deploy`

`DOANCHU_DEBUG=0` trên Pages (không mở tab Kho từ cho khách).

## Gỡ lỗi thường gặp

**“Từ không hợp lệ” khi mò nguyên âm** — hard-refresh (Ctrl+Shift+R). `mock.js` phải load như file riêng, không còn `VALID.has(guess)`.

**Link trycloudflare không mở** — DNS LAN đôi khi cache NXDOMAIN vài phút. Thử http://127.0.0.1:18765/ hoặc đợi / DoH. Mỗi lần `make dev` ra URL mới.

**Cổng đang dùng** — `make stop` rồi `make dev`.
