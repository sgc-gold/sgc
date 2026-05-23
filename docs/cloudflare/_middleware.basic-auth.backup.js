const REALM = "SGC Portal";
const BLOCKED_PATH_PREFIXES = [
  "/scripts",
  "/.github",
  "/gas",
  "/tools"
];
const BLOCKED_EXACT_PATHS = new Set([
  "/data/diamonds.json",
  "/package.json",
  "/package-lock.json",
  "/wrangler.toml",
  "/wrangler.jsonc",
  "/.env"
]);

function notFound() {
  return new Response("Not found", {
    status: 404,
    headers: {
      "Cache-Control": "no-store"
    }
  });
}

function isBlockedPath(pathname) {
  if (BLOCKED_EXACT_PATHS.has(pathname)) {
    return true;
  }

  return BLOCKED_PATH_PREFIXES.some((prefix) => (
    pathname === prefix || pathname.startsWith(`${prefix}/`)
  ));
}

function unauthorized() {
  const body = `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta http-equiv="cache-control" content="no-store">
  <meta http-equiv="pragma" content="no-cache">
  <meta http-equiv="expires" content="0">
  <title>再ログインが必要です</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #0e1f17;
      --panel: #ffffff;
      --text: #17231d;
      --muted: #5f6f67;
      --gold: #c09a50;
      --gold-dark: #8a6a28;
      --border: rgba(14, 31, 23, 0.14);
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      min-height: 100%;
      margin: 0;
    }

    body {
      display: grid;
      place-items: center;
      padding: max(24px, env(safe-area-inset-top)) 18px max(24px, env(safe-area-inset-bottom));
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.65;
    }

    main {
      width: min(100%, 440px);
      padding: 28px 24px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22);
    }

    h1 {
      margin: 0 0 12px;
      font-size: 22px;
      line-height: 1.35;
      letter-spacing: 0;
    }

    p {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 15px;
    }

    button {
      width: 100%;
      min-height: 48px;
      border: 0;
      border-radius: 6px;
      background: var(--gold);
      color: #111;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button:active {
      background: var(--gold-dark);
      color: #fff;
    }

    .note {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 13px;
    }

    .note p {
      margin-bottom: 8px;
      font-size: inherit;
    }
  </style>
</head>
<body>
  <main>
    <h1>再ログインが必要です</h1>
    <p>パスワード変更などにより、保存済みのログイン情報が使えなくなりました。</p>
    <button type="button" id="reload-button">再ログイン</button>
    <div class="note">
      <p>ホーム画面から開いている場合、ボタンで戻れないときはアプリを一度終了してから開き直してください。</p>
      <p>それでも改善しない場合は、SafariまたはChromeで同じURLを開いてログインしてから、ホーム画面のアプリを開いてください。</p>
    </div>
  </main>
  <script>
    document.getElementById("reload-button").addEventListener("click", function() {
      var url = new URL(window.location.href);
      url.searchParams.set("auth_retry", Date.now().toString());
      window.location.replace(url.toString());
    });
  </script>
</body>
</html>`;

  return new Response(body, {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
      "Cache-Control": "no-store",
      "Content-Type": "text/html; charset=UTF-8"
    }
  });
}

function serverError() {
  return new Response("Authentication is not configured", {
    status: 500,
    headers: {
      "Cache-Control": "no-store"
    }
  });
}

function decodeBasicCredentials(header) {
  const match = header && header.match(/^Basic\s+(.+)$/i);
  if (!match) {
    return null;
  }

  try {
    const encoded = match[1].trim();
    const binary = atob(encoded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const decoded = new TextDecoder().decode(bytes);
    const separator = decoded.indexOf(":");

    if (separator === -1) {
      return null;
    }

    return {
      user: decoded.slice(0, separator),
      pass: decoded.slice(separator + 1)
    };
  } catch {
    return null;
  }
}

async function digest(value) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return new Uint8Array(hash);
}

async function timingSafeEqual(left, right) {
  const leftHash = await digest(left);
  const rightHash = await digest(right);

  if (leftHash.length !== rightHash.length) {
    return false;
  }

  let diff = 0;
  for (let index = 0; index < leftHash.length; index += 1) {
    diff |= leftHash[index] ^ rightHash[index];
  }
  return diff === 0;
}

async function credentialsMatch(actual, expectedUser, expectedPass) {
  if (!actual) {
    return false;
  }

  const userMatches = await timingSafeEqual(actual.user, expectedUser);
  const passMatches = await timingSafeEqual(actual.pass, expectedPass);
  return userMatches && passMatches;
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (isBlockedPath(url.pathname)) {
    return notFound();
  }

  const expectedUser = context.env.BASIC_AUTH_USER;
  const expectedPass = context.env.BASIC_AUTH_PASS;

  if (!expectedUser || !expectedPass) {
    return serverError();
  }

  const credentials = decodeBasicCredentials(context.request.headers.get("Authorization"));
  if (!(await credentialsMatch(credentials, expectedUser, expectedPass))) {
    return unauthorized();
  }

  return context.next();
}
