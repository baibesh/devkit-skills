# Security basics

Boot 4 ships Spring Security 7: lambda DSL only (the `and()` chaining style is gone), `authorizeHttpRequests` only.

Starters: `spring-boot-starter-security`, and for JWT APIs `spring-boot-starter-security-oauth2-resource-server` (the old `spring-boot-starter-oauth2-resource-server` name is deprecated in Boot 4).

## Resource server with JWT

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: ${OIDC_ISSUER_URI}   # discovers JWKS, validates iss and exp
          audiences: orders-api             # validates aud
```

```java
@Configuration(proxyBeanMethods = false)
@EnableMethodSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable()) // stateless bearer-token API, no cookies
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**", "/actuator/info").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/catalog/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()));
        return http.build();
    }

    @Bean
    JwtAuthenticationConverter jwtAuthenticationConverter() {
        var authorities = new JwtGrantedAuthoritiesConverter();
        authorities.setAuthoritiesClaimName("roles");
        authorities.setAuthorityPrefix("ROLE_");
        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(authorities);
        return converter;
    }
}
```

- Deny by default: end with `.anyRequest().authenticated()` (or `denyAll()`), and list public paths explicitly.
- Keep CSRF enabled for browser apps that use session cookies; disabling it is only correct for stateless bearer-token APIs.
- Map the IdP's role/scope claim with a `JwtAuthenticationConverter` bean; scopes map to `SCOPE_x` authorities by default.
- 401/403 responses: Spring Security writes them before MVC, so the `@RestControllerAdvice` does not see them. If clients need Problem Details there too, configure an `AuthenticationEntryPoint` / `AccessDeniedHandler` that writes `application/problem+json`.
- Never roll your own JWT parsing or signature checking.

## Method security

```java
@Service
@Transactional(readOnly = true)
public class OrderService {

    @PreAuthorize("hasRole('ADMIN') or #customerId == authentication.name")
    public List<OrderSummary> ordersOf(String customerId) { ... }
}
```

- `@EnableMethodSecurity` enables `@PreAuthorize`/`@PostAuthorize`.
- URL rules for coarse access, method security for ownership and business rules.
- For non-trivial checks, call a bean: `@PreAuthorize("@orderAccess.canView(#id, authentication)")`.
- Current user in code: inject `@AuthenticationPrincipal Jwt jwt` in controllers and pass the needed values (user ID) into services as parameters, rather than reading `SecurityContextHolder` deep in the domain.

## CORS

```java
@Bean
CorsConfigurationSource corsConfigurationSource(CorsProperties props) {
    var config = new CorsConfiguration();
    config.setAllowedOrigins(props.allowedOrigins());       // exact origins from config
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE"));
    config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
    config.setMaxAge(Duration.ofHours(1));
    var source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", config);
    return source;
}
```

and `http.cors(Customizer.withDefaults())` in the filter chain so preflight requests are handled before authentication.

- Never `allowedOrigins("*")` together with credentials. List origins per environment in a properties record.
- Prefer configuring CORS once here instead of `@CrossOrigin` on controllers.

## Other basics

- Passwords (if the service stores any): `PasswordEncoderFactories.createDelegatingPasswordEncoder()`.
- Secrets and keys come from configuration, never source code (see configuration.md).
- Actuator: expose management endpoints on a separate port (`management.server.port`) or protect them with a dedicated filter chain.
- Validate and bound all input (sizes, page sizes, upload limits) to limit abuse.
- Security headers (HSTS, X-Content-Type-Options, frame options) are on by default; do not disable them globally.
- Testing secured endpoints: `spring-boot-starter-security-test` gives `@WithMockUser` and `jwt()` request post-processors (see `spring-boot-testing`).
