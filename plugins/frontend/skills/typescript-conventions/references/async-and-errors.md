# Async, errors, dates, and money

## Promises

- Every promise is awaited, returned, or explicitly discarded with `void` plus a `.catch` handler. Lint: `@typescript-eslint/no-floating-promises`, `no-misused-promises`.
- Run independent work in parallel: `await Promise.all([a(), b()])`. Use `Promise.allSettled` when partial failure is acceptable and you report each result.
- Don't `await` inside a loop unless order or rate limiting requires it; batch with `Promise.all` or a small concurrency limiter.
- Don't mix `.then()` chains and `async/await` in the same function.
- Don't make event handlers `async` without handling rejection: `onClick={() => void save().catch(report)}`.
- Return `Promise<void>` from async functions that produce nothing; never `Promise<any>`.

## Cancellation

```ts
export async function search(query: string, signal: AbortSignal): Promise<Hit[]> {
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return HitList.parse(await res.json());
}

// timeouts
const signal = AbortSignal.any([userSignal, AbortSignal.timeout(10_000)]);
```

- Accept `signal` as a parameter in every fetch helper; framework data layers (React Query, Angular `resource`/`httpResource`, Next.js) pass their own.
- Treat `AbortError` (`error.name === 'AbortError'` or `'TimeoutError'`) as a non-error: don't show it to users or log it as a failure.
- Clean up on unmount/destroy by aborting; never let a stale response overwrite newer state.

## Error model

```ts
export class AppError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = new.target.name;
  }
}
export class NotFoundError extends AppError {}
export class ValidationError extends AppError {
  constructor(readonly issues: readonly { path: string; message: string }[]) {
    super('Validation failed');
  }
}
```

- Throw only `Error` subclasses; chain causes with `new AppError('Saving failed', { cause: err })`.
- In `catch (err)`, `err` is `unknown`. Narrow with `instanceof` or a type guard before reading properties.
- Use `Error.isError(value)` where the runtime supports it (cross-realm safe); fall back to `instanceof Error`.
- Throw for bugs and truly exceptional cases. For expected outcomes (validation failed, not found, conflict), return a result union so callers must handle them.

```ts
export type Result<T, E = AppError> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
export const err = <E>(error: E): Result<never, E> => ({ ok: false, error });
```

- Keep result unions at module boundaries (API client, form submit, server action); inside, plain throws are fine.
- Don't adopt a full FP library (fp-ts, Effect) just for this; a 10-line `Result` is enough unless the team already uses one.
- Map errors to user messages in one place (an error-to-message function or i18n keys), not ad hoc in components.
- Log once, at the top-level handler (error boundary, Angular `ErrorHandler`, Next.js `error.tsx`/`onRequestError`), with the cause chain. Don't log and rethrow at every layer.

## Retries

- Retry only idempotent requests (GET, PUT with same body) and only on network errors, 408, 429, 502-504.
- Use exponential backoff with jitter and a cap (e.g., 3 attempts, 250 ms base). Honor `Retry-After`.
- Abort retries when the signal aborts.
- Prefer the data layer's retry (React Query `retry`, Angular `retry` operator) over hand-rolled loops.

## Dates and time

- Wire format: ISO 8601 strings in UTC (`2026-10-29T08:30:00Z`) for instants; `YYYY-MM-DD` for calendar dates without time (birthdays, due dates). Never send local-time strings without an offset.
- Keep wire values as strings in types (`createdAt: string`) and convert at the edge, or parse once into a dedicated type; don't pass `Date` objects through JSON boundaries.
- `Date` is mutable and timezone-confusing. Prefer `Temporal` (`Temporal.Instant`, `Temporal.PlainDate`, `Temporal.ZonedDateTime`) where the target browsers support it, or a polyfill/library already in the project (`date-fns`, `date-fns-tz`, `dayjs`). Don't add Moment.js.
- A calendar date (`PlainDate`) must never go through `new Date('2026-10-29')`: that parses as UTC midnight and shifts by a day in negative offsets.
- Format for display with `Intl.DateTimeFormat` (or the framework's i18n pipe) using the user's locale and an explicit `timeZone` when it matters.
- Inject the clock (`now = () => Temporal.Now.instant()` or `() => new Date()`) into logic you test; in tests use fake timers / `vi.setSystemTime`.

## Money

- Never use floating-point arithmetic for money (`0.1 + 0.2 !== 0.3`).
- Represent amounts as integer minor units plus currency: `{ amountMinor: 1999, currency: 'EUR' }`. Use `bigint` if values can exceed `Number.MAX_SAFE_INTEGER`.
- If the API sends decimal strings (`"19.99"`), keep them as strings and convert with a decimal library (`dinero.js`, `big.js`, `decimal.js`) or to minor units using the currency's exponent; don't `parseFloat`.
- Currency exponents differ (JPY 0, EUR 2, KWD 3); read them from `Intl.NumberFormat(locale, { style: 'currency', currency }).resolvedOptions().maximumFractionDigits` or a table.
- Allocate/split with remainders distributed explicitly (e.g., 100 split 3 ways = 34/33/33).
- Display with `Intl.NumberFormat(locale, { style: 'currency', currency })`; let the backend own rounding rules, tax, and FX.

```ts
export type Money = Readonly<{ amountMinor: number; currency: string }>;

export function formatMoney(m: Money, locale: string): string {
  const fmt = new Intl.NumberFormat(locale, { style: 'currency', currency: m.currency });
  const digits = fmt.resolvedOptions().maximumFractionDigits ?? 2;
  return fmt.format(m.amountMinor / 10 ** digits);
}
```

## Concurrency and races

- Debounce user-driven queries and cancel the previous request (abort or `switchMap` in RxJS).
- Guard double submits: disable while pending or make the handler idempotent.
- Don't rely on response order; key state by request ID or use the data layer's dedupe.
