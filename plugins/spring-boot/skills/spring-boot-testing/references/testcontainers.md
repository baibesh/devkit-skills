# Testcontainers with Spring Boot 4

Boot 4 manages Testcontainers 2.x. In 2.x, module artifacts are prefixed `testcontainers-` and container classes moved to per-module packages (for example `org.testcontainers.postgresql.PostgreSQLContainer`, no longer generic). Older 1.x code uses `org.testcontainers.containers.PostgreSQLContainer<?>`; match whatever version the build resolves.

## Dependencies (Maven, versions from the Boot BOM)

```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-testcontainers</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>testcontainers-junit-jupiter</artifactId>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.testcontainers</groupId>
  <artifactId>testcontainers-postgresql</artifactId>
  <scope>test</scope>
</dependency>
```

Gradle: the same coordinates as `testImplementation`.

## Shared configuration

```java
package com.acme;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer(DockerImageName.parse("postgres:17-alpine"));
    }
}
```

- `@ServiceConnection` creates `JdbcConnectionDetails` (and R2DBC, Flyway uses them too) from the container; no `spring.datasource.url` needed.
- Pin the image tag to the production major version. Never `latest`.
- Spring starts the container bean before the beans that need it and stops it when the context closes. Because the context is cached across test classes, one container serves the whole suite as long as the context configuration is identical.
- Other services: `@ServiceConnection` supports Kafka, RabbitMQ, Redis (`@ServiceConnection(name = "redis")` on a `GenericContainer`), MongoDB, Elasticsearch, and more. Check the Boot reference table for the supported container types.

Use it from tests:

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfiguration.class)
@AutoConfigureRestTestClient
class OrderFlowIT { ... }

@DataJpaTest
@Import(TestcontainersConfiguration.class)
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest { ... }
```

`Replace.NONE` keeps Boot from swapping in an embedded database. Recent Boot versions already skip replacement for service-connection datasources, but being explicit is harmless and survives version differences.

## Alternative: static containers

When a test must control the container directly (for example, to stop it and test resilience), use JUnit-managed static containers:

```java
@Testcontainers
@SpringBootTest
class ResilienceIT {
    @Container
    @ServiceConnection
    static PostgreSQLContainer postgres = new PostgreSQLContainer(DockerImageName.parse("postgres:17-alpine"));
}
```

Caveat: the JUnit extension stops the container after the class while the cached Spring context may still reference it. Prefer bean-declared containers for the normal suite.

To share static containers across classes without beans, put them in an interface and use `@ImportTestcontainers(MyContainers.class)` on a `@TestConfiguration`.

## Dynamic properties for unsupported services

```java
@Bean
DynamicPropertyRegistrar mailProperties(GenericContainer<?> mailpit) {
    return registry -> {
        registry.add("spring.mail.host", mailpit::getHost);
        registry.add("spring.mail.port", () -> mailpit.getMappedPort(1025));
    };
}
```

`DynamicPropertyRegistrar` beans (Framework 6.2+) replace `@DynamicPropertySource` when the container is itself a bean. Use them only where no `@ServiceConnection` exists.

## Dev-time: run the app against containers

```java
// src/test/java/com/acme/TestApplication.java
public class TestApplication {
    public static void main(String[] args) {
        SpringApplication.from(Application::main)
                .with(TestcontainersConfiguration.class)
                .run(args);
    }
}
```

Run `TestApplication` from the IDE, or `./mvnw spring-boot:test-run` / `./gradlew bootTestRun`. This is an alternative to `spring-boot-docker-compose`; pick one per project.

## Container reuse (local only)

- Faster local loops: set `testcontainers.reuse.enable=true` in `~/.testcontainers.properties` and call `.withReuse(true)` on the container. The container survives JVM exits.
- Reused containers keep data between runs, so tests must not depend on an empty database (see test-data.md).
- Never rely on reuse in CI; CI gets fresh containers. Reuse is ignored unless the user-level property is set, so leaving `.withReuse(true)` in code is safe.

## Performance and CI

- One context, one set of containers: keep the same `@Import(TestcontainersConfiguration.class)` and same mocks across integration tests so Spring's context cache hits.
- Separate slow tests by naming (`*IT` run by Failsafe / a dedicated Gradle task) if the team wants fast `test` and full `verify`.
- CI needs a Docker-compatible runtime (GitHub Actions `ubuntu-latest` has Docker). Testcontainers Cloud or a remote Docker host also works.
- Ryuk (the reaper container) cleans up after crashed runs; do not disable it unless the CI environment forbids privileged containers.
- Startup checks: the Postgres module waits for the "ready to accept connections" log line; for `GenericContainer` add `.waitingFor(Wait.forListeningPort())` or an HTTP wait strategy.
