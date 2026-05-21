import { cp, mkdir, readdir, rm, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const outDir = path.join(root, "dist-portal");

const allowedRootFiles = [
  "index.html",
  "main.html",
  "price.html",
  "diamond.html",
  "gemstone.html",
  "coin.html",
  "schedule.html",
  "contacts.html",
  "news.html",
  "youtube.html",
  "register.html",
  "market.html",
  "portal-frame-bridge.js",
  "sw.js",
  "manifest.json"
];

const allowedDirs = ["image", "data"];
const excludedDataFiles = new Set(["diamonds.json"]);
const allowedRootEntries = new Set([...allowedRootFiles, ...allowedDirs]);

function resolveInside(base, target) {
  const resolved = path.resolve(base, target);
  const relative = path.relative(base, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Path escapes base directory: ${target}`);
  }
  return resolved;
}

async function copyFileFromRoot(file) {
  const source = resolveInside(root, file);
  const dest = resolveInside(outDir, file);

  if (!existsSync(source)) {
    throw new Error(`Required file is missing: ${file}`);
  }

  await mkdir(path.dirname(dest), { recursive: true });
  await cp(source, dest);
}

async function copyDirFromRoot(dir) {
  const source = resolveInside(root, dir);
  const dest = resolveInside(outDir, dir);

  if (!existsSync(source)) {
    throw new Error(`Required directory is missing: ${dir}`);
  }

  await mkdir(dest, { recursive: true });
  await copyDirContents(source, dest, dir);
}

async function copyDirContents(sourceDir, destDir, relativeDir) {
  const entries = await readdir(sourceDir, { withFileTypes: true });

  for (const entry of entries) {
    const relativePath = path.posix.join(
      relativeDir.split(path.sep).join(path.posix.sep),
      entry.name
    );
    const source = path.join(sourceDir, entry.name);
    const dest = path.join(destDir, entry.name);

    if (relativeDir === "data" && excludedDataFiles.has(entry.name)) {
      continue;
    }

    if (entry.isDirectory()) {
      await mkdir(dest, { recursive: true });
      await copyDirContents(source, dest, relativePath);
      continue;
    }

    if (entry.isFile()) {
      await cp(source, dest);
    }
  }
}

async function assertExists(relativePath) {
  const target = resolveInside(outDir, relativePath);
  if (!existsSync(target)) {
    throw new Error(`Build verification failed: missing ${relativePath}`);
  }
}

async function assertNotExists(relativePath) {
  const target = resolveInside(outDir, relativePath);
  if (existsSync(target)) {
    throw new Error(`Build verification failed: forbidden path exists: ${relativePath}`);
  }
}

async function assertNoRootFilesByExtension(extension) {
  const entries = await readdir(outDir, { withFileTypes: true });
  const matches = entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(extension))
    .map((entry) => entry.name);

  if (matches.length > 0) {
    throw new Error(
      `Build verification failed: forbidden ${extension} files found: ${matches.join(", ")}`
    );
  }
}

async function assertOnlyAllowedRootEntries() {
  const entries = await readdir(outDir, { withFileTypes: true });
  const forbiddenEntries = entries
    .map((entry) => entry.name)
    .filter((name) => !allowedRootEntries.has(name));

  if (forbiddenEntries.length > 0) {
    throw new Error(
      `Build verification failed: unexpected root entries found: ${forbiddenEntries.join(", ")}`
    );
  }
}

async function assertDirectory(relativePath) {
  await assertExists(relativePath);
  const target = resolveInside(outDir, relativePath);
  const info = await stat(target);
  if (!info.isDirectory()) {
    throw new Error(`Build verification failed: ${relativePath} is not a directory`);
  }
}

async function build() {
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  for (const file of allowedRootFiles) {
    await copyFileFromRoot(file);
  }

  for (const dir of allowedDirs) {
    await copyDirFromRoot(dir);
  }

  await assertExists("index.html");
  await assertDirectory("data");
  await assertDirectory("image");

  await assertNotExists("scripts");
  await assertNotExists(".github");
  await assertNotExists("gas");
  await assertNotExists("tools");
  await assertNotExists("package.json");
  await assertNotExists("package-lock.json");
  await assertNotExists("data/diamonds.json");

  await assertNoRootFilesByExtension(".py");
  await assertNoRootFilesByExtension(".ps1");
  await assertNoRootFilesByExtension(".txt");
  await assertNoRootFilesByExtension(".log");
  await assertOnlyAllowedRootEntries();

  console.log("dist-portal build completed");
}

build().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
