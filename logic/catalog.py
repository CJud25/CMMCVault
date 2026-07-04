"""Load the control catalog and sample assessment produced by scripts/build_catalog.py."""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def load_catalog() -> tuple[dict, tuple]:
    payload = json.loads((DATA_DIR / "controls.json").read_text(encoding="utf-8"))
    return payload["meta"], tuple(payload["controls"])


def load_sample() -> dict:
    return json.loads((DATA_DIR / "sample_assessment.json").read_text(encoding="utf-8"))


def controls() -> list[dict]:
    return list(load_catalog()[1])


def meta() -> dict:
    return load_catalog()[0]


@lru_cache(maxsize=1)
def poam_rules() -> dict:
    """POA&M eligibility ruleset (32 CFR 170.21). Static reference data, like the
    catalog — consumed as a plain dict by logic/readiness.py."""
    return json.loads((DATA_DIR / "poam_eligibility.json").read_text(encoding="utf-8"))
