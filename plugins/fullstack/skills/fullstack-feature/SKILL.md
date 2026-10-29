---
name: fullstack-feature
description: "End-to-end workflow for a feature that spans a Spring Boot API and a TypeScript frontend: clarify scope, design the contract first (api-contract), implement the backend with tests (spring-boot-conventions, spring-boot-testing), regenerate the client, implement the UI with tests (frontend-testing plus the framework skill), run the review checklist and prepare the pull request. Use when asked to implement, plan or estimate a feature, user story or ticket that touches both backend and frontend. Not for single-layer changes."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# Fullstack Feature

Targets: Spring Boot 4 / Java 21-25 backend; Angular 22, React 19 or Next.js 16 TypeScript frontend. First detect the project's real versions (`pom.xml`/`build.gradle*`, `package.json`) and adapt; never downgrade a project.

This skill is the conductor. Each step delegates detail to a sibling skill; load it when you reach that step.
Contract first, backend second, client generated, UI last: the frontend never guesses the API shape.

## Use when / do not use

Use when:

- Implementing a feature, user story or ticket that needs a new or changed endpoint and UI that uses it.
- Planning or estimating such a feature (run steps 1-2 and stop with the plan).
- Splitting a cross-layer feature into reviewable commits or pull requests.

Do not use:

- For backend-only changes (use `spring-boot-conventions`, `spring-boot-testing`, `api-contract`).
- For frontend-only changes against an existing API (use `angular-developer` or `vercel-react-best-practices`, plus `frontend-testing`).
- For only regenerating a client or fixing the spec (use `api-contract`).
- For reviewing someone else's change (use `review-checklist`).

## Workflow

1. **Clarify scope.** Restate the goal, actors and acceptance criteria as testable statements. List what is out of scope, permissions (who may do what), edge cases (empty, large, concurrent, invalid), and non-functional needs (pagination, performance, audit). Ask the user only about decisions you cannot infer from the code or ticket; otherwise state assumptions explicitly.
2. **Explore and plan.** Find the backend module, the closest existing endpoint and screen to copy patterns from, the spec location, the generated client folder and the test setup. Write a short plan: endpoints, DTOs, persistence changes (migration), UI routes/components, tests per layer, and the commit/PR split. For an estimate, stop here and report the plan with sizes and risks.
3. **Design the contract first** with `api-contract`: paths, methods, request/response DTOs, error types (RFC 9457), pagination, enums, dates, authorization per operation. Check `oasdiff breaking` if existing endpoints change. Get user sign-off on the contract when it is non-trivial or breaking.
4. **Implement the backend** with `spring-boot-conventions`: migration, entity/repository, service with transaction boundary and authorization, controller with validation, exception mapping. Write tests with `spring-boot-testing`: controller slice (validation, security, error shapes), repository with Testcontainers for custom queries, service/integration for the main flow. Run the backend test suite.
5. **Export the spec and regenerate the client.** Run the spec export, review `git diff api/openapi.json` for exactly the intended change, regenerate the TypeScript client, commit both. Never hand-edit generated code.
6. **Implement the UI** with the framework skill (`angular-developer` for Angular, `vercel-react-best-practices` for React/Next.js) and `typescript-conventions`: data access through the generated client, loading/empty/error states, Problem Details mapped to form fields, accessibility, route and permission handling. Write tests with `frontend-testing` (HTTP mocked at the network layer, error states covered; E2E for the critical path if the project has E2E). Run lint, type-check, unit tests and build.
7. **Self-review** with `review-checklist` against the base branch. Fix blockers and majors; list deliberate trade-offs. Run the full checks once more: backend tests, spec drift (`git diff --exit-code`), frontend lint/test/build.
8. **Prepare the pull request** with [references/pr-template.md](references/pr-template.md): summary, contract changes, screenshots, test evidence, migration and rollout notes. Commit in logical steps (contract + backend, client, UI) following the repo's commit convention. Do not push or open the PR unless asked.

### Slicing guidance

- Prefer one PR per feature when it stays reviewable (roughly under 600 changed lines excluding generated code).
- Otherwise split: PR 1 contract + backend (endpoint behind a flag or unused), PR 2 client + UI. The backend must be deployable before the UI that uses it.
- Breaking API changes: expand (add new field/endpoint) → migrate frontend → contract (remove old) in separate releases.
- Database: migrations are backward compatible with the running version (expand/contract); destructive steps come in a later release.

## Rules

- Do write acceptance criteria before code and map each one to at least one test.
- Do finish and commit the contract before writing UI code against it.
- Do follow the closest existing feature's structure; consistency beats novelty.
- Do enforce authorization on the backend; frontend guards are UX only.
- Do keep generated client changes in their own commit for clean review.
- Do run each layer's tests before moving to the next layer.
- Do handle loading, empty, error and permission-denied states in the UI.
- Do state assumptions and open questions in the plan and the PR.
- Do keep feature flags for partially shipped features if the project uses them.
- Don't start the UI with hand-written types or mocks that guess the API shape.
- Don't change unrelated code; note refactor ideas as follow-ups.
- Don't skip the spec diff review because "the client compiles".
- Don't mix a breaking contract change and its consumer migration in an unannounced single deploy.
- Don't leave TODOs for required behavior (validation, authz, error handling) without a ticket reference.
- Don't push, merge, or open the PR without the user's request.

## References

| File | Read when |
|---|---|
| [references/pr-template.md](references/pr-template.md) | Writing the pull request description and the pre-merge checklist |
