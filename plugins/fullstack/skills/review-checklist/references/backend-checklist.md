# Backend review checklist (Spring Boot)

Severity hints in brackets: [B] blocker, [M] major, [m] minor. Adjust to impact.

## Controllers and API surface

- [ ] [B] Every new endpoint has an authorization rule (`@PreAuthorize`, security filter chain matcher, or explicit `permitAll` with justification).
- [ ] [M] Request bodies are DTO records with `@Valid`; path/query params constrained (`@Positive`, `@Size`, `@Pattern`) with `@Validated` where needed.
- [ ] [B] No JPA entity returned or accepted at the boundary (entity leakage: lazy-loading exceptions, exposed internal fields, mass assignment).
- [ ] [M] Status codes match semantics (201 + `Location` on create, 204 on delete, 404 vs 403 policy).
- [ ] [M] Errors go through the central handler as Problem Details; no `try/catch` returning `ResponseEntity.badRequest().body(e.getMessage())`.
- [ ] [M] List endpoints are paginated with a max page size; sort fields whitelisted.
- [ ] [M] DTO, controller or error change is reflected in `api/openapi.json` and the generated client (see `api-contract`).
- [ ] [m] No business logic in controllers beyond mapping and delegation.

## Services and transactions

- [ ] [M] `@Transactional` on the service method that owns the unit of work, not on controllers or repositories by default.
- [ ] [M] Read-only paths use `@Transactional(readOnly = true)` where the project does so.
- [ ] [B] No self-invocation of `@Transactional`/`@Async`/`@Cacheable` methods (proxy bypass means no transaction/async/cache).
- [ ] [M] No remote calls (HTTP, messaging, email) inside a DB transaction that holds locks; use after-commit events or the outbox pattern.
- [ ] [M] Checked exceptions do not commit unexpectedly: rollback rules (`rollbackFor`) match intent.
- [ ] [M] Events published inside a transaction use `@TransactionalEventListener` when handlers must see committed data.
- [ ] [M] Concurrency: read-modify-write on shared rows uses optimistic locking (`@Version`) or explicit locking; counters use atomic updates.
- [ ] [m] Constructor injection, final fields; no field injection in new code.

## JPA and persistence

- [ ] [M] N+1: loops over entities touching lazy associations; list endpoints mapping collections. Fix with fetch joins, `@EntityGraph`, DTO projections or batch fetching.
- [ ] [M] `FetchType.EAGER` on `@ManyToOne`/`@OneToMany` added without need.
- [ ] [M] Queries with `Pageable` plus collection fetch join (in-memory pagination warning).
- [ ] [B] String-concatenated JPQL/SQL or `Sort` from raw user input (see security checklist).
- [ ] [M] `equals`/`hashCode` on entities not based on mutable or generated fields incorrectly; no Lombok `@Data` on entities.
- [ ] [M] Bidirectional associations kept in sync; cascade and `orphanRemoval` intentional.
- [ ] [M] Bulk updates (`@Modifying`) clear or refresh the persistence context when needed.
- [ ] [m] `findAll()` without limits on tables that grow.
- [ ] [M] Open Session in View relied upon (`spring.jpa.open-in-view` default true logs a warning); lazy loading in the web layer.

## Migrations (Flyway/Liquibase)

- [ ] [B] Migration is compatible with the currently deployed version (expand/contract): no dropping or renaming columns still read by running code.
- [ ] [B] Entity mapping matches the migration (column names, nullability, types); `ddl-auto` is `validate` or `none` outside local dev.
- [ ] [M] Large-table changes: adding NOT NULL with default, new indexes, or backfills that lock the table; use concurrent index creation where supported.
- [ ] [M] Never edit an already-applied migration; add a new one.
- [ ] [m] Indexes exist for new foreign keys and new query predicates.

## Configuration and resources

- [ ] [B] No secrets in `application*.yml`, code or tests; values come from env/secret store.
- [ ] [M] New config properties bound via `@ConfigurationProperties` records with validation, defaults documented.
- [ ] [M] HTTP clients (`RestClient`, `WebClient`, `HttpInterface`) have connect/read timeouts; retries only on idempotent calls.
- [ ] [M] Thread pools, `@Async` executors, and virtual-thread usage reviewed: no `synchronized` blocks around blocking I/O on hot paths when using virtual threads on older JDKs; no unbounded queues.
- [ ] [M] Caches have size and TTL limits; cache keys include tenant/user where data is scoped.
- [ ] [m] Actuator endpoints exposed only as intended.

## Error handling and logging

- [ ] [M] Exceptions not swallowed (`catch (Exception e) {}`) or logged and rethrown twice.
- [ ] [B] No sensitive data in logs: passwords, tokens, full card numbers, personal data beyond policy.
- [ ] [m] Structured log messages with parameters (`log.info("Order {} created", id)`), not string concatenation.
- [ ] [m] Correlation/trace IDs propagated through async boundaries.

## Java language

- [ ] [M] `Optional.get()` without check; `null` returned where `Optional` or empty collection is expected.
- [ ] [M] Mutable static state; non-thread-safe types (`SimpleDateFormat`, `HashMap`) shared across requests.
- [ ] [M] `BigDecimal` compared with `equals` where scale differs (use `compareTo`); money as `double`.
- [ ] [M] Time: `LocalDateTime.now()` for instants; use `Instant` and an injectable `Clock`.
- [ ] [m] Records for DTOs and value objects; sealed types / pattern matching where they simplify branching (Java 21+).
- [ ] [m] Resources closed (`try-with-resources`) for streams, files, JDBC.

## Tests

- [ ] [M] New behavior has tests that fail without the change; bug fixes include a regression test.
- [ ] [M] Right test slice: `@WebMvcTest` for controller mapping/validation/security, `@DataJpaTest` with Testcontainers for queries, `@SpringBootTest` for flows (follow `spring-boot-testing`).
- [ ] [M] Authorization tested: at least one forbidden/unauthenticated case per new endpoint.
- [ ] [M] Error paths tested (validation 400, not-found 404, conflict 409), asserting Problem Details fields.
- [ ] [m] No `Thread.sleep` for async; use Awaitility. No test order dependence or shared mutable fixtures.
- [ ] [m] Mocks do not replace the thing under test; prefer real collaborators inside the slice.
- [ ] [m] Assertions are specific (AssertJ), not only `isNotNull()`.
