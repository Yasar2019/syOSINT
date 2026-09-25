import {
  reclaimStaleWorkspaces,
  shutdownSessionWorkspaces,
} from "./e2e-fixture-server.mjs";

export default async function globalTeardown() {
  const sessionId = process.env.SYOSINT_E2E_SESSION_ID;
  if (!sessionId) {
    throw new Error("fixture cleanup requires SYOSINT_E2E_SESSION_ID");
  }
  await shutdownSessionWorkspaces({ sessionId, timeoutMs: 15_000 });
  await reclaimStaleWorkspaces();
}
