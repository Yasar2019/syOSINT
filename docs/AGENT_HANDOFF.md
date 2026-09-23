# Agent Handoff

Use this procedure whenever a new ChatGPT/Codex/agent session resumes work on syOSINT.

## 1. Establish repository truth

Read, in order:

1. `docs/PROJECT_STATE.md`
2. `docs/AGENT_HANDOFF.md`
3. `docs/ROADMAP.md`
4. `docs/DECISIONS.md`
5. the active design under `docs/superpowers/specs/`
6. the active implementation plan under `docs/superpowers/plans/`, if one exists
7. recent commits and open pull requests

Do not rely on chat memory when it conflicts with committed repository state.

## 2. Check active work

Confirm:

- current branch;
- latest commit on that branch;
- whether a PR already exists;
- whether CI is green;
- whether the active milestone has an approved written design;
- whether an implementation plan exists and which task is next.

Never create a second branch or duplicate plan merely because a prior agent session ended.

## 3. Follow Superpowers workflow

For substantial feature work:

1. invoke the relevant Superpowers process skill;
2. respect any design/spec approval gate;
3. write or recover the implementation plan;
4. use TDD for production behavior;
5. make focused conventional commits;
6. run verification before claiming completion;
7. request/review code before merge;
8. finish the development branch through a PR.

If a prior session stopped mid-plan, resume the first incomplete task instead of restarting completed work.

## 4. Safety boundaries

Every agent must preserve these non-negotiable product boundaries:

- lawful public-source research only;
- no private/invite-only source access or access-control bypassing;
- no autonomous publication;
- no ordinary-person tracking, profiling, facial recognition, or doxxing;
- no precise live tactical publication;
- raw evidence and secrets remain private/local;
- Telegram-derived content is never sent to AI/ML systems;
- all public exports pass explicit safety and schema gates.

If a requested change conflicts with these boundaries, stop that change and surface the conflict.

## 5. Milestone boundaries

Current sequence:

- Milestone 0: foundation — complete
- Milestone 1: public dashboard — complete
- Milestone 2: private analyst desk — active
- Milestone 3: RSS — not started
- Milestone 4: Telegram — not started
- Milestone 5: discovery/hardening — not started

Do not pull RSS or Telegram implementation into Milestone 2 unless the user explicitly changes the roadmap.

## 6. Before ending a session

Update persistent state before stopping if meaningful work occurred:

- commit completed code/docs;
- update `docs/PROJECT_STATE.md` with what is complete and what comes next;
- update the active plan/task ledger if applicable;
- push the branch;
- ensure the PR description reflects current status;
- record any architectural decision in `docs/DECISIONS.md`.

The final handoff should name the exact branch, latest commit, verification status, and next incomplete task.

## 7. Recovery rule

If an agent or plugin stops unexpectedly:

1. inspect GitHub first;
2. recover the current branch and latest committed task;
3. inspect CI and PR status;
4. compare against `docs/PROJECT_STATE.md`;
5. continue from the first uncompleted step.

Never assume another agent is still working in the background.
