"""Workspace scan: find damage that already happened."""
import re
import unicodedata
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             ".mypy_cache", "dist", "build", ".next", "target"}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
                 ".yaml", ".yml", ".toml", ".csv", ".html", ".css", ".java",
                 ".go", ".rs", ".rb", ".sh", ".sql", ".xml", ".ini", ".cfg"}

ESCAPE_RE = re.compile(r"\\u([0-9A-Fa-f]{4})")

# Ranges that should have been written as real characters, not escapes.
CJK_RANGES = (
    (0x1100, 0x11FF),   # Hangul Jamo
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0x3130, 0x318F),   # Hangul compatibility Jamo
    (0x4E00, 0x9FFF),   # CJK unified ideographs
    (0xAC00, 0xD7A3),   # Hangul syllables
)


def _is_cjk_escape(hex4):
    cp = int(hex4, 16)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def _walk(root):
    for p in Path(root).rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def scan_replacement_char(root):
    """U+FFFD left in files = irreversible corruption."""
    out = []
    for p in _walk(root):
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "�" in text:
            out.append({"path": str(p), "count": text.count("�"),
                        "line": text[:text.index("�")].count("\n") + 1})
    return out


def scan_unicode_escapes(root):
    """Escapes where the character should have been written directly."""
    out = []
    for p in _walk(root):
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = [m for m in ESCAPE_RE.finditer(text) if _is_cjk_escape(m.group(1))]
        if hits:
            out.append({"path": str(p), "count": len(hits),
                        "line": text[:hits[0].start()].count("\n") + 1,
                        "sample": hits[0].group(0)})
    return out


def scan_normalization(root):
    """NFC/NFD mixed filenames: the agent may fail to find them."""
    nfc, nfd = [], []
    for p in _walk(root):
        name = p.name
        if not any(ord(c) > 127 for c in name):
            continue
        (nfd if unicodedata.normalize("NFC", name) != name else nfc).append(str(p))
    return {"nfc": nfc, "nfd": nfd, "mixed": bool(nfc) and bool(nfd)}


def scan_legacy_encoding(root):
    """Files that are not valid UTF-8 but decode as CP949 / EUC-KR."""
    out = []
    for p in _walk(root):
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        if not raw or b"\x00" in raw[:1024]:
            continue
        try:
            raw.decode("utf-8")
            continue
        except UnicodeDecodeError:
            pass
        for enc in ("cp949", "euc-kr"):
            try:
                text = raw.decode(enc)
            except UnicodeDecodeError:
                continue
            if any("가" <= c <= "힣" for c in text):
                out.append({"path": str(p), "encoding": enc})
                break
    return out


def run_all(root):
    return {"replacement": scan_replacement_char(root),
            "escapes": scan_unicode_escapes(root),
            "normalization": scan_normalization(root),
            "legacy": scan_legacy_encoding(root)}
