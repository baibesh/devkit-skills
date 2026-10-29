# springdoc-openapi setup and spec export

springdoc-openapi 3.x is the line for Spring Boot 4 / Spring Framework 7 (2.x targets Boot 3).
Check the current release on <https://springdoc.org> before pinning; do not downgrade an existing version.

## Dependency

Spring MVC (servlet) with Swagger UI:

```xml
<dependency>
  <groupId>org.springdoc</groupId>
  <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
  <version>${springdoc.version}</version>
</dependency>
```

Without UI (spec only): `springdoc-openapi-starter-webmvc-api`.
WebFlux: `springdoc-openapi-starter-webflux-ui` / `-webflux-api`.

Gradle: `implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:$springdocVersion")`.

## Configuration

```yaml
springdoc:
  api-docs:
    path: /v3/api-docs            # default
  writer-with-order-by-keys: true # deterministic output, stable diffs
  default-produces-media-type: application/json
  swagger-ui:
    enabled: true                 # disable or secure in prod profiles
```

Global metadata in one bean, not scattered across controllers:

```java
@Configuration
class OpenApiConfig {
    @Bean
    OpenAPI apiInfo() {
        return new OpenAPI()
            .info(new Info().title("Orders API").version("1"))
            .components(new Components().addSecuritySchemes("bearer",
                new SecurityScheme().type(SecurityScheme.Type.HTTP).scheme("bearer").bearerFormat("JWT")))
            .addSecurityItem(new SecurityRequirement().addList("bearer"));
    }
}
```

Do not put an environment-specific server URL in the committed spec; clients set the base URL at runtime.
If springdoc infers a localhost `servers` entry, override with a relative server (`new Server().url("/")`) so the exported file is identical on every machine.

## Annotating the contract

- `@Tag(name = "orders")` per controller; tags group generated services/functions.
- `@Operation(operationId = "getOrder", summary = "...")` for a stable, unique operationId. Without it springdoc derives one from the method name and may append `_1` on collisions.
- `@ApiResponse(responseCode = "404", content = @Content(mediaType = "application/problem+json", schema = @Schema(implementation = ProblemDetail.class)))` for documented errors. Prefer a reusable `@ApiResponses` meta-annotation or an `OperationCustomizer` that adds the standard 400/401/403/404/409/500 responses.
- Records: Bean Validation annotations (`@NotNull`, `@Size`, `@Pattern`, `@Min`) are reflected in the schema. Use `@Schema(requiredMode = Schema.RequiredMode.REQUIRED)` where validation does not imply it.
- Enums: `@Schema(enumAsRef = true)` makes the enum a named component instead of inlined strings, so generated clients get one reusable type.
- Hide internal endpoints with `@Hidden` or restrict scanning with `springdoc.paths-to-match` / `springdoc.packages-to-scan`.

## Exporting the spec

Commit the result as `api/openapi.json` (repo root, or `<backend>/api/openapi.json` in a mono-repo; pick one and document it).

### Option A: build-time Maven plugin

`springdoc-openapi-maven-plugin` calls the running app during `integration-test`, so `spring-boot-maven-plugin` must start and stop it:

```xml
<plugin>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-maven-plugin</artifactId>
  <configuration>
    <jvmArguments>-Dspring.application.admin.enabled=true</jvmArguments>
  </configuration>
  <executions>
    <execution><id>pre-integration-test</id><goals><goal>start</goal></goals></execution>
    <execution><id>post-integration-test</id><goals><goal>stop</goal></goals></execution>
  </executions>
</plugin>
<plugin>
  <groupId>org.springdoc</groupId>
  <artifactId>springdoc-openapi-maven-plugin</artifactId>
  <version>${springdoc-maven-plugin.version}</version>
  <executions>
    <execution><id>integration-test</id><goals><goal>generate</goal></goals></execution>
  </executions>
  <configuration>
    <apiDocsUrl>http://localhost:8080/v3/api-docs</apiDocsUrl>
    <outputFileName>openapi.json</outputFileName>
    <outputDir>${project.basedir}/../api</outputDir>
    <failOnError>true</failOnError>
  </configuration>
</plugin>
```

Run with `mvn verify`. Downsides: the app must boot with all its infrastructure (database, broker). Use a dedicated profile with in-memory or Testcontainers-backed dependencies, or prefer option B.
For Gradle, the equivalent is the `org.springdoc.openapi-gradle-plugin` (`generateOpenApiDocs` task).

### Option B: test that writes the spec (recommended)

Reuses the existing test context (Testcontainers, mocks) and runs on every `mvn test`:

```java
@SpringBootTest
@AutoConfigureMockMvc
class OpenApiSpecExportTest {

    @Autowired MockMvc mvc;

    @Test
    void exportSpec() throws Exception {
        String json = mvc.perform(get("/v3/api-docs"))
            .andExpect(status().isOk())
            .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        Path out = Path.of("..", "api", "openapi.json"); // adjust to repo layout
        Files.createDirectories(out.getParent());
        Files.writeString(out, prettyPrint(json) + "\n");
    }
}
```

- In Spring Boot 4, `@AutoConfigureMockMvc` lives in `org.springframework.boot.webmvc.test.autoconfigure`, and `@SpringBootTest` no longer configures MockMvc without it. Detect the project's import style.
- Pretty-print with the project's `JsonMapper`/`ObjectMapper` (`INDENT_OUTPUT`) so diffs are line-based.
- `MockMvcTester` (AssertJ style) works equally; follow `spring-boot-testing`.
- CI then checks `git diff --exit-code api/openapi.json`: if the test regenerated a different file, the developer forgot to commit it.

## Security and profiles

- Permit `/v3/api-docs/**` and `/swagger-ui/**` only where intended (dev, staging, or authenticated).
- In production either disable (`springdoc.api-docs.enabled=false`, `springdoc.swagger-ui.enabled=false`) or protect them.
- The export test must not depend on real credentials; use the test security configuration.

## Common pitfalls

- Spec differs between machines: missing `writer-with-order-by-keys`, a host-specific `servers` URL, or non-deterministic map ordering in examples.
- Every field optional in TypeScript: required-ness not declared on the DTO.
- `Object`/`Map` return types: generated as `unknown`/`Record<string, unknown>`; introduce a record.
- Generic wrappers (`ApiResponse<T>`): springdoc names schemas like `ApiResponseOrderDto`; acceptable, but prefer plain DTOs plus HTTP status codes and Problem Details.
- Jackson config (naming strategy, `WRITE_DATES_AS_TIMESTAMPS`) changes runtime JSON but springdoc reflects only part of it; keep Jackson defaults (camelCase, ISO dates) and verify with a test.
