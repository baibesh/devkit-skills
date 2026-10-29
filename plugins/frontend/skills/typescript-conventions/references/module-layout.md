# Module layout, naming, and import hygiene

## Feature-first folders

Group by feature (domain), not by technical kind. Shared code lives in a small number of clearly named places.

```text
src/
  app/                    # framework entry: routes, layouts, bootstrap
  features/
    billing/
      api/                # API client functions + schemas
      components/         # or ui/ ; framework components
      model/              # types, pure logic, state
      billing.test.ts
      index.ts            # the ONLY public entry of the feature
    users/
      ...
  shared/
    ui/                   # design-system primitives, no feature knowledge
    lib/                  # pure utilities (dates, money, assertNever)
    api/                  # http client, ApiError, interceptors
  env.ts
```

- Framework-mandated folders win: Next.js `app/` routing files, Angular CLI conventions. Put features beside them, not inside route folders, unless the code is used by one route only (then colocate).
- Dependency direction: `app` -> `features` -> `shared`. `shared` never imports from `features`; a feature never imports another feature's internals.
- When two features need the same thing, move it to `shared` or create a third feature; don't cross-import.

## Public entry points and barrels

- Each feature (or package in a monorepo) may have one `index.ts` that re-exports its public API explicitly: `export { BillingSummary } from './components/billing-summary';`.
- No `export *` in that file; explicit names keep tree-shaking and refactors predictable.
- No nested barrels (`components/index.ts`, `model/index.ts`). Inside a feature, import files directly by relative path.
- Why: barrels force bundlers and test runners to load whole subtrees (slower Vitest/Jest startup, larger dev bundles) and are the most common source of import cycles.
- Next.js: `"use client"` boundaries and barrels mix badly; a barrel that re-exports a client component drags it into server graphs. Import client components directly.
- For third-party barrel-heavy packages in Next.js, `optimizePackageImports` exists; see the Next.js docs rather than adding your own barrels.

## Path aliases

- One alias, `@/*` -> `src/*`, is enough. Avoid an alias per folder.
- Use relative imports inside a feature, the alias across features and to `shared`.
- Configure in tsconfig `paths` (no `baseUrl`); make sure the test runner and bundler resolve it (Vite 8 `resolve.tsconfigPaths: true`, or `vite-tsconfig-paths`).

## Detecting and fixing cycles

- Detect: `npx madge --circular --extensions ts,tsx src` or `dpdm --circular src/main.ts`. Run it in CI for larger apps.
- ESLint options: `import-x/no-cycle` (eslint-plugin-import-x) works but is slow on big repos; prefer madge in CI.
- Enforce boundaries with `eslint-plugin-boundaries` or `no-restricted-imports` patterns, e.g. forbid `@/features/*/!(index)` from outside the feature.
- Fix by: extracting shared types to a leaf module, inverting the dependency (pass a callback or token), or merging two modules that are really one.
- Type-only cycles are harmless at runtime with `import type`, but still a design smell.

## Naming

| Thing | Convention | Example |
| --- | --- | --- |
| Files | kebab-case, role suffix where the framework expects it | `invoice-list.tsx`, `invoice.service.ts` (Angular) |
| Types, interfaces, classes, components | PascalCase, no `I` prefix | `Invoice`, `InvoiceList` |
| Functions, variables | camelCase, verbs for functions | `formatMoney`, `loadInvoices` |
| Booleans | `is/has/can/should` prefix | `isOverdue` |
| Constants (module-level, immutable, primitive) | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| `as const` lookup objects | PascalCase or camelCase, consistent per repo | `InvoiceStatus` |
| Generic type params | `T`, or descriptive `TItem` when several | `Result<TValue, TError>` |
| Tests | same name + `.test.ts` or `.spec.ts` (Angular) | `money.test.ts` |

- Abbreviations as words: `userId`, `HttpClient`, `parseUrl` (not `userID`, `HTTPClient`).
- Name units in identifiers when not obvious: `timeoutMs`, `amountMinor`, `sizeBytes`.

## Literal unions instead of enums

```ts
export const InvoiceStatus = ['draft', 'sent', 'paid', 'void'] as const;
export type InvoiceStatus = (typeof InvoiceStatus)[number];

export const ROLE = { Admin: 'admin', Member: 'member' } as const;
export type Role = (typeof ROLE)[keyof typeof ROLE];
```

- Iterable arrays give you runtime lists for selects and schema enums (`z.enum(InvoiceStatus)`).
- `enum` and `namespace` are not erasable syntax; they break `erasableSyntaxOnly` and Node's type stripping.

## Exhaustiveness helper

```ts
// shared/lib/assert-never.ts
export function assertNever(value: never, message = 'Unexpected value'): never {
  throw new Error(`${message}: ${JSON.stringify(value)}`);
}
```

## Exports

- Named exports by default: better rename refactors, grep-ability, and auto-imports.
- Default exports only where required: Next.js `page.tsx`/`layout.tsx`/`route` conventions, `React.lazy`, Angular `loadComponent` with default (optional).
- One main concept per file; small helpers private to the file stay unexported.

## Shared utilities checklist

- Pure, synchronous where possible, no framework imports in `shared/lib`.
- Inputs and outputs typed precisely; no `options: any`.
- Unit-tested (see `frontend-testing`).
- No hidden global state; inject clocks (`now: () => Date`) and random sources when tests need control.
