export async function onRequestGet({ env }) {
  const raw = String(env.DOANCHU_DEBUG || "0").toLowerCase();
  const debug = raw === "1" || raw === "true" || raw === "yes";
  return Response.json(
    { debug },
    { headers: { "Cache-Control": "no-store" } },
  );
}
