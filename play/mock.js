/* Local unlimited mode: intercept PHP APIs so each reload is a new phrase. */
(() => {
  const FALLBACK = [
    "bố mẹ", "anh em", "gia đình", "học sinh", "cà phê", "bánh mì"
  ];
  const PHRASES = (window.DOANCHU_PHRASES && window.DOANCHU_PHRASES.length
    ? window.DOANCHU_PHRASES
    : FALLBACK
  ).map((p) => String(p).normalize("NFC").toLowerCase());
  const SETTINGS_KEY = "doanchu:settings";

  function wordsOf(phrase) {
    return String(phrase).trim().split(/\s+/);
  }

  function loadSettings() {
    try {
      const raw = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
      const words = Number(raw.words) || 2;
      const lengths = Array.isArray(raw.lengths) ? raw.lengths : [];
      return {
        words,
        lengths: Array.from({ length: words }, (_, i) => {
          const n = Number(lengths[i]);
          return Number.isFinite(n) && n > 0 ? n : null;
        })
      };
    } catch (e) {
      return { words: 2, lengths: [null, null] };
    }
  }

  function matchesSettings(phrase, settings) {
    const parts = wordsOf(phrase);
    if (parts.length !== settings.words) return false;
    return parts.every((word, i) => {
      const want = settings.lengths[i];
      return want == null || word.length === want;
    });
  }

  function poolFor(settings) {
    return PHRASES.filter((p) => matchesSettings(p, settings));
  }

  function pickAnswer(settings) {
    const pool = poolFor(settings);
    const src = pool.length ? pool : PHRASES;
    return src[Math.floor(Math.random() * src.length)];
  }

  function availableWordCounts() {
    const counts = new Set(PHRASES.map((p) => wordsOf(p).length));
    return [...counts].sort((a, b) => a - b);
  }

  function availableLengths(wordCount, index) {
    const set = new Set();
    for (const phrase of PHRASES) {
      const parts = wordsOf(phrase);
      if (parts.length !== wordCount || !parts[index]) continue;
      set.add(parts[index].length);
    }
    return [...set].sort((a, b) => a - b);
  }

  function labelSettings(settings) {
    const lens = settings.lengths.map((n) => (n == null ? "?" : n));
    const allAny = settings.lengths.every((n) => n == null);
    return allAny
      ? `${settings.words} từ · bất kỳ`
      : `${settings.words} từ · ${lens.join(" + ")}`;
  }

  const settings = loadSettings();
  const matched = poolFor(settings);
  const pageParams = new URLSearchParams(location.search);
  const ROOM_MODE = pageParams.has("room") || pageParams.get("mode") === "party";
  const answer = ROOM_MODE ? "" : pickAnswer(settings);
  window.__DOANCHU_ANSWER = ROOM_MODE ? "" : answer;
  window.__DOANCHU_SETTINGS = settings;
  window.__DOANCHU_ROOM_MODE = ROOM_MODE;

  const markApi = globalThis.DOANCHU_MARK || {};
  const markGuess = markApi.markGuess;
  const isPlayableGuess =
    markApi.isPlayableGuess ||
    ((guess, ans) =>
      guess.length === ans.length && guess.indexOf(" ") === ans.indexOf(" "));

  function json(obj, status = 200) {
    return new Response(JSON.stringify(obj), {
      status,
      headers: { "Content-Type": "application/json; charset=UTF-8" }
    });
  }

  const origFetch = window.fetch.bind(window);

  window.fetch = async (input, init = {}) => {
    const url = String(typeof input === "string" ? input : input.url || "");
    if (url.includes("getWord.php")) {
      if (ROOM_MODE) {
        const api = window.DOANCHU_ROOM;
        if (!api || !api.whenStarted) {
          return json({ error: "room chưa sẵn sàng" }, 503);
        }
        const info = await api.whenStarted();
        const date = "room-" + info.room_id + "-" + String(info.started_at || 0);
        if (info.board && info.board.guesses && info.board.guesses.length) {
          try {
            localStorage.setItem("doanchu:v3:" + date, JSON.stringify({
              version: 3,
              date,
              len: info.length,
              spaceIndex: info.spaceIndex,
              guesses: info.board.guesses,
              marksList: info.board.marksList,
              current: "",
              solvedAnswer: ""
            }));
          } catch (e) {}
        }
        return json({
          date,
          length: info.length,
          spaceIndex: info.spaceIndex
        });
      }
      return json({
        date: "unlimited-" + Date.now(),
        length: answer.length,
        spaceIndex: answer.indexOf(" ")
      });
    }
    if (url.includes("checkGuess.php")) {
      let body = {};
      try {
        body = JSON.parse(init.body || "{}");
      } catch (e) {
        body = {};
      }
      const guess = String(body.guess || "").normalize("NFC").toLowerCase();
      if (ROOM_MODE) {
        const api = window.DOANCHU_ROOM;
        if (!api || !api.submitGuess) {
          return json({ status: "error", message: "Chưa vào phòng." });
        }
        try {
          const result = await api.submitGuess(guess, Number(body.attempt) || 1);
          return json(result);
        } catch (err) {
          return json({ status: "error", message: err.message || "Từ không hợp lệ." });
        }
      }
      if (!isPlayableGuess(guess, answer)) {
        return json({ status: "error", message: "Từ không hợp lệ." });
      }
      const marks = markGuess(guess, answer);
      const won = guess === answer;
      const attempt = Number(body.attempt) || 1;
      const out = { status: "success", marks, won };
      if (won || attempt >= 6) out.solution = answer;
      return json(out);
    }
    if (url.includes("logResult.php")) {
      return json({ ok: true });
    }
    return origFetch(input, init);
  };

  function readForm() {
    const words = Number(document.getElementById("settings-words").value) || 2;
    const lengths = Array.from({ length: words }, (_, i) => {
      const el = document.getElementById("settings-len-" + i);
      const n = Number(el && el.value);
      return Number.isFinite(n) && n > 0 ? n : null;
    });
    return { words, lengths };
  }

  function optionHtml(value, label, selected) {
    const sel = selected ? " selected" : "";
    return `<option value="${value}"${sel}>${label}</option>`;
  }

  function renderLengthSelects(current) {
    const wrap = document.getElementById("settings-lengths");
    wrap.innerHTML = Array.from({ length: current.words }, (_, i) => {
      const opts = [
        optionHtml("", "bất kỳ", current.lengths[i] == null),
        ...availableLengths(current.words, i).map((n) =>
          optionHtml(String(n), n + " chữ", current.lengths[i] === n)
        )
      ].join("");
      return `<label class="settings-field">Từ ${i + 1}
        <select id="settings-len-${i}">${opts}</select>
      </label>`;
    }).join("");
  }

  function updateMatchHint() {
    const next = readForm();
    const n = poolFor(next).length;
    const hint = document.getElementById("settings-count");
    const summary = document.getElementById("settings-summary");
    if (hint) {
      hint.textContent = n
        ? `${n.toLocaleString("vi-VN")} cụm khớp`
        : "Không có cụm nào khớp — chọn độ dài khác";
      hint.classList.toggle("empty", n === 0);
    }
    if (summary) summary.textContent = labelSettings(next);
  }

  function mountSettings() {
    if (document.getElementById("game-settings")) return;
    const bar = document.querySelector(".howto-bar");
    if (!bar || !bar.parentElement) return;

    const box = document.createElement("details");
    box.id = "game-settings";
    const counts = availableWordCounts();
    const wordOpts = counts
      .map((n) => optionHtml(String(n), n + " từ", settings.words === n))
      .join("");
    box.innerHTML = `
      <summary>Cài đặt <span id="settings-summary">${labelSettings(settings)}</span></summary>
      <div class="settings-body">
        <div class="settings-row">
          <label class="settings-field">Số từ
            <select id="settings-words">${wordOpts}</select>
          </label>
          <div id="settings-lengths" class="settings-row"></div>
        </div>
        <p id="settings-count" class="hint"></p>
        <button type="button" id="settings-go">Sinh câu hỏi</button>
      </div>
    `;
    bar.parentElement.insertBefore(box, bar);
    renderLengthSelects(settings);
    updateMatchHint();
    if (!matched.length && PHRASES.length) {
      const hint = document.getElementById("settings-count");
      if (hint) {
        hint.textContent = "Cài đặt cũ không khớp kho từ — đang chơi ngẫu nhiên. Chọn lại rồi sinh câu hỏi.";
        hint.classList.add("empty");
      }
    }

    document.getElementById("settings-words").addEventListener("change", () => {
      const next = readForm();
      next.lengths = Array.from({ length: next.words }, () => null);
      renderLengthSelects(next);
      updateMatchHint();
    });
    document.getElementById("settings-lengths").addEventListener("change", updateMatchHint);
    const goBtn = document.getElementById("settings-go");
    if (ROOM_MODE && goBtn) goBtn.textContent = "Lưu cho phòng";
    goBtn.addEventListener("click", () => {
      const next = readForm();
      if (!poolFor(next).length) {
        updateMatchHint();
        return;
      }
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
      if (ROOM_MODE) {
        updateMatchHint();
        return;
      }
      location.reload();
    });
  }

  async function holdSoloSlot() {
    if (ROOM_MODE) return;
    let token = sessionStorage.getItem("doanchu:soloToken") || "";
    try {
      const res = await origFetch("/api/presence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token })
      });
      if (res.status === 404) return;
      const data = await res.json().catch(() => ({}));
      if (data.token) sessionStorage.setItem("doanchu:soloToken", data.token);
      if (res.ok) {
        document.getElementById("solo-full")?.remove();
        return;
      }
      let box = document.getElementById("solo-full");
      if (!box) {
        box = document.createElement("p");
        box.id = "solo-full";
        document.querySelector(".container")?.prepend(box);
      }
      box.textContent = data.error || "Máy chủ đang đông — thử lại sau.";
    } catch (e) {}
  }

  window.addEventListener("DOMContentLoaded", () => {
    mountSettings();
    holdSoloSlot();
    if (!ROOM_MODE) setInterval(holdSoloSlot, 20000);
    const reload = () => location.reload();
    const newBtn = document.getElementById("new-game");
    if (newBtn) {
      newBtn.onclick = () => {
        if (ROOM_MODE && window.DOANCHU_ROOM && window.DOANCHU_ROOM.rematch) {
          window.DOANCHU_ROOM.rematch();
          return;
        }
        reload();
      };
    }
    const close = document.getElementById("endgame-close");
    const row = close && close.parentElement;
    if (row && !document.getElementById("endgame-new")) {
      const b = document.createElement("button");
      b.id = "endgame-new";
      b.textContent = "Ván mới";
      b.style.cssText =
        "padding:12px 24px;background:#fc0;color:#831810;border:none;border-radius:10px;font-weight:800;font-size:18px;cursor:pointer;";
      b.onclick = () => {
        if (ROOM_MODE && window.DOANCHU_ROOM && window.DOANCHU_ROOM.rematch) {
          window.DOANCHU_ROOM.rematch();
          return;
        }
        reload();
      };
      row.insertBefore(b, close);
    }
  });
})();
