# Contributing

## Adding or changing a skill

1. Copy `templates/SKILL.template.md` to `plugins/<plugin>/skills/<skill-name>/SKILL.md`.
2. Follow the authoring standard below.
3. Register a new skill in the plugin's `skills` array in `.claude-plugin/marketplace.json` and in `skills.sh.json` groupings.
4. Bump `version` in both `plugins/<plugin>/.claude-plugin/plugin.json` and `plugins/<plugin>/.codex-plugin/plugin.json` (same value) and add a `CHANGELOG.md` entry.
5. Run the local checks.

## Authoring standard

- `name` equals the directory name: kebab-case, at most 64 characters, unique across the repo and prefixed with its domain (`spring-boot-*`, `frontend-*`). `npx skills` flattens all skills into one folder, so names must not collide.
- `description`: one paragraph, at most 1024 characters, formula "What it does (with concrete keywords). Use when <triggers>. Not for <anti-trigger> (see <sibling>)." It must contain "Use when". Put the main use case first.
- Frontmatter keys: `name`, `description`, `license: MIT`, `metadata.author: baibesh/devkit-skills`. Optional spec keys: `compatibility`, `allowed-tools`. Claude-only keys (`argument-hint`, `user-invocable`, `disable-model-invocation`, `context`, `paths`, `hooks`, `model`, `effort`) raise a CI warning; justify them in the PR. Quote YAML values containing `[ ] : # | >`.
- SKILL.md body: aim for 250 lines; over 300 warns, over 500 fails.
- `references/*.md`: one topic per file, at most 400 lines, linked from SKILL.md with a "read when" sentence. Links are relative, one level deep, no `..`.
- Open every skill with version targets and an instruction to detect the project's real versions first.
- Current targets: Angular 20+ (22.x), React 19, Next.js 16, Spring Boot 4.x, Java 21 or 25, springdoc-openapi 3.x.
- Do not duplicate upstream skills (Angular, React, Next.js, sivalabs). Refer to them by name.
- No scripts inside skills for now.

## Third-party sources

A source qualifies if it is official, or has 200+ stars and a push within the last 6 months, under MIT, Apache-2.0 or BSD. Reference it from `marketplace.json` (`github` or `git-subdir`); do not vendor. Vendoring needs the upstream LICENSE copied into the skill directory and a line in the README credits table.

## Local checks

```sh
pip install pyyaml
python3 scripts/validate_skills.py
claude plugin validate --strict .
for d in plugins/*/; do claude plugin validate --strict "$d"; done
```

Try your change in Claude Code:

```sh
claude plugin marketplace add "$PWD"
claude plugin install <plugin>@devkit-skills
# in a session: /reload-plugins, then check /skills
claude plugin marketplace remove devkit-skills
```

## Commits

Conventional Commits in English: `feat(spring-boot): add flyway skill`, `fix(api-contract): correct springdoc coordinates`.
