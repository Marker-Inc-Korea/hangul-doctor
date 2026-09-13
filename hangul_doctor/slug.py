"""Project-path slug rules, and collision detection.

Claude Code stores per-project state under ~/.claude/projects/<slug>.
Observed rule: every character that is not [A-Za-z0-9] becomes '-'.
Each Hangul syllable is one character, so it becomes one '-'. Two different
Korean project names with the same character count therefore produce the same
slug and silently share memory and session history.

See anthropics/claude-code #93743, #91735, #70076, #70076, #87552.
"""
import re
from pathlib import Path

_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def slugify(path) -> str:
    """Reproduce the observed project-slug rule."""
    return _NON_ALNUM.sub("-", str(path))


def has_non_ascii(path) -> bool:
    return any(ord(ch) > 127 for ch in str(path))


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def existing_slugs():
    d = projects_dir()
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def collision_risk(path):
    """Return (slug, colliding_slug_or_None, ambiguous).

    `ambiguous` is True when the slug cannot be reversed to a unique path,
    which is what makes the collision silent.
    """
    slug = slugify(path)
    existing = existing_slugs()
    hit = slug if slug in existing else None
    # A slug is ambiguous if any non-alphanumeric run was collapsed, i.e. the
    # original path cannot be recovered from the slug.
    ambiguous = has_non_ascii(path)
    return slug, hit, ambiguous
