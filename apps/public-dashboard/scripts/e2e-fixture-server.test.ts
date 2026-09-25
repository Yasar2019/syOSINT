// @vitest-environment node

import { access, mkdtemp, mkdir, readFile, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error The production supervisor is a directly executed Node module.
import { auditWorkspaceLinks, copyDependencyTree, reclaimStaleWorkspaces, runIsolatedFixture, shutdownSessionWorkspaces } from "./e2e-fixture-server.mjs";

const temporaryRoots: string[] = [];

async function sandbox() {
  const root = await mkdtemp(join(tmpdir(), "syosint-fixture-test-"));
  temporaryRoots.push(root);
  const repositoryRoot = join(root, "repository");
  const temporaryParent = join(root, "temporary");
  const appRoot = join(repositoryRoot, "apps/public-dashboard");
  await mkdir(join(repositoryRoot, "data/public"), { recursive: true });
  await mkdir(join(appRoot, "public"), { recursive: true });
  await mkdir(join(appRoot, "out"), { recursive: true });
  await mkdir(temporaryParent, { recursive: true });
  await writeFile(join(repositoryRoot, "data/public/news-wire.v1.json"), "production-data");
  await writeFile(join(appRoot, "public/news-wire.v1.json"), "production-public");
  await writeFile(join(appRoot, "out/index.html"), "production-out");
  return { root, repositoryRoot, appRoot, temporaryParent };
}

async function productionState(paths: Awaited<ReturnType<typeof sandbox>>) {
  return Promise.all([
    readFile(join(paths.repositoryRoot, "data/public/news-wire.v1.json"), "utf8"),
    readFile(join(paths.appRoot, "public/news-wire.v1.json"), "utf8"),
    readFile(join(paths.appRoot, "out/index.html"), "utf8"),
  ]);
}

function isInside(path: string, parent: string) {
  const offset = relative(parent, path);
  return offset !== "" && !offset.startsWith("..") && !isAbsolute(offset);
}

async function pathExists(path: string) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function prepareFixture({ workspaceRoot, fixtureWire }: Record<string, string>) {
  await mkdir(join(workspaceRoot, "data/public"), { recursive: true });
  await mkdir(join(workspaceRoot, "apps/public-dashboard/public"), { recursive: true });
  await writeFile(join(workspaceRoot, "data/public/news-wire.v1.json"), fixtureWire);
}

afterEach(async () => {
  await Promise.all(
    temporaryRoots.splice(0).map((root) => rm(root, { recursive: true, force: true })),
  );
});

describe("isolated E2E fixture server", () => {
  it("reclaims dead and invalid roots but preserves a possibly reused live PID", async () => {
    const paths = await sandbox();
    const invalid = join(paths.temporaryParent, "syosint-e2e-invalid");
    const dead = join(paths.temporaryParent, "syosint-e2e-dead");
    const live = join(paths.temporaryParent, "syosint-e2e-live");
    await mkdir(invalid);
    await mkdir(dead);
    await mkdir(live);
    await writeFile(join(dead, "owner.json"), JSON.stringify({ pid: 2_147_483_647, sessionId: "dead", token: "dead" }));
    await writeFile(join(live, "owner.json"), JSON.stringify({ pid: process.pid, sessionId: "possibly-reused", token: "live" }));

    const result = await reclaimStaleWorkspaces({ temporaryParent: paths.temporaryParent });

    expect(result.reclaimed).toBe(2);
    expect(await pathExists(invalid)).toBe(false);
    expect(await pathExists(dead)).toBe(false);
    expect(await pathExists(live)).toBe(true);
  });

  it("times out without deleting an unresponsive live owner", async () => {
    const paths = await sandbox();
    const live = join(paths.temporaryParent, "syosint-e2e-unresponsive");
    await mkdir(live);
    await writeFile(join(live, "owner.json"), JSON.stringify({
      pid: process.pid,
      sessionId: "unresponsive",
      token: "unresponsive-token",
    }));

    await expect(shutdownSessionWorkspaces({
      sessionId: "unresponsive",
      temporaryParent: paths.temporaryParent,
      timeoutMs: 10,
    })).rejects.toThrow("fixture cleanup timed out for 1 live workspace");
    expect(await pathExists(live)).toBe(true);
  });

  it("shuts down one owned session without touching a concurrent active run", async () => {
    const paths = await sandbox();
    const controller = new AbortController();
    const roots = new Map<string, string>();
    const ready = new Map<string, () => void>();

    function start(sessionId: string, signal?: AbortSignal) {
      const started = new Promise<void>((resolve) => ready.set(sessionId, resolve));
      const running = runIsolatedFixture({
        repositoryRoot: paths.repositoryRoot,
        temporaryParent: paths.temporaryParent,
        sessionId,
        signal,
        fixtureWire: sessionId,
        prepareWorkspace: async ({ workspaceRoot, fixtureWire }: Record<string, string>) => {
          roots.set(sessionId, dirname(workspaceRoot));
          await prepareFixture({ workspaceRoot, fixtureWire });
        },
        runBuild: async ({ outPath }: Record<string, string>) => {
          await mkdir(outPath, { recursive: true });
        },
        runServe: async ({ signal: runSignal }: { signal: AbortSignal }) => {
          ready.get(sessionId)?.();
          await new Promise((_, reject) => runSignal.addEventListener(
            "abort",
            () => reject(new DOMException("terminated", "AbortError")),
            { once: true },
          ));
        },
      });
      return { started, running };
    }

    const first = start("session-one");
    const second = start("session-two", controller.signal);
    const firstStopped = expect(first.running).rejects.toMatchObject({ name: "AbortError" });
    const secondStopped = expect(second.running).rejects.toMatchObject({ name: "AbortError" });
    await Promise.all([first.started, second.started]);
    await shutdownSessionWorkspaces({
      sessionId: "session-one",
      temporaryParent: paths.temporaryParent,
      timeoutMs: 2_000,
    });

    await firstStopped;
    expect(await pathExists(roots.get("session-one")!)).toBe(false);
    expect(await pathExists(roots.get("session-two")!)).toBe(true);
    controller.abort();
    await secondStopped;
  });

  it("copies Windows dependency junctions inside the temporary workspace", async () => {
    const paths = await sandbox();
    const workspaceRoot = join(paths.temporaryParent, "windows-workspace");
    const packageRoot = join(paths.repositoryRoot, "node_modules/.pnpm/example/node_modules/example");
    const appModules = join(paths.repositoryRoot, "apps/public-dashboard/node_modules");
    await mkdir(packageRoot, { recursive: true });
    await mkdir(appModules, { recursive: true });
    await writeFile(join(packageRoot, "index.js"), "production dependency");
    await symlink(packageRoot, join(appModules, "example"), "dir");

    await copyDependencyTree({
      source: join(paths.repositoryRoot, "node_modules/.pnpm"),
      destination: join(workspaceRoot, "node_modules/.pnpm"),
      repositoryRoot: paths.repositoryRoot,
      workspaceRoot,
      platform: "win32",
    });
    await copyDependencyTree({
      source: appModules,
      destination: join(workspaceRoot, "apps/public-dashboard/node_modules"),
      repositoryRoot: paths.repositoryRoot,
      workspaceRoot,
      platform: "win32",
    });
    await auditWorkspaceLinks(workspaceRoot);

    const copiedLink = join(workspaceRoot, "apps/public-dashboard/node_modules/example");
    expect(isInside(await realpath(copiedLink), workspaceRoot)).toBe(true);
    await writeFile(join(copiedLink, "index.js"), "temporary dependency");
    expect(await readFile(join(packageRoot, "index.js"), "utf8")).toBe("production dependency");
  });

  it("uses Node with a JavaScript package-manager entry on the real Windows build path", async () => {
    const paths = await sandbox();
    const managerEntry = join(paths.root, "pnpm.cjs");
    const nodeExecutable = join(paths.root, "node.exe");
    const commands: Array<{ command: string[]; cwd: string }> = [];
    await writeFile(managerEntry, "// fixture package manager");

    await runIsolatedFixture({
      repositoryRoot: paths.repositoryRoot,
      temporaryParent: paths.temporaryParent,
      fixtureWire: "fixture-data",
      prepareWorkspace: prepareFixture,
      buildPlatform: "win32",
      buildEnvironment: { npm_execpath: managerEntry },
      nodeExecutable,
      commandRunner: async (command: string[], options: { cwd: string }) => {
        commands.push({ command, cwd: options.cwd });
        await mkdir(join(options.cwd, "out"), { recursive: true });
      },
      runServe: async () => {},
    });

    expect(commands).toEqual([{
      command: [nodeExecutable, managerEntry, "build"],
      cwd: expect.stringMatching(/workspace[/\\]apps[/\\]public-dashboard$/),
    }]);
    expect(commands[0].command.join(" ")).not.toContain("corepack");
    expect(commands[0].command.join(" ")).not.toContain(".cmd");
  });

  it("rejects dependency links that resolve outside the repository", async () => {
    const paths = await sandbox();
    const workspaceRoot = join(paths.temporaryParent, "unsafe-workspace");
    const modules = join(paths.repositoryRoot, "node_modules");
    const outside = join(paths.root, "outside-dependency");
    await mkdir(modules, { recursive: true });
    await mkdir(outside, { recursive: true });
    await symlink(outside, join(modules, "unsafe"), "dir");

    await expect(copyDependencyTree({
      source: modules,
      destination: join(workspaceRoot, "node_modules"),
      repositoryRoot: paths.repositoryRoot,
      workspaceRoot,
      platform: "win32",
    })).rejects.toThrow("outside repository");
  });

  it("builds and serves only inside a unique temporary workspace", async () => {
    const paths = await sandbox();
    const before = await productionState(paths);
    let workspace = "";

    await runIsolatedFixture({
      repositoryRoot: paths.repositoryRoot,
      temporaryParent: paths.temporaryParent,
      fixtureWire: "fixture-data",
      prepareWorkspace: prepareFixture,
      runBuild: async ({ workspaceRoot, dataPath, publicPath, outPath }: Record<string, string>) => {
        workspace = workspaceRoot;
        expect(isInside(workspaceRoot, paths.temporaryParent)).toBe(true);
        expect(isInside(dataPath, workspaceRoot)).toBe(true);
        expect(isInside(publicPath, workspaceRoot)).toBe(true);
        expect(isInside(outPath, workspaceRoot)).toBe(true);
        expect(await productionState(paths)).toEqual(before);
        expect(await readFile(dataPath, "utf8")).toBe("fixture-data");
        await writeFile(publicPath, "fixture-public");
        await mkdir(outPath, { recursive: true });
        await writeFile(join(outPath, "index.html"), "fixture-out");
      },
      runServe: async ({ fixtureOut, workspaceRoot }: Record<string, string>) => {
        expect(isInside(fixtureOut, workspaceRoot)).toBe(true);
        expect(isInside(fixtureOut, paths.appRoot)).toBe(false);
        expect(await productionState(paths)).toEqual(before);
        expect(await readFile(join(fixtureOut, "index.html"), "utf8")).toBe("fixture-out");
      },
    });

    expect(workspace).not.toBe("");
    expect(await pathExists(dirname(workspace))).toBe(false);
    expect(await productionState(paths)).toEqual(before);
  });

  it("never changes production when the temporary build fails", async () => {
    const paths = await sandbox();
    const before = await productionState(paths);
    let workspace = "";

    await expect(
      runIsolatedFixture({
        repositoryRoot: paths.repositoryRoot,
        temporaryParent: paths.temporaryParent,
        fixtureWire: "fixture-data",
        prepareWorkspace: prepareFixture,
        runBuild: async ({ workspaceRoot, publicPath, outPath }: Record<string, string>) => {
          workspace = workspaceRoot;
          await writeFile(publicPath, "failed-fixture-public");
          await mkdir(outPath, { recursive: true });
          await writeFile(join(outPath, "index.html"), "failed-fixture-out");
          expect(await productionState(paths)).toEqual(before);
          throw new Error("build failure");
        },
        runServe: async () => {
          throw new Error("serve must not run");
        },
      }),
    ).rejects.toThrow("build failure");

    expect(await pathExists(dirname(workspace))).toBe(false);
    expect(await productionState(paths)).toEqual(before);
  });

  it("never changes production when the temporary build is terminated", async () => {
    const paths = await sandbox();
    const before = await productionState(paths);
    const controller = new AbortController();
    let workspace = "";
    let started!: () => void;
    const buildStarted = new Promise<void>((resolve) => { started = resolve; });

    const running = runIsolatedFixture({
      repositoryRoot: paths.repositoryRoot,
      temporaryParent: paths.temporaryParent,
      signal: controller.signal,
      fixtureWire: "fixture-data",
      prepareWorkspace: prepareFixture,
      runBuild: async ({ workspaceRoot, publicPath, outPath, signal }: { workspaceRoot: string; publicPath: string; outPath: string; signal: AbortSignal }) => {
        workspace = workspaceRoot;
        await writeFile(publicPath, "terminated-fixture-public");
        await mkdir(outPath, { recursive: true });
        await writeFile(join(outPath, "index.html"), "terminated-fixture-out");
        expect(await productionState(paths)).toEqual(before);
        started();
        await new Promise((_, reject) => {
          signal.addEventListener("abort", () => reject(new DOMException("terminated", "AbortError")), { once: true });
        });
      },
      runServe: async () => {
        throw new Error("serve must not run");
      },
    });
    await buildStarted;
    controller.abort();

    await expect(running).rejects.toMatchObject({ name: "AbortError" });
    expect(await pathExists(dirname(workspace))).toBe(false);
    expect(await productionState(paths)).toEqual(before);
  });

  it("uses distinct noninterfering workspaces for concurrent runs", async () => {
    const paths = await sandbox();
    const before = await productionState(paths);
    const workspaces: string[] = [];

    async function run(marker: string) {
      await runIsolatedFixture({
        repositoryRoot: paths.repositoryRoot,
        temporaryParent: paths.temporaryParent,
        fixtureWire: marker,
        prepareWorkspace: prepareFixture,
        runBuild: async ({ workspaceRoot, dataPath, outPath }: Record<string, string>) => {
          workspaces.push(workspaceRoot);
          expect(await readFile(dataPath, "utf8")).toBe(marker);
          await mkdir(outPath, { recursive: true });
          await writeFile(join(outPath, "index.html"), marker);
        },
        runServe: async ({ fixtureOut }: Record<string, string>) => {
          expect(await readFile(join(fixtureOut, "index.html"), "utf8")).toBe(marker);
        },
      });
    }

    await Promise.all([run("fixture-one"), run("fixture-two")]);
    expect(new Set(workspaces).size).toBe(2);
    expect(await productionState(paths)).toEqual(before);
  });

  it("ignores stale temporary residue from an earlier crashed run", async () => {
    const paths = await sandbox();
    const staleRoot = join(paths.temporaryParent, "syosint-e2e-stale", "workspace");
    await mkdir(join(staleRoot, "data/public"), { recursive: true });
    await writeFile(join(staleRoot, "data/public/news-wire.v1.json"), "poison");
    let activeWorkspace = "";

    await runIsolatedFixture({
      repositoryRoot: paths.repositoryRoot,
      temporaryParent: paths.temporaryParent,
      fixtureWire: "fresh-fixture",
      prepareWorkspace: prepareFixture,
      runBuild: async ({ workspaceRoot, dataPath, outPath }: Record<string, string>) => {
        activeWorkspace = workspaceRoot;
        expect(await readFile(dataPath, "utf8")).toBe("fresh-fixture");
        await mkdir(outPath, { recursive: true });
      },
      runServe: async () => {},
    });

    expect(activeWorkspace).not.toBe(staleRoot);
    expect(await pathExists(staleRoot)).toBe(false);
    expect(await productionState(paths)).toEqual(["production-data", "production-public", "production-out"]);
  });
});
