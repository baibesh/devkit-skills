# Runtime validation at I/O boundaries

TypeScript types vanish at runtime. Anything that enters the app from outside is `unknown` until a schema proves its shape. Parse once at the boundary, then pass typed values inward.

## Boundaries to cover

| Source | Where to parse |
| --- | --- |
| HTTP/JSON responses | in the API client function, before returning |
| Form input | form schema (also drives error messages) |
| URL path and search params | route loader / page entry, with coercion |
| `localStorage`, `sessionStorage`, IndexedDB | read helper; on failure, discard and fall back to defaults |
| `postMessage`, `BroadcastChannel`, WebSocket, SSE | message handler entry |
| Environment variables | one `env.ts` module at startup |
| Third-party SDK callbacks with loose types | adapter function |

Do not validate data that never left your process (function arguments between your own modules); types already cover that.

## Pick one library per project

- zod 4: largest ecosystem, good error messages, used by many form and tRPC-style libraries.
- valibot 1: modular, tree-shakable, much smaller bundle for client-heavy apps.
- Both implement Standard Schema, so libraries that accept "any Standard Schema" (form libraries, router search-param validators, `@t3-oss/env-*`) work with either. Don't mix both in one app.
- If the project already uses one (check package.json), keep it.

## zod 4 patterns

```ts
import { z } from 'zod';

export const User = z.object({
  id: z.uuid(),
  email: z.email(),
  name: z.string().min(1),
  role: z.enum(['admin', 'member']),
  createdAt: z.iso.datetime(),        // keep as ISO string; convert at the edge
  balance: z.object({ amountMinor: z.int(), currency: z.string().length(3) }),
});
export type User = z.infer<typeof User>;

export const UserList = z.array(User);
```

- Name the schema and its inferred type the same (`User`), or use `UserSchema` + `User` consistently; pick one style per repo.
- Use `safeParse` at boundaries where failure is expected (user input, storage); use `parse` where failure is a bug you want thrown (API contract).
- Format errors with `z.prettifyError(error)` for logs or `error.issues` for field mapping.
- Prefer `z.strictObject` for request payloads you build and `z.object` (strips unknown keys) for responses, so a backend adding fields does not break the client.
- Use `z.coerce.number()` only for string sources (URL params, form fields), never for JSON.
- Discriminated unions: `z.discriminatedUnion('status', [...])` mirrors TS unions and gives better errors.

## valibot 1 patterns

```ts
import * as v from 'valibot';

export const User = v.object({
  id: v.pipe(v.string(), v.uuid()),
  email: v.pipe(v.string(), v.email()),
  role: v.picklist(['admin', 'member']),
  createdAt: v.pipe(v.string(), v.isoTimestamp()),
});
export type User = v.InferOutput<typeof User>;

const result = v.safeParse(User, data);
if (!result.success) log(v.flatten(result.issues));
```

## Typed API client

```ts
export class ApiError extends Error {
  override name = 'ApiError';
  constructor(readonly status: number, readonly body: unknown) {
    super(`HTTP ${status}`);
  }
}

export async function getJson<T>(
  url: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(url, init);
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return schema.parse(body);
}

export const fetchUsers = (signal?: AbortSignal) =>
  getJson('/api/users', UserList, { signal });
```

- Angular `HttpClient`: pipe `map((body: unknown) => User.parse(body))` instead of using the generic `get<User>()` as if it validated.
- If the backend publishes OpenAPI, generate types (`openapi-typescript`) or schemas (`orval`, `openapi-zod-client`) instead of hand-writing them; still validate at runtime for critical paths.

## Typed environment access

One module owns env parsing; everything else imports from it.

```ts
// src/env.ts (Next.js; server-only values)
import 'server-only';
import { z } from 'zod';

const Env = z.object({
  DATABASE_URL: z.url(),
  API_TOKEN: z.string().min(1),
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
});
export const env = Env.parse(process.env);
```

```ts
// src/public-env.ts (browser-safe values)
import { z } from 'zod';

// Next inlines NEXT_PUBLIC_* only when referenced literally, so list each key.
export const publicEnv = z.object({
  NEXT_PUBLIC_API_URL: z.url(),
}).parse({ NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL });
```

- Vite apps: parse `import.meta.env` the same way; only `VITE_*` keys reach the client. Type them via `ImportMetaEnv` in `vite-env.d.ts`.
- Angular: there is no runtime env object in the browser; use `environment.ts` file replacements or the builder `define` option, and see `angular-developer` for the current approach.
- Fail fast at startup with a readable error listing missing keys; don't default secrets.
- Never put secrets in client-exposed prefixes. Treat everything shipped to the browser as public.
- `@t3-oss/env-core` / `@t3-oss/env-nextjs` package this pattern with server/client split checks; fine to use if the project already does.

## Storage and URL params

```ts
const Prefs = z.object({ theme: z.enum(['light', 'dark']), pageSize: z.int().positive() });
const DEFAULT_PREFS: z.infer<typeof Prefs> = { theme: 'light', pageSize: 20 };

export function readPrefs(): z.infer<typeof Prefs> {
  try {
    const raw = localStorage.getItem('prefs');
    const parsed = Prefs.safeParse(raw ? JSON.parse(raw) : null);
    return parsed.success ? parsed.data : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS; // storage blocked or JSON corrupt
  }
}
```

- Version stored payloads (`{ v: 2, ... }`) when the shape may change; migrate or drop old versions.
- URL params are always strings or string arrays: coerce, clamp, and default (`page` must be a positive int, unknown `sort` falls back).

## Anti-patterns

- `const user = (await res.json()) as User;` — a cast is not validation.
- Validating deep inside components instead of at the client function.
- Duplicating a TS interface and a schema by hand.
- Throwing raw `ZodError` to the UI; map issues to field messages or a domain error.
