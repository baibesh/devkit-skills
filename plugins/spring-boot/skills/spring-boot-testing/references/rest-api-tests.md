# REST API integration tests

Full-context tests that exercise HTTP, service, persistence and real infrastructure together. Keep them few and scenario-shaped (create, read back, transition, error path).

## Running server with RestTestClient

`RestTestClient` is new in Spring Framework 7 (`org.springframework.test.web.servlet.client.RestTestClient`). Boot 4 auto-configures one bound to the random port when the test is annotated `@AutoConfigureRestTestClient` (`org.springframework.boot.resttestclient.autoconfigure`, from `spring-boot-resttestclient` / `spring-boot-starter-restclient-test`).

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient
@Import(TestcontainersConfiguration.class)
class OrderFlowIT {

    @Autowired RestTestClient client;

    @Test
    void shouldCreateAndFetchOrder_whenRequestValid() {
        var request = new CreateOrderRequest("c-1", List.of(new LineItemRequest("A-1", 2)), null);

        EntityExchangeResult<OrderResponse> created = client.post().uri("/api/orders")
                .body(request)
                .exchange()
                .expectStatus().isCreated()
                .expectBody(OrderResponse.class)
                .returnResult();

        OrderResponse body = created.getResponseBody();
        assertThat(body).isNotNull();
        assertThat(created.getResponseHeaders().getLocation()).hasPath("/api/orders/" + body.id());

        client.get().uri("/api/orders/{id}", body.id())
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.status").isEqualTo("NEW")
                .jsonPath("$.customerId").isEqualTo("c-1");
    }

    @Test
    void shouldReturnProblem_whenOrderMissing() {
        client.get().uri("/api/orders/{id}", UUID.randomUUID())
                .exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON)
                .expectBody()
                .jsonPath("$.status").isEqualTo(404)
                .jsonPath("$.title").isEqualTo("Resource not found");
    }
}
```

- `.body(obj)` sends the object as JSON; `.expectBody(T.class).returnResult().getResponseBody()` extracts it; `.expectBody().jsonPath(...)` asserts fields; `.json("...")` compares whole documents leniently.
- AssertJ style is available too: `assertThat(RestTestClientResponse.from(spec)).hasStatusOk()`.
- Authenticated calls: `.header(HttpHeaders.AUTHORIZATION, "Bearer " + token)`. Obtain tokens from a Keycloak Testcontainer for true end-to-end, or override the `JwtDecoder` with a test bean that accepts a locally signed token. Do not disable security in integration tests.
- `TestRestTemplate` still exists in Boot 4 (`org.springframework.boot.resttestclient.TestRestTemplate`) but requires `@AutoConfigureTestRestTemplate`; use it only in existing suites.

## Mock environment with MockMvcTester

When you do not need a real server (no servlet container specifics, faster), use the default `MOCK` web environment:

```java
@SpringBootTest
@AutoConfigureMockMvc   // Boot 4: required, no longer implied by @SpringBootTest
@Import(TestcontainersConfiguration.class)
class OrderApiIT {

    @Autowired MockMvcTester mvc;

    @Test
    void shouldListOrders_whenCustomerHasOrders() {
        assertThat(mvc.get().uri("/api/orders?customerId=c-1"))
                .hasStatusOk()
                .bodyJson().extractingPath("$.content").asArray().isNotEmpty();
    }
}
```

Note: in the MOCK environment the test and the request share a thread, so a test-level `@Transactional` would wrap the request too. Do not rely on that; with `RANDOM_PORT` the server runs on other threads and test transactions never roll back the server's writes.

## Data isolation

- `RANDOM_PORT` tests cannot use rollback. Choose one strategy per suite:
  1. Unique data per test (random customer IDs, UUIDs) and assertions scoped to that data. Simplest and parallel-safe.
  2. `@Sql(scripts = "/sql/cleanup.sql", executionPhase = AFTER_TEST_METHOD)` truncating the touched tables.
  3. A `@BeforeEach` that deletes via repositories (order matters with FKs).
- Never `@DirtiesContext` to reset data; it restarts the context and containers.

## External HTTP dependencies

- Stub third-party APIs with WireMock (`org.wiremock.integrations:wiremock-spring-boot` provides `@EnableWireMock` and injects the base URL into a property) or a WireMock Testcontainer.
- Point the client's base URL property at the stub; never call real external services from tests.
- Assert both the happy path and the error mapping (timeouts, 5xx, malformed body) into your Problem Details.

## Messaging and async

- Kafka/RabbitMQ: real broker via `@ServiceConnection` containers.
- Assert eventual outcomes with Awaitility:

```java
await().atMost(Duration.ofSeconds(10))
       .untilAsserted(() -> assertThat(repository.findById(id)).get()
               .extracting(Order::getStatus).isEqualTo(OrderStatus.PAID));
```

## What to cover at this level

- One happy path per endpoint group, wired end to end.
- Cross-cutting concerns that slices skip: real security filter chain, transaction boundaries, Flyway schema, serialization config, error handling for persistence exceptions (unique constraint -> 409 problem).
- Leave combinatorial validation cases to `@WebMvcTest`.
