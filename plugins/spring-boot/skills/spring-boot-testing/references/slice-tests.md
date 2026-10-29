# Unit and slice tests

## Boot 4 test modules

Boot 4 split test auto-configuration per technology. Add the matching test starter, which pulls in `spring-boot-starter-test` transitively:

| Slice | Test starter | Annotation import |
|---|---|---|
| `@WebMvcTest`, `@AutoConfigureMockMvc` | `spring-boot-starter-webmvc-test` | `org.springframework.boot.webmvc.test.autoconfigure` |
| `@DataJpaTest`, `TestEntityManager` | `spring-boot-starter-data-jpa-test` | `org.springframework.boot.data.jpa.test.autoconfigure` / `org.springframework.boot.jpa.test.autoconfigure` |
| `@AutoConfigureTestDatabase`, `@JdbcTest` | `spring-boot-starter-jdbc-test` | `org.springframework.boot.jdbc.test.autoconfigure` |
| `@RestClientTest` | `spring-boot-starter-restclient-test` | let the IDE resolve |
| Security helpers | `spring-boot-starter-security-test` | `org.springframework.security.test.*` |

`spring-boot-starter-test-classic` restores the Boot 3 all-in-one layout for migrations; do not use it in new projects. When imports fail after an upgrade, the class usually moved into one of these modules.

## Plain unit tests

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock OrderRepository repository;
    @Mock PaymentClient payments;
    Clock clock = Clock.fixed(Instant.parse("2026-01-01T10:00:00Z"), ZoneOffset.UTC);

    OrderService service;

    @BeforeEach
    void setUp() {
        service = new OrderService(repository, payments, clock);
    }

    @Test
    void shouldRejectCancel_whenOrderShipped() {
        Order order = anOrder().shipped().build();
        given(repository.findById(order.getId())).willReturn(Optional.of(order));

        assertThatThrownBy(() -> service.cancel(order.getId()))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Shipped");
    }
}
```

- Construct the class under test yourself (constructor injection makes this trivial). No Spring context.
- BDD-style Mockito (`given(...).willReturn(...)`, `then(mock).should()...`) reads well with AssertJ.
- `MockitoExtension` uses strict stubs: unused stubbing fails the test. Remove it rather than loosening strictness.
- Use `ArgumentCaptor` only when the argument is the observable outcome (for example, the event published).

## @WebMvcTest with MockMvcTester

```java
@WebMvcTest(OrderController.class)
@Import(SecurityConfig.class)          // only if the app has a custom SecurityFilterChain
class OrderControllerTest {

    @Autowired MockMvcTester mvc;
    @MockitoBean OrderService orders;

    @Test
    @WithMockUser
    void shouldCreateOrder_whenRequestValid() {
        var response = new OrderResponse(UUID.randomUUID(), "c-1", OrderStatus.NEW,
                new BigDecimal("20.00"), Instant.parse("2026-01-01T10:00:00Z"));
        given(orders.create(any())).willReturn(response);

        assertThat(mvc.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"customerId": "c-1", "items": [{"sku": "A-1", "quantity": 2}]}
                        """))
                .hasStatus(HttpStatus.CREATED)
                .hasHeader("Location", "http://localhost/api/orders/" + response.id())
                .bodyJson().extractingPath("$.status").isEqualTo("NEW");
    }

    @Test
    @WithMockUser
    void shouldReturnValidationProblem_whenItemsEmpty() {
        assertThat(mvc.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"customerId": "c-1", "items": []}
                        """))
                .hasStatus(HttpStatus.BAD_REQUEST)
                .bodyJson()
                .extractingPath("$.errors[0].field").isEqualTo("items");
    }

    @Test
    void shouldReturn401_whenAnonymous() {
        assertThat(mvc.get().uri("/api/orders")).hasStatus(HttpStatus.UNAUTHORIZED);
    }
}
```

- `MockMvcTester` (`org.springframework.test.web.servlet.assertj`) is auto-configured when AssertJ is on the classpath.
- Useful assertions: `hasStatusOk()`, `hasStatus(...)`, `hasStatus4xxClientError()`, `hasContentType(...)`, `hasHeader(...)`, `bodyJson().extractingPath("$.x")`, `bodyJson().isLenientlyEqualTo(...)` (JSON string or classpath resource), `bodyJson().convertTo(OrderResponse.class)`.
- `@WebMvcTest` loads controllers, `@ControllerAdvice`, converters, filters and MVC config only. Services must be `@MockitoBean`.
- Name the controller (`@WebMvcTest(OrderController.class)`) to keep the slice small.
- JWT-secured APIs: `.with(SecurityMockMvcRequestPostProcessors.jwt().authorities(new SimpleGrantedAuthority("ROLE_ADMIN")))` on the request.
- Assert request JSON from text blocks rather than serializing the request record, so the test catches field renames.

## @DataJpaTest

```java
@DataJpaTest
@Import(TestcontainersConfiguration.class)
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest {

    @Autowired OrderRepository repository;
    @Autowired TestEntityManager em;

    @Test
    void shouldLoadLinesInOneQuery_whenUsingEntityGraph() {
        Order order = anOrder().noLines().withLine("A-1", 2).withLine("B-2", 1).build();
        em.persistAndFlush(order);
        em.clear(); // force a real database read

        Order loaded = repository.findWithLinesById(order.getId()).orElseThrow();

        assertThat(loaded.getLines()).hasSize(2);
    }
}
```

- Each test runs in a transaction rolled back at the end. Call `em.flush()` and `em.clear()` before reading back, otherwise you only test the first-level cache.
- Flyway runs on context start, so the slice also validates migrations against Hibernate mappings.
- Test custom queries, projections, entity graphs, and DB constraints (unique, FK, not-null). Do not test inherited `save`/`findById`.
- Constraint violations surface on flush: `assertThatThrownBy(() -> em.persistAndFlush(dup)).isInstanceOf(ConstraintViolationException.class)` (Hibernate's) or Spring's `DataIntegrityViolationException` when going through a repository.

## Other slices

- `@JsonTest`: verify custom Jackson (3.x) serialization with `JacksonTester<T>`; useful for polymorphic types or custom serializers.
- `@RestClientTest(PaymentClient.class)`: binds a `MockRestServiceServer` to the auto-configured `RestClient.Builder`; assert outgoing request and response mapping.
- `@WebMvcTest` + `@MockitoBean` vs `@SpringBootTest`: if the test needs more than two or three mocks, the controller probably does too much.
- Slices and context cache: identical slice configuration across classes reuses the cached context. Keep `@Import` and `@MockitoBean` sets consistent; consider a shared meta-annotation.
