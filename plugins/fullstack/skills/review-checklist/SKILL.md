---
name: review-checklist
description: "Structured code review for this stack: a checklist covering correctness, security (OWASP Top 10, authorization, input validation, secrets), Spring Boot pitfalls (N+1, transaction boundaries, entity leakage, missing validation), TypeScript and frontend pitfalls (signal and effect misuse, stale closures, accessibility, bundle size), tests, and API contract drift. Produces findings ordered by severity with file and line references. Use when asked to review code, a diff, a branch or a pull request, or before opening one."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# Review Checklist

Targets: Spring Boot 4 / Java 21-25 backends; Angular 22, React 19, Next.js 16 TypeScript frontends. First detect the project's real versions and adapt; never downgrade a project.

A review finds defects a linter and the compiler cannot: wrong behavior, security holes, data loss, performance traps, missing tests and contract drift.
It reports them in a fixed format, most severe first, each tied to a file and line.

## Use when / do not use

Use when:

- Asked to review code, a diff, a commit range, a branch or a pull request.
- Self-reviewing before opening a pull request (the last step of `fullstack-feature`).
- Asked "is this safe / ready to merge / what did I miss".

Do not use:

- To restyle code or enforce formatting that ESLint, Prettier, Checkstyle, Spotless or similar already enforce.
- To write the feature or fix itself (use `fullstack-feature`, `spring-boot-conventions`, the framework skills); review first, then fix only if asked.
- For a dedicated threat model or penetration test; this is a code-level security pass.

## Workflow

1. **Get the change set.** Determine the base (`main` unless told otherwise; for a PR, its target branch): `git fetch origin && git merge-base origin/main HEAD`, then `git diff --stat <base>...HEAD` and `git diff <base>...HEAD`. For uncommitted work add `git diff HEAD`. For a GitHub PR, `gh pr diff <n>` and `gh pr view <n>` for the description.
2. **Understand intent.** Read the PR description, linked ticket and commit messages. Review against the stated goal; note scope creep separately.
3. **Detect versions and tooling.** Read `pom.xml`/`build.gradle*`, `package.json`, `angular.json`/`next.config.*`, and lint configs. Note which checks a linter already covers so you skip them.
4. **Classify changed files by layer:** controller/API, service/domain, persistence (entities, repositories, migrations), security config, frontend component/state, frontend data access, generated client, spec (`api/openapi.json`), tests, build/CI, config/secrets.
5. **Apply checklists per layer.** Read surrounding code, not only the hunk: callers, transaction boundaries, the entity mapping, the template. Use `references/backend-checklist.md`, `references/frontend-checklist.md`, and `references/security-checklist.md` for every change that touches input, auth, data access or config.
6. **Check cross-cutting items:** contract drift (DTO changed but spec/client not regenerated, or hand-edited generated code; see `api-contract`), missing or weak tests for new behavior, migrations vs. entity changes, feature flags, logging of sensitive data.
7. **Verify when cheap.** Run the targeted tests, `tsc --noEmit`, or the build if the environment allows. A finding confirmed by a failing test beats a guess.
8. **Report** in the output format below. If nothing significant is found, say so and list what was checked.

### Severity

| Level | Meaning | Examples |
| --- | --- | --- |
| Blocker | Must fix before merge: security hole, data loss/corruption, broken build, production crash | Missing authorization on endpoint, SQL injection, migration drops a column still read |
| Major | Wrong behavior or serious risk under realistic conditions | N+1 on a list endpoint, race on update without locking, unhandled error state in UI |
| Minor | Correct but fragile, unclear or slightly wrong | Missing test for an edge case, leaky abstraction, confusing naming that hides behavior |
| Nit | Optional polish; omit entirely when a linter or formatter exists | Wording, small simplification |

### Output format

```text
## Review: <branch or PR> (<n> files, base <sha>)

Summary: <one or two sentences: overall risk and merge recommendation>

### Blocker
1. `path/to/File.java:42` <short title>
   Why: <concrete consequence, the input or scenario that triggers it>
   Fix: <specific change, code snippet if short>

### Major
...

### Minor
...

### Checked, no findings
- Security: authz on new endpoints, input validation, secrets
- Contract: spec and client regenerated
- Tests: ...
```

- Order by severity, then by file. Number findings so they can be referenced.
- Every finding has `file:line` (line in the new version), a `Why` stating the consequence, and a `Fix`.
- Group repeated instances of one issue into a single finding listing all locations.
- Questions about intent go in a separate "Questions" section, not disguised as findings.

## Rules

- Do review the diff in context: open the full file and its callers before judging a hunk.
- Do state the concrete failure scenario for each finding; "could be a problem" is not a finding.
- Do prioritize: security, data integrity and correctness before performance, before maintainability.
- Do check authorization on every new or changed endpoint and every new query by ID.
- Do check that new behavior has tests that would fail without the change.
- Do check spec and generated client are regenerated whenever a DTO, controller or error shape changed.
- Do check database migrations for locking, backfills, and compatibility with the currently deployed code.
- Do mark uncertain findings as such and say what would confirm them.
- Do acknowledge clearly good decisions briefly when it helps the author; keep it to one line.
- Don't report style issues a configured linter or formatter enforces.
- Don't flood the review with nits; cap at a handful, or omit them.
- Don't propose rewrites outside the change scope; note them as follow-ups.
- Don't approve changes you could not read fully (binary files, huge generated diffs): say what was skipped.
- Don't edit files during a review unless asked to apply fixes.
- Don't trust comments or PR descriptions over code; verify claims.
- Don't include secrets found in the diff in the report verbatim; reference location and rotate advice.

## References

| File | Read when |
|---|---|
| [references/backend-checklist.md](references/backend-checklist.md) | Any Java/Spring change: controllers, services, JPA, transactions, migrations, config, tests |
| [references/frontend-checklist.md](references/frontend-checklist.md) | Any Angular, React or Next.js change: components, state, effects, data fetching, a11y, bundle, tests |
| [references/security-checklist.md](references/security-checklist.md) | Changes touching input, authentication, authorization, data access, file handling, config, dependencies or secrets |
