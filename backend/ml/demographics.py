import json
import os
from functools import lru_cache

INCOME_LEVEL_MAP = {"low": 0, "mid": 1, "high": 2}


@lru_cache(maxsize=1)
def load_demographics() -> dict:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "district_demographics.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw["districts"]


def features_for(district_name: str) -> dict:
    """Return numeric features for a district. Falls back to averages if missing."""
    demos = load_demographics()
    d = demos.get(district_name)
    if d is None:
        # average fallback so the model still runs on unknown districts
        all_d = list(demos.values())
        d = {
            "population": sum(x["population"] for x in all_d) / len(all_d),
            "households": sum(x["households"] for x in all_d) / len(all_d),
            "area_sqkm": sum(x["area_sqkm"] for x in all_d) / len(all_d),
            "commercial_index": sum(x["commercial_index"] for x in all_d) / len(all_d),
            "income_level": "mid",
        }
    pop = float(d["population"])
    area = float(d["area_sqkm"])
    return {
        "population": pop,
        "households": float(d["households"]),
        "area_sqkm": area,
        "population_density": pop / area if area else 0.0,
        "commercial_index": float(d["commercial_index"]),
        "income_level_encoded": float(INCOME_LEVEL_MAP.get(d["income_level"], 1)),
    }


def area_sqkm(district_name: str) -> float:
    demos = load_demographics()
    d = demos.get(district_name)
    if d is None:
        return 20.0  # avg fallback
    return float(d["area_sqkm"])


def population(district_name: str) -> int:
    demos = load_demographics()
    d = demos.get(district_name)
    if d is None:
        return 80000
    return int(d["population"])
