/* Room party: lobby + WebSocket. Peers see name / attempts / done only. */
(() => {
  const STORE = {
    room: "doanchu:roomId",
    token: "doanchu:roomToken",
    name: "doanchu:playerName",
    player: "doanchu:playerId"
  };
  const params = new URLSearchParams(location.search);
  const queryRoom = (params.get("room") || "").toUpperCase();
  const partyMode = Boolean(queryRoom) || params.get("mode") === "party";
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
    error: ""
  };

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

  function resolveStarted(data) {
    if (data.length == null) return;
    startedResolve({
      room_id: data.room_id || state.room_id,
      length: data.length,
      spaceIndex: data.spaceIndex,
      started_at: data.started_at || 0,
      board: data.board || { guesses: [], marksList: [] }
    });
  }

  function applyRoom(data) {
    state.room_id = data.room_id || state.room_id;
    state.status = data.status || state.status;
    state.host_id = data.host_id || state.host_id;
    state.players = data.players || state.players;
    if (data.you) state.player_id = data.you.id;
    if (data.ranking) state.ranking = data.ranking;
    if (data.status === "playing" || data.status === "finished") {
      resolveStarted(data);
    }
    render();
  }

  function handle(msg) {
    switch (msg.type) {
      case "room":
        applyRoom(msg);
        break;
      case "started":
        state.status = "playing";
        state.players = msg.players || state.players;
        resolveStarted(msg);
        if (document.querySelector(".row .tile")) {
          location.reload();
          return;
        }
        render();
        break;
      case "guess_result": {
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
        state.status = "finished";
        state.ranking = msg.ranking || [];
        if (msg.players) state.players = msg.players;
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
    const roomId = state.room_id || queryRoom;
    const token = state.token || storedToken();
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
    const next = new URL(location.href);
    next.searchParams.set("room", roomId);
    location.href = next.pathname + next.search;
  }

  async function createRoom() {
    const name = (document.getElementById("room-name") || {}).value || state.name || "Chủ phòng";
    sessionStorage.setItem(STORE.name, name);
    try {
      const data = await api("/api/rooms", { name, settings: loadSettings() });
      saveAuth(data);
      goToRoom(data.room_id);
    } catch (err) {
      state.error = err.message;
      render();
    }
  }

  async function joinRoom(code) {
    const roomId = String(code || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
    const name = (document.getElementById("room-name") || {}).value || state.name || "Khách";
    sessionStorage.setItem(STORE.name, name);
    if (roomId.length !== 4) {
      state.error = "Mã phòng 4 ký tự";
      render();
      return;
    }
    try {
      const data = await api(`/api/rooms/${roomId}/join`, {
        name,
        token: storedToken()
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
    sessionStorage.removeItem(STORE.room);
    sessionStorage.removeItem(STORE.token);
    sessionStorage.removeItem(STORE.player);
    goToMode("party");
  }

  function goToMode(mode) {
    const next = new URL(location.href);
    if (mode === "party") {
      next.searchParams.delete("room");
      next.searchParams.set("mode", "party");
    } else {
      sessionStorage.removeItem(STORE.room);
      sessionStorage.removeItem(STORE.token);
      sessionStorage.removeItem(STORE.player);
      next.searchParams.delete("room");
      next.searchParams.delete("mode");
    }
    location.href = next.pathname + next.search;
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
        return `<li><span class="${you.trim()}">${esc(p.name)}${host}${you ? " (bạn)" : ""}</span><span class="${cls}">${badge}</span></li>`;
      })
      .join("");
  }

  function statusText() {
    if (state.error) return state.error;
    if (state.status === "lobby") return "Chờ chủ phòng bấm Bắt đầu (cần ≥ 2 người).";
    if (state.status === "playing") return "Đang chơi — mọi người đoán cùng lúc.";
    if (state.status === "finished") return "Hết ván. Chủ phòng có thể chơi lại cùng nhóm.";
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
    const startBtn = document.getElementById("room-start");
    const rematchBtn = document.getElementById("room-rematch");
    if (startBtn) {
      startBtn.hidden = !(isHost() && state.status === "lobby");
    }
    if (rematchBtn) {
      rematchBtn.hidden = !(isHost() && state.status === "finished");
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
        <div class="room-row">
          <button type="button" id="room-create">Tạo phòng</button>
          <input id="room-code-in" type="text" maxlength="4" placeholder="MÃ" autocomplete="off"/>
          <button type="button" id="room-join">Vào phòng</button>
        </div>
      </div>
      <div id="room-in">
        <div class="room-row">
          <span>Mã</span>
          <span id="room-code-out">${esc(state.room_id || "----")}</span>
          <button type="button" class="ghost" id="room-copy">Copy link</button>
        </div>
        <p id="room-status"></p>
        <ul id="room-roster"></ul>
        <div id="room-actions">
          <button type="button" id="room-start">Bắt đầu</button>
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
    rematch() {
      if (isHost() && state.status === "finished") send("rematch");
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
    if (!queryRoom) return;
    try {
      const data = await api(`/api/rooms/${queryRoom}/join`, {
        name: state.name || "Khách",
        token: storedToken()
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
