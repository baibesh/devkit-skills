# MSW: API mocking for tests, Storybook, and dev

MSW intercepts requests at the network layer, so components, `fetch`, axios, and Angular `HttpClient` run unchanged. One set of handlers serves unit/component tests (Node), browser-mode tests, Storybook, and local dev.

## Versions

- MSW 3 (Sept 2026) is ESM-only, needs Node >= 22 and TypeScript >= 5.9.
- MSW 2 is still common. Most handler code is identical; the differences are listed at the end.
- Generate the browser worker once: `npx msw init public --save` (Angular: `public/` or the configured assets dir). Commit `mockServiceWorker.js` and regenerate after upgrades.

## Layout

```text
src/test/msw/
  handlers.ts         # happy-path defaults for every endpoint the app calls
  factories.ts        # typed data builders
  server.ts           # Node: setupServer(...handlers)
  browser.ts          # Browser: setupWorker(...handlers)
```

## Handlers

```ts
// handlers.ts
import { http, HttpResponse, delay } from 'msw';
import { makeInvoice } from './factories';

export const handlers = [
  http.get('/api/invoices', ({ request }) => {
    const status = new URL(request.url).searchParams.get('status') ?? 'open';
    return HttpResponse.json([makeInvoice({ status }), makeInvoice({ status })]);
  }),

  http.post('/api/invoices', async ({ request }) => {
    const body = (await request.json()) as { amountMinor: number };
    return HttpResponse.json(makeInvoice({ amountMinor: body.amountMinor }), { status: 201 });
  }),

  http.get('/api/invoices/:id', ({ params }) =>
    params.id === 'missing'
      ? HttpResponse.json({ message: 'Not found' }, { status: 404 })
      : HttpResponse.json(makeInvoice({ id: String(params.id) })),
  ),
];
```

- Defaults cover the happy path; tests override per case with `server.use(...)`, which is reset in `afterEach`.
- Type handlers with generics when helpful: `http.get<{ id: string }, never, Invoice>('/api/invoices/:id', ...)`.
- Validate request bodies in handlers with the app's own schemas (zod/valibot) to catch contract drift.
- Use absolute URLs or path-only patterns consistently with how the app builds URLs. In Node, relative URLs need a base, so configure the app's API base URL in tests (`http://localhost/api`) or match with `*/api/invoices`.
- Network errors: `HttpResponse.error()`. Latency: `await delay(200)` (avoid `delay('infinite')` except for loading-state tests).
- One-off response: `http.get(url, resolver, { once: true })`.
- GraphQL: `graphql.query('GetUser', ...)` (MSW 3 imports from `msw/graphql`; `graphql` is an optional peer). WebSockets: `ws.link('wss://...')`. SSE: `sse(...)`.

## Factories

```ts
let seq = 0;
export function makeInvoice(overrides: Partial<Invoice> = {}): Invoice {
  seq += 1;
  return { id: `inv_${seq}`, number: `INV-${seq}`, status: 'open', amountMinor: 1000, currency: 'EUR', ...overrides };
}
```

- Return fresh objects; never share mutable fixtures across tests.
- Derive the `Invoice` type from the app's schema so factories break when the contract changes.
- For stateful flows (create then list), keep a tiny in-memory store in the handler module and reset it in `afterEach`; consider `@mswjs/data` for larger models.

## Node (Vitest jsdom, Angular unit-test builder)

```ts
// server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';
export const server = setupServer(...handlers);
```

```ts
// test setup file
beforeAll(() => server.listen({ onUnhandledFrame: 'error' })); // MSW 2: onUnhandledRequest
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Per test:

```ts
server.use(http.get('/api/invoices', () => HttpResponse.json([], { status: 200 })));
```

- Unhandled requests must fail the test; silent passthrough hides missing mocks.
- To assert what was sent, capture inside a handler (`let sent: unknown; ... sent = await request.json()`) and assert after the action; avoid spying on `fetch`.
- Listen to `server.events.on('request:start', ...)` only for debugging.

## Fake timers

- MSW 3 no longer patches `setTimeout` to escape fake timers. With `vi.useFakeTimers()`, advance timers (`await vi.advanceTimersByTimeAsync(ms)`) so `delay()` resolves.
- Prefer `vi.useFakeTimers({ toFake: ['setTimeout', 'setInterval', 'Date'] })` scoped to the test that needs it.

## Browser (Vitest browser mode, Storybook, dev)

```ts
// browser.ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';
export const worker = setupWorker(...handlers);
```

- Vitest browser mode: start in a setup file with `await worker.start({ quiet: true, onUnhandledFrame: 'error' })`; `worker.resetHandlers()` after each test; `await worker.stop()` (returns a Promise in MSW 3).
- Dev in a Vite app (MSW 3): `msw/vite` plugin serves the worker and exposes `virtual:msw`; guard with `import.meta.env.DEV`. Without the plugin, start the worker before rendering:

```ts
async function enableMocking() {
  if (!import.meta.env.DEV || import.meta.env.VITE_MOCKS !== 'true') return;
  const { worker } = await import('./test/msw/browser');
  await worker.start({ onUnhandledFrame: 'bypass' });
}
void enableMocking().then(() => mount());
```

- Next.js: mock client fetches with the browser worker; server-side fetches (Server Components, route handlers) need `msw/node` started in `instrumentation.ts` under a dev/test flag, or a separate mock backend. Never ship mocks to production.
- Storybook: `msw-storybook-addon` with `parameters.msw.handlers` per story, reusing the same handler modules.

## Playwright

- E2E normally hits a real or seeded backend. For UI-only E2E, prefer Playwright's `page.route()` (see `playwright-e2e.md`).
- To reuse MSW handlers in Playwright, `@msw/playwright` (pre-1.0, verify its API before adopting) bridges handlers onto `page.route`.

## MSW 2 to 3 changes that affect tests

| MSW 2 | MSW 3 |
| --- | --- |
| `onUnhandledRequest` option | `onUnhandledFrame` (`'bypass' \| 'warn' \| 'error'` or callback) |
| CJS + ESM | ESM-only |
| `import { graphql } from 'msw'` | `import { graphql } from 'msw/graphql'` |
| `worker.stop()` sync | returns a Promise |
| patches `setTimeout` under fake timers | does not; advance timers |
| Node cookie jar emulated; `request.headers.get('cookie')` mocked | not emulated; header returns `null`, use the `cookies` resolver argument |
| WebSocket `connection` event | `websocket:connection` |
| `handleRequest()` | removed; use `defineNetwork()` |
| `msw/native` | `@msw/react-native` |
| — | `msw/utils` entry (`delay`, `passthrough`), `msw/vite` plugin, GraphQL subscriptions |

Upgrade steps: bump Node to 22+, rename the option, update GraphQL imports, regenerate `mockServiceWorker.js`, run the suite with `onUnhandledFrame: 'error'`.
