# Project structure

## Package by feature

One top-level package per business capability. Inside a feature, split by role only when it grows.

```text
com.acme
├── Application.java                 // @SpringBootApplication, @ConfigurationPropertiesScan
├── orders
│   ├── package-info.java            // @NullMarked
│   ├── OrderService.java            // public entry point of the feature
│   ├── api
│   │   ├── OrderController.java
│   │   ├── CreateOrderRequest.java  // record
│   │   └── OrderResponse.java       // record
│   ├── domain
│   │   ├── Order.java               // @Entity
│   │   ├── OrderLine.java
│   │   ├── OrderStatus.java
│   │   └── OrderNotFoundException.java
│   └── infra
│       ├── OrderRepository.java     // Spring Data
│       └── PaymentClient.java       // RestClient / HTTP interface
├── customers
│   └── ...
└── shared                           // small, stable, no business logic
    ├── web/GlobalExceptionHandler.java
    └── config/...
```

- `api`: HTTP adapters, DTO records, mapping. Depends on `domain` and the feature's service.
- `domain`: entities, value objects, domain exceptions, domain events. No Spring web types.
- `infra`: repositories, outbound clients, messaging adapters.
- The feature's service class sits in the feature root (or `domain`) and owns transactions.
- Small features may stay flat (all classes in `com.acme.orders`); split once a package passes roughly 10-15 classes.

## Visibility

- Default to package-private classes and constructors. Make public only what other features need (usually the service, DTO/event records and IDs).
- Controllers, repositories and mappers stay package-private where the layout allows. Spring handles package-private beans fine.
- Do not put classes in `shared` "just in case". If only one feature uses it, it belongs in that feature.

## Module boundaries

- Feature A never injects feature B's repository or entity. It calls B's public service, or reacts to B's events.
- Refer to other aggregates by ID (`UUID customerId`), not by JPA association across features.
- Cross-feature side effects (send email after order placed) go through application events: publish with `ApplicationEventPublisher`, consume with `@TransactionalEventListener` (after commit) or `@ApplicationModuleListener` if Spring Modulith is used.
- No cycles between features. Enforce with ArchUnit or Spring Modulith tests (see `spring-boot-testing`).

## Spring Modulith (optional, recommended for larger monoliths)

Spring Modulith treats each direct subpackage of the application root as an application module and verifies that other modules only use its top-level (API) package, not its internals.

- Spring Modulith 2.x is the line for Boot 4; check its compatibility matrix before adding.
- `ApplicationModules.of(Application.class).verify()` in a test fails on boundary violations and cycles.
- `@ApplicationModuleListener` = async + transactional event listener; the event publication registry (`spring-modulith-starter-jpa` or `-jdbc`) makes events survive crashes.
- `@ApplicationModuleTest` boots a single module for integration tests.
- With Modulith, internals go in subpackages (`orders.internal`, or the `api/domain/infra` split) and only the module root package is public API. Use `@NamedInterface` to expose an extra package deliberately.

## Application class

```java
@SpringBootApplication
@ConfigurationPropertiesScan
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

- No `@Bean` methods here; put them in a `@Configuration(proxyBeanMethods = false)` class in the relevant feature or `shared.config`.
- No `@EnableJpaRepositories`/`@EntityScan` unless entities live outside the root package (in Boot 4 `@EntityScan` lives in `org.springframework.boot.persistence.autoconfigure`).

## Resources layout

```text
src/main/resources
├── application.yml
├── application-local.yml      // optional, dev-only overrides
└── db/migration
    ├── V1__create_orders.sql
    └── V2__add_order_status.sql
compose.yaml                   // project root, used by spring-boot-docker-compose
```

## Multi-module builds

Prefer a single deployable module with feature packages. Split into Maven/Gradle modules only for real reuse (a published client library) or build-time isolation; packages plus ArchUnit/Modulith give boundaries without the build overhead.
