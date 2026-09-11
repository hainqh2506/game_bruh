/* Dev live-reload: long-poll /api/reload, then refresh. No-op if the API is down. */
(() => {
  const KEY = "doanchuReloadGen";
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function loop() {
    let gen = Number(sessionStorage.getItem(KEY) || "0");
    while (true) {
      try {
        const res = await fetch(`/api/reload?gen=${gen}`, { cache: "no-store" });
        if (!res.ok) {
          await wait(2000);
          continue;
        }
        const data = await res.json();
        const next = Number(data.generation);
        if (!Number.isFinite(next)) {
          await wait(1000);
          continue;
        }
        if (next > gen) {
          sessionStorage.setItem(KEY, String(next));
          location.reload();
          return;
        }
        gen = next;
        sessionStorage.setItem(KEY, String(gen));
      } catch {
        await wait(2000);
      }
    }
  }

  loop();
})();
