# TypeScript client generation

All clients are generated from the committed `api/openapi.json`. Generated output is committed and never hand-edited.
Detect which generator the project already uses and keep it; the options below are the defaults for new setups.

| Frontend | Default | Output |
| --- | --- | --- |
| React 19, Next.js 16 | `openapi-typescript` + `openapi-fetch` | one `schema.d.ts` with `paths`/`components` types; tiny runtime client |
| Angular 22 | `ng-openapi-gen` | functions per operation + `Api` invoker service on `HttpClient` |
| Angular (alternative) | `openapi-generator` `typescript-angular` | injectable services per tag + model files |

## React and Next.js: openapi-typescript + openapi-fetch

```sh
npm i openapi-fetch
npm i -D openapi-typescript typescript
```

`package.json` scripts:

```json
{
  "scripts": {
    "api:generate": "openapi-typescript ../api/openapi.json -o src/api/schema.d.ts",
    "api:check": "openapi-typescript ../api/openapi.json -o src/api/schema.d.ts --check"
  }
}
```

Useful flags (verify on <https://openapi-ts.dev/cli>): `--root-types` (export `components` schemas as top-level aliases), `--enum` (TS enums instead of string unions; keep the default unions unless the project already uses enums), `--immutable` (readonly types), `--alphabetize`.

Client module, one per API:

```ts
// src/api/client.ts
import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: process.env.NEXT_PUBLIC_API_URL });

const auth: Middleware = {
  async onRequest({ request }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
};
api.use(auth);
```

Calling:

```ts
const { data, error, response } = await api.GET("/orders/{id}", {
  params: { path: { id }, query: { include: "items" } },
});
if (error) throw new ApiError(response.status, error); // error is the typed problem+json body
return data; // typed 2xx body
```

- `data` is set only for 2xx; `error` for 4xx/5xx/default. Always handle `error`; it does not throw.
- Derive app types from the schema instead of redeclaring: `type Order = components["schemas"]["OrderDto"]` (or root types with `--root-types`).
- Next.js: call the API from Server Components/Route Handlers with a server-only base URL; use `NEXT_PUBLIC_` only for browser calls. Pass `cache`/`next` fetch options per request where the project uses them.
- Data-fetching libraries: `openapi-react-query` wraps the same client for TanStack Query if the project already uses it.

## Angular: ng-openapi-gen

```sh
npm i -D ng-openapi-gen
```

`ng-openapi-gen.json` (read automatically from the current directory):

```json
{
  "$schema": "node_modules/ng-openapi-gen/ng-openapi-gen-schema.json",
  "input": "../api/openapi.json",
  "output": "src/app/api",
  "ignoreUnusedModels": false
}
```

Script: `"api:generate": "ng-openapi-gen"`.

Version 1.x generates one function per operation under `fn/` plus an `Api` invoker service; `enumStyle` defaults to `alias` (string unions); `services: true` adds per-tag services (larger bundles). Check the installed version's README before changing options.

```ts
// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([authInterceptor])),
    provideApiConfiguration(environment.apiUrl),
  ],
};

// orders.store.ts
private readonly api = inject(Api);
order = resource({
  params: () => ({ id: this.id() }),
  loader: ({ params }) => this.api.invoke(getOrder, params),
});
```

- `invoke` returns a Promise by default (`promises: true`); keep RxJS-based usage if the project's config sets it.
- Auth and error mapping go into functional `HttpInterceptorFn`s, not into generated code.
- Follow `angular-developer` for signals, `resource`/`httpResource` and component patterns.

## Angular alternative: openapi-generator typescript-angular

Use when the project already does, or needs per-tag injectable services.

```sh
npm i -D @openapitools/openapi-generator-cli
npx openapi-generator-cli generate -i ../api/openapi.json -g typescript-angular -o src/app/api \
  --additional-properties=ngVersion=22.0.0,providedIn=root,stringEnums=true,fileNaming=kebab-case,useSingleRequestParameter=true
```

- Requires a Java runtime (the CLI downloads the generator JAR); pin the generator version in `openapitools.json`.
- Set `ngVersion` to the project's Angular version; the generator documents support for 9.x to 22.x.
- `stringEnums=true` emits string enums instead of const objects; pick one style and keep it.
- Add `.openapi-generator-ignore` and delete stale files before regenerating, or old models linger.

## Committing and linting generated code

- Commit the output folder; reviewers see the client diff next to the spec diff.
- Exclude it from ESLint/Prettier formatting rules that would rewrite it, or run Prettier as part of `api:generate` so output is stable.
- Never import from generated internals that are not exported from the generator's index.

## CI drift checks

```sh
# backend: regenerates api/openapi.json (export test or maven plugin)
./mvnw -B verify
# frontend: regenerate client from the committed spec
npm ci && npm run api:generate
# fail if anything changed
git diff --exit-code -- api/openapi.json web/src/api
```

openapi-typescript can also use `--check` instead of regenerate-and-diff.

## Breaking-change gate (oasdiff)

```sh
git fetch origin "$BASE_REF"
oasdiff breaking "origin/$BASE_REF:api/openapi.json" "HEAD:api/openapi.json" --fail-on ERR
```

- `--fail-on ERR` fails on breaking changes; `WARN` also fails on potential ones.
- `--format` accepts `text` (default), `json`, `yaml`, `markdown`, `html`, `githubactions`, `junit`, `singleline`.
- GitHub Action: `oasdiff/oasdiff-action/breaking@v0` with inputs `base`, `revision`, `fail-on`.
- `oasdiff changelog <base> <revision>` produces a human-readable list for the PR description.

A failing gate is not overridden silently: either revert, version the endpoint, or record the decision and coordinate the release in the PR.
