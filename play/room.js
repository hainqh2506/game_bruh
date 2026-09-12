/* Room party: lobby + WebSocket. Peers see name / attempts / done only. */
(() => {
  const STORE = {
    room: "doanchu:roomId",
    token: "doanchu:roomToken",
    name: "doanchu:playerName",
    player: "doanchu:playerId"
  };
  function normalizeRoomCode(raw) {
    const text = String(raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
    return text.length === 4 ? text : "";
  }

  function pageUrl(roomId, party) {
    if (roomId) return location.pathname + "?room=" + encodeURIComponent(roomId);
    if (party) return location.pathname + "?mode=party";
    return location.pathname;
  }

  const params = new URLSearchParams(location.search);
  const queryRoom = normalizeRoomCode(params.get("room"));
  const badRoom = params.has("room") && !queryRoom;
  const partyMode = Boolean(queryRoom) || badRoom || params.get("mode") === "party";
  const cleanUrl = pageUrl(queryRoom, partyMode);
  if (location.pathname + location.search + location.hash !== cleanUrl) {
    history.replaceState(null, "", cleanUrl);
  }
  if (document.body) {
    document.body.classList.toggle("solo-play", !partyMode);
    document.body.classList.toggle("party-lobby", partyMode);
  }

  let startedResolve;
  const startedPromise = new Promise((resolve) => {
    startedResolve = resolve;
  });
  let ws = null;
  let pingTimer = null;
  let reconnectTimer = null;
  const guessWaiters = [];
  const state = {
    room_id: queryRoom,
    token: "",
    player_id: "",
    name: sessionStorage.getItem(STORE.name) || "",
    status: queryRoom ? "lobby" : "idle",
    host_id: "",
    players: [],
    ranking: [],
    error: "",
    round: 1,
    total_rounds: 1,
    time_limit: 0,
    started_at: 0,
    round_summary: null
  };

  let roundTimer = null;
  let nextRoundCountdownTimer = null;

  function stopTimer() {
    if (roundTimer) {
      clearInterval(roundTimer);
      roundTimer = null;
    }
    const timerEl = document.getElementById("room-timer");
    if (timerEl) timerEl.textContent = "";
  }

  function stopNextRoundCountdown() {
    if (nextRoundCountdownTimer) {
      clearInterval(nextRoundCountdownTimer);
      nextRoundCountdownTimer = null;
    }
    const cdEl = document.getElementById("next-round-cd");
    if (cdEl) cdEl.textContent = "";
  }

  function startTimer() {
    stopTimer();
    if (!state.time_limit || state.status !== "playing") return;
    function tick() {
      const now = Math.floor(Date.now() / 1000);
      const start = state.started_at || now;
      const elapsed = now - start;
      const left = Math.max(0, state.time_limit - elapsed);
      const mins = String(Math.floor(left / 60)).padStart(2, "0");
      const secs = String(left % 60).padStart(2, "0");
      const timerEl = document.getElementById("room-timer");
      if (timerEl) {
        timerEl.textContent = `⏱️ ${mins}:${secs}`;
        timerEl.classList.toggle("danger", left <= 20);
      }
      if (left <= 0) {
        stopTimer();
      }
    }
    tick();
    roundTimer = setInterval(tick, 1000);
  }

  function startNextRoundCountdown() {
    if (nextRoundCountdownTimer) {
      clearInterval(nextRoundCountdownTimer);
      nextRoundCountdownTimer = null;
    }
    let left = 5;
    function tick() {
      const cdEl = document.getElementById("next-round-cd");
      if (cdEl) cdEl.textContent = `(${left}s)`;
      if (left <= 0) {
        clearInterval(nextRoundCountdownTimer);
        nextRoundCountdownTimer = null;
        if (isHost()) {
          send("next_round");
        }
      }
      left--;
    }
    tick();
    nextRoundCountdownTimer = setInterval(tick, 1000);
  }

  function loadSettings() {
    try {
      return JSON.parse(localStorage.getItem("doanchu:settings") || "{}");
    } catch (e) {
      return {};
    }
  }

  function saveAuth(data) {
    if (data.room_id) sessionStorage.setItem(STORE.room, data.room_id);
    if (data.token) sessionStorage.setItem(STORE.token, data.token);
    if (data.player_id) sessionStorage.setItem(STORE.player, data.player_id);
    if (data.name) {
      state.name = data.name;
      sessionStorage.setItem(STORE.name, data.name);
    }
    state.room_id = data.room_id || state.room_id;
    state.token = data.token || state.token;
    state.player_id = data.player_id || state.player_id;
  }

  function storedToken() {
    return sessionStorage.getItem(STORE.token) || "";
  }

  function storedRoom() {
    return normalizeRoomCode(sessionStorage.getItem(STORE.room) || "");
  }

  function tokenFor(roomId) {
    const room = normalizeRoomCode(roomId);
    if (!room || storedRoom() !== room) return "";
    return storedToken();
  }

  async function api(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  function stashSolution(sol) {
    if (!sol) return;
    window.__DOANCHU_ROOM_SOLUTION = sol;
    if (typeof window.__DOANCHU_REVEAL === "function") {
      window.__DOANCHU_REVEAL(sol);
    }
  }

  function resolveStarted(data) {
    if (data.length == null) return;
    stashSolution(data.solution);
    startedResolve({
      room_id: data.room_id || state.room_id,
      length: data.length,
      spaceIndex: data.spaceIndex,
      started_at: data.started_at || 0,
      board: data.board || { guesses: [], marksList: [] },
      solution: data.solution || ""
    });
  }

  function applyRoom(data) {
    state.room_id = data.room_id || state.room_id;
    state.status = data.status || state.status;
    state.host_id = data.host_id || state.host_id;
    state.players = data.players || state.players;
    state.round = data.round || state.round || 1;
    state.total_rounds = data.total_rounds || state.total_rounds || 1;
    state.time_limit = data.time_limit != null ? data.time_limit : state.time_limit;
    state.started_at = data.started_at || state.started_at || 0;
    if (data.you) state.player_id = data.you.id;
    if (data.ranking) state.ranking = data.ranking;
    if (data.status === "playing" || data.status === "round_summary" || data.status === "finished") {
      resolveStarted(data);
    }
    if (data.status === "playing" && state.time_limit > 0) {
      startTimer();
    } else if (data.status !== "playing") {
      stopTimer();
    }
    if (data.status !== "round_summary") {
      stopNextRoundCountdown();
    }
    render();
  }

  function handle(msg) {
    switch (msg.type) {
      case "room":
        applyRoom(msg);
        break;
      case "started":
        stopNextRoundCountdown();
        state.status = "playing";
        state.round = msg.round || state.round || 1;
        state.total_rounds = msg.total_rounds || state.total_rounds || 1;
        state.time_limit = msg.time_limit != null ? msg.time_limit : state.time_limit;
        state.started_at = msg.started_at || 0;
        state.players = msg.players || state.players;
        state.round_summary = null;
        resolveStarted(msg);
        if (state.time_limit > 0) startTimer();
        if (document.querySelector(".row .tile")) {
          location.reload();
          return;
        }
        render();
        break;
      case "round_finished":
        state.status = "round_summary";
        state.round = msg.round || state.round;
        state.total_rounds = msg.total_rounds || state.total_rounds;
        state.ranking = msg.ranking || [];
        state.round_summary = msg;
        if (msg.players) state.players = msg.players;
        stashSolution(msg.solution);
        stopTimer();
        render();
        startNextRoundCountdown();
        break;
      case "guess_result": {
        stashSolution(msg.solution);
        const waiter = guessWaiters.shift();
        if (waiter) waiter.resolve(msg);
        break;
      }
      case "error": {
        const waiter = guessWaiters.shift();
        if (waiter) waiter.reject(new Error(msg.message || "Lỗi"));
        else {
          state.error = msg.message || "Lỗi";
          render();
        }
        break;
      }
      case "peer_update":
      case "peer_solved":
        if (msg.players) state.players = msg.players;
        render();
        break;
      case "finished":
        stopNextRoundCountdown();
        state.status = "finished";
        state.round = msg.round || state.round;
        state.total_rounds = msg.total_rounds || state.total_rounds;
        state.ranking = msg.ranking || [];
        if (msg.players) state.players = msg.players;
        stashSolution(msg.solution);
        stopTimer();
        render();
        break;
      case "ping":
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "ping" }));
        break;
      default:
        break;
    }
  }

  function stopPing() {
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
  }

  function connect() {
    const roomId = normalizeRoomCode(state.room_id || queryRoom);
    const token = tokenFor(roomId) || (storedRoom() === roomId ? state.token : "");
    if (!roomId || !token) return;
    if (ws && (ws.readyState === 0 || ws.readyState === 1)) return;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(
      `${proto}//${location.host}/ws?room=${encodeURIComponent(roomId)}&token=${encodeURIComponent(token)}`
    );
    ws.onmessage = (ev) => {
      try {
        handle(JSON.parse(ev.data));
      } catch (e) {}
    };
    ws.onopen = () => {
      state.error = "";
      stopPing();
      pingTimer = setInterval(() => {
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "ping" }));
      }, 20000);
      render();
    };
    ws.onclose = () => {
      stopPing();
      if (!state.room_id || !storedToken()) return;
      if (reconnectTimer) return;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, 1500);
    };
  }

  function send(type, extra) {
    if (!ws || ws.readyState !== 1) {
      state.error = "Mất kết nối phòng";
      render();
      return;
    }
    ws.send(JSON.stringify(Object.assign({ type }, extra || {})));
  }

  function goToRoom(roomId) {
    const room = normalizeRoomCode(roomId);
    if (!room) return;
    location.href = pageUrl(room, false);
  }

  async function createRoom() {
    const name = (document.getElementById("room-name") || {}).value || state.name || "Chủ phòng";
    const rounds = Number((document.getElementById("room-rounds-select") || {}).value) || 5;
    const timeLimit = Number((document.getElementById("room-time-select") || {}).value) || 0;
    sessionStorage.setItem(STORE.name, name);
    try {
      const settings = Object.assign(loadSettings(), { rounds, time_limit: timeLimit });
      const data = await api("/api/rooms", { name, settings, rounds, time_limit: timeLimit });
      saveAuth(data);
      goToRoom(data.room_id);
    } catch (err) {
      state.error = err.message;
      render();
    }
  }

  async function joinRoom(code) {
    const roomId = normalizeRoomCode(code);
    const name = (document.getElementById("room-name") || {}).value || state.name || "Khách";
    sessionStorage.setItem(STORE.name, name);
    if (!roomId) {
      state.error = "Mã phòng 4 ký tự";
      render();
      return;
    }
    try {
      const data = await api(`/api/rooms/${roomId}/join`, {
        name,
        token: tokenFor(roomId)
      });
      saveAuth(data);
      if (queryRoom !== roomId) {
        goToRoom(roomId);
        return;
      }
      applyRoom(data);
      connect();
    } catch (err) {
      state.error = err.message;
      render();
    }
  }

  function copyLink() {
    const url = `${location.origin}/?room=${state.room_id}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).catch(() => {
        window.prompt("Copy link phòng", url);
      });
    } else {
      window.prompt("Copy link phòng", url);
    }
  }

  function leaveRoom() {
    goToMode("party");
  }

  function goToMode(mode) {
    if (mode === "party") {
      location.href = pageUrl("", true);
      return;
    }
    sessionStorage.removeItem(STORE.room);
    sessionStorage.removeItem(STORE.token);
    sessionStorage.removeItem(STORE.player);
    location.href = pageUrl("", false);
  }

  function syncPlayfield() {
    const inGame = state.status === "playing" || state.status === "finished";
    document.body.classList.toggle("solo-play", !partyMode);
    document.body.classList.toggle("party-lobby", partyMode && !inGame);
    document.body.classList.toggle("party-play", partyMode && inGame);
    const soloBtn = document.getElementById("mode-solo");
    const partyBtn = document.getElementById("mode-party");
    if (soloBtn) soloBtn.classList.toggle("on", !partyMode);
    if (partyBtn) partyBtn.classList.toggle("on", partyMode);
  }

  function isHost() {
    return state.player_id && state.player_id === state.host_id;
  }

  function rosterHtml() {
    const ranks = {};
    (state.ranking || []).forEach((row) => {
      ranks[row.id] = row.rank;
    });
    return (state.players || [])
      .map((p) => {
        const you = p.id === state.player_id ? " you" : "";
        const host = p.id === state.host_id ? " · chủ" : "";
        const score = p.total_score != null ? p.total_score : 0;
        const roundScore = p.round_score ? ` (+${p.round_score})` : "";
        let badge = `${p.attempts || 0}/6`;
        let cls = "badge";
        if (p.solved) {
          badge = ranks[p.id] ? `xong · #${ranks[p.id]}` : "xong";
          cls += " done";
        }
        if (p.disconnected) {
          badge += " · mất máy";
          cls += " off";
        }
        return `<li>
          <span class="${you.trim()}">${esc(p.name)}${host}${you ? " (bạn)" : ""}</span>
          <span class="score-badge">${score}đ${roundScore}</span>
          <span class="${cls}">${badge}</span>
        </li>`;
      })
      .join("");
  }

  function statusText() {
    if (state.error) return state.error;
    if (state.status === "lobby") {
      const rText = state.total_rounds > 1 ? `Trận ${state.total_rounds} câu. ` : "";
      return `${rText}Chờ chủ phòng bấm Bắt đầu (cần ≥ 2 người).`;
    }
    if (state.status === "playing") {
      const rText = state.total_rounds > 1 ? `Câu ${state.round}/${state.total_rounds}: ` : "";
      return `${rText}Đang chơi — mọi người đoán cùng lúc.`;
    }
    if (state.status === "round_summary") {
      return `Hết Câu ${state.round}/${state.total_rounds}. Chuẩn bị sang câu tiếp theo...`;
    }
    if (state.status === "finished") {
      return state.total_rounds > 1
        ? `Trận đấu hoàn tất (${state.total_rounds} câu)! Chủ phòng có thể chơi trận mới.`
        : "Hết ván. Chủ phòng có thể chơi lại cùng nhóm.";
    }
    return "";
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render() {
    const root = document.getElementById("room-panel");
    if (!root) return;
    const inRoom = Boolean(queryRoom);
    root.className = inRoom ? "in" : "idle";
    const nameEl = document.getElementById("room-name");
    if (nameEl && !nameEl.value && state.name) nameEl.value = state.name;
    const codeOut = document.getElementById("room-code-out");
    if (codeOut) codeOut.textContent = state.room_id || "----";
    const roster = document.getElementById("room-roster");
    if (roster) roster.innerHTML = rosterHtml() || "<li>Chưa có ai</li>";
    const status = document.getElementById("room-status");
    if (status) {
      status.textContent = statusText();
      status.classList.toggle("error", Boolean(state.error));
    }
    const roundBadge = document.getElementById("room-round-badge");
    if (roundBadge) {
      if (state.total_rounds > 1 && (state.status === "playing" || state.status === "round_summary")) {
        roundBadge.textContent = `Câu ${state.round}/${state.total_rounds}`;
        roundBadge.hidden = false;
      } else {
        roundBadge.hidden = true;
      }
    }
    const startBtn = document.getElementById("room-start");
    const nextBtn = document.getElementById("room-next");
    const rematchBtn = document.getElementById("room-rematch");
    if (startBtn) {
      startBtn.hidden = !(isHost() && state.status === "lobby");
    }
    if (nextBtn) {
      nextBtn.hidden = !(isHost() && state.status === "round_summary");
    }
    if (rematchBtn) {
      rematchBtn.hidden = !(isHost() && state.status === "finished");
    }
    const summaryBox = document.getElementById("room-summary-box");
    if (summaryBox) {
      if (state.status === "round_summary" && state.round_summary) {
        summaryBox.hidden = false;
        summaryBox.innerHTML = `
          <div class="summary-card">
            <div class="summary-title">Kết thúc Câu ${state.round}/${state.total_rounds}</div>
            <div class="summary-answer">Đáp án: <strong>${esc(state.round_summary.solution || "")}</strong></div>
          </div>
        `;
      } else if (state.status === "finished" && state.total_rounds > 1 && (state.ranking || []).length) {
        summaryBox.hidden = false;
        const top1 = state.ranking[0];
        const top2 = state.ranking[1];
        const top3 = state.ranking[2];
        summaryBox.innerHTML = `
          <div class="summary-card victory-card">
            <div class="summary-title">🏆 KẾT QUẢ CHUNG CUỘC 🏆</div>
            <div class="podium">
              ${top1 ? `<div class="podium-item gold">🥇 <strong>${esc(top1.name)}</strong>: ${top1.total_score || 0}đ</div>` : ""}
              ${top2 ? `<div class="podium-item silver">🥈 ${esc(top2.name)}: ${top2.total_score || 0}đ</div>` : ""}
              ${top3 ? `<div class="podium-item bronze">🥉 ${esc(top3.name)}: ${top3.total_score || 0}đ</div>` : ""}
            </div>
          </div>
        `;
      } else {
        summaryBox.hidden = true;
        summaryBox.innerHTML = "";
      }
    }
    const loader = document.getElementById("loader");
    if (loader && partyMode && (state.status === "lobby" || !queryRoom)) {
      loader.textContent = queryRoom
        ? "Đang chờ chủ phòng bắt đầu…"
        : "Tạo phòng hoặc nhập mã để chơi cùng bạn.";
    }
    const caps = document.getElementById("room-caps");
    if (caps && window.__DOANCHU_LIMITS) {
      const L = window.__DOANCHU_LIMITS;
      caps.textContent =
        `Slot: ${L.rooms || 0}/${L.max_rooms} phòng · ` +
        `${L.party || 0}/${L.max_party} người · tối đa ${L.max_players}/phòng`;
    }
    syncPlayfield();
  }

  function mount() {
    if (document.getElementById("mode-bar")) return;
    const bar = document.querySelector(".howto-bar");
    if (!bar || !bar.parentElement) return;
    const modes = document.createElement("nav");
    modes.id = "mode-bar";
    modes.innerHTML = `
      <button type="button" id="mode-solo">Chơi đơn</button>
      <button type="button" id="mode-party">Cùng bạn</button>
    `;
    const box = document.createElement("section");
    box.id = "room-panel";
    box.className = queryRoom ? "in" : "idle";
    box.innerHTML = `
      <h2>Phòng</h2>
      <p id="room-caps" class="room-caps"></p>
      <div id="room-lobby">
        <div class="room-row">
          <input id="room-name" type="text" maxlength="20" placeholder="Tên của bạn" autocomplete="nickname"/>
        </div>
        <div class="room-row room-setup-row">
          <label for="room-rounds-select">Số câu:</label>
          <select id="room-rounds-select" class="room-select">
            <option value="5" selected>5 câu (Chuẩn)</option>
            <option value="1">1 câu (Nhanh)</option>
            <option value="3">3 câu</option>
            <option value="10">10 câu (Marathon)</option>
          </select>
          <label for="room-time-select">Thời gian:</label>
          <select id="room-time-select" class="room-select">
            <option value="0" selected>Không giới hạn</option>
            <option value="120">2 phút</option>
            <option value="180">3 phút</option>
            <option value="300">5 phút</option>
          </select>
        </div>
        <div class="room-row">
          <button type="button" id="room-create">Tạo phòng</button>
          <input id="room-code-in" type="text" maxlength="4" placeholder="MÃ" autocomplete="off"/>
          <button type="button" id="room-join">Vào phòng</button>
        </div>
      </div>
      <div id="room-in">
        <div class="room-row room-header-row">
          <span>Mã</span>
          <span id="room-code-out">${esc(state.room_id || "----")}</span>
          <button type="button" class="ghost" id="room-copy">Copy link</button>
          <span id="room-round-badge" class="round-badge" hidden></span>
          <span id="room-timer" class="room-timer"></span>
        </div>
        <p id="room-status"></p>
        <div id="room-summary-box" hidden></div>
        <ul id="room-roster"></ul>
        <div id="room-actions">
          <button type="button" id="room-start">Bắt đầu</button>
          <button type="button" id="room-next" hidden>Câu tiếp theo <span id="next-round-cd"></span></button>
          <button type="button" id="room-rematch">Chơi lại</button>
          <button type="button" class="ghost" id="room-leave">Rời phòng</button>
        </div>
      </div>
    `;
    bar.parentElement.insertBefore(modes, bar);
    bar.parentElement.insertBefore(box, bar);
    document.getElementById("mode-solo").onclick = () => {
      if (!partyMode) return;
      goToMode("solo");
    };
    document.getElementById("mode-party").onclick = () => {
      if (partyMode) return;
      goToMode("party");
    };
    const nameEl = document.getElementById("room-name");
    if (nameEl) nameEl.value = state.name;
    document.getElementById("room-create").onclick = createRoom;
    document.getElementById("room-join").onclick = () => {
      joinRoom((document.getElementById("room-code-in") || {}).value);
    };
    document.getElementById("room-code-in").addEventListener("keydown", (e) => {
      if (e.key === "Enter") joinRoom(e.target.value);
    });
    document.getElementById("room-copy").onclick = copyLink;
    document.getElementById("room-start").onclick = () => send("start");
    document.getElementById("room-next").onclick = () => send("next_round");
    document.getElementById("room-rematch").onclick = () => send("rematch");
    document.getElementById("room-leave").onclick = leaveRoom;
    render();
  }

  window.DOANCHU_ROOM = {
    whenStarted() {
      return startedPromise;
    },
    submitGuess(guess) {
      return new Promise((resolve, reject) => {
        if (!ws || ws.readyState !== 1) {
          reject(new Error("Mất kết nối phòng"));
          return;
        }
        guessWaiters.push({ resolve, reject });
        ws.send(JSON.stringify({ type: "guess", guess }));
      });
    },
    roomFinished() {
      return state.status === "finished";
    },
    canRematch() {
      return isHost() && state.status === "finished";
    },
    rematch() {
      if (isHost() && state.status === "finished") send("rematch");
    },
    canNextRound() {
      return isHost() && state.status === "round_summary";
    },
    nextRound() {
      if (isHost() && state.status === "round_summary") send("next_round");
    }
  };

  async function boot() {
    mount();
    try {
      const cfg = await fetch("/api/config", { cache: "no-store" }).then((r) => r.json());
      if (cfg.limits) {
        window.__DOANCHU_LIMITS = cfg.limits;
        render();
      }
    } catch (e) {}
    if (badRoom) {
      state.error = "Mã phòng không hợp lệ";
      render();
      return;
    }
    if (!queryRoom) return;
    try {
      const data = await api(`/api/rooms/${queryRoom}/join`, {
        name: state.name || "Khách",
        token: tokenFor(queryRoom)
      });
      saveAuth(data);
      applyRoom(data);
      connect();
    } catch (err) {
      state.error = err.message;
      render();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
