"""Load the known-issue dictionary."""
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "issues.json"


def load():
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)


def issues():
    return load()["issues"]


def meta():
    return load()["_meta"]
