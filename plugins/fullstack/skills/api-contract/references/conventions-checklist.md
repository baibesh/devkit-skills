# API conventions checklist

Apply when designing or reviewing an endpoint. Existing project conventions win over this list; flag inconsistencies instead of mixing styles.

## Resources and naming

- [ ] Paths are plural, kebab-case nouns: `/purchase-orders/{orderId}/line-items`.
- [ ] No verbs in paths, except explicit actions that are not CRUD: `POST /orders/{id}/cancel`.
- [ ] Nesting at most one level under a parent; deeper relations use query filters.
- [ ] Path variables are camelCase in the spec (`{orderId}`) and match `@PathVariable` names.
- [ ] JSON properties are camelCase; booleans read as predicates (`active`, `hasAttachments`).
- [ ] IDs are strings in JSON when they are UUIDs or may exceed 2^53 (`Long` IDs above that lose precision in JS).
- [ ] DTO names describe role: `OrderDto`/`OrderResponse`, `CreateOrderRequest`, `UpdateOrderRequest`. One naming scheme per project.
- [ ] `operationId` is unique, verb-first camelCase (`listOrders`, `getOrder`, `createOrder`).

## HTTP methods and status codes

| Method | Use | Success |
| --- | --- | --- |
| GET | read, no side effects | 200 |
| POST | create, or non-idempotent action | 201 + `Location` header, or 200/202 |
| PUT | full replace, idempotent | 200 or 204 |
| PATCH | partial update (JSON Merge Patch semantics: absent field = unchanged) | 200 |
| DELETE | remove, idempotent | 204 (also when already gone, if the project chooses so) |

- [ ] Async work returns 202 with a status resource URL.
- [ ] Errors follow `error-format-rfc9457.md`.

## Dates, times, numbers

- [ ] Instants: `Instant` or `OffsetDateTime`, serialized as ISO-8601 UTC (`2026-10-29T08:15:00Z`), `format: date-time`.
- [ ] Calendar dates: `LocalDate`, `format: date` (`2026-10-29`). Never an instant at midnight.
- [ ] No `LocalDateTime` on the wire for moments in time; no epoch numbers.
- [ ] Jackson `WRITE_DATES_AS_TIMESTAMPS` stays disabled (Spring Boot default).
- [ ] Durations as ISO-8601 (`PT15M`) or an explicit unit in the name (`timeoutSeconds`).
- [ ] Money: decimal as string or integer minor units plus currency code; never a float.
- [ ] Clients parse date-time strings at the edge and render in the user's time zone.

## Enums

- [ ] Serialized as strings (constant name, UPPER_SNAKE_CASE), never ordinals.
- [ ] `@Schema(enumAsRef = true)` so the enum is a named schema and one generated type.
- [ ] Adding a value is a potential breaking change for clients with exhaustive `switch`; clients include a default branch.
- [ ] Removing or renaming a value is breaking: deprecate first.

## Nullability and required fields

- [ ] Required response fields are marked required; generated TS types then have no `?`.
- [ ] Optional means "may be absent"; nullable means "present with null". Do not use both for one field without reason.
- [ ] Empty collections are `[]`, not `null` or absent.
- [ ] Request DTOs validate with Bean Validation (`@NotNull`, `@NotBlank`, `@Size`, `@Email`) and the controller uses `@Valid`.

## Pagination

One envelope for the whole API. Default: offset pagination with Spring Data's stable DTO.

```java
@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)
```

Renders `Page<T>` as `PagedModel<T>`:

```json
{ "content": [ ... ], "page": { "size": 20, "number": 0, "totalElements": 135, "totalPages": 7 } }
```

or return `new PagedModel<>(page)` explicitly. Alternatively define an own record (`PageResponse<T>(List<T> items, int page, int size, long total)`); in all cases never serialize `PageImpl` directly.

- [ ] Query params: `page` (0-based, document it), `size` with a maximum (`spring.data.web.pageable.max-page-size`), `sort=field,asc`.
- [ ] Sort fields are whitelisted; never pass arbitrary property paths to the repository.
- [ ] Large or fast-changing collections use cursor pagination: `?cursor=...&limit=...` returning `{ items, nextCursor }`.
- [ ] List endpoints have a default `size` and never return unbounded results.

## Filtering and search

- [ ] Filters as explicit query params (`status=OPEN&createdAfter=...`), documented with types.
- [ ] Multi-value params repeat the key (`status=OPEN&status=PAID`) or use a documented comma list; pick one.
- [ ] Free-text search param named consistently (`q` or `search`).

## Idempotency and concurrency

- [ ] PUT, DELETE and GET are idempotent by implementation, not only by convention.
- [ ] Retry-prone POSTs (payments, orders) accept an `Idempotency-Key` header; the server stores key + response hash and replays the stored response on repeat.
- [ ] Optimistic locking: expose `version` in the DTO or an `ETag`; updates send it back (`If-Match` or body field) and conflicts return 409/412.

## Versioning and evolution

- [ ] Additive changes (new optional request field, new response field, new endpoint) are non-breaking.
- [ ] Breaking: removing/renaming fields or endpoints, changing types or formats, making optional fields required, new required request fields, narrowing validation, changing status codes or error `type`s.
- [ ] Breaking changes go through `oasdiff breaking` and an explicit decision: new version, or deprecation (`@Deprecated` + `deprecated: true` in the spec + `Deprecation`/`Sunset` headers) followed by removal.
- [ ] One versioning strategy per API. Spring Framework 7 supports first-class versioning (`version` attribute on `@RequestMapping`/`@GetMapping`, Boot properties under `spring.mvc.apiversion.*`, e.g. header-based); path prefixes (`/api/v1`) remain fine when already used.
- [ ] Clients ignore unknown response fields (generated clients do; hand-written validators like strict zod schemas must use passthrough).

## Security on the contract

- [ ] Every operation declares its security requirement; public endpoints are explicit.
- [ ] No internal fields in DTOs (password hashes, internal flags, other tenants' IDs).
- [ ] Request DTOs contain only client-settable fields; no `id`, `createdAt`, `ownerId`, `role` in create/update requests (mass assignment).
- [ ] Limits documented: max lengths, max items, max upload size.
