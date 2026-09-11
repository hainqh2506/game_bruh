/*
 * Client game logic extracted from https://doanchu.vn/ (V3).
 * Hex identifiers renamed for readability. Behavior is unchanged.
 * Puzzle answers and the valid-word dictionary are NOT in this file;
 * they are served by getWord.php / checkGuess.php on the server.
 */
(() => {
  const VIET_CHARS = ["a", "á", "à", "ạ", "ả", "ã", "ă", "ắ", "ằ", "ặ", "ẳ", "ẵ", "â", "ấ", "ầ", "ậ", "ẩ", "ẫ", "e", "é", "è", "ẹ", "ẻ", "ẽ", "ê", "ế", "ề", "ệ", "ể", "ễ", "i", "í", "ì", "ị", "ỉ", "ĩ", "o", "ó", "ò", "ọ", "ỏ", "õ", "ô", "ố", "ồ", "ộ", "ổ", "ỗ", "ơ", "ớ", "ờ", "ợ", "ở", "ỡ", "u", "ú", "ù", "ụ", "ủ", "ũ", "ư", "ứ", "ừ", "ự", "ử", "ữ", "y", "ý", "ỳ", "ỵ", "ỷ", "ỹ", "đ", "none", "acute", "grave", "dot", "hook", "tilde"],
    CHAR_TO_BASE_TONE = {
      a: {
        b: "a",
        t: "none"
      },
      á: {
        b: "a",
        t: "acute"
      },
      à: {
        b: "a",
        t: "grave"
      },
      ạ: {
        b: "a",
        t: "dot"
      },
      ả: {
        b: "a",
        t: "hook"
      },
      ã: {
        b: "a",
        t: "tilde"
      },
      ă: {
        b: "ă",
        t: "none"
      },
      ắ: {
        b: "ă",
        t: "acute"
      },
      ằ: {
        b: "ă",
        t: "grave"
      },
      ặ: {
        b: "ă",
        t: "dot"
      },
      ẳ: {
        b: "ă",
        t: "hook"
      },
      ẵ: {
        b: "ă",
        t: "tilde"
      },
      â: {
        b: "â",
        t: "none"
      },
      ấ: {
        b: "â",
        t: "acute"
      },
      ầ: {
        b: "â",
        t: "grave"
      },
      ậ: {
        b: "â",
        t: "dot"
      },
      ẩ: {
        b: "â",
        t: "hook"
      },
      ẫ: {
        b: "â",
        t: "tilde"
      },
      e: {
        b: "e",
        t: "none"
      },
      é: {
        b: "e",
        t: "acute"
      },
      è: {
        b: "e",
        t: "grave"
      },
      ẹ: {
        b: "e",
        t: "dot"
      },
      ẻ: {
        b: "e",
        t: "hook"
      },
      ẽ: {
        b: "e",
        t: "tilde"
      },
      ê: {
        b: "ê",
        t: "none"
      },
      ế: {
        b: "ê",
        t: "acute"
      },
      ề: {
        b: "ê",
        t: "grave"
      },
      ệ: {
        b: "ê",
        t: "dot"
      },
      ể: {
        b: "ê",
        t: "hook"
      },
      ễ: {
        b: "ê",
        t: "tilde"
      },
      i: {
        b: "i",
        t: "none"
      },
      í: {
        b: "i",
        t: "acute"
      },
      ì: {
        b: "i",
        t: "grave"
      },
      ị: {
        b: "i",
        t: "dot"
      },
      ỉ: {
        b: "i",
        t: "hook"
      },
      ĩ: {
        b: "i",
        t: "tilde"
      },
      o: {
        b: "o",
        t: "none"
      },
      ó: {
        b: "o",
        t: "acute"
      },
      ò: {
        b: "o",
        t: "grave"
      },
      ọ: {
        b: "o",
        t: "dot"
      },
      ỏ: {
        b: "o",
        t: "hook"
      },
      õ: {
        b: "o",
        t: "tilde"
      },
      ô: {
        b: "ô",
        t: "none"
      },
      ố: {
        b: "ô",
        t: "acute"
      },
      ồ: {
        b: "ô",
        t: "grave"
      },
      ộ: {
        b: "ô",
        t: "dot"
      },
      ổ: {
        b: "ô",
        t: "hook"
      },
      ỗ: {
        b: "ô",
        t: "tilde"
      },
      ơ: {
        b: "ơ",
        t: "none"
      },
      ớ: {
        b: "ơ",
        t: "acute"
      },
      ờ: {
        b: "ơ",
        t: "grave"
      },
      ợ: {
        b: "ơ",
        t: "dot"
      },
      ở: {
        b: "ơ",
        t: "hook"
      },
      ỡ: {
        b: "ơ",
        t: "tilde"
      },
      u: {
        b: "u",
        t: "none"
      },
      ú: {
        b: "u",
        t: "acute"
      },
      ù: {
        b: "u",
        t: "grave"
      },
      ụ: {
        b: "u",
        t: "dot"
      },
      ủ: {
        b: "u",
        t: "hook"
      },
      ũ: {
        b: "u",
        t: "tilde"
      },
      ư: {
        b: "ư",
        t: "none"
      },
      ứ: {
        b: "ư",
        t: "acute"
      },
      ừ: {
        b: "ư",
        t: "grave"
      },
      ự: {
        b: "ư",
        t: "dot"
      },
      ử: {
        b: "ư",
        t: "hook"
      },
      ữ: {
        b: "ư",
        t: "tilde"
      },
      y: {
        b: "y",
        t: "none"
      },
      ý: {
        b: "y",
        t: "acute"
      },
      ỳ: {
        b: "y",
        t: "grave"
      },
      ỵ: {
        b: "y",
        t: "dot"
      },
      ỷ: {
        b: "y",
        t: "hook"
      },
      ỹ: {
        b: "y",
        t: "tilde"
      },
      đ: {
        b: "đ",
        t: "none"
      }
    };
  const BASE_TONE_TO_CHAR = {
    a: {
      none: "a",
      acute: "á",
      grave: "à",
      dot: "ạ",
      hook: "ả",
      tilde: "ã"
    },
    ă: {
      none: "ă",
      acute: "ắ",
      grave: "ằ",
      dot: "ặ",
      hook: "ẳ",
      tilde: "ẵ"
    },
    â: {
      none: "â",
      acute: "ấ",
      grave: "ầ",
      dot: "ậ",
      hook: "ẩ",
      tilde: "ẫ"
    },
    e: {
      none: "e",
      acute: "é",
      grave: "è",
      dot: "ẹ",
      hook: "ẻ",
      tilde: "ẽ"
    },
    ê: {
      none: "ê",
      acute: "ế",
      grave: "ề",
      dot: "ệ",
      hook: "ể",
      tilde: "ễ"
    },
    i: {
      none: "i",
      acute: "í",
      grave: "ì",
      dot: "ị",
      hook: "ỉ",
      tilde: "ĩ"
    },
    o: {
      none: "o",
      acute: "ó",
      grave: "ò",
      dot: "ọ",
      hook: "ỏ",
      tilde: "õ"
    },
    ô: {
      none: "ô",
      acute: "ố",
      grave: "ồ",
      dot: "ộ",
      hook: "ổ",
      tilde: "ỗ"
    },
    ơ: {
      none: "ơ",
      acute: "ớ",
      grave: "ờ",
      dot: "ợ",
      hook: "ở",
      tilde: "ỡ"
    },
    u: {
      none: "u",
      acute: "ú",
      grave: "ù",
      dot: "ụ",
      hook: "ủ",
      tilde: "ũ"
    },
    ư: {
      none: "ư",
      acute: "ứ",
      grave: "ừ",
      dot: "ự",
      hook: "ử",
      tilde: "ữ"
    },
    y: {
      none: "y",
      acute: "ý",
      grave: "ỳ",
      dot: "ỵ",
      hook: "ỷ",
      tilde: "ỹ"
    },
    đ: {
      none: "đ"
    }
  };

  function decomposeChar(c) {
    const l = (c || "").toLowerCase();
    return CHAR_TO_BASE_TONE[l] || {
      b: l,
      t: "none"
    };
  }

  function composeChar(b, t) {
    const x = BASE_TONE_TO_CHAR[b] || BASE_TONE_TO_CHAR[decomposeChar(b).b];
    return (x && x[t]) || b;
  }

  function findTonePosition(r, s) {
    const e = r.length,
      g = spaceIndex,
      E = (s < g) ? Math.min(e, g) : e,
      I = [],
      B = [];
    for (let i = s; i < E; i++) {
      const d = decomposeChar(r[i]);
      if ("aăâeêioôơuưy".includes(d.b)) {
        I.push(i);
        B.push(d.b);
      }
    }
    if (!I.length) return null;
    if (I.length >= 2 && I[0] === s + 1) {
      const p = decomposeChar(r[s]).b,
        f = B[0];
      if ((p === "q" && f === "u") || (p === "g" && f === "i")) {
        I.shift();
        B.shift();
        if (!I.length) return null;
      }
    }
    for (let k = 0; k < B.length - 1; k++) {
      const b1 = B[k],
        b2 = B[k + 1];
      if ((b1 === "u" || b1 === "ư") && (b2 === "o" || b2 === "ô" || b2 === "ơ")) return I[k + 1];
    }
    for (let k = 0; k < B.length; k++)
      if (B[k] === "ă" || B[k] === "â") return I[k];
    for (let k = 0; k < B.length; k++)
      if (["ê", "ô", "ơ"].includes(B[k])) return I[k];
    if (B.length === 3) return I[1];
    if (B.length === 2) {
      const pair = B[0] + B[1];
      if (I[1] < E - 1) return I[1];
      if (pair === "oa" || pair === "oe" || pair === "uy") return I[1];
      return I[0];
    }
    return I[0];
  }

  function applyTone(r, s, t) {
    const ti = findTonePosition(r, s);
    if (ti === null) return null;
    const d = decomposeChar(r[ti]);
    return r.slice(0, ti) + composeChar(d.b, t) + r.slice(ti + 1);
  }
  const rowsEl = document.getElementById("rows"),
    messageEl = document.getElementById("message"),
    keyboardEl = document.getElementById("kb"),
    lenHintEl = document.getElementById("lenhint"),
    lengthInfoEl = document.getElementById("length-info"),
    stickyShareEl = document.getElementById("sticky-share");
  let guesses = [],
    marksList = [],
    currentInput = "",
    MAX_ATTEMPTS = 6,
    resultsGrid = [],
    shareState = null,
    gameOver = false,
    popupOpen = false,
    solvedAnswer = "",
    puzzleDate = "",
    storageKey = "",
    boardLength = 0,
    spaceIndex = 0,
    saveTimer, word1ToneWindowUntil = 0,
    lastKey = "",
    lastKeyTime = 0;
  const stripSpaces = s => (s || "").replace(/\s+/g, "");

  function insertSpace(r) {
    const c = boardLength - 1,
      x = r.slice(0, c);
    return x.slice(0, spaceIndex) + " " + x.slice(spaceIndex);
  }

  function makeStorageKey() {
    return `doanchu:v3:${puzzleDate||new Date().toISOString().slice(0,10)}`;
  }

  function scheduleSave() {
    if (!storageKey) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(storageKey, JSON.stringify({
          version: 3,
          date: puzzleDate || null,
          len: boardLength,
          spaceIndex: spaceIndex,
          guesses: guesses,
          marksList: marksList,
          current: currentInput,
          solvedAnswer: solvedAnswer
        }));
      } catch (e) {}
    }, 300);
  }

  function pruneOldSaves() {
    try {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const k = localStorage.key(i);
        if (k && k.startsWith("doanchu:v3") && k !== storageKey) localStorage.removeItem(k);
      }
    } catch (e) {}
  }

  function rebuildResults() {
    resultsGrid = [];
    for (const m of (marksList || [])) {
      if (!Array.isArray(m)) continue;
      const rc = [];
      for (let i = 0; i < m.length; i++) {
        if (i === spaceIndex) {
          rc.push(null);
          continue;
        }
        const v = m[i];
        rc.push(v === "green" ? "c" : v === "yellow" ? "p" : v === "blue" ? "b" : "a");
      }
      resultsGrid.push(rc);
    }
  }

  function getGameStatus() {
    const w = marksList.some(m => Array.isArray(m) && m.every((v, i) => i === spaceIndex || v === "green")),
      o = w || guesses.length >= MAX_ATTEMPTS;
    return {
      over: o,
      won: w
    };
  }

  function syncGameOverUi() {
    const s = getGameStatus();
    gameOver = s.over;
    shareState = gameOver ? {
      results: resultsGrid.slice(),
      maxAttempts: MAX_ATTEMPTS
    } : null;
    if (stickyShareEl) stickyShareEl.hidden = !(gameOver && !popupOpen);
  }

  function restoreFromStorage() {
    if (!storageKey) return false;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return false;
      const d = JSON.parse(raw);
      if (!d || typeof d !== "object" || d.len !== boardLength) return false;
      guesses = Array.isArray(d.guesses) ? d.guesses.slice(0, MAX_ATTEMPTS) : [];
      marksList = Array.isArray(d.marksList) ? d.marksList.slice(0, MAX_ATTEMPTS) : [];
      currentInput = d.current || "";
      solvedAnswer = d.solvedAnswer || "";
      rebuildResults();
      popupOpen = false;
      syncGameOverUi();
      renderBoard();
      return true;
    } catch (e) {
      return false;
    }
  }

  function cursorIndex() {
    const f = stripSpaces(currentInput).length;
    return !boardLength ? null : (f <= spaceIndex ? f : f + 1);
  }
  const TONE_KEYS = {
    s: "acute",
    f: "grave",
    r: "hook",
    x: "tilde",
    j: "dot",
    z: "none"
  };

  function applyKey(r, k) {
    k = (k || "").toLowerCase();
    if (!k) return r;
    const now = Date.now(),
      isl = k === "s" || k === "r" || k === "x";
    if (k in TONE_KEYS) {
      const tn = TONE_KEYS[k];
      if (r.length >= spaceIndex) {
        if (r.length === spaceIndex) {
          if (now <= word1ToneWindowUntil) {
            const td = applyTone(r, 0, tn);
            if (td !== null) return td;
          }
          return isl ? (r + k) : r;
        }
        const td2 = applyTone(r, spaceIndex, tn);
        if (td2 !== null) return td2;
        return isl ? (r + k) : r;
      }
      const td1 = applyTone(r, 0, tn);
      if (td1 !== null) return td1;
      return isl ? (r + k) : r;
    }
    if ("adeouw".includes(k)) return applyVowelKey(r, k);
    if (/^[a-z]$/.test(k)) return k === "w" ? r : (r + k);
    return r;
  }

  function applyVowelKey(r, k) {
    if (!r) return k === "w" ? r : (r + k);
    if (r.length === spaceIndex && k !== "w") {
      if (!(lastKey === k && (Date.now() - lastKeyTime) <= 700)) return r + k;
    }
    const i = r.length - 1,
      p = r[i];
    if (k === "d" && p === "d") return r.slice(0, i) + "đ";
    if (k === "a" && p === "a") return r.slice(0, i) + "â";
    if (k === "w" && p === "a") return r.slice(0, i) + "ă";
    if (k === "e" && p === "e") return r.slice(0, i) + "ê";
    if (k === "o" && p === "o") return r.slice(0, i) + "ô";
    if (k === "w" && p === "o") return r.slice(0, i) + "ơ";
    if (k === "w" && p === "u") return r.slice(0, i) + "ư";
    if (k === "w") {
      const st = r.length > spaceIndex ? spaceIndex : 0;
      for (let j = r.length - 1; j > st; j--) {
        const dj = decomposeChar(r[j]),
          di = decomposeChar(r[j - 1]);
        if (di.b === "u" && dj.b === "o") return r.slice(0, j - 1) + composeChar("ư", di.t) + composeChar("ơ", dj.t) + r.slice(j + 1);
      }
      for (let j = r.length - 1; j >= st; j--) {
        const d = decomposeChar(r[j]);
        if (d.b === "a") return r.slice(0, j) + composeChar("ă", d.t) + r.slice(j + 1);
        if (d.b === "o") return r.slice(0, j) + composeChar("ơ", d.t) + r.slice(j + 1);
        if (d.b === "u") return r.slice(0, j) + composeChar("ư", d.t) + r.slice(j + 1);
      }
    }
    return r + k;
  }

  function renderBoard() {
    rowsEl.innerHTML = "";
    if (!boardLength) {
      const p = document.createElement("div");
      p.className = "loading";
      p.textContent = "Đang chờ từ khóa…";
      rowsEl.appendChild(p);
      return;
    }
    const ca = cursorIndex();
    for (let r = 0; r < MAX_ATTEMPTS; r++) {
      const row = document.createElement("div");
      row.className = "row";
      const sh = (r === guesses.length) ? (currentInput || "") : (guesses[r] || "");
      for (let i = 0; i < boardLength; i++) {
        if (i === spaceIndex) {
          const g = document.createElement("div");
          g.className = "gap";
          row.appendChild(g);
          continue;
        }
        const t = document.createElement("div"),
          mk = marksList[r]?.[i];
        t.className = "tile " + (mk === "green" ? "t-green" : mk === "yellow" ? "t-yellow" : mk === "blue" ? "t-blue" : "t-grey");
        t.textContent = sh[i] || "";
        if (r === guesses.length && i === ca && !gameOver) t.classList.add("cursor");
        row.appendChild(t);
      }
      rowsEl.appendChild(row);
    }
    scheduleSave();
  }

  function setCurrent(v) {
    currentInput = insertSpace((v || "").toLowerCase().slice(0, boardLength - 1));
    renderBoard();
  }

  function typeKey(k) {
    if (!boardLength || gameOver) return;
    const raw = stripSpaces(currentInput),
      cap = boardLength - 1,
      nxt = applyKey(raw, k);
    if (raw.length >= cap && !(k in TONE_KEYS) && nxt.length > raw.length) return;
    if (raw.length < spaceIndex && nxt.length >= spaceIndex) word1ToneWindowUntil = Date.now() + 700;
    setCurrent(nxt);
    lastKey = (k || "").toLowerCase();
    lastKeyTime = Date.now();
  }

  function backspace() {
    if (!boardLength || gameOver) return;
    const raw = stripSpaces(currentInput);
    if (!raw) return;
    const nxt = raw.slice(0, -1);
    if (nxt.length < spaceIndex) word1ToneWindowUntil = 0;
    setCurrent(nxt);
  }
  let keyboardBound = false;

  function buildKeyboard() {
    keyboardEl.innerHTML = "";
    const ck = (l, w = false, x = "") => {
        const b = document.createElement("button");
        b.className = (w ? "key key--wide" : "key") + (x ? (" " + x) : "");
        b.type = "button";
        b.textContent = l;
        if (l === "Enter") b.setAttribute("aria-label", "Enter");
        if (l === "Del") b.setAttribute("aria-label", "Delete");
        return b;
      },
      r1 = document.createElement("div");
    r1.className = "kb-row";
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"].forEach(k => r1.appendChild(ck(k)));
    keyboardEl.appendChild(r1);
    const r2 = document.createElement("div");
    r2.className = "kb-row row-9";
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"].forEach(k => r2.appendChild(ck(k)));
    keyboardEl.appendChild(r2);
    const r3 = document.createElement("div");
    r3.className = "kb-row";
    r3.appendChild(ck("Enter", true, "enter"));
    ["Z", "X", "C", "V", "B", "N", "M"].forEach(k => r3.appendChild(ck(k)));
    r3.appendChild(ck("Del", true));
    keyboardEl.appendChild(r3);
  }

  function bindKeyboard() {
    if (keyboardBound) return;
    keyboardBound = true;
    keyboardEl.addEventListener("pointerdown", e => {
      e.preventDefault();
      const k = e.target.closest(".key");
      if (!k) return;
      const t = k.textContent.toLowerCase();
      if (t === "enter") submitGuess();
      else if (t === "del") backspace();
      else typeKey(t);
    }, {
      passive: false
    });
  }
  const SHARE_COLORS = {
    g: "#22c55e",
    a: "#6b7280",
    b: "#111827",
    w: "#e5e7eb"
  };
  let previewCache = null;

  function formatShareText(s) {
    const ds = puzzleDate || new Date().toISOString().slice(0, 10),
      [y, m, d] = ds.split("-"),
      st = getGameStatus(),
      at = st.won ? guesses.length : 0;
    let txt = `Đoán Chữ - ${d}.${m}.${y}\n${at}/6\n\n`;
    (s.results || []).forEach(r => {
      let w1 = "",
        w2 = "";
      r.forEach((c, i) => {
        if (c === null) return;
        const em = c === "c" ? "🟩" : c === "p" ? "🟨" : c === "b" ? "🟦" : "⬛";
        if (i < spaceIndex) w1 += em;
        else if (i > spaceIndex) w2 += em;
      });
      txt += `${w1} - ${w2}\n`;
    });
    return txt + "\ndoanchu.vn";
  }
  async function copyText(t) {
    try {
      await navigator.clipboard.writeText(t);
      alert("Đã sao chép! Bạn có thể dán vào bất kỳ ứng dụng nào.");
      return true;
    } catch (e) {
      try {
        const ta = document.createElement("textarea");
        ta.value = t;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        alert("Đã sao chép! Bạn có thể dán vào bất kỳ ứng dụng nào.");
        return true;
      } catch (e2) {
        alert("Không thể sao chép tự động. Hãy thử lại hoặc dùng nút Tải ảnh.");
        return false;
      }
    }
  }
  let popupOpenedAt = 0;

  function showEndgame(w, s) {
    const p = document.getElementById("endgame-popup"),
      m = document.getElementById("endgame-modal"),
      msg = document.getElementById("endgame-message"),
      tw = document.getElementById("endgame-title-wrap");
    if (!p) return;
    p.style.display = "flex";
    document.body.style.overflow = "hidden";
    popupOpen = true;
    popupOpenedAt = Date.now();
    if (tw?.firstElementChild) tw.firstElementChild.textContent = w ? "Chúc mừng!" : "Hết lượt rồi!";
    if (msg) msg.textContent = w ? "Hooray, bạn đã thắng! Hãy chia sẻ bảng màu với bạn bè nhé." : "Thua rồi… thử lại vào ngày mai! Chia sẻ bảng màu của bạn?";
    try {
      const cv = document.getElementById("endgame-preview");
      if (cv) drawPreview(cv, s);
    } catch (err) {}
    const cb = document.getElementById("endgame-close");
    if (cb) cb.onclick = closeEndgame;
    const sb = document.getElementById("endgame-share");
    if (sb) sb.onclick = async () => {
      await copyText(formatShareText(s || {
        results: resultsGrid
      }));
    };
    const db = document.getElementById("endgame-download");
    if (db) db.onclick = () => {
      const cv = document.getElementById("endgame-preview");
      if (cv) cv.toBlob(b => {
        const u = URL.createObjectURL(b),
          a = document.createElement("a");
        a.href = u;
        a.download = "doan-chu-ket-qua.png";
        a.click();
        setTimeout(() => URL.revokeObjectURL(u), 1500);
      }, "image/png");
    };
    p.onclick = e => {
      if (Date.now() - popupOpenedAt < 400) return;
      if (e.target === p) closeEndgame();
    };
    if (m) m.onclick = e => e.stopPropagation();
    syncGameOverUi();
  }

  function closeEndgame() {
    const p = document.getElementById("endgame-popup");
    if (p) p.style.display = "none";
    document.body.style.overflow = "";
    popupOpen = false;
    syncGameOverUi();
  }

  function drawPreview(cv, s) {
    if (previewCache) {
      const ctx = cv.getContext("2d");
      cv.width = previewCache.width;
      cv.height = previewCache.height;
      ctx.drawImage(previewCache, 0, 0);
      return;
    }
    const rows = (s?.results || []).map(r => (r || []).map(c => c == null ? null : (c === "c" ? "c" : "a"))),
      rc = rows.length,
      cc = rows.reduce((m, r) => Math.max(m, r.length), 0),
      tl = 48,
      gp = 6,
      pd = 16,
      fh = 26,
      sc = Math.max(cc, 1),
      sr = Math.max(rc, 1);
    cv.width = Math.max(pd * 2 + sc * tl + Math.max(0, sc - 1) * gp, 100);
    cv.height = Math.max(pd * 2 + sr * tl + Math.max(0, sr - 1) * gp + fh, 100);
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = SHARE_COLORS.b;
    ctx.fillRect(0, 0, cv.width, cv.height);
    for (let r = 0; r < rc; r++) {
      const row = rows[r] || [];
      for (let c = 0; c < cc; c++) {
        if (row[c] == null) continue;
        const x = pd + c * (tl + gp),
          y = pd + r * (tl + gp);
        ctx.beginPath();
        ctx.moveTo(x + 8, y);
        ctx.arcTo(x + tl, y, x + tl, y + tl, 8);
        ctx.arcTo(x + tl, y + tl, x, y + tl, 8);
        ctx.arcTo(x, y + tl, x, y, 8);
        ctx.arcTo(x, y, x + tl, y, 8);
        ctx.closePath();
        ctx.fillStyle = row[c] === "c" ? SHARE_COLORS.g : SHARE_COLORS.a;
        ctx.fill();
      }
    }
    ctx.font = "bold 16px system-ui,-apple-system,Segoe UI,Roboto,Arial";
    ctx.fillStyle = SHARE_COLORS.w;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("doanchu.vn", cv.width / 2, cv.height - fh / 2);
    previewCache = document.createElement("canvas");
    previewCache.width = cv.width;
    previewCache.height = cv.height;
    previewCache.getContext("2d").drawImage(cv, 0, 0);
  }

  function setupPuzzle(l, si, ds) {
    boardLength = l || 0;
    spaceIndex = typeof si === "number" ? si : -1;
    puzzleDate = (typeof ds === "string" && ds) ? ds : puzzleDate;
    storageKey = makeStorageKey();
    pruneOldSaves();
    if (spaceIndex > -1) {
      const inf = `Độ dài hôm nay: ${spaceIndex} + ${boardLength-spaceIndex-1}`;
      if (lengthInfoEl) lengthInfoEl.textContent = inf;
      else if (lenHintEl) lenHintEl.textContent = inf;
    } else {
      if (lengthInfoEl) lengthInfoEl.textContent = "";
      else if (lenHintEl) lenHintEl.textContent = "";
    }
    if (!restoreFromStorage()) {
      rebuildResults();
      popupOpen = false;
      syncGameOverUi();
      renderBoard();
    }
  }
  async function loadPuzzle() {
    const ld = document.getElementById("loader");
    try {
      const res = await fetch("getWord.php", {
        cache: "no-store"
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (data.answer) {
        const ans = (data.answer || "").normalize("NFC");
        setupPuzzle(ans.length, ans.indexOf(" "), data.date);
      } else {
        setupPuzzle(data.length, data.spaceIndex, data.date);
      }
      ld.textContent = "Sẵn sàng!";
      setTimeout(() => ld.remove(), 300);
      initUi();
    } catch (err) {
      ld.classList.add("error");
      ld.textContent = "Lỗi tải dữ liệu: " + err.message;
    }
  }
  let submitting = false;
  async function submitGuess() {
    if (!boardLength || gameOver || submitting) return;
    const raw = stripSpaces(currentInput),
      need = boardLength - 1;
    if (raw.length === spaceIndex) {
      messageEl.textContent = "Hãy điền tiếp từ thứ hai.";
      return;
    }
    if (raw.length < need) {
      messageEl.textContent = "Điền đủ chữ trước đã.";
      return;
    }
    const guess = currentInput;
    for (let i = 0; i < boardLength; i++) {
      if (i === spaceIndex) continue;
      if (!/[a-zA-ZÀ-ỹ]/.test(guess[i] || "")) {
        messageEl.textContent = "Chỉ dùng chữ cái tiếng Việt trong ô.";
        return;
      }
    }
    submitting = true;
    try {
      const res = await fetch("checkGuess.php", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          guess: guess,
          attempt: guesses.length + 1
        })
      });
      if (!res.ok) throw new Error("Lỗi kết nối máy chủ");
      const d = await res.json();
      if (d.status !== "success") {
        messageEl.textContent = d.message || "Từ không hợp lệ.";
        submitting = false;
        return;
      }
      const mk = d.marks;
      guesses.push(guess.toLowerCase());
      marksList.push(mk);
      currentInput = "";
      rebuildResults();
      syncGameOverUi();
      const won = d.won === true;
      if (d.solution) solvedAnswer = d.solution;
      if (won) {
        fetch("logResult.php", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            won: 1,
            guesses: guesses.length
          })
        }).catch(() => {});
        const dw = solvedAnswer || guess;
        messageEl.classList.add("reveal");
        messageEl.innerHTML = "🎉 Chính xác!<br><span>" + dw.toUpperCase() + "</span>";
        try {
          showEndgame(true, {
            results: resultsGrid,
            maxAttempts: MAX_ATTEMPTS
          });
        } catch (e) {}
      } else if (guesses.length >= MAX_ATTEMPTS) {
        fetch("logResult.php", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            won: 0,
            guesses: guesses.length
          })
        }).catch(() => {});
        messageEl.textContent = "";
        messageEl.classList.add("reveal");
        messageEl.innerHTML = "Hết lượt. Cụm từ là:<br><span>" + (solvedAnswer || "").toUpperCase() + "</span>";
        try {
          showEndgame(false, {
            results: resultsGrid,
            maxAttempts: MAX_ATTEMPTS
          });
        } catch (e) {}
      } else {
        messageEl.classList.remove("reveal");
        messageEl.textContent = "";
      }
      renderBoard();
    } catch (err) {
      messageEl.textContent = err.message || "Không thể kết nối đến máy chủ";
    } finally {
      submitting = false;
    }
  }

  function initUi() {
    renderBoard();
    buildKeyboard();
    bindKeyboard();
    if (stickyShareEl) {
      stickyShareEl.onclick = async () => {
        if (!shareState || popupOpen) return;
        await copyText(formatShareText(shareState));
      };
    }
    window.addEventListener("keydown", e => {
      const k = e.key.toLowerCase();
      if (k === "enter") {
        e.preventDefault();
        submitGuess();
        return;
      }
      if (k === "backspace") {
        e.preventDefault();
        backspace();
        return;
      }
      if (k === " ") {
        e.preventDefault();
        return;
      }
      if (k.length === 1) {
        e.preventDefault();
        typeKey(k);
      }
    });
    if ((navigator.maxTouchPoints > 0) || ("ontouchstart" in window)) {
      ["gesturestart", "gesturechange", "gestureend"].forEach(ev => {
        window.addEventListener(ev, e => e.preventDefault(), {
          passive: false
        });
      });
    }
    syncGameOverUi();
  }
  loadPuzzle();
})();
