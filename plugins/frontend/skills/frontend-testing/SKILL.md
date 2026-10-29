---
name: frontend-testing
description: "Testing strategy and setup for TypeScript frontends: Vitest with Testing Library for React and Next.js, the Angular Vitest builder (@angular/build:unit-test) with TestBed and component harnesses, MSW for API mocking, Playwright for end-to-end, coverage thresholds and CI wiring. Use when writing or fixing frontend unit, component or E2E tests, configuring Vitest, Playwright or MSW, or deciding what to test at which level. Not for Spring Boot tests (see spring-boot-testing)."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# Frontend Testing

Targets: Vitest 5 (4.x still common), Testing Library (React 16, user-event 14, jest-dom 7), Angular 22 with `@angular/build:unit-test` (Vitest is the default runner for new projects since Angular 21), MSW 3 (2.x still common), Playwright 1.5x/1.6x, React 19, Next.js 16.
First detect the project's real versions from package.json and adapt; never downgrade a project.

## Use when / do not use

- Use when adding, fixing, or reviewing unit, component, integration, or E2E tests in a TypeScript frontend, or configuring Vitest, Playwright, MSW, coverage, or CI test jobs.
- Use when deciding which level a behavior should be tested at.
- Do not use for framework API details (signals, hooks, Server Components): see `angular-developer`, `vercel-react-best-practices`, and the Next.js skills / generated `AGENTS.md`. For TS style see `typescript-conventions`.
- Not for backend tests: Spring Boot goes to `spring-boot-testing`.

## Workflow

Test levels:

| Level | Tool | What belongs here |
| --- | --- | --- |
| Unit | Vitest (node env) | pure functions, schemas, reducers, services without DOM |
| Component / integration | Vitest + Testing Library (jsdom or browser mode), Angular TestBed + harnesses, MSW for HTTP | rendering, user interaction, a feature slice with its data layer |
| End-to-end | Playwright against a built app | critical user journeys, routing, auth, async Server Components, real browser APIs |

Most tests are component/integration tests. Keep E2E to a few journeys per feature; they are slower and flakier.

1. Detect the stack: framework, `vitest`/`@angular/build`/`karma`/`jest`, `msw`, `@playwright/test` versions, and existing config files (`vitest.config.*`, `angular.json` test target, `playwright.config.ts`). Follow the existing runner unless asked to migrate.
2. Choose the level from the table above; test behavior a user or caller can observe, not implementation details.
3. Set up or fix the runner: React/Next per `references/vitest-react.md`, Angular per `references/angular-testing.md`.
4. Mock the network, not your modules: shared MSW handlers per `references/msw-mocking.md`, with unhandled requests failing the test.
5. Write the test: arrange with factories, act through user-event or harnesses, assert on accessible output (roles, labels, text).
6. Add or update E2E for the journey if it crosses pages, auth, or server rendering (`references/playwright-e2e.md`).
7. Run locally in single-run mode, then wire CI: unit and E2E jobs, coverage thresholds, JUnit/HTML reports, Playwright traces as artifacts.
8. If a test is flaky, find the race (missing `await`, timer, unmocked request) instead of adding retries or sleeps.

## Rules

- Do query by role, label, or text (`getByRole('button', { name: 'Save' })`); use `data-testid` only when nothing accessible exists.
- Do use `@testing-library/user-event` (`const user = userEvent.setup()`) over `fireEvent`.
- Do `await` every async assertion and `findBy*`; Vitest 5 fails unawaited `resolves`/`rejects`.
- Don't use fixed sleeps; wait for UI state (`findBy*`, `expect.poll`, Playwright web-first assertions).
- Do mock HTTP with MSW; don't mock `fetch`, `HttpClient`, or your own API client module in component tests.
- Do set `onUnhandledFrame: 'error'` (MSW 3) or `onUnhandledRequest: 'error'` (MSW 2).
- Do reset MSW handlers, timers, and mocks after each test; remember Vitest 5 defaults `clearMocks: true`.
- Do build test data with typed factories (`makeUser({ role: 'admin' })`), not shared mutable fixtures.
- Don't snapshot whole component trees; snapshot small serialized values or use visual/ARIA snapshots in Playwright.
- Do use Angular component harnesses (`@angular/cdk/testing`) for Material/CDK and your own complex components.
- Don't use `fakeAsync`/`tick` with the Angular Vitest runner (zoneless); use `vi.useFakeTimers()` and `await fixture.whenStable()`.
- Do test async React Server Components and full Next.js routes with Playwright, not Vitest.
- Do keep E2E tests independent: each creates its own data or uses an isolated account; no ordering dependencies.
- Do reuse auth via a Playwright setup project and `storageState`, not a UI login in every test.
- Do enforce coverage thresholds in CI on meaningful code; exclude generated code, types, and config files.
- Don't chase 100% coverage; cover branches with business logic and error states.
- Do record Playwright traces `on-first-retry` and upload reports on failure.
- Don't retry unit tests in CI; allow at most 1-2 retries for E2E and treat retries as flakiness to fix.
- Do name tests as behavior: `it('shows an error when the card is declined')`.

## References

| File | Read when |
| --- | --- |
| [references/vitest-react.md](references/vitest-react.md) | configuring Vitest for React or Next.js, writing Testing Library tests, browser mode, coverage, Vitest 4 to 5 upgrade |
| [references/angular-testing.md](references/angular-testing.md) | configuring `@angular/build:unit-test`, TestBed, signal inputs, HTTP testing, harnesses, migrating from Karma/Jasmine |
| [references/msw-mocking.md](references/msw-mocking.md) | mocking HTTP/GraphQL/WebSocket with MSW in tests, Storybook, or dev; MSW 2 to 3 changes |
| [references/playwright-e2e.md](references/playwright-e2e.md) | writing or configuring Playwright E2E tests, auth setup, network mocking, visual checks, CI sharding |
