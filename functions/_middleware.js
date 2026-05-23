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

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (isBlockedPath(url.pathname)) {
    return notFound();
  }

  return context.next();
}
