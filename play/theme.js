(() => {
  const KEY = "doanchu:theme";
  const THEMES = [
    { id: "classic", label: "Cổ điển" },
    { id: "office", label: "Sáng" },
    { id: "slate", label: "Tối" }
  ];
  const COLORS = {
    classic: "#a12629",
    office: "#ffffff",
    slate: "#1b1a19"
  };

  function readTheme() {
    try {
      const raw = localStorage.getItem(KEY) || "classic";
      return THEMES.some((t) => t.id === raw) ? raw : "classic";
    } catch (e) {
      return "classic";
    }
  }

  function apply(id) {
    const theme = THEMES.some((t) => t.id === id) ? id : "classic";
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", COLORS[theme]);
    try {
      localStorage.setItem(KEY, theme);
    } catch (e) {}
    const sel = document.getElementById("theme-select");
    if (sel && sel.value !== theme) sel.value = theme;
  }

  function bind(sel) {
    const el = sel || document.getElementById("theme-select");
    if (!el || el.dataset.bound) return;
    el.dataset.bound = "1";
    el.value = readTheme();
    const stop = (e) => e.stopPropagation();
    el.addEventListener("click", stop);
    el.addEventListener("mousedown", stop);
    el.addEventListener("pointerdown", stop);
    el.addEventListener("change", (e) => apply(e.target.value));
  }

  apply(readTheme());

  function mount() {
    bind();
  }

  window.DOANCHU_THEME = { apply, bind, readTheme };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
