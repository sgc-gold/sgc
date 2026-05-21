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
  return new Response("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
      "Cache-Control": "no-store"
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
