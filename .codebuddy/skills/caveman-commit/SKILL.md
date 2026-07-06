---
name: caveman-commit
description: >
  Ultra-compressed commit message generator. Cuts noise from commit messages while preserving
  intent and reasoning. Conventional Commits format. Subject ≤50 chars, body only when "why"
  isn't obvious. Use when user says "write a commit", "commit message", "generate commit",
  "/commit", or invokes /caveman-commit. Auto-triggers when staging changes.
---

Write commit messages in Chinese, terse and exact. Conventional Commits format. No fluff. Why over what.

## Rules

**Subject line:**
- `<type>(<scope>): <imperative summary>` — `<scope>` optional
- Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `build`, `ci`, `style`, `revert`
- Imperative mood: "add", "fix", "remove" — not "added", "adds", "adding"
- ≤50 chars when possible, hard cap 72
- No trailing period

**Body (only if needed):**
- Skip entirely when subject is self-explanatory
- Add body only for: non-obvious *why*, breaking changes, migration notes, linked issues
- Wrap at 72 chars
- Bullets `-` not `*`
- Reference issues/PRs at end: `Closes #42`, `Refs #17`

**What NEVER goes in:**
- "This commit does X", "I", "we", "now", "currently" — the diff says what
- "As requested by..." — use Co-authored-by trailer
- "Generated with Claude Code" or any AI attribution — unless the user's own rule requires an `Assisted-by`/AI-attribution trailer, then add it as a trailer
- Emoji (unless project convention requires)
- Restating the file name when scope already says it

## Examples

Diff: new endpoint for user profile with body explaining the why
- ❌ "feat(api): add a new endpoint to get user profile information from the database"
- ✅
  ```
  feat(api): 新增 GET /users/:id/profile

  移动端冷启动时需获取精简用户资料以减少 LTE 带宽消耗。

  Closes #128
  ```

Diff: breaking API change
- ✅
  ```
  feat(api)!: 将 /v1/orders 重命名为 /v1/checkout

  BREAKING CHANGE: 客户端需在 2026-06-01 前从 /v1/orders 迁移到
  /v1/checkout，旧路由届时返回 410。
  ```

## Auto-Clarity

Always include body for: breaking changes, security fixes, data migrations, anything reverting a prior commit. Never compress these into subject-only — future debuggers need the context.

## Execution

After generating the commit message, run `git commit` with it immediately:
- Stage files first: `git add <files>` (stage all tracked changes with `git add -u`, or all with `git add -A`)
- Then commit: use `git commit -m "subject" -m "body"` (multiple `-m` for body lines)
- For multi-line bodies, chain `-m` per line/paragraph
- Use `--amend` only if the user explicitly asks for it
- Commit 完成后，**主动询问用户是否需要 push**：提示已提交的 commit hash（前 7 位），问"是否需要推送到远程仓库？"
- 仅在用户明确同意后再执行 `git push`

## Boundaries

Only stages, generates the commit message, commits, and **asks user whether to push**. Does not push without user confirmation. Does not amend unless asked. "stop caveman-commit" or "normal mode": revert to verbose commit style, but still execute the commit.
