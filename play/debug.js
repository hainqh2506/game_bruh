/* Debug warehouse + CRUD. Visible only when /api/config says debug: true. */
(() => {
  const PAGE_SIZE = 50;
  const POOLS = [
    { id: "play", label: "Play" },
    { id: "raw", label: "Raw" },
    { id: "rejected", label: "Đã loại" }
  ];
  let page = 1;
  let query = "";
  let pool = "play";
  let counts = { raw: 0, play: 0, rejected: 0 };

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function patternOf(phrase, spaceIndex) {
    if (typeof spaceIndex === "number" && spaceIndex >= 0) {
      return `${spaceIndex} + ${phrase.length - spaceIndex - 1}`;
    }
    const i = phrase.indexOf(" ");
    return i < 0 ? String(phrase.length) : `${i} + ${phrase.length - i - 1}`;
  }

  async function debugEnabled() {
    try {
      const res = await fetch("/api/config", { cache: "no-store" });
      if (!res.ok) return false;
      const data = await res.json();
      return !!data.debug;
    } catch (e) {
      return false;
    }
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ cache: "no-store" }, opts || {}));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  function actionsFor(phrase) {
    const p = encodeURIComponent(phrase);
    if (pool === "raw") {
      return `<button data-act="play" data-phrase="${p}">→ Play</button>
              <button data-act="rejected" data-phrase="${p}">Loại</button>
              <button class="danger" data-act="delete" data-phrase="${p}">Xóa</button>`;
    }
    if (pool === "play") {
      return `<button data-act="raw" data-phrase="${p}">→ Raw</button>
              <button data-act="rejected" data-phrase="${p}">Loại</button>
              <button class="danger" data-act="delete" data-phrase="${p}">Xóa</button>`;
    }
    return `<button data-act="play" data-phrase="${p}">→ Play</button>
            <button data-act="raw" data-phrase="${p}">→ Raw</button>
            <button class="danger" data-act="delete" data-phrase="${p}">Xóa</button>`;
  }

  async function load() {
    const url = `/api/phrases?pool=${encodeURIComponent(pool)}&q=${encodeURIComponent(query)}&page=${page}&limit=${PAGE_SIZE}`;
    return api(url);
  }

  async function renderTable() {
    const data = await load();
    counts = data.counts || counts;
    page = data.page;
    POOLS.forEach(({ id }) => {
      const el = document.getElementById("count-" + id);
      if (el) el.textContent = Number(counts[id] || 0).toLocaleString("vi-VN");
    });
    document.querySelectorAll(".pool-tab").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.pool === pool);
    });
    const tbody = document.getElementById("debug-body");
    tbody.innerHTML = (data.items || [])
      .map((row, idx) => {
        const phrase = row.phrase || "";
        const n = (data.page - 1) * PAGE_SIZE + idx + 1;
        const pat = patternOf(phrase, row.space_index);
        return `<tr>
          <td>${n}</td>
          <td>${esc(phrase)}</td>
          <td>${pat}</td>
          <td>${esc(row.source || "")}</td>
          <td class="acts">${actionsFor(phrase)}</td>
        </tr>`;
      })
      .join("");
    const qn = query ? ` khớp “${query}”` : "";
    document.getElementById("debug-meta").textContent =
      `${Number(data.total || 0).toLocaleString("vi-VN")} cụm trong pool ${pool}${qn}`;
    document.getElementById("debug-page-info").textContent = `${data.page} / ${data.pages || 1}`;
    document.getElementById("debug-prev").disabled = data.page <= 1;
    document.getElementById("debug-next").disabled = data.page >= (data.pages || 1);
  }

  async function movePhrase(phrase, nextPool) {
    await api("/api/phrases", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrase, pool: nextPool })
    });
    await renderTable();
  }

  async function deletePhrase(phrase) {
    if (!confirm(`Xóa hẳn “${phrase}” khỏi DB?`)) return;
    await api("/api/phrases", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrase, pool })
    });
    await renderTable();
  }

  async function addPhrase() {
    const input = document.getElementById("debug-new");
    const phrase = (input.value || "").trim();
    if (!phrase) return;
    try {
      await api("/api/phrases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phrase, pool })
      });
      input.value = "";
      page = 1;
      await renderTable();
    } catch (err) {
      alert(err.message || "Không thêm được");
    }
  }

  function showTab(name) {
    const play = document.getElementById("play-root");
    const debug = document.getElementById("debug-root");
    document.querySelectorAll("#app-tabs > .tab").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.tab === name);
    });
    if (play) play.hidden = name !== "play";
    if (debug) debug.hidden = name !== "debug";
  }

  function mount() {
    const container = document.querySelector(".container");
    const header = container && container.querySelector(".header");
    if (!container || !header) return;

    const playRoot = document.createElement("div");
    playRoot.id = "play-root";
    const move = [];
    let node = header.nextSibling;
    while (node) {
      const next = node.nextSibling;
      move.push(node);
      node = next;
    }
    move.forEach((el) => playRoot.appendChild(el));
    header.after(playRoot);

    const nav = document.createElement("nav");
    nav.id = "app-tabs";
    nav.innerHTML =
      '<button type="button" class="tab on" data-tab="play">Chơi</button>' +
      '<button type="button" class="tab" data-tab="debug">Kho từ</button>';
    header.after(nav);

    const debug = document.createElement("section");
    debug.id = "debug-root";
    debug.hidden = true;
    debug.innerHTML = `
      <h2>Quản lý kho từ</h2>
      <p id="debug-answer">Đáp án ván hiện tại (pool Play): <code>${esc(window.__DOANCHU_ANSWER || "?")}</code></p>
      <p class="hint">Play = từ ghép thông dụng (Viet11K, mỗi từ 2–5 chữ). Raw = dump gốc. Đã loại = bậy/không dùng. Sửa Play xong F5 để ván mới lấy pool mới.</p>
      <div id="pool-tabs">
        ${POOLS.map(({ id, label }) =>
          `<button type="button" class="pool-tab ${id === "play" ? "on" : ""}" data-pool="${id}">${label} (<span id="count-${id}">0</span>)</button>`
        ).join("")}
      </div>
      <p id="debug-meta"></p>
      <div id="debug-add">
        <input id="debug-new" type="text" placeholder="Thêm cụm 2 từ vào pool này…" autocomplete="off"/>
        <button type="button" id="debug-add-btn">Thêm</button>
      </div>
      <input id="debug-search" type="search" placeholder="Tìm trong pool…" autocomplete="off"/>
      <table id="debug-table">
        <thead><tr><th>#</th><th>Cụm từ</th><th>Độ dài</th><th>Nguồn</th><th></th></tr></thead>
        <tbody id="debug-body"></tbody>
      </table>
      <div id="debug-pager">
        <button type="button" id="debug-prev">Trước</button>
        <span id="debug-page-info"></span>
        <button type="button" id="debug-next">Sau</button>
      </div>
    `;
    playRoot.after(debug);

    nav.addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (btn) showTab(btn.dataset.tab);
    });
    document.getElementById("pool-tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".pool-tab");
      if (!btn) return;
      pool = btn.dataset.pool;
      page = 1;
      renderTable();
    });
    document.getElementById("debug-search").addEventListener("input", (e) => {
      query = e.target.value;
      page = 1;
      renderTable();
    });
    document.getElementById("debug-add-btn").onclick = addPhrase;
    document.getElementById("debug-new").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addPhrase();
    });
    document.getElementById("debug-prev").onclick = () => {
      page -= 1;
      renderTable();
    };
    document.getElementById("debug-next").onclick = () => {
      page += 1;
      renderTable();
    };
    document.getElementById("debug-body").addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-act]");
      if (!btn) return;
      const phrase = decodeURIComponent(btn.dataset.phrase);
      const act = btn.dataset.act;
      try {
        if (act === "delete") await deletePhrase(phrase);
        else await movePhrase(phrase, act);
      } catch (err) {
        alert(err.message || "Lỗi");
      }
    });

    renderTable().catch((err) => {
      document.getElementById("debug-meta").textContent = err.message;
    });
  }

  window.addEventListener("DOMContentLoaded", async () => {
    if (await debugEnabled()) mount();
  });
})();
