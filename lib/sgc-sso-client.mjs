// ../sgc-auth/src/oidc.mjs
var enc = new TextEncoder();
var b64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
var random = () => b64(crypto.getRandomValues(new Uint8Array(32)));
var hash = async (value) => b64(await crypto.subtle.digest("SHA-256", enc.encode(value)));
var validToken = (value) => typeof value === "string" && /^[A-Za-z0-9_-]{43}$/.test(value);

// ../sgc-auth/src/auth.mjs
var cookie = (name, value, age) => `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
function readCookie(request, name) {
  const entries = (request.headers.get("cookie") ?? "").split(";").map((s) => s.trim()).filter((s) => s.startsWith(name + "="));
  return entries.length === 1 ? entries[0].slice(name.length + 1) : "";
}
function localPath(value = "/") {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || /[\\\x00-\x20#]/.test(value) || value.length > 2048) throw Error("INVALID_RETURN");
  if (/%(?:2f|5c|0[0-9a-f]|1[0-9a-f]|7f)/i.test(value)) throw Error("INVALID_RETURN");
  return value;
}

// ../sgc-auth/src/client.mjs
var APP_COOKIE = "__Host-sgc_app";
var FLOW = "__Host-sgc_appflow";
var safeHeaders = { "cache-control": "no-store", "referrer-policy": "no-referrer", "x-content-type-options": "nosniff" };
var redirect = (location, cookies = []) => {
  const h = new Headers({ ...safeHeaders, location });
  for (const c of cookies) h.append("set-cookie", c);
  return new Response(null, { status: 303, headers: h });
};
function createSsoClient({ origin, authOrigin, appId, binding, now = () => Math.floor(Date.now() / 1e3) }) {
  for (const value of [origin, authOrigin]) if (new URL(value).origin !== value || !value.startsWith("https://")) throw Error("INVALID_ORIGIN");
  return {
    async handle(request) {
      const u = new URL(request.url);
      if (u.origin !== origin) return new Response(null, { status: 400, headers: safeHeaders });
      if (u.pathname === "/auth/login" && request.method === "GET") {
        const state = random(), verifier = random(), expires = now() + 300;
        const target = new URL("/login", authOrigin);
        for (const [k, v] of Object.entries({ app: appId, state, challenge: await hash(verifier), return: localPath(u.searchParams.get("return") ?? "/"), redirect_uri: origin + "/auth/callback" })) target.searchParams.set(k, v);
        return redirect(target.href, [cookie(FLOW, `${state}.${verifier}.${expires}`, 300)]);
      }
      if (u.pathname === "/auth/callback" && request.method === "GET") {
        const parts = readCookie(request, FLOW).split("."), [state, verifier, expiry] = parts, expires = Number(expiry);
        if (parts.length !== 3 || !validToken(state) || !validToken(verifier) || u.searchParams.getAll("state").length !== 1 || u.searchParams.get("state") !== state || u.searchParams.getAll("code").length !== 1 || !validToken(u.searchParams.get("code")) || !Number.isSafeInteger(expires) || expires <= now() || expires > now() + 300)
          return new Response("\u30ED\u30B0\u30A4\u30F3\u306E\u78BA\u8A8D\u306B\u5931\u6557\u3057\u307E\u3057\u305F\u3002\u3082\u3046\u4E00\u5EA6\u30ED\u30B0\u30A4\u30F3\u3057\u3066\u304F\u3060\u3055\u3044\u3002", { status: 401, headers: safeHeaders });
        const result = await binding.redeem(u.searchParams.get("code"), verifier);
        if (!validToken(result?.token) || !Number.isSafeInteger(result.expires) || result.expires <= now()) throw Error("INVALID_SESSION");
        const prior = readCookie(request, APP_COOKIE);
        if (validToken(prior)) await binding.revoke(prior);
        return redirect(localPath(result.returnPath), [cookie(APP_COOKIE, result.token, Math.min(28800, result.expires - now())), cookie(FLOW, "", 0)]);
      }
      if (u.pathname === "/auth/logout" && request.method === "POST") {
        if (request.headers.get("origin") !== origin || request.headers.get("sec-fetch-site") === "cross-site") return new Response(null, { status: 403, headers: safeHeaders });
        await binding.logout(readCookie(request, APP_COOKIE));
        return redirect("/auth/signed-out", [cookie(APP_COOKIE, "", 0), cookie(FLOW, "", 0)]);
      }
      if (u.pathname === "/auth/signed-out" && request.method === "GET") return new Response('<!doctype html><html lang="ja"><meta charset="utf-8"><title>\u30ED\u30B0\u30A2\u30A6\u30C8</title><h1>\u30ED\u30B0\u30A2\u30A6\u30C8\u3057\u307E\u3057\u305F</h1><p>SGC\u5171\u901A\u30BB\u30C3\u30B7\u30E7\u30F3\u3092\u7D42\u4E86\u3057\u307E\u3057\u305F\u3002</p><a href="/auth/login">LINE WORKS\u3067\u30ED\u30B0\u30A4\u30F3</a></html>', { headers: { ...safeHeaders, "content-type": "text/html; charset=utf-8" } });
      return null;
    },
    principal(request) {
      return binding.principal(readCookie(request, APP_COOKIE));
    }
  };
}
export {
  APP_COOKIE,
  createSsoClient
};
