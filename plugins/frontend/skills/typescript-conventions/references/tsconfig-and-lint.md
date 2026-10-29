# tsconfig, ESLint and Prettier

## TypeScript version line (late 2026)

- TypeScript 6.0 is the last JavaScript-based compiler. It changed defaults: `strict: true`, `module: esnext`, `target` = latest ES before `esnext`, `types: []`, `rootDir` = the tsconfig directory, `noUncheckedSideEffectImports: true`.
- 6.0 deprecated `target: es5`, `downlevelIteration`, `moduleResolution: node`/`node10`/`classic`, `module: amd|umd|system`, `baseUrl`, `outFile`. TypeScript 7.0 (Go-native `tsc`) removes them as hard errors.
- TypeScript 7 adopts 6.0 defaults. Code that compiles cleanly on 6.0 without `ignoreDeprecations` (and with `stableTypeOrdering`) should compile the same on 7.0.
- Tooling lag: TypeScript 7 ships no stable JS API, so typescript-eslint 8 and Angular 22 (`@angular/build`) still peer on `typescript >=6.0 <6.1` / `<6.1.0`. Check `npm view <pkg> peerDependencies` before bumping.
- Practical setup: keep `typescript@~6.0` as the project dependency; optionally run TypeScript 7 as a faster CI type-check (`npx -p typescript@7 tsc --noEmit`) once it passes.
- Because `types` now defaults to `[]`, list global type packages explicitly (`"types": ["node"]`, `"vitest/globals"` only if you use globals).

## Base tsconfig (bundler-driven app)

```jsonc
{
  "compilerOptions": {
    "target": "es2023",
    "lib": ["es2023", "dom", "dom.iterable"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "moduleDetection": "force",
    "jsx": "react-jsx",                 // React/Next only; Angular omits
    "noEmit": true,                     // the bundler emits

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noPropertyAccessFromIndexSignature": true,
    "useUnknownInCatchVariables": true, // part of strict, kept for clarity

    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "erasableSyntaxOnly": true,         // forbids enum, namespace, parameter properties
    "noUncheckedSideEffectImports": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,

    "types": [],
    "paths": { "@/*": ["./src/*"] }     // no baseUrl: deprecated in 6.0
  },
  "include": ["src"]
}
```

Notes:

- Frameworks generate their own tsconfig. Merge these flags into it rather than replacing it; keep framework-required options (Angular `angularCompilerOptions`, Next `plugins: [{ "name": "next" }]`, `allowJs`, `incremental`).
- `erasableSyntaxOnly` conflicts with Angular constructor parameter properties (`constructor(private http: HttpClient)`). Angular code should use `inject()` anyway; if legacy code still uses parameter properties, leave the flag off.
- `exactOptionalPropertyTypes` makes `{ a?: string }` reject `{ a: undefined }`. Write `a?: string | undefined` where `undefined` is a real value (often for props passed through).
- Split configs: `tsconfig.json` (app), `tsconfig.spec.json` or a `vitest` types entry (tests), `tsconfig.node.json` (config files run in Node). Use `references` or `extends`, not copy-paste.
- Libraries that emit `.d.ts` add `declaration`, `declarationMap`, and consider `isolatedDeclarations` for fast parallel builds.
- Paths: `paths` resolve relative to the tsconfig. The bundler must agree: Vite 8 has `resolve.tsconfigPaths: true`; Next.js and Angular read `paths` natively.

## ESLint 10 flat config

ESLint 10 supports only flat config (`eslint.config.js|mjs|ts`). Use `defineConfig` and `globalIgnores` from `eslint/config`.

```ts
// eslint.config.mjs
import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default defineConfig(
  globalIgnores(['dist/', 'coverage/', '.next/', '.angular/', 'playwright-report/']),
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/ban-ts-comment': ['error', { 'ts-expect-error': 'allow-with-description' }],
      '@typescript-eslint/only-throw-error': 'error',
      '@typescript-eslint/prefer-promise-reject-errors': 'error',
      'no-restricted-syntax': ['error',
        { selector: 'TSEnumDeclaration', message: 'Use a string-literal union or `as const` object.' }],
    },
  },
  {
    files: ['**/*.{js,mjs,cjs}'],
    extends: [tseslint.configs.disableTypeChecked],
  },
  prettier, // last: turns off rules that fight Prettier
);
```

- `tseslint.config()` is deprecated in favor of ESLint's `defineConfig()`; both accept the same arrays.
- `projectService: true` replaces listing `project` paths; it uses the nearest tsconfig per file.
- Framework presets come first, project overrides after:
  - Next.js 16: `next lint` was removed; run `eslint .` directly. `eslint-config-next` exports flat configs (`eslint-config-next/core-web-vitals`, `eslint-config-next/typescript`).
  - Angular: `angular-eslint` (`ng add angular-eslint`) adds `angular.configs.tsRecommended` and template configs.
  - React (non-Next): `eslint-plugin-react-hooks` flat `recommended` config.
- Import ordering: let Prettier's import-sorting plugin or `eslint-plugin-simple-import-sort` own it, not both.
- Do not enable formatting rules (`indent`, `quotes`, `semi`, `@stylistic/*`) next to Prettier.

## Prettier

```json
{ "singleQuote": true, "printWidth": 100, "trailingComma": "all" }
```

- Keep config minimal; defaults are fine. Add `.prettierignore` for generated files, lockfiles, and build output.
- Run `prettier --check .` in CI and `prettier --write` in a pre-commit hook (lint-staged or similar).
- Plugins only when needed: `prettier-plugin-tailwindcss` for class sorting (must be last in `plugins`).

## Scripts

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  }
}
```

- Angular: type errors surface through `ng build`; add `tsc -p tsconfig.app.json --noEmit` only for a fast pre-check.
- Next.js: `next build` type-checks; keep a separate `typecheck` script for CI speed and editor parity. Run `next typegen` first if typed routes are enabled.
- Monorepo: one root `eslint.config.mjs` and `prettier` config; per-package tsconfig extending a shared base.

## Upgrade checklist

1. Read the release notes of every major you cross (TypeScript, ESLint, typescript-eslint, framework).
2. Remove `baseUrl`; keep `paths`. Replace `moduleResolution: node` with `bundler` (apps) or `nodenext` (Node packages).
3. Add explicit `types` arrays where globals disappeared after the 6.0 `types: []` default.
4. Remove `ignoreDeprecations` before attempting TypeScript 7.
5. Run typecheck, lint, tests, and a production build.
