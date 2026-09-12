/* Debug warehouse + CRUD. Visible only when /api/config says debug: true. */
(() => {
  const PAGE_SIZE = 50;
  const POOLS = [
    { id: "play", label: "Play" },
    { id: "raw", label: "Raw / chờ duyệt" },
    { id: "rejected", label: "Đã loại" }
  ];
  let page = 1;
  let query = "";
  let pool = "play";
  let counts = { raw: 0, play: 0, rejected: 0 };
  const selected = new Set();

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
              <button data-act="rejected" data-phrase="${p}">Loại</button>`;
    }
    if (pool === "play") {
      return `<button data-act="raw" data-phrase="${p}">→ Raw</button>
              <button data-act="rejected" data-phrase="${p}">Loại</button>`;
    }
    return `<button data-act="play" data-phrase="${p}">→ Play</button>
            <button data-act="raw" data-phrase="${p}">→ Raw</button>
            <button class="danger" data-act="delete" data-phrase="${p}">Xóa hẳn</button>`;
  }

  function selectedList() {
    return [...selected];
  }

  function syncBulkBar() {
    const n = selected.size;
    const bar = document.getElementById("debug-bulk");
    const countEl = document.getElementById("debug-sel-count");
    if (countEl) countEl.textContent = String(n);
    if (bar) bar.hidden = n === 0;
    const purge = document.getElementById("debug-bulk-purge");
    if (purge) purge.hidden = pool !== "rejected";
    const all = document.getElementById("debug-check-all");
    if (all) {
      const boxes = document.querySelectorAll("#debug-body input[data-phrase]");
      const checked = [...boxes].filter((el) => el.checked).length;
      all.checked = boxes.length > 0 && checked === boxes.length;
      all.indeterminate = checked > 0 && checked < boxes.length;
    }
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
        const on = selected.has(phrase) ? " checked" : "";
        return `<tr>
          <td><input type="checkbox" data-phrase="${esc(phrase)}"${on}/></td>
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
    syncBulkBar();
  }

  function showImportResult(data) {
    const el = document.getElementById("debug-import-result");
    if (!el) return;
    const added = (data.added || []).length;
    const existed = (data.existed || []).length;
    const invalid = (data.invalid || []).length;
    el.textContent = `Thêm ${added} · đã có ${existed} · bỏ qua ${invalid}`;
  }

  async function movePhrases(phrases, nextPool) {
    if (!phrases.length) return;
    await api("/api/phrases", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrases, pool: nextPool })
    });
    phrases.forEach((p) => selected.delete(p));
    await renderTable();
  }

  async function deletePhrases(phrases) {
    if (!phrases.length) return;
    const label = phrases.length === 1 ? `“${phrases[0]}”` : `${phrases.length} cụm`;
    if (pool !== "rejected") {
      await movePhrases(phrases, "rejected");
      return;
    }
    if (!confirm(`Xóa hẳn ${label} khỏi Đã loại? Không lấy lại được.`)) return;
    await api("/api/phrases", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phrases, pool })
    });
    phrases.forEach((p) => selected.delete(p));
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

  async function importText() {
    const area = document.getElementById("debug-import-text");
    const text = (area && area.value) || "";
    if (!text.trim()) return;
    try {
      const data = await api("/api/phrases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, pool })
      });
      if (area) area.value = "";
      showImportResult(data);
      page = 1;
      await renderTable();
    } catch (err) {
      alert(err.message || "Không nhập được");
    }
  }

  async function exportPool() {
    const res = await fetch(`/api/phrases/export?pool=${encodeURIComponent(pool)}`, { cache: "no-store" });
    if (!res.ok) {
      alert("Không xuất được");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `doanchu-${pool}.txt`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function showTab(name) {
    const play = document.getElementById("play-root");
    const debug = document.getElementById("debug-root");
    document.querySelectorAll("#app-tabs > .tab").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.tab === name);
    });
    if (play) play.hidden = name !== "play";
    if (debug) debug.hidden = name !== "debug";
    document.body.classList.toggle("tab-debug", name === "debug");
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
      <p id="debug-answer">${window.__DOANCHU_ROOM_MODE
        ? "Phòng party: đáp án chỉ nằm trên server, không hiện ở đây."
        : `Đáp án ván hiện tại (pool Play): <code>${esc(window.__DOANCHU_ANSWER || "?")}</code>`}</p>
      <p class="hint">Play = đáp án. Raw = chờ duyệt. <b>Loại</b> chuyển sang Đã loại — vào đó bấm → Play / → Raw để lấy lại. Chỉ <b>Xóa hẳn</b> ở Đã loại mới mất. Sửa Play xong F5.</p>
      <div id="pool-tabs">
        ${POOLS.map(({ id, label }) =>
          `<button type="button" class="pool-tab ${id === "play" ? "on" : ""}" data-pool="${id}">${label} (<span id="count-${id}">0</span>)</button>`
        ).join("")}
      </div>
      <p id="debug-meta"></p>
      <div id="debug-add">
        <input id="debug-new" type="text" placeholder="Thêm một cụm 2 từ vào pool này…" autocomplete="off"/>
        <button type="button" id="debug-add-btn">Thêm</button>
        <button type="button" id="debug-export" class="ghost">Xuất .txt</button>
      </div>
      <details id="debug-import">
        <summary>Nhập hàng loạt từ file / dán text</summary>
        <p class="hint">Mỗi dòng một cụm (<code>học sinh</code>), hoặc CSV <code>học,sinh</code>. Dòng <code>#</code> bỏ qua. Nhập vào pool đang mở.</p>
        <textarea id="debug-import-text" rows="6" placeholder="bánh mì&#10;cà phê&#10;gia đình"></textarea>
        <div id="debug-import-actions">
          <input id="debug-import-file" type="file" accept=".txt,.csv,text/plain"/>
          <button type="button" id="debug-import-btn">Nhập vào pool này</button>
        </div>
        <p id="debug-import-result"></p>
      </details>
      <input id="debug-search" type="search" placeholder="Tìm trong pool…" autocomplete="off"/>
      <div id="debug-bulk" hidden>
        <span>Đã chọn <b id="debug-sel-count">0</b></span>
        <button type="button" data-bulk="play">→ Play</button>
        <button type="button" data-bulk="raw">→ Raw</button>
        <button type="button" data-bulk="rejected">Loại</button>
        <button type="button" class="danger" data-bulk="delete" id="debug-bulk-purge">Xóa hẳn</button>
        <button type="button" class="ghost" data-bulk="clear">Bỏ chọn</button>
      </div>
      <table id="debug-table">
        <thead><tr>
          <th><input type="checkbox" id="debug-check-all" title="Chọn cả trang"/></th>
          <th>#</th><th>Cụm từ</th><th>Độ dài</th><th>Nguồn</th><th></th>
        </tr></thead>
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
      selected.clear();
      renderTable();
    });
    document.getElementById("debug-search").addEventListener("input", (e) => {
      query = e.target.value;
      page = 1;
      selected.clear();
      renderTable();
    });
    document.getElementById("debug-add-btn").onclick = addPhrase;
    document.getElementById("debug-new").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addPhrase();
    });
    document.getElementById("debug-export").onclick = exportPool;
    document.getElementById("debug-import-btn").onclick = importText;
    document.getElementById("debug-import-file").addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const area = document.getElementById("debug-import-text");
        if (area) area.value = String(reader.result || "");
      };
      reader.readAsText(file, "utf-8");
    });
    document.getElementById("debug-prev").onclick = () => {
      page -= 1;
      renderTable();
    };
    document.getElementById("debug-next").onclick = () => {
      page += 1;
      renderTable();
    };
    document.getElementById("debug-check-all").addEventListener("change", (e) => {
      const on = e.target.checked;
      document.querySelectorAll("#debug-body input[data-phrase]").forEach((box) => {
        box.checked = on;
        if (on) selected.add(box.dataset.phrase);
        else selected.delete(box.dataset.phrase);
      });
      syncBulkBar();
    });
    document.getElementById("debug-body").addEventListener("change", (e) => {
      const box = e.target.closest("input[data-phrase]");
      if (!box) return;
      if (box.checked) selected.add(box.dataset.phrase);
      else selected.delete(box.dataset.phrase);
      syncBulkBar();
    });
    document.getElementById("debug-body").addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-act]");
      if (!btn) return;
      const phrase = decodeURIComponent(btn.dataset.phrase);
      const act = btn.dataset.act;
      try {
        if (act === "delete") await deletePhrases([phrase]);
        else await movePhrases([phrase], act);
      } catch (err) {
        alert(err.message || "Lỗi");
      }
    });
    document.getElementById("debug-bulk").addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-bulk]");
      if (!btn) return;
      const act = btn.dataset.bulk;
      const phrases = selectedList();
      try {
        if (act === "clear") {
          selected.clear();
          await renderTable();
          return;
        }
        if (act === "delete") await deletePhrases(phrases);
        else await movePhrases(phrases, act);
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
