# Configuration

## Typed properties

```java
@ConfigurationProperties(prefix = "app.orders")
@Validated
public record OrdersProperties(
        @NotNull Duration paymentTimeout,
        @Min(1) @Max(1000) int maxLines,
        @NotNull URI paymentBaseUrl,
        @DefaultValue("true") boolean notificationsEnabled) {}
```

```yaml
app:
  orders:
    payment-timeout: 5s
    max-lines: 200
    payment-base-url: ${PAYMENT_BASE_URL:http://localhost:8081}
```

- One record per concern, prefix `app.<feature>`. Registered by `@ConfigurationPropertiesScan` on the application class.
- `@Validated` + Jakarta constraints make the app fail fast at startup on bad config.
- Use `Duration`, `DataSize`, `URI`, enums, nested records; Boot converts `5s`, `10MB` etc.
- `@DefaultValue` on a record component supplies defaults (`org.springframework.boot.context.properties.bind.DefaultValue`).
- Inject the record into the beans that need it; never use `@Value("${...}")` scattered across classes, and never `Environment.getProperty` in business code.
- Add `spring-boot-configuration-processor` (annotation processor, optional) for IDE metadata.

## application.yml layout

- One `application.yml` with production-safe defaults. Values that differ per environment come from env vars (`${DB_URL}`), not from per-environment files checked into the repo.
- `application-local.yml` (or a `local` profile) for developer convenience only. Never ship `-prod` profiles containing secrets.
- Profiles are for wiring differences (`local`, `test`), not for feature flags. Feature flags go in properties records.
- Activate via `SPRING_PROFILES_ACTIVE`; avoid `spring.profiles.active` in the packaged `application.yml`.
- Relaxed binding: `app.orders.max-lines` maps to env var `APP_ORDERS_MAXLINES`.

## Secrets

- Never commit secrets, including in `application-local.yml`. Use env vars, a mounted secret file (`spring.config.import=configtree:/run/secrets/`), or a secret manager integration (Vault, AWS/GCP/Azure secret managers via Spring Cloud).
- Do not log configuration objects that contain secrets; exclude them from `toString()` of properties records by overriding it, or keep secrets in a separate record.
- Actuator `/env` and `/configprops` mask values by default (`management.endpoint.env.show-values=never`); keep it that way.

## Local development with Docker Compose

Add the dev-only dependency:

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-docker-compose</artifactId>
  <scope>runtime</scope>
  <optional>true</optional>
</dependency>
```

(Gradle: `developmentOnly("org.springframework.boot:spring-boot-docker-compose")`.)

```yaml
# compose.yaml in the project root
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: orders
      POSTGRES_USER: orders
      POSTGRES_PASSWORD: orders
    ports:
      - "5432"
```

- On `bootRun`/`spring-boot:run` Boot starts the services and creates connection details automatically; no datasource URL needed locally.
- Lifecycle: `spring.docker.compose.lifecycle-management=start-only` keeps containers between restarts.
- Docker Compose support is skipped in tests by default; tests use Testcontainers (see `spring-boot-testing`).
- Alternative: a `TestApplication` main in `src/test` that runs the app with Testcontainers (`SpringApplication.from(Application::main).with(TestcontainersConfiguration.class)`). Pick one per project.

## Virtual threads

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

- Requires Java 21+. Tomcat request handling, `@Async`, scheduling and several clients switch to virtual threads.
- Do not pool virtual threads or size thread pools for concurrency; limit concurrency with the DB connection pool or a `Semaphore`.
- The connection pool (HikariCP `maximum-pool-size`) becomes the real bottleneck; size it for the database.
- On Java 21-23, `synchronized` blocks around blocking I/O pin the carrier thread; prefer `ReentrantLock` there. Java 24+ (JEP 491) removes most pinning.
- Keep `ThreadLocal` usage small; virtual threads are numerous.

## Null-safety with JSpecify

Spring Framework 7 and Boot 4 APIs are annotated with JSpecify. Do the same in application code:

```java
// src/main/java/com/acme/orders/package-info.java
@NullMarked
package com.acme.orders;

import org.jspecify.annotations.NullMarked;
```

- In `@NullMarked` code everything is non-null unless annotated `@Nullable` (`org.jspecify.annotations.Nullable`).
- Type-use placement: `private @Nullable String note;`, `List<@Nullable String>`, `String @Nullable []`.
- Optional enforcement at build time: Error Prone + NullAway in JSpecify mode. IDEs (IntelliJ) understand the annotations without it.
- Remove `javax.annotation`/`org.springframework.lang.Nullable` usages in new code; Spring's own annotations are deprecated in favour of JSpecify.

## Bean configuration

- `@Configuration(proxyBeanMethods = false)` unless one `@Bean` method must call another.
- Conditional beans: `@ConditionalOnProperty(prefix = "app.orders", name = "notifications-enabled")`.
- Outbound HTTP: build `RestClient` from the auto-configured `RestClient.Builder` so observability and message converters apply; set base URL and timeouts from properties records. Declarative clients: `@HttpExchange` interfaces (Framework 7 adds `@ImportHttpServices` for registering groups of them).
