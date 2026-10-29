# Vitest + Testing Library for React and Next.js

## Packages

```sh
npm i -D vitest @vitejs/plugin-react jsdom \
  @testing-library/react @testing-library/dom @testing-library/user-event @testing-library/jest-dom \
  @vitest/coverage-v8 msw
# optional real-browser component tests
npm i -D @vitest/browser-playwright vitest-browser-react playwright
```

- Vitest 5 requires Node >= 22.12 and Vite >= 6.4, with `vite` as a peer dependency (install it explicitly with Yarn/pnpm strict).
- `@testing-library/react` 16 needs `@testing-library/dom` installed separately.
- Next.js: the official guide (`node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md`) uses the same packages plus `vite-tsconfig-paths`. With Vite 8 you can use `resolve.tsconfigPaths: true` instead.

## Config

```ts
// vitest.config.mts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },          // Vite 8; else vite-tsconfig-paths plugin
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,                      // also restores vi.spyOn originals
    unstubEnvs: true,
    unstubGlobals: true,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/**/*.d.ts', 'src/test/**', 'src/**/generated/**'],
      thresholds: { lines: 80, functions: 80, branches: 75, statements: 80 },
      reporter: ['text-summary', 'html', 'lcov'],
    },
  },
});
```

- Vitest 4 removed `coverage.all`; set `coverage.include` explicitly so untested files count. In Vitest 5, `include`/`exclude` match relative to root and a pattern without wildcards matches a whole directory; re-check the file set after upgrading.
- Vitest 4 replaced `workspace` with `test.projects`. In Vitest 5 inline projects inherit the root config by default (`extends: true`).
- Prefer explicit imports (`import { describe, it, expect, vi } from 'vitest'`) over `globals: true`; if you use globals, add `"types": ["vitest/globals"]` to the test tsconfig.

## Setup file

```ts
// src/test/setup.ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './msw/server';

beforeAll(() => server.listen({ onUnhandledFrame: 'error' })); // MSW 2: onUnhandledRequest
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
```

`cleanup` runs automatically only with `globals: true`; call it explicitly otherwise.

## Unit and component projects

Split pure-logic tests (fast, node) from DOM tests:

```ts
test: {
  projects: [
    { test: { name: 'unit', environment: 'node', include: ['src/**/*.unit.test.ts'] } },
    { test: { name: 'dom', environment: 'jsdom', include: ['src/**/*.test.tsx'],
              setupFiles: ['./src/test/setup.ts'] } },
  ],
}
```

Run one with `vitest --project dom`.

## Writing component tests

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '@/test/msw/server';
import { renderWithProviders } from '@/test/render';
import { InvoiceForm } from './invoice-form';

describe('InvoiceForm', () => {
  it('shows a server error when saving fails', async () => {
    server.use(http.post('/api/invoices', () => HttpResponse.json({ message: 'Declined' }, { status: 402 })));
    const user = userEvent.setup();
    renderWithProviders(<InvoiceForm />);

    await user.type(screen.getByLabelText('Amount'), '19.99');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Declined');
  });
});
```

- `renderWithProviders` wraps the UI with the app's real providers (query client with `retry: false`, router, i18n, theme). Create a fresh query client per test.
- Query priority: `getByRole` > `getByLabelText` > `getByPlaceholderText` > `getByText` > `getByTestId`.
- `getBy*` for presence, `queryBy*` only to assert absence, `findBy*` for async appearance.
- `waitFor` only for non-DOM conditions; never put side effects inside it.
- Hooks: test through a component that uses them; use `renderHook` only for reusable hooks with no UI.
- React 19 `use()` / Suspense: render inside `<Suspense>` and `await screen.findBy*` for the resolved content.
- Forms with Actions (`useActionState`, `<form action>`): submit via user-event and await the resulting UI.

## Next.js specifics

- Vitest does not support async Server Components; test them (and routes, middleware/proxy, caching) with Playwright.
- Sync Server Components and Client Components render fine in jsdom.
- Mock `next/navigation` only at the edge: `vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => '/x', useSearchParams: () => new URLSearchParams() }))`. Keep this in a shared helper.
- Server Actions and Route Handlers: extract logic into plain functions and unit-test those; test the HTTP surface of route handlers by calling the exported `GET`/`POST` with a `Request`.
- `server-only` imports throw outside a server bundle; alias it in Vitest: `resolve: { alias: { 'server-only': new URL('./src/test/empty.ts', import.meta.url).pathname } }`.

## Mocks, timers, env

- `vi.mock` / `vi.hoisted` must be top-level (Vitest 5 throws otherwise). Use `vi.doMock` for conditional mocks.
- Vitest 5 `clearMocks` defaults to true: call history resets before each test; don't rely on counts from earlier tests.
- Fake timers: `vi.useFakeTimers()` then `await vi.advanceTimersByTimeAsync(ms)`; with user-event pass `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`. Restore with `vi.useRealTimers()` in `afterEach`.
- Vitest 5 fake timers and `vi.setSystemTime` also fake `Temporal`; opt out with `toNotFake: ['Temporal']`.
- Env: `vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://test')` with `unstubEnvs: true`.

## Browser mode (real browser components)

Use when jsdom lacks the API (layout, IntersectionObserver, canvas, CSS) or you want higher fidelity.

```ts
import { playwright } from '@vitest/browser-playwright';

export default defineConfig({
  plugins: [react()],
  test: {
    browser: {
      enabled: true,
      provider: playwright(),
      headless: true,
      instances: [{ browser: 'chromium' }],
    },
  },
});
```

```tsx
import { render } from 'vitest-browser-react';
import { expect, test } from 'vitest';
import { page } from 'vitest/browser';

test('opens the menu', async () => {
  const screen = await render(<Menu />);              // render is async
  await screen.getByRole('button', { name: 'Open' }).click();
  await expect.element(page.getByRole('menu')).toBeVisible();
});
```

- Vitest 5: locators match text exactly by default (`browser.locators.exact`); `toHaveTextContent` requires equality, use `toMatchTextContent` for partial/regex.
- MSW in browser mode uses `setupWorker` from `msw/browser` (see `msw-mocking.md`).

## Upgrading Vitest 4 to 5 (checklist)

1. Node >= 22.12, Vite >= 6.4, install `vite`.
2. Fix tests that relied on call history across tests (`clearMocks` now true) and unawaited async assertions.
3. Replace `test.sequential`/`describe.sequential` with `{ concurrent: false }`.
4. Move non-top-level `vi.mock`/`vi.hoisted` to the top level.
5. Update CI artifact paths: reporters write under `.vitest/` (JUnit `.vitest/junit/output.xml`, HTML `.vitest/index.html`, blob `.vitest/blob/`); `json`/`junit` write files by default.
6. Re-check coverage include/exclude globs and per-glob `perFile` thresholds.
7. `-t` patterns now join suite and test names with ` > `.
8. Custom matcher types augment `vitest.Matchers`, not `jest.Matchers`.

## CI

```sh
vitest run --coverage --reporter=default --reporter=junit
```

- Fail on threshold misses (the default). Upload `coverage/lcov.info` and the JUnit file.
- Shard large suites: `vitest run --shard=1/4 --reporter=blob`, then `vitest --merge-reports`.
