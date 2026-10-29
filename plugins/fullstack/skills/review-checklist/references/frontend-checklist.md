# Frontend review checklist (Angular, React, Next.js)

Severity hints in brackets: [B] blocker, [M] major, [m] minor. Framework idioms follow `angular-developer` and `vercel-react-best-practices`; TypeScript style follows `typescript-conventions`.

## TypeScript

- [ ] [M] No new `any`, non-null assertions (`!`) or `as` casts that hide real nullability; `unknown` + narrowing at boundaries.
- [ ] [M] API types come from the generated client, not redeclared by hand; no edits inside generated folders.
- [ ] [M] Exhaustive handling of unions/enums from the API includes a fallback for unknown values.
- [ ] [M] Promises are awaited or explicitly handled; no floating promises in event handlers.
- [ ] [m] Dates parsed once at the edge; no string comparison of date-times; display in user time zone.

## Angular (signals era)

- [ ] [M] `effect()` used to derive state; should be `computed()` or `linkedSignal()`. Effects are for side effects (DOM, logging, storage sync).
- [ ] [M] Signal writes inside `computed()`; or effects writing signals they read, causing loops.
- [ ] [M] Async data loaded with `resource`/`httpResource`/`rxResource` or RxJS with proper cancellation; no manual `subscribe` without teardown (`takeUntilDestroyed`, `async` pipe, `toSignal`).
- [ ] [M] Nested subscribes or `subscribe` inside `subscribe`; use `switchMap`/`concatMap` chosen deliberately (cancellation vs. ordering).
- [ ] [M] Reading signals in templates without calling them (`count` vs `count()`), or calling functions/getters with heavy work in templates.
- [ ] [M] `@for` has a stable `track` expression (ID, not `$index` for mutable lists).
- [ ] [m] Standalone components, `inject()`, `input()`/`output()`/`model()` used per the project's Angular version; no new NgModules in a standalone app.
- [ ] [m] `OnPush` or zoneless-compatible change detection in new components.
- [ ] [B] `bypassSecurityTrust*` or `[innerHTML]` with unsanitized data.
- [ ] [M] Lazy-loaded routes for new feature areas; guards (`CanActivateFn`) mirror backend authorization but are not relied on for security.

## React and Next.js

- [ ] [M] `useEffect` used to derive state or sync props to state; compute during render or use `useMemo` only when costly.
- [ ] [M] Stale closures: effects/callbacks reading state or props missing from the dependency array; intervals/listeners capturing old values. Fix deps, use functional `setState`, or `useEffectEvent` where available.
- [ ] [M] Effects without cleanup (subscriptions, timers, `AbortController` for fetches); race conditions on fast param changes.
- [ ] [M] Keys: stable IDs, not array index for reorderable lists; no random keys.
- [ ] [M] State mutated in place (`push`, property assignment) instead of new objects.
- [ ] [M] Data fetching: no client-side waterfalls; parallelize with `Promise.all` or fetch in Server Components; Suspense boundaries placed deliberately.
- [ ] [M] Next.js: `"use client"` pushed to leaf components; no server-only code (secrets, DB, server env) imported into client components; `server-only` package used for modules that must stay on the server.
- [ ] [B] Server Actions and Route Handlers authenticate and authorize every call; they are public HTTP endpoints.
- [ ] [M] Caching and revalidation intent explicit for fetches and routes (per project's Next.js version); user-specific data never cached as shared.
- [ ] [M] Hydration mismatches: `Date.now()`, `Math.random()`, `window` access during render.
- [ ] [B] `dangerouslySetInnerHTML` with unsanitized input.
- [ ] [m] React 19 APIs (`use`, actions, `useActionState`, `useOptimistic`) used consistently with project patterns.

## State and data flow

- [ ] [M] Single source of truth: server state in the query/resource layer, not duplicated in a global store.
- [ ] [M] Loading, empty and error states all rendered; errors from Problem Details mapped to fields or messages.
- [ ] [M] Optimistic updates roll back on failure.
- [ ] [M] Forms: validation mirrors backend constraints; submit disabled or idempotent against double submission.
- [ ] [m] No derived values stored in state.

## Accessibility

- [ ] [M] Interactive elements are native (`button`, `a`, `input`) or have role, tabindex and keyboard handlers.
- [ ] [M] Every form control has an associated label; errors linked with `aria-describedby`.
- [ ] [M] Images have meaningful `alt` or `alt=""` when decorative; icon-only buttons have `aria-label`.
- [ ] [M] Focus managed on route change, dialog open/close, and after async errors; no focus traps outside modals.
- [ ] [m] Color is not the only signal; contrast meets WCAG AA; visible focus styles not removed.
- [ ] [m] Live regions for async status messages (toasts, validation summaries).

## Performance and bundle size

- [ ] [M] New heavy dependency (date, charting, editor, icon sets): justify, check tree-shakeable import paths, lazy-load if not on the critical path.
- [ ] [M] Barrel imports pulling whole libraries into the client bundle.
- [ ] [M] Large lists virtualized; expensive work not repeated on every render/change detection.
- [ ] [m] Images optimized (`next/image`, `NgOptimizedImage`) with dimensions to avoid layout shift.
- [ ] [m] Angular budget or Next.js bundle analyzer output checked when dependencies change.

## Security (frontend specifics)

- [ ] [B] No secrets or private API keys in client code or `NEXT_PUBLIC_*` variables.
- [ ] [M] Tokens not stored in `localStorage` when the project uses httpOnly cookies; no tokens in URLs.
- [ ] [M] External links with `target="_blank"` and user-controlled URLs validated (`javascript:` scheme).
- [ ] [M] Authorization decisions only for UX; server enforces them.

## Tests (see `frontend-testing`)

- [ ] [M] New components/hooks/services have tests asserting user-visible behavior (Testing Library queries by role/label).
- [ ] [M] HTTP mocked at the network layer (MSW, `HttpTestingController`), not by mocking the generated client internals.
- [ ] [M] Error and empty states tested, not only the happy path.
- [ ] [m] No snapshot-only tests for logic; no arbitrary timeouts; fake timers restored.
- [ ] [m] E2E covers the critical path of the feature when the project has E2E.
