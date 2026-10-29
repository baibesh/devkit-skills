---
name: typescript-conventions
description: "Framework-agnostic TypeScript conventions for frontend code (Angular, React, Next.js): strict tsconfig, ESLint flat config with Prettier, naming and module layout, no barrel-file cycles, runtime validation at I/O boundaries with zod or valibot, typed environment access, date and money handling, async and error patterns. Use when setting up or reviewing a TypeScript project, writing shared utilities, or when the question is about TypeScript style rather than a specific framework. Framework-specific guidance lives in the angular, react and nextjs plugins."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# TypeScript Conventions

Targets: TypeScript 6.0 (the toolchain line most frameworks and typescript-eslint pin today) with TypeScript 7 (native `tsc`) as an optional fast type-checker, ESLint 10 flat config, typescript-eslint 8, Prettier 3, zod 4 or valibot 1.
First detect the project's real versions from package.json and adapt; never downgrade a project.

## Use when / do not use

- Use when creating or reviewing `tsconfig.json`, `eslint.config.*`, Prettier setup, folder layout, shared utilities, API clients, env access, or error handling in any TS frontend.
- Use when a review comment is about types, naming, imports, or validation rather than framework APIs.
- Do not use for framework specifics: Angular goes to `angular-developer` (angular/skills); React to `vercel-react-best-practices` and `vercel-composition-patterns`; Next.js to the vercel/next.js skills and the generated `AGENTS.md` (read `node_modules/next/dist/docs/`).
- Do not use for tests; see the sibling skill `frontend-testing`.

## Workflow

1. Read `package.json`, lockfile, `tsconfig*.json`, and `eslint.config.*`. Note the versions of `typescript`, `typescript-eslint`, `eslint`, and the framework, and which TypeScript range the framework's peer dependency allows.
2. Make the tsconfig strict per `references/tsconfig-and-lint.md`. Turn on new flags one at a time and fix errors in the same change; never use `ignoreDeprecations` as a permanent fix.
3. Set up ESLint flat config with type-aware rules plus `eslint-config-prettier` last. Prettier formats, ESLint finds bugs; never overlap them.
4. Check module layout (`references/module-layout.md`): feature folders, explicit public entry points, no import cycles, no deep imports across features.
5. Find every I/O boundary (HTTP responses, `localStorage`, URL/search params, `postMessage`, env vars, form input) and parse it with one schema library (`references/boundary-validation.md`).
6. Review async and error handling (`references/async-and-errors.md`): no floating promises, typed error results at boundaries, cancellation with `AbortSignal`.
7. Run `tsc --noEmit` (or the framework's type-check), `eslint .`, and `prettier --check .`; all three must pass in CI.

## Rules

- Do enable `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `verbatimModuleSyntax`.
- Do keep `typescript` inside the range your framework and typescript-eslint declare as peers; trial TypeScript 7 separately.
- Do use `unknown` for untrusted data and narrow with a schema or type guard; don't use `any` (lint it as an error).
- Do derive types from schemas (`z.infer`, `v.InferOutput`) or from `as const` data; don't hand-write a type and a schema that can drift.
- Do use `satisfies` to check literals while keeping their narrow type.
- Do use discriminated unions with a `kind`/`status` tag and an exhaustive `switch` ending in `assertNever`.
- Don't use `enum` or `namespace`; use string-literal unions or `as const` objects (works with `erasableSyntaxOnly`).
- Don't use non-null `!` or `as` casts to silence errors; fix the type or validate.
- Do mark imports used only as types with `import type`.
- Do name files `kebab-case.ts`, types/classes `PascalCase`, functions/variables `camelCase`, true constants `SCREAMING_SNAKE_CASE`.
- Don't prefix interfaces with `I` or suffix types with `Type`.
- Do prefer named exports; reserve default exports for files a framework requires (Next.js pages/layouts, lazy routes).
- Don't create barrel `index.ts` files inside a feature; one public `index.ts` per feature or package is the maximum.
- Do read env vars once in a typed, validated `env` module; don't read `process.env` or `import.meta.env` anywhere else.
- Do keep money as integer minor units (or a decimal string from the API) plus an ISO 4217 currency; never float arithmetic.
- Do keep instants as ISO 8601 UTC strings on the wire and format with `Intl` at the edge.
- Do await or explicitly `void` every promise; lint with `no-floating-promises` and `no-misused-promises`.
- Do throw only `Error` subclasses; in `catch`, treat the value as `unknown`.
- Do pass an `AbortSignal` to every cancellable fetch and long task.
- Do keep functions pure where possible and push side effects (fetch, storage, time, randomness) to the edges.
- Do prefer `readonly` arrays and properties for data that should not be mutated.
- Don't use `@ts-ignore`; use `@ts-expect-error` with a reason, and lint it.
- Don't add comments that restate code; comment only the "why".

## References

| File | Read when |
| --- | --- |
| [references/tsconfig-and-lint.md](references/tsconfig-and-lint.md) | writing or reviewing `tsconfig.json`, ESLint flat config, Prettier, or TypeScript 6/7 version questions |
| [references/boundary-validation.md](references/boundary-validation.md) | parsing API responses, forms, storage, URL params, or environment variables with zod or valibot |
| [references/module-layout.md](references/module-layout.md) | deciding folder structure, naming, public entry points, path aliases, or fixing import cycles |
| [references/async-and-errors.md](references/async-and-errors.md) | writing async code, error types, result unions, retries, cancellation, dates, or money |
