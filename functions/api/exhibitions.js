const SPREADSHEET_ID = "1jOGUMT7gQOadV-UXbZw6r7YktbHur_v42BQR6efuoAE";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly";

function jsonResponse(body, status = 200, cacheControl = "no-store") {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": cacheControl }
  });
}

function base64UrlEncode(value) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function pemToArrayBuffer(pem) {
  const base64 = pem.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\s/g, "");
  const binary = atob(base64);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0)).buffer;
}

async function createAccessToken(email, privateKey) {
  const now = Math.floor(Date.now() / 1000);
  const header = base64UrlEncode(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64UrlEncode(JSON.stringify({
    iss: email, scope: SHEETS_SCOPE, aud: TOKEN_URL, iat: now, exp: now + 3600
  }));
  const unsigned = `${header}.${claim}`;
  const key = await crypto.subtle.importKey(
    "pkcs8", pemToArrayBuffer(privateKey),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(unsigned));
  const assertion = `${unsigned}.${base64UrlEncode(new Uint8Array(signature))}`;
  const response = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=${encodeURIComponent("urn:ietf:params:oauth:grant-type:jwt-bearer")}&assertion=${assertion}`
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.access_token) throw new Error("Google access token request failed");
  return data.access_token;
}

function dateFromValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Date(Date.UTC(1899, 11, 30) + value * 86400000).toISOString().slice(0, 10);
  }
  const match = String(value || "").trim().match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})$/);
  return match ? `${match[1]}-${match[2].padStart(2, "0")}-${match[3].padStart(2, "0")}` : "";
}

function isNextDay(previous, current) {
  const next = new Date(`${previous}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString().slice(0, 10) === current;
}

function normalizeRows(values) {
  const rows = values
    .map((row) => ({ date: dateFromValue(row?.[0]), title: String(row?.[2] || "").trim() }))
    .filter((row) => row.date && row.title)
    .sort((a, b) => a.date.localeCompare(b.date));
  const events = [];
  for (const row of rows) {
    const previous = events[events.length - 1];
    if (previous && previous.title === row.title && isNextDay(previous.end, row.date)) {
      previous.end = row.date;
    } else {
      events.push({
        title: row.title,
        location: "",
        category: "\u5927\u9ec4\u91d1\u5c55",
        start: row.date,
        end: row.date
      });
    }
  }
  return events;
}

export async function onRequestGet(context) {
  const email = context.env?.GOOGLE_SERVICE_ACCOUNT_EMAIL;
  const privateKey = String(context.env?.GOOGLE_PRIVATE_KEY || "").replace(/\\n/g, "\n").trim();
  if (!email || !privateKey) return jsonResponse({ error: "Google Sheets credentials are not configured" }, 503);
  try {
    const accessToken = await createAccessToken(email, privateKey);
    const range = encodeURIComponent("A:C");
    const response = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/${range}?majorDimension=ROWS&valueRenderOption=UNFORMATTED_VALUE`, {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !Array.isArray(data?.values)) return jsonResponse({ error: "Google Sheets data request failed" }, 502);
    return jsonResponse(normalizeRows(data.values), 200, "public, max-age=60, s-maxage=300");
  } catch (error) {
    return jsonResponse({ error: "Failed to load exhibition schedule" }, 502);
  }
}
