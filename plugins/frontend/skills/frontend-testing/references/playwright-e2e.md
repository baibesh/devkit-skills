# Playwright end-to-end tests

E2E covers what lower levels cannot: real routing, SSR/RSC output, auth cookies, redirects, multi-page journeys, and browser APIs. Keep the suite small, stable, and fast enough to run on every PR.

## Setup

```sh
npm init playwright@latest        # or: npm i -D @playwright/test && npx playwright install --with-deps chromium
```

```ts
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const PORT = 3000;
const baseURL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? '50%' : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }], ['junit', { outputFile: 'e2e-results/junit.xml' }]] : 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' }, dependencies: ['setup'] },
    // add firefox/webkit/mobile projects only for journeys that need them
  ],
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'npm run build && npm run start',   // test the production build
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
```

- Next.js: `next build && next start`. Angular: `ng build` then serve `dist/<app>/browser` (static) or the SSR server (`node dist/<app>/server/server.mjs`). Vite: `vite build && vite preview`.
- Dev servers are acceptable locally for speed but CI should test a production build.
- Add `e2e/.auth/` and `playwright-report/`, `test-results/` to `.gitignore`.
- Keep Playwright in its own `tsconfig` include or folder so Vitest does not pick up `e2e/**`.

## Auth via setup project

```ts
// e2e/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

setup('sign in', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.E2E_USER!);
  await page.getByLabel('Password').fill(process.env.E2E_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
```

- Faster: authenticate via API (`request.post('/api/login')`) and save `storageState`.
- Multiple roles: one setup test and storage file per role; select with `test.use({ storageState: ... })`.
- Tests that need a signed-out state: `test.use({ storageState: { cookies: [], origins: [] } })`.

## Writing tests

```ts
import { test, expect } from './fixtures';

test('user pays an open invoice', async ({ page, invoice }) => {
  await page.goto(`/invoices/${invoice.id}`);
  await page.getByRole('button', { name: 'Pay now' }).click();
  await page.getByLabel('Card number').fill('4242 4242 4242 4242');
  await page.getByRole('button', { name: 'Confirm payment' }).click();

  await expect(page.getByRole('status')).toHaveText('Paid');
  await expect(page).toHaveURL(/\/invoices\/.+\/receipt$/);
});
```

- Locators: `getByRole` > `getByLabel` > `getByText` > `getByTestId`. Avoid CSS/XPath tied to markup.
- Web-first assertions (`await expect(locator).toBeVisible()`, `toHaveText`, `toHaveURL`) auto-wait; never use `page.waitForTimeout`.
- `expect.poll(() => fn())` for non-DOM conditions (API state, downloads).
- Each test is independent: create its data through fixtures or API calls, clean up after if the environment is shared.
- Use `test.step()` to label phases of long journeys in reports.

## Fixtures for data

```ts
// e2e/fixtures.ts
import { test as base, expect } from '@playwright/test';

type Fixtures = { invoice: { id: string } };

export const test = base.extend<Fixtures>({
  invoice: async ({ request }, use) => {
    const res = await request.post('/api/test/invoices', { data: { amountMinor: 1999, currency: 'EUR' } });
    expect(res.ok()).toBeTruthy();
    const invoice = (await res.json()) as { id: string };
    await use(invoice);
    await request.delete(`/api/test/invoices/${invoice.id}`);
  },
});
export { expect };
```

- Seed via API or a DB script, not via UI clicks.
- Use unique identifiers per test (`test.info().testId`, worker index) so parallel workers do not collide.

## Network control

```ts
await page.route('**/api/recommendations', (route) =>
  route.fulfill({ json: [{ id: 'r1', title: 'Mocked' }] }));

await page.route('**/analytics/**', (route) => route.abort());
```

- Mock only third parties and nondeterministic services (payments sandbox down, analytics, ads); keep your own backend real for true E2E.
- `page.routeFromHAR()` replays recorded traffic for UI-only suites.
- Server-side fetches (Next.js Server Components, Angular SSR) are not visible to `page.route`; mock those in the backend/test environment or with `msw/node` in the server process.

## Visual and accessibility checks

- `await expect(page).toHaveScreenshot()` for a handful of stable pages; mask dynamic regions (`mask: [locator]`), fix viewport and fonts, and run in one OS image (the official Playwright Docker image) to avoid diffs.
- `await expect(locator).toMatchAriaSnapshot(...)` checks accessible structure without pixels; less brittle than screenshots.
- Accessibility scan: `@axe-core/playwright` (`new AxeBuilder({ page }).analyze()`) on key pages; fail on serious/critical violations.

## Flakiness

- Read the trace (`npx playwright show-trace`), don't add sleeps or blanket retries.
- Common causes: asserting before navigation finishes (assert on URL or heading first), shared test data, animations (`reducedMotion: 'reduce'` in `use`), time-dependent UI (`page.clock.install({ time })`), unmocked third parties.
- Quarantine with `test.fixme()` plus an issue link, never by deleting.
- `--repeat-each=10 --workers=1` locally to reproduce.

## CI

```yaml
# GitHub Actions sketch
e2e:
  runs-on: ubuntu-latest
  strategy: { matrix: { shard: [1, 2, 3, 4] } }
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: 22, cache: npm }
    - run: npm ci
    - run: npx playwright install --with-deps chromium
    - run: npx playwright test --shard=${{ matrix.shard }}/4 --reporter=blob
    - uses: actions/upload-artifact@v4
      if: ${{ !cancelled() }}
      with: { name: blob-${{ matrix.shard }}, path: blob-report }
```

- Merge shards in a follow-up job with `npx playwright merge-reports --reporter html ./all-blob-reports` and upload `playwright-report/`.
- Cache browsers by Playwright version, or use the `mcr.microsoft.com/playwright` image pinned to the same version as `@playwright/test`.
- Run a small smoke subset (`--grep @smoke`) on every PR and the full suite on main/nightly if the suite is large.
- Pass secrets (test users) via CI secrets; never commit `storageState` files.

## Tooling notes

- `npx playwright codegen <url>` to draft locators; rewrite the output into readable steps.
- UI mode (`npx playwright test --ui`) for local debugging; `--debug` for step-through.
- Recent Playwright versions ship AI test agents (`npx playwright init-agents`); verify availability with `npx playwright --help` before relying on them, and review generated tests like any other code.
