"""Domain model: constants, dataclasses, and unit conversion for Open-Trainer.

Pure stdlib — safe to import anywhere (engine, CLI, tests) without network or
third-party dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Enumerations (kept as plain strings to match the DB CHECK constraints)
# --------------------------------------------------------------------------- #
GOALS = ("build_muscle", "lose_weight", "general", "endurance")
LOCATIONS = ("home", "gym", "both")
PERSONALITIES = ("motivational", "nononsense", "science")
UNITS = ("kg", "lbs")
EQUIPMENT = ("barbell", "dumbbells", "machines", "cables", "bodyweight", "kettlebell", "bands")
SPLITS = ("push", "pull", "legs", "upper", "lower", "full")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Human-readable labels for Telegram menus / summaries.
GOAL_LABELS = {
    "build_muscle": "Build Muscle",
    "lose_weight": "Lose Weight",
    "general": "General Fitness",
    "endurance": "Endurance",
}
LOCATION_LABELS = {"home": "Home", "gym": "Gym", "both": "Both"}
PERSONALITY_LABELS = {
    "motivational": "Motivational Coach",
    "nononsense": "No-Nonsense Trainer",
    "science": "Science-Based",
}

LBS_PER_KG = 2.2046226218


# --------------------------------------------------------------------------- #
# Unit conversion / formatting
# --------------------------------------------------------------------------- #
def to_kg(value: float, unit: str) -> float:
    """Convert a user-entered weight to kilograms (canonical storage unit)."""
    if value is None:
        return None
    return round(float(value) / LBS_PER_KG, 2) if unit == "lbs" else round(float(value), 2)


def from_kg(weight_kg: float, unit: str) -> float:
    """Convert a stored kg weight to the user's display unit."""
    if weight_kg is None:
        return None
    if unit == "lbs":
        # Round to the nearest 0.5 lb for clean display.
        return round(float(weight_kg) * LBS_PER_KG * 2) / 2
    return round(float(weight_kg), 1)


def format_weight(weight_kg: float, unit: str) -> str:
    """Render a stored kg weight in the user's unit, e.g. '135 lbs'."""
    if weight_kg is None:
        return "bodyweight"
    val = from_kg(weight_kg, unit)
    if float(val).is_integer():
        val = int(val)
    return f"{val} {unit}"


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class Exercise:
    """A library exercise the engine can program."""

    name: str
    exercise_type: str            # strength | cardio | bodyweight
    primary_muscle: str
    equipment: tuple = ()         # any-of equipment that can perform it
    movement_pattern: str = ""    # squat|hinge|push_h|push_v|pull_h|pull_v|lunge|core|cardio
    split: str = ""               # push|pull|legs|core|cardio
    is_compound: bool = False
    default_sets: int = 3
    default_reps: int = 10
    secondary_muscles: tuple = ()
    instructions: str = ""

    def usable_with(self, available: set) -> bool:
        """True if any required equipment is available (bodyweight always ok)."""
        if "bodyweight" in self.equipment:
            return True
        return bool(set(self.equipment) & available)


@dataclass
class PlannedExercise:
    name: str
    target_sets: int
    target_reps: int
    target_weight_kg: float | None = None   # suggested working weight (None = judge by feel)
    exercise_type: str = "strength"
    target_muscle_group: str = ""
    notes: str = ""
    sort_order: int = 0


@dataclass
class PlannedWorkout:
    name: str
    focus: str                                  # push|pull|legs|upper|lower|full
    exercises: list = field(default_factory=list)   # list[PlannedExercise]
    rationale: str = ""                         # why this session was chosen
