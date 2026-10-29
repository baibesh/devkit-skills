#!/usr/bin/env python3
"""Structural checks for skills and marketplace manifests. Exits 1 on any error."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_ONLY_KEYS = {
    "argument-hint", "user-invocable", "disable-model-invocation", "context",
    "paths", "hooks", "model", "effort", "agent", "when_to_use",
}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BODY_MAX, BODY_WARN, REF_MAX = 500, 300, 400

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def split_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 4:].lstrip("\n")


def check_links(path: Path, text: str, skill_dir: Path) -> None:
    # Strip fenced code so example links in snippets are not checked.
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        target = target.split("#", 1)[0]
        if ".." in Path(target).parts:
            err(f"{path}: link escapes skill dir: {target}")
            continue
        if not (path.parent / target).resolve().is_relative_to(skill_dir.resolve()):
            err(f"{path}: link escapes skill dir: {target}")
        elif not (path.parent / target).exists():
            err(f"{path}: broken link: {target}")


def check_skill(skill_md: Path) -> str | None:
    rel = skill_md.relative_to(ROOT)
    skill_dir = skill_md.parent
    raw_fm, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if raw_fm is None:
        err(f"{rel}: missing frontmatter")
        return None
    try:
        fm = yaml.safe_load(raw_fm)
    except yaml.YAMLError as e:
        err(f"{rel}: frontmatter is not valid YAML: {e}")
        return None
    if not isinstance(fm, dict):
        err(f"{rel}: frontmatter is not a mapping")
        return None

    name = fm.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
        err(f"{rel}: invalid name {name!r}")
    elif name != skill_dir.name:
        err(f"{rel}: name {name!r} != directory {skill_dir.name!r}")

    desc = fm.get("description")
    if not isinstance(desc, str) or not 1 <= len(desc) <= 1024:
        err(f"{rel}: description must be 1-1024 chars")
    elif "use when" not in desc.lower():
        err(f"{rel}: description must contain 'Use when'")

    if fm.get("license") != "MIT":
        err(f"{rel}: license must be MIT")
    for key in fm:
        if key in CLAUDE_ONLY_KEYS:
            warn(f"{rel}: Claude-only frontmatter key {key!r}")
        elif key not in SPEC_KEYS:
            err(f"{rel}: unknown frontmatter key {key!r}")

    lines = body.count("\n") + 1
    if lines > BODY_MAX:
        err(f"{rel}: body has {lines} lines (max {BODY_MAX})")
    elif lines > BODY_WARN:
        warn(f"{rel}: body has {lines} lines (aim for <= 250)")
    check_links(skill_md, body, skill_dir)

    for ref in sorted(skill_dir.glob("references/**/*.md")):
        text = ref.read_text(encoding="utf-8")
        n = text.count("\n") + 1
        if n > REF_MAX:
            err(f"{ref.relative_to(ROOT)}: {n} lines (max {REF_MAX})")
        check_links(ref, text, skill_dir)
    return name if isinstance(name, str) else None


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        err(f"{path.relative_to(ROOT)}: {e}")
        return None


def check_plugins() -> dict[str, list[str]]:
    """Returns plugin name -> skill dir names."""
    found: dict[str, list[str]] = {}
    for pdir in sorted(p for p in (ROOT / "plugins").iterdir() if p.is_dir()):
        rel = pdir.relative_to(ROOT)
        claude = load_json(pdir / ".claude-plugin" / "plugin.json")
        codex = load_json(pdir / ".codex-plugin" / "plugin.json")
        if claude:
            if claude.get("name") != pdir.name:
                err(f"{rel}: plugin.json name != directory")
            for key in ("version", "description", "license"):
                if not claude.get(key):
                    err(f"{rel}: plugin.json missing {key}")
            if not (claude.get("author") or {}).get("name"):
                err(f"{rel}: plugin.json missing author.name")
        if claude and codex and (codex.get("name"), codex.get("version")) != (claude.get("name"), claude.get("version")):
            err(f"{rel}: .codex-plugin/plugin.json name/version differ from .claude-plugin")
        for forbidden in ("CLAUDE.md", "bin", "package.json"):
            if (pdir / forbidden).exists():
                err(f"{rel}: {forbidden} not allowed at plugin root")
        found[pdir.name] = sorted(d.name for d in (pdir / "skills").iterdir() if d.is_dir()) if (pdir / "skills").is_dir() else []
    return found


def check_marketplaces(own: dict[str, list[str]], skill_names: set[str]) -> None:
    mp = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    names: set[str] = set()
    if mp:
        if mp.get("name") != "devkit-skills":
            err("marketplace.json: name must be devkit-skills")
        for entry in mp.get("plugins", []):
            n = entry.get("name")
            if n in names:
                err(f"marketplace.json: duplicate entry {n}")
            names.add(n)
            if "version" in entry:
                err(f"marketplace.json: entry {n} must not set version")
            src = entry.get("source")
            skills = entry.get("skills", [])
            if isinstance(src, str):
                pdir = (ROOT / src).resolve()
                if not pdir.is_dir():
                    err(f"marketplace.json: {n}: source {src} missing")
                    continue
                if pdir.name != n:
                    err(f"marketplace.json: {n}: entry name != plugin dir")
                for s in skills:
                    if not (pdir / s / "SKILL.md").is_file():
                        err(f"marketplace.json: {n}: skill path {s} has no SKILL.md")
                listed = {Path(s).name for s in skills}
                for s in own.get(pdir.name, []):
                    if s not in listed:
                        err(f"marketplace.json: {n}: skill {s} not listed in entry skills")
            elif isinstance(src, dict):
                if src.get("source") not in {"github", "git-subdir", "url"}:
                    err(f"marketplace.json: {n}: unsupported source {src.get('source')}")
                for s in skills:
                    if not s.startswith("./") or ".." in s:
                        err(f"marketplace.json: {n}: bad skill path {s}")
            else:
                err(f"marketplace.json: {n}: missing source")

    codex = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    if codex:
        for entry in codex.get("plugins", []):
            path = (entry.get("source") or {}).get("path", "")
            if not (ROOT / path).is_dir():
                err(f".agents/plugins/marketplace.json: {entry.get('name')}: path {path} missing")
            if entry.get("name") not in names:
                err(f".agents/plugins/marketplace.json: {entry.get('name')} not in Claude marketplace")

    sh = load_json(ROOT / "skills.sh.json")
    if sh:
        for p in sh.get("paths", []):
            if not (ROOT / p).is_dir():
                err(f"skills.sh.json: path {p} missing")
        for g in sh.get("groupings", []):
            for s in g.get("skills", []):
                if s not in skill_names:
                    err(f"skills.sh.json: grouping skill {s} not found")


def run() -> int:
    own = check_plugins()
    skill_names: set[str] = set()
    for skill_md in sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")):
        name = check_skill(skill_md)
        if name in skill_names:
            err(f"{skill_md.relative_to(ROOT)}: duplicate skill name {name}")
        if name:
            skill_names.add(name)
    for plugin, skills in own.items():
        for s in skills:
            if not (ROOT / "plugins" / plugin / "skills" / s / "SKILL.md").is_file():
                err(f"plugins/{plugin}/skills/{s}: missing SKILL.md")
    check_marketplaces(own, skill_names)

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(skill_names)} skills, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def self_test() -> int:
    fm, body = split_frontmatter("---\nname: a\n---\nbody\n")
    assert fm == "name: a" and body == "body\n"
    assert split_frontmatter("no frontmatter")[0] is None
    assert NAME_RE.match("spring-boot-testing")
    for bad in ("Spring", "a--b", "-a", "a-", "a_b"):
        assert not NAME_RE.match(bad), bad
    assert LINK_RE.findall("see [x](references/a.md) and [y](https://e.com)") == ["references/a.md", "https://e.com"]
    print("self-test ok")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else run())
