"""Onboarding flow: ordered steps, tolerant free-text parsing, and summaries.

The LLM conducts onboarding conversationally, but uses these helpers (via
`trainer_cli.py parse-onboarding`) to map a user's reply to a canonical value
before saving it, so the stored profile always matches the DB CHECK constraints.
"""
from __future__ import annotations

from models import (
    GOAL_LABELS, LOCATION_LABELS, PERSONALITY_LABELS, EQUIPMENT,
)

STEPS = ["goal", "location", "equipment", "duration", "personality", "unit"]

QUESTIONS = {
    "goal": "What's your fitness goal? (Build Muscle / Lose Weight / General Fitness / Endurance)",
    "location": "Where do you work out? (Home / Gym / Both)",
    "equipment": "What equipment can you use? (barbell, dumbbells, machines, cables, kettlebell, bands, bodyweight — list any)",
    "duration": "How long per session? (30 / 45 / 60 min / Flexible)",
    "personality": "Pick your trainer style: Motivational Coach / No-Nonsense Trainer / Science-Based",
    "unit": "Weights in pounds (lbs) or kilograms (kg)?",
}

_GOAL_KEYS = {
    "build_muscle": ["build", "muscle", "gain", "bulk", "strength", "hypertrophy"],
    "lose_weight": ["lose", "weight", "fat", "cut", "lean", "slim"],
    "endurance": ["endurance", "cardio", "stamina", "run", "marathon", "conditioning"],
    "general": ["general", "fitness", "health", "tone", "overall", "maintain"],
}
_LOCATION_KEYS = {
    "both": ["both", "either", "home and gym", "gym and home"],
    "gym": ["gym", "commercial", "fitness center"],
    "home": ["home", "house", "garage", "apartment"],
}
_PERSONALITY_KEYS = {
    "motivational": ["motiv", "coach", "hype", "energy", "encourag", "positive"],
    "nononsense": ["no-nonsense", "nonsense", "direct", "tough", "drill", "blunt", "efficient", "no fluff"],
    "science": ["science", "evidence", "explain", "why", "nerd", "data", "smart"],
}
_EQUIP_KEYS = {
    "barbell": ["barbell", "bar"],
    "dumbbells": ["dumbbell", "dumbell", "db"],
    "machines": ["machine", "selectorized", "smith"],
    "cables": ["cable", "pulley"],
    "kettlebell": ["kettlebell", "kb"],
    "bands": ["band", "resistance band"],
    "bodyweight": ["bodyweight", "body weight", "calisthenic", "none", "nothing", "no equipment"],
}


def _match(text: str, keymap: dict) -> str | None:
    t = (text or "").lower()
    for canon, keys in keymap.items():
        if any(k in t for k in keys):
            return canon
    return None


def parse_goal(text: str) -> str | None:
    return _match(text, _GOAL_KEYS)


def parse_location(text: str) -> str | None:
    return _match(text, _LOCATION_KEYS)


def parse_personality(text: str) -> str | None:
    return _match(text, _PERSONALITY_KEYS)


def parse_unit(text: str) -> str | None:
    t = (text or "").lower()
    if any(k in t for k in ["kg", "kilo", "metric"]):
        return "kg"
    if any(k in t for k in ["lb", "pound", "imperial"]):
        return "lbs"
    return None


def parse_duration(text: str) -> int | None:
    t = (text or "").lower()
    if any(k in t for k in ["flex", "any", "whatever", "varies"]):
        return 0
    for n in ("30", "45", "60"):
        if n in t:
            return int(n)
    if "half hour" in t or "half an hour" in t:
        return 30
    if "hour" in t or "hr" in t:
        return 60
    digits = "".join(c for c in t if c.isdigit())
    if digits:
        v = int(digits)
        return min((30, 45, 60), key=lambda x: abs(x - v))
    return None


def parse_equipment(text: str) -> list[str]:
    t = (text or "").lower()
    found = [canon for canon, keys in _EQUIP_KEYS.items() if any(k in t for k in keys)]
    if not found:
        return []
    # Always include bodyweight as a fallback movement source.
    if "bodyweight" not in found:
        found.append("bodyweight")
    return [e for e in EQUIPMENT if e in found]   # stable, de-duplicated order


def parse_answer(step: str, text: str):
    return {
        "goal": parse_goal, "location": parse_location, "personality": parse_personality,
        "unit": parse_unit, "duration": parse_duration, "equipment": parse_equipment,
    }[step](text)


def next_step(profile: dict | None) -> str | None:
    """Return the first step not yet captured, or None when onboarding is done."""
    p = profile or {}
    for step in STEPS:
        key = "session_duration" if step == "duration" else (
              "unit_preference" if step == "unit" else step)
        val = p.get(key)
        if step == "equipment":
            if not val:
                return step
        elif val in (None, ""):
            return step
    return None


def summary(profile: dict) -> str:
    dur = profile.get("session_duration")
    dur_label = "Flexible" if not dur else f"{dur} min"
    return (
        f"Goal: {GOAL_LABELS.get(profile.get('goal'), '?')} | "
        f"{LOCATION_LABELS.get(profile.get('location'), '?')} | "
        f"{', '.join(profile.get('equipment') or []) or 'bodyweight'} | "
        f"{dur_label} | "
        f"{PERSONALITY_LABELS.get(profile.get('personality'), '?')} | "
        f"{profile.get('unit_preference', 'lbs')}"
    )
