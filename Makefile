UV       ?= uv run
PORT     ?= 18765
PYTHONUNBUFFERED ?= 1
export PYTHONUNBUFFERED

.PHONY: help dev serve stop build filter curate test link

help:
	@echo "make dev     - debug + Quick Tunnel + reload (sửa play/ rồi đợi F5)"
	@echo "make serve   - local only, debug + reload"
	@echo "make stop    - tắt server/tunnel"
	@echo "make build   - build public/"
	@echo "make filter  - lọc tục vào pool rejected"
	@echo "make curate  - lọc Play còn từ ghép thông dụng (Viet11K)"
	@echo "make test    - test tô màu (JS + Python) + phòng"
	@echo "make link    - in link hiện tại"

dev:
	DOANCHU_DEBUG=1 $(UV) python main.py --tunnel --reload --port $(PORT)

serve:
	DOANCHU_DEBUG=1 $(UV) python main.py --serve --port $(PORT)

stop:
	$(UV) python main.py --stop

build:
	$(UV) python main.py --build-play

filter:
	$(UV) python main.py --filter-vulgar

curate:
	$(UV) python main.py --curate-play

test:
	node --test tests/marks.test.js
	$(UV) pytest tests/test_engine.py tests/test_room.py tests/test_api.py tests/test_phrases.py

link:
	@cat run/LINK.txt 2>/dev/null || echo "Chưa có tunnel. Chạy: make dev"
