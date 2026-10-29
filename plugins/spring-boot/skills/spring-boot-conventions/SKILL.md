---
name: spring-boot-conventions
description: "Team conventions for Spring Boot 4.x on Java 21+ services: package-by-feature layout, constructor injection, records as DTOs, REST controllers with RFC 9457 Problem Details, Spring Data JPA and transaction boundaries, typed @ConfigurationProperties, Flyway migrations, JSpecify null-safety, virtual threads, Micrometer observability. Use when creating or modifying a Spring Boot application, controller, service, entity, repository or configuration, or when asked how to structure Java backend code. Not for test code (see spring-boot-testing) or API contract design (see api-contract)."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# Spring Boot Conventions

Targets: Spring Boot 4.x (4.0/4.1), Spring Framework 7, Java 21 or 25. First detect the project's real versions from pom.xml / build.gradle(.kts) and adapt; never downgrade a project.

## Use when / do not use

- Use when adding or changing controllers, services, entities, repositories, configuration, migrations or wiring in a Spring Boot service.
- Use when asked how to lay out a new Java backend or where a class belongs.
- Do not use for tests: see `spring-boot-testing`. Do not use for designing the HTTP contract itself (resource names, status codes, OpenAPI): see `api-contract`.
- If the `spring-boot-community` plugin (sivalabs) is installed, its `spring-boot` skill has deeper references; these conventions take precedence where they differ.

## Workflow

1. Read the build file: Boot version, Java toolchain, starters present (Boot 4 uses modular starters such as `spring-boot-starter-webmvc`, `spring-boot-starter-flyway`). Match what exists.
2. Locate the feature package (`com.acme.<feature>`); create `api`, `domain`, `infra` subpackages only as needed. Never add a top-level `controller/` or `service/` package.
3. Model the change inward-out: Flyway migration, then entity and repository, then service with the transaction boundary, then controller and DTO records.
4. Put new settings in a `@ConfigurationProperties` record with `@Validated`; never sprinkle `@Value`.
5. Map failures to Problem Details through the shared `@RestControllerAdvice`; throw domain exceptions, never build error bodies in controllers.
6. Add `package-info.java` with `@NullMarked` to every new package; mark nullable spots with `@Nullable`.
7. Make the change observable: meaningful log lines (structured), metrics or `@Observed` on key operations, health indicators for new external dependencies.
8. Build and run the tests (`./mvnw verify` or `./gradlew check`); hand test authoring to `spring-boot-testing`.

## Rules

- Do organize by feature: `com.acme.orders.{api,domain,infra}`; features talk through public services or events, not each other's repositories.
- Do use constructor injection with `final` fields (or records for simple beans); never `@Autowired` on fields or setters.
- Do use Java records for request/response DTOs, commands, events and projections.
- Don't return or accept JPA entities in controllers; map explicitly (a static `from(entity)` factory on the response record is enough).
- Do put `@Transactional` on service methods only (`readOnly = true` for queries); never on controllers or repositories you write.
- Don't use `Optional` for fields, parameters or collections; return `Optional` only from lookups.
- Do validate input with Jakarta Bean Validation (`@Valid @RequestBody`, constraints on record components).
- Do return RFC 9457 Problem Details for every error via one `@RestControllerAdvice` extending `ResponseEntityExceptionHandler`.
- Do bind config to `@ConfigurationProperties` records annotated `@Validated`, registered via `@ConfigurationPropertiesScan`.
- Do keep secrets out of `application.yml`; read them from env vars or a secret store.
- Do write schema changes as Flyway scripts in `src/main/resources/db/migration` (`V<n>__<desc>.sql`); never edit an applied migration.
- Do set `spring.jpa.hibernate.ddl-auto=validate` and `spring.jpa.open-in-view=false`.
- Do mark `@ManyToOne`/`@OneToOne` `fetch = LAZY` and fetch what a use case needs with `@EntityGraph` or a projection.
- Do enable `spring.threads.virtual.enabled=true` on Java 21+; size DB pools for the database, not the request rate.
- Do annotate each package with JSpecify `@NullMarked` in `package-info.java`.
- Do use `spring-boot-docker-compose` (dev-only) with a `compose.yaml` for local Postgres and friends.
- Do expose only `health`, `info`, `prometheus` (plus what ops asks for) over HTTP; keep `env`, `heapdump`, `loggers` off public ports.
- Do log through SLF4J with structured output: `logging.structured.format.console=ecs` (or `logstash`) outside local dev.
- Don't log secrets, tokens or full request bodies; use parameterized messages, not string concatenation.
- Do use `RestClient` (or HTTP interface clients) for outbound HTTP; never `RestTemplate` in new code.
- Do keep `@SpringBootApplication` in the root package and free of bean definitions.
- Don't catch and swallow exceptions; translate them into domain exceptions or let them reach the advice.
- Do use `Instant`/`OffsetDateTime` in UTC for timestamps and `BigDecimal` for money.
- Do note that Boot 4 ships Jackson 3 (`tools.jackson.*`); annotations stay in `com.fasterxml.jackson.annotation`.

```java
// Shape of a typical feature slice
@RestController
@RequestMapping("/api/orders")
class OrderController {
    private final OrderService orders;
    OrderController(OrderService orders) { this.orders = orders; }

    @PostMapping
    ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrderRequest req, UriComponentsBuilder uri) {
        OrderResponse created = orders.create(req);
        return ResponseEntity.created(uri.path("/api/orders/{id}").build(created.id())).body(created);
    }
}

public record CreateOrderRequest(@NotBlank String customerId, @NotEmpty List<@Valid LineItem> items) {}
```

## References

| File | Read when ... |
|---|---|
| [references/project-structure.md](references/project-structure.md) | creating a service or feature, deciding where a class goes, enforcing module boundaries, considering Spring Modulith |
| [references/rest-controllers.md](references/rest-controllers.md) | writing controllers: validation, pagination, versioning, Problem Details shape and the exception advice |
| [references/persistence-jpa.md](references/persistence-jpa.md) | designing entities and repositories, fixing N+1, projections, auditing, transactions, Flyway |
| [references/configuration.md](references/configuration.md) | adding properties, profiles, secrets, Docker Compose dev setup, virtual threads |
| [references/security-basics.md](references/security-basics.md) | protecting endpoints with JWT resource server, method security, CORS |
| [references/observability.md](references/observability.md) | Actuator exposure, Micrometer metrics, tracing, health checks, structured logging |
