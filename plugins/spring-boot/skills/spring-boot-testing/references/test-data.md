# Test data

Goal: each test shows only the data that matters to it, and tests never depend on each other's data.

## Test data builders

```java
// src/test/java/com/acme/orders/OrderFixtures.java
final class OrderFixtures {
    private OrderFixtures() {}

    static OrderBuilder anOrder() {
        return new OrderBuilder();
    }

    static final class OrderBuilder {
        private String customerId = "c-" + UUID.randomUUID();
        private final List<LineSpec> lines = new ArrayList<>(List.of(new LineSpec("SKU-1", 1, new BigDecimal("10.00"))));
        private boolean shipped;

        OrderBuilder customer(String customerId) { this.customerId = customerId; return this; }
        OrderBuilder withLine(String sku, int qty) { lines.add(new LineSpec(sku, qty, new BigDecimal("10.00"))); return this; }
        OrderBuilder noLines() { lines.clear(); return this; }
        OrderBuilder shipped() { this.shipped = true; return this; }

        Order build() {
            Order order = new Order(customerId);
            lines.forEach(l -> order.addLine(l.sku(), l.qty(), l.price()));
            if (shipped) {
                order.markShipped();
            }
            return order;
        }
    }

    private record LineSpec(String sku, int qty, BigDecimal price) {}
}
```

- Defaults produce a valid object; each test overrides only what it is about (`anOrder().shipped().build()`).
- Build through the public constructor and behaviour methods so fixtures respect invariants. Avoid reflection-set fields.
- Default IDs and unique keys are random so tests do not collide in a shared or reused database.
- Keep one fixtures class per aggregate, next to the tests of that feature. Request DTO records get small factory methods too (`validCreateOrderRequest()`).
- Instancio or similar random-object libraries are fine for "any valid value" fields, but keep the fields under test explicit.

## @Sql fixtures

Use SQL scripts when data is large, relational, or needs to bypass domain rules (legacy states):

```java
@Test
@Sql("/sql/orders/three-orders-for-c1.sql")
void shouldPageOrders_whenCustomerHasMany() { ... }

@SpringBootTest
@Sql(scripts = "/sql/cleanup.sql", executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
class OrderFlowIT { ... }
```

- Place scripts under `src/test/resources/sql/<feature>/`; name them after the scenario, not the test method.
- Class-level `@Sql` applies to every method; method-level overrides it unless `@SqlMergeMode(MERGE)` is used.
- In `@DataJpaTest` (transactional tests) `@Sql` data is rolled back with the test transaction.
- `cleanup.sql` uses `TRUNCATE ... RESTART IDENTITY CASCADE` on Postgres for speed; list tables explicitly. Never truncate `flyway_schema_history`.
- Do not seed test data through Flyway migrations in `src/main`. If a dev/test seed is needed, use a separate location (`classpath:db/testdata`) added only in tests via `spring.flyway.locations`.

## Cleanup strategies by test type

| Test type | Strategy |
|---|---|
| Unit | Nothing to clean |
| `@DataJpaTest` | Automatic rollback per test |
| `@SpringBootTest` (MOCK) without async | Unique data per test; or `@Sql` cleanup |
| `@SpringBootTest(RANDOM_PORT)` | Unique data per test, or `@Sql` cleanup AFTER_TEST_METHOD. Rollback does not apply |
| Reused local containers | Unique data per test is mandatory; never assume an empty table |

Assertions should be scoped to the test's own data (`findByCustomerId(customerId)`) rather than global counts (`count() == 3`).

## Time, IDs and randomness

- Inject `java.time.Clock` into services; in tests pass `Clock.fixed(Instant.parse("2026-01-01T10:00:00Z"), ZoneOffset.UTC)`. In a Spring context, provide a `@Primary` `Clock` bean in a `@TestConfiguration`.
- Compare `Instant`s from the database with tolerance (`isCloseTo(expected, within(1, ChronoUnit.SECONDS))`) or truncate: Postgres stores microseconds, Java has nanoseconds.
- If ID generation must be deterministic, inject an ID supplier; otherwise read the generated ID from the response.
- Seed any `Random` explicitly.

## JSON payloads

- Inline small request bodies with text blocks in the test; they double as documentation and catch field renames.
- Larger expected responses: `src/test/resources/<feature>/<scenario>.json` with `bodyJson().isLenientlyEqualTo("orders/created.json")` (MockMvcTester treats a `.json` string as a classpath resource).
- Exclude volatile fields (IDs, timestamps) from whole-document comparisons by asserting them separately.

## Anti-patterns

- A shared `data.sql` loaded for every test: hidden coupling, order-dependent failures.
- Mutating a shared static fixture object across tests.
- Copy-pasted 30-line setup blocks: extract a builder.
- Test data that is invalid by accident (missing required fields) so the test passes for the wrong reason.
