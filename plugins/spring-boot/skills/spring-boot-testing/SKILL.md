---
name: spring-boot-testing
description: "How to test Spring Boot 4.x applications: unit tests with JUnit 5 and Mockito, slice tests (@WebMvcTest with MockMvcTester, @DataJpaTest), @SpringBootTest integration tests with Testcontainers and @ServiceConnection, test data setup, ArchUnit architecture rules, and which test level to use for what. Use when writing, fixing or reviewing Java or Spring tests, setting up Testcontainers, or deciding how a change should be tested. Not for frontend tests (see frontend-testing)."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# Spring Boot Testing

Targets: Spring Boot 4.x (4.0/4.1), Spring Framework 7, Java 21 or 25. First detect the project's real versions from pom.xml / build.gradle(.kts) and adapt; never downgrade a project.

## Use when / do not use

- Use when writing, fixing or reviewing JUnit tests for a Spring Boot service, or choosing the test level for a change.
- Use when setting up Testcontainers, `@ServiceConnection`, test fixtures or ArchUnit rules.
- Do not use for production code conventions (see `spring-boot-conventions`) or browser/UI tests (see `frontend-testing`).
- If the `spring-boot-community` plugin (sivalabs) is installed, its `spring-boot` skill has deeper references.

## Pick the test level

| What changed | Test with | Notes |
|---|---|---|
| Pure logic (domain method, mapper, calculator) | Plain JUnit 5 unit test, no Spring | Milliseconds. `new` the class; Mockito only for real collaborators |
| Service orchestration | Unit test with `@ExtendWith(MockitoExtension.class)` | Mock ports (repositories, clients); assert outcomes, not call counts |
| Controller: mapping, validation, status codes, Problem Details, security rules | `@WebMvcTest(XController.class)` + `MockMvcTester` + `@MockitoBean` service | No DB, no full context |
| Repository: custom queries, projections, entity graphs, constraints | `@DataJpaTest` + real DB via Testcontainers | Never H2: dialect, constraints and SQL differ |
| Flyway migrations | Any Testcontainers-backed test that boots JPA | Startup with `ddl-auto=validate` is the check |
| End-to-end flow through HTTP, DB, messaging | `@SpringBootTest(webEnvironment = RANDOM_PORT)` + `RestTestClient` | Few, high-value scenarios |
| Outbound HTTP client | `@RestClientTest` or WireMock | Assert request shape and error mapping |
| Architecture and module boundaries | ArchUnit (or Spring Modulith `verify()`) | Runs as a fast unit test |

Most tests should be unit and slice tests; keep `@SpringBootTest` for flows that cross layers.

## Workflow

1. Read the build file: Boot version, test starters (Boot 4: `spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`, ...), Testcontainers version, existing test base classes. Reuse what exists.
2. Choose the level from the table; prefer the lowest level that can catch the bug.
3. Ensure one shared `TestcontainersConfiguration` with `@ServiceConnection` beans exists; import it, do not declare containers per class.
4. Write the test: name `shouldX_whenY`, arrange with builders/fixtures, act once, assert with AssertJ.
5. For a bug fix, write the failing test first and watch it fail for the right reason.
6. Run the narrowest scope first (`./mvnw test -Dtest=OrderControllerTest`, `./gradlew test --tests '*OrderControllerTest'`), then the full suite.
7. Check that the context cache is not fragmented (same imports and mocks across similar tests) and no `@DirtiesContext` was added.

## Rules

- Do use JUnit 5 (Jupiter) and AssertJ (`assertThat`); no Hamcrest or JUnit `assertEquals` in new tests.
- Do name tests `shouldX_whenY` (for example `shouldReturn404_whenOrderMissing`); `@DisplayName` only if the team uses it.
- Do keep test classes package-private and in the same package as the class under test.
- Do use `@MockitoBean` / `@MockitoSpyBean`; `@MockBean` / `@SpyBean` are removed in Boot 4.
- Do use `MockMvcTester` (AssertJ) for MVC tests; plain `MockMvc` only in existing suites.
- Do use `RestTestClient` (`@AutoConfigureRestTestClient`) for running-server tests; `TestRestTemplate` needs `@AutoConfigureTestRestTemplate` in Boot 4.
- Do add `@AutoConfigureMockMvc` explicitly when a `@SpringBootTest` needs MockMvc; Boot 4 no longer adds it implicitly.
- Do run repository and integration tests against the production database engine via Testcontainers; never H2 or embedded substitutes.
- Do declare containers once as `@Bean @ServiceConnection` in a shared `@TestConfiguration`; never hand-copy URLs into `@DynamicPropertySource` when a service connection exists.
- Don't use `@DirtiesContext`; reset state with `@Sql`, transactional rollback or explicit cleanup instead.
- Don't vary mocks, profiles or properties per class without need; each unique combination creates a new Spring context.
- Do make tests independent of order and of each other's data; generate unique IDs per test.
- Don't use `Thread.sleep`; use Awaitility for asynchronous outcomes.
- Don't mock what you own and can construct (records, value objects, entities); mock only boundaries.
- Do verify behaviour through public APIs; don't test private methods or Spring wiring itself.
- Do assert error responses as Problem Details (`status`, `type`, `title`, field errors), not just the status code.
- Do test security rules in `@WebMvcTest` with `@WithMockUser` or `jwt()` (from `spring-security-test`).
- Do inject a `Clock` in production code and pass a fixed clock in tests instead of asserting on `now()`.
- Do aim coverage at decisions: every branch of domain logic and every error mapping. Treat a line-coverage number (for example 80% via JaCoCo) as a floor signal, never the goal.
- Don't write tests that only assert a mock returned what it was told to return.

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvcTester mvc;
    @MockitoBean OrderService orders;

    @Test
    void shouldReturn404Problem_whenOrderMissing() {
        UUID id = UUID.randomUUID();
        given(orders.get(id)).willThrow(new OrderNotFoundException(id));

        assertThat(mvc.get().uri("/api/orders/{id}", id))
                .hasStatus(HttpStatus.NOT_FOUND)
                .bodyJson().extractingPath("$.title").isEqualTo("Resource not found");
    }
}
```

## References

| File | Read when ... |
|---|---|
| [references/testcontainers.md](references/testcontainers.md) | setting up containers, `@ServiceConnection`, reuse, dev-time `TestApplication`, CI concerns |
| [references/slice-tests.md](references/slice-tests.md) | writing `@WebMvcTest`, `@DataJpaTest`, `@JsonTest`, `@RestClientTest` tests, or unit tests with Mockito |
| [references/rest-api-tests.md](references/rest-api-tests.md) | writing `@SpringBootTest` HTTP flow tests with `RestTestClient` or `MockMvcTester` |
| [references/test-data.md](references/test-data.md) | building fixtures: test data builders, `@Sql` scripts, cleanup strategy, clocks and IDs |
| [references/archunit.md](references/archunit.md) | enforcing package-by-feature boundaries, layering and coding rules with ArchUnit or Spring Modulith |
