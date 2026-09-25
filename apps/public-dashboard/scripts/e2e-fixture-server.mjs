import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import {
  access,
  cp,
  copyFile,
  lstat,
  mkdir,
  mkdtemp,
  readdir,
  readFile,
  realpath,
  rename,
  rm,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const defaultAppRoot = resolve(dirname(scriptPath), "..");
const defaultRepositoryRoot = resolve(defaultAppRoot, "../..");
const workspacePrefix = "syosint-e2e-";
const initializingPrefix = ".syosint-e2e-init-";
const ownerFilename = "owner.json";
const shutdownFilename = "shutdown-request.json";

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

function createFixtureWire() {
  const generatedAt = "2026-09-24T18:00:00Z";
  const sources = [
    {
      id: "fixture-en",
      label: { en: "Fixture English", ar: "مصدر إنجليزي تجريبي" },
      language: "en",
      attribution: "Fixture English attribution",
      attributionUrl: "https://example.org/en/legal",
    },
    {
      id: "fixture-ar",
      label: { en: "Fixture Arabic", ar: "مصدر عربي تجريبي" },
      language: "ar",
      attribution: "Fixture Arabic attribution",
      attributionUrl: "https://example.org/ar/legal",
    },
  ];
  const entries = Array.from({ length: 55 }, (_, index) => {
    const source = sources[index % sources.length];
    const publishedAt = new Date(Date.parse(generatedAt) - index * 60_000)
      .toISOString()
      .replace(".000Z", "Z");
    return {
      id: `${source.id}:${index}`,
      sourceId: source.id,
      sourceLabel: source.label,
      language: source.language,
      headline:
        source.language === "ar"
          ? `عنوان تجريبي عن سوريا ${index}`
          : `Fixture Syria headline ${index}`,
      url: `https://example.org/${source.language}/${index}`,
      publishedAt,
      collectedAt: generatedAt,
    };
  });
  return {
    schemaVersion: "1.1.0",
    generatedAt,
    lastSuccessfulRefreshAt: generatedAt,
    sources: { configured: 2, healthy: 2, delayed: 0 },
    sourceStates: sources.map((source) => ({
      ...source,
      status: "healthy",
      lastSuccessfulRefreshAt: generatedAt,
      entryCount: entries.filter((entry) => entry.sourceId === source.id).length,
    })),
    entries,
  };
}

function abortError() {
  return new DOMException("The operation was aborted", "AbortError");
}

function processIsPossiblyAlive(pid) {
  if (!Number.isSafeInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code !== "ESRCH";
  }
}

async function readOwner(temporaryRoot) {
  try {
    const value = JSON.parse(await readFile(join(temporaryRoot, ownerFilename), "utf8"));
    if (
      !Number.isSafeInteger(value.pid)
      || value.pid <= 0
      || typeof value.sessionId !== "string"
      || value.sessionId.length === 0
      || typeof value.token !== "string"
      || value.token.length === 0
    ) return null;
    return value;
  } catch {
    return null;
  }
}

async function ownedWorkspaceRoots(temporaryParent) {
  try {
    return (await readdir(temporaryParent, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory() && entry.name.startsWith(workspacePrefix))
      .map((entry) => join(temporaryParent, entry.name));
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

export async function reclaimStaleWorkspaces({ temporaryParent = tmpdir() } = {}) {
  let reclaimed = 0;
  let preserved = 0;
  for (const temporaryRoot of await ownedWorkspaceRoots(temporaryParent)) {
    const owner = await readOwner(temporaryRoot);
    if (owner && processIsPossiblyAlive(owner.pid)) {
      preserved += 1;
      continue;
    }
    await rm(temporaryRoot, { recursive: true, force: true });
    reclaimed += 1;
  }
  return { reclaimed, preserved };
}

function wait(delayMs) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, delayMs));
}

export async function shutdownSessionWorkspaces({
  sessionId,
  temporaryParent = tmpdir(),
  timeoutMs = 15_000,
}) {
  const targets = [];
  for (const temporaryRoot of await ownedWorkspaceRoots(temporaryParent)) {
    const owner = await readOwner(temporaryRoot);
    if (!owner || owner.sessionId !== sessionId) continue;
    if (!processIsPossiblyAlive(owner.pid)) {
      await rm(temporaryRoot, { recursive: true, force: true });
      continue;
    }
    await writeFile(
      join(temporaryRoot, shutdownFilename),
      `${JSON.stringify({ token: owner.token })}\n`,
      "utf8",
    );
    targets.push({ temporaryRoot, token: owner.token });
  }

  const deadline = Date.now() + timeoutMs;
  while (targets.length > 0) {
    for (let index = targets.length - 1; index >= 0; index -= 1) {
      const target = targets[index];
      if (!(await exists(target.temporaryRoot))) {
        targets.splice(index, 1);
        continue;
      }
      const owner = await readOwner(target.temporaryRoot);
      if (!owner) {
        await rm(target.temporaryRoot, { recursive: true, force: true });
        targets.splice(index, 1);
        continue;
      }
      if (owner.token !== target.token) {
        throw new Error("fixture workspace ownership changed during cleanup");
      }
      if (!processIsPossiblyAlive(owner.pid)) {
        await rm(target.temporaryRoot, { recursive: true, force: true });
        targets.splice(index, 1);
      }
    }
    if (targets.length === 0) break;
    if (Date.now() >= deadline) {
      throw new Error(`fixture cleanup timed out for ${targets.length} live workspace(s)`);
    }
    await wait(50);
  }
}

async function createOwnedWorkspaceRoot({ temporaryParent, sessionId }) {
  await mkdir(temporaryParent, { recursive: true });
  await reclaimStaleWorkspaces({ temporaryParent });
  const token = randomUUID();
  const initializingRoot = await mkdtemp(join(temporaryParent, initializingPrefix));
  const temporaryRoot = join(temporaryParent, `${workspacePrefix}${token}`);
  try {
    await writeFile(
      join(initializingRoot, ownerFilename),
      `${JSON.stringify({ pid: process.pid, sessionId, token })}\n`,
      "utf8",
    );
    await rename(initializingRoot, temporaryRoot);
  } catch (error) {
    await rm(initializingRoot, { recursive: true, force: true });
    throw error;
  }
  return { temporaryRoot, token };
}

function runCommand(command, { cwd, signal, ownProcessGroup = true }) {
  if (signal?.aborted) return Promise.reject(abortError());
  return new Promise((resolvePromise, reject) => {
    const detached = ownProcessGroup && process.platform !== "win32";
    const child = spawn(command[0], command.slice(1), {
      cwd,
      detached,
      env: { ...process.env, GITHUB_ACTIONS: "false" },
      stdio: "inherit",
    });
    let escalation;

    function killOwnedProcesses(force = false) {
      if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
      const childPid = detached ? -child.pid : child.pid;
      try {
        process.kill(childPid, force ? "SIGKILL" : "SIGTERM");
      } catch (error) {
        if (error?.code !== "ESRCH") throw error;
      }
    }

    function onAbort() {
      killOwnedProcesses();
      escalation = setTimeout(() => killOwnedProcesses(true), 2_000);
      escalation.unref();
    }

    signal?.addEventListener("abort", onAbort, { once: true });
    child.once("error", (error) => {
      signal?.removeEventListener("abort", onAbort);
      if (escalation) clearTimeout(escalation);
      reject(error);
    });
    child.once("exit", (code, childSignal) => {
      signal?.removeEventListener("abort", onAbort);
      if (escalation) clearTimeout(escalation);
      if (signal?.aborted) reject(abortError());
      else if (code === 0) resolvePromise();
      else reject(new Error(`command stopped: code=${code} signal=${childSignal}`));
    });
  });
}

async function validatedJavaScriptEntry(candidate, { requirePnpmName = false } = {}) {
  if (
    typeof candidate !== "string"
    || !isAbsolute(candidate)
    || /[\0\r\n]/.test(candidate)
    || ![".cjs", ".js", ".mjs"].includes(extname(candidate).toLowerCase())
  ) return null;
  try {
    const resolved = await realpath(candidate);
    const details = await stat(resolved);
    if (!details.isFile()) return null;
    if (requirePnpmName && !basename(resolved).toLowerCase().includes("pnpm")) {
      return null;
    }
    return resolved;
  } catch {
    return null;
  }
}

export async function resolveBuildCommand({
  buildPlatform = process.platform,
  buildEnvironment = process.env,
  nodeExecutable = process.execPath,
}) {
  const configuredEntry = buildEnvironment.npm_execpath;
  const configured = await validatedJavaScriptEntry(
    buildPlatform === "win32"
      && typeof configuredEntry === "string"
      && configuredEntry.toLowerCase().endsWith(".cmd")
      ? null
      : configuredEntry,
    { requirePnpmName: true },
  );
  if (configured) return [nodeExecutable, configured, "build"];

  for (const candidate of [
    resolve(dirname(nodeExecutable), "../node_modules/pnpm/bin/pnpm.cjs"),
    resolve(dirname(nodeExecutable), "../lib/node_modules/pnpm/bin/pnpm.cjs"),
  ]) {
    const pnpmEntry = await validatedJavaScriptEntry(candidate, {
      requirePnpmName: true,
    });
    if (pnpmEntry) return [nodeExecutable, pnpmEntry, "build"];
  }

  for (const candidate of [
    resolve(dirname(nodeExecutable), "../lib/node_modules/corepack/dist/corepack.js"),
    resolve(dirname(nodeExecutable), "../node_modules/corepack/dist/corepack.js"),
  ]) {
    const corepackEntry = await validatedJavaScriptEntry(candidate);
    if (corepackEntry) {
      return [nodeExecutable, corepackEntry, "pnpm", "build"];
    }
  }
  throw new Error("portable package-manager JavaScript entry not found");
}

export async function runDefaultBuild({
  appRoot,
  signal,
  buildPlatform = process.platform,
  buildEnvironment = process.env,
  nodeExecutable = process.execPath,
  commandRunner = runCommand,
}) {
  const command = await resolveBuildCommand({
    buildPlatform,
    buildEnvironment,
    nodeExecutable,
  });
  await commandRunner(command, { cwd: appRoot, signal });
}

async function copyDirectory(source, destination, excludedTopLevel = []) {
  const excluded = new Set(excludedTopLevel);
  await cp(source, destination, {
    recursive: true,
    verbatimSymlinks: true,
    filter: (candidate) => {
      const offset = relative(source, candidate);
      if (offset === "") return true;
      const topLevel = offset.split(sep)[0];
      return !excluded.has(topLevel);
    },
  });
}

function isInside(candidate, root) {
  const offset = relative(root, candidate);
  return offset === "" || (!offset.startsWith("..") && !isAbsolute(offset));
}

export async function copyDependencyTree({
  source,
  destination,
  repositoryRoot,
  workspaceRoot,
  platform = process.platform,
  excludedTopLevel = [],
}) {
  const excluded = new Set(excludedTopLevel);
  await mkdir(destination, { recursive: true });

  async function copyEntry(sourcePath, destinationPath, topLevel) {
    if (excluded.has(topLevel)) return;
    const details = await lstat(sourcePath);
    if (details.isSymbolicLink()) {
      const productionTarget = await realpath(sourcePath);
      if (!isInside(productionTarget, repositoryRoot)) {
        throw new Error("dependency link resolves outside repository");
      }
      const temporaryTarget = join(
        workspaceRoot,
        relative(repositoryRoot, productionTarget),
      );
      const targetDetails = await stat(sourcePath);
      const linkType = targetDetails.isDirectory()
        ? platform === "win32" ? "junction" : "dir"
        : "file";
      const linkTarget = platform === "win32"
        ? temporaryTarget
        : relative(dirname(destinationPath), temporaryTarget);
      await symlink(linkTarget, destinationPath, linkType);
      return;
    }
    if (details.isDirectory()) {
      await mkdir(destinationPath, { recursive: true });
      const children = await readdir(sourcePath);
      await Promise.all(children.map((child) => copyEntry(
        join(sourcePath, child),
        join(destinationPath, child),
        topLevel,
      )));
      return;
    }
    if (details.isFile()) {
      await copyFile(sourcePath, destinationPath, constants.COPYFILE_FICLONE);
      return;
    }
    throw new Error("unsupported dependency filesystem entry");
  }

  const entries = await readdir(source);
  await Promise.all(entries.map((entry) => copyEntry(
    join(source, entry),
    join(destination, entry),
    entry,
  )));
}

export async function auditWorkspaceLinks(workspaceRoot) {
  async function audit(path) {
    const details = await lstat(path);
    if (details.isSymbolicLink()) {
      const target = await realpath(path);
      if (!isInside(target, workspaceRoot)) {
        throw new Error("temporary workspace link resolves outside workspace");
      }
      return;
    }
    if (!details.isDirectory()) return;
    const children = await readdir(path);
    await Promise.all(children.map((child) => audit(join(path, child))));
  }

  await audit(workspaceRoot);
}

export async function prepareFixtureWorkspace({
  repositoryRoot,
  workspaceRoot,
  fixtureWire,
}) {
  await mkdir(workspaceRoot, { recursive: true });
  for (const filename of [
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "tsconfig.base.json",
  ]) {
    await cp(join(repositoryRoot, filename), join(workspaceRoot, filename));
  }
  await copyDirectory(
    join(repositoryRoot, "apps/public-dashboard"),
    join(workspaceRoot, "apps/public-dashboard"),
    [".next", "node_modules", "out", "playwright-report", "test-results"],
  );
  await copyDirectory(
    join(repositoryRoot, "packages/schemas"),
    join(workspaceRoot, "packages/schemas"),
    ["node_modules"],
  );
  await copyDirectory(
    join(repositoryRoot, "data/public"),
    join(workspaceRoot, "data/public"),
  );
  await writeFile(
    join(workspaceRoot, "data/public/news-wire.v1.json"),
    fixtureWire,
    "utf8",
  );
  await mkdir(join(workspaceRoot, "node_modules"), { recursive: true });
  await copyDependencyTree({
    source: join(repositoryRoot, "node_modules/.pnpm"),
    destination: join(workspaceRoot, "node_modules/.pnpm"),
    repositoryRoot,
    workspaceRoot,
    excludedTopLevel: ["node_modules"],
  });
  await copyDependencyTree({
    source: join(repositoryRoot, "apps/public-dashboard/node_modules"),
    destination: join(workspaceRoot, "apps/public-dashboard/node_modules"),
    repositoryRoot,
    workspaceRoot,
    excludedTopLevel: [".vite", ".vite-temp"],
  });
  await copyDependencyTree({
    source: join(repositoryRoot, "packages/schemas/node_modules"),
    destination: join(workspaceRoot, "packages/schemas/node_modules"),
    repositoryRoot,
    workspaceRoot,
  });
  await auditWorkspaceLinks(workspaceRoot);
}

export async function runIsolatedFixture({
  repositoryRoot = defaultRepositoryRoot,
  temporaryParent = tmpdir(),
  sessionId = process.env.SYOSINT_E2E_SESSION_ID ?? randomUUID(),
  fixtureWire = `${JSON.stringify(createFixtureWire(), null, 2)}\n`,
  signal,
  buildPlatform = process.platform,
  buildEnvironment = process.env,
  nodeExecutable = process.execPath,
  commandRunner = runCommand,
  prepareWorkspace = prepareFixtureWorkspace,
  runBuild = runDefaultBuild,
  runServe = ({ appRoot, signal: serveSignal }) =>
    runCommand([process.execPath, join(appRoot, "scripts/serve-static.mjs")], {
      cwd: appRoot,
      ownProcessGroup: false,
      signal: serveSignal,
    }),
}) {
  const { temporaryRoot, token } = await createOwnedWorkspaceRoot({
    temporaryParent,
    sessionId,
  });
  const controller = new AbortController();
  const onExternalAbort = () => controller.abort();
  signal?.addEventListener("abort", onExternalAbort, { once: true });
  if (signal?.aborted) controller.abort();
  const shutdownPoll = setInterval(async () => {
    try {
      const request = JSON.parse(
        await readFile(join(temporaryRoot, shutdownFilename), "utf8"),
      );
      if (request.token === token) controller.abort();
    } catch (error) {
      if (error?.code !== "ENOENT" && !(error instanceof SyntaxError)) {
        controller.abort(error);
      }
    }
  }, 50);
  const workspaceRoot = join(temporaryRoot, "workspace");
  const appRoot = join(workspaceRoot, "apps/public-dashboard");
  const dataPath = join(workspaceRoot, "data/public/news-wire.v1.json");
  const publicPath = join(appRoot, "public/news-wire.v1.json");
  const outPath = join(appRoot, "out");
  const context = {
    repositoryRoot,
    temporaryRoot,
    workspaceRoot,
    appRoot,
    dataPath,
    publicPath,
    outPath,
    fixtureOut: outPath,
    fixtureWire,
    signal: controller.signal,
    buildPlatform,
    buildEnvironment,
    nodeExecutable,
    commandRunner,
  };

  try {
    if (controller.signal.aborted) throw abortError();
    await prepareWorkspace(context);
    if (controller.signal.aborted) throw abortError();
    await runBuild(context);
    if (!(await exists(outPath))) {
      throw new Error("fixture build produced no out directory");
    }
    await runServe(context);
  } finally {
    clearInterval(shutdownPoll);
    signal?.removeEventListener("abort", onExternalAbort);
    await rm(temporaryRoot, { recursive: true, force: true });
  }
}

async function main() {
  const controller = new AbortController();
  let receivedSignal = null;
  const handlers = new Map();
  for (const name of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    const handler = () => {
      receivedSignal = name;
      controller.abort();
    };
    handlers.set(name, handler);
    process.once(name, handler);
  }
  try {
    await runIsolatedFixture({ signal: controller.signal });
  } catch (error) {
    if (!receivedSignal) throw error;
  } finally {
    for (const [name, handler] of handlers) {
      process.removeListener(name, handler);
    }
  }
  if (receivedSignal) process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === scriptPath) {
  await main();
}
