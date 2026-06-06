"""Workout engine — deterministic programming logic.

Responsibilities (no LLM, no network — fully unit-testable):
  * recommend the next session focus from history + goal (split rotation)
  * build a planned session sized to the user's available equipment & duration
  * apply linear progression / deload to each exercise from past performance

History is a list of workout dicts (most recent first), shaped like Supabase rows:

    {
      "focus": "push", "status": "completed", "date": "2026-06-02",
      "exercises": [
        {"name": "Barbell Bench Press", "target_reps": 8,
         "sets": [{"reps": 8, "weight_kg": 61.2, "completed": True}, ...]},
        ...
      ],
    }
"""
from __future__ import annotations

from exercises import for_split, available_equipment
from models import PlannedExercise, PlannedWorkout

# Linear-progression increments, in kilograms.
COMPOUND_INC_KG = 2.5      # ≈ 5 lb jump on big lifts
ACCESSORY_INC_KG = 1.25    # ≈ 2.5 lb jump on isolation work
DELOAD_FACTOR = 0.9        # 10% back-off after repeated misses

# Per-goal rotation of session focuses.
ROTATIONS = {
    "build_muscle": ["push", "pull", "legs"],
    "general": ["upper", "lower"],
    "lose_weight": ["full", "cardio"],
    "endurance": ["cardio", "full"],
}

# Which library splits feed each focus.
FOCUS_SOURCES = {
    "push": ["push"],
    "pull": ["pull"],
    "legs": ["legs"],
    "upper": ["push", "pull"],
    "lower": ["legs"],
    "full": ["legs", "push", "pull"],
    "cardio": ["cardio"],
}

FOCUS_LABELS = {
    "push": "Push Day", "pull": "Pull Day", "legs": "Leg Day",
    "upper": "Upper Body", "lower": "Lower Body", "full": "Full Body",
    "cardio": "Conditioning",
}

# Exercise count by session duration (minutes); 0 = flexible.
def _exercise_count(duration: int) -> int:
    return {30: 4, 45: 5, 60: 6, 0: 5}.get(duration or 0, 5)


def rep_scheme(goal: str, is_compound: bool) -> tuple[int, int]:
    """Return (sets, reps) for the goal and exercise role."""
    if goal == "build_muscle":
        return (4, 8) if is_compound else (3, 12)
    if goal == "lose_weight":
        return (3, 15)
    if goal == "endurance":
        return (3, 20) if not is_compound else (3, 15)
    # general fitness
    return (3, 10) if is_compound else (3, 12)


def last_completed_focus(history: list[dict]) -> str | None:
    for w in history:
        if w.get("status") == "completed" and w.get("focus"):
            return w["focus"]
    return None


def recommend_focus(goal: str, history: list[dict]) -> str:
    """Next focus = the one after the last completed session in the rotation."""
    rotation = ROTATIONS.get(goal, ROTATIONS["general"])
    last = last_completed_focus(history)
    if last in rotation:
        return rotation[(rotation.index(last) + 1) % len(rotation)]
    return rotation[0]


def exercise_history(history: list[dict], name: str) -> list[dict]:
    """Per-session performance summaries for an exercise, most recent first.

    Each entry: {weight_kg, top_reps, target_reps, hit} where `hit` means the
    minimum reps across the heaviest sets met the target.
    """
    out = []
    for w in history:
        for ex in w.get("exercises", []):
            if ex.get("name") != name:
                continue
            sets = [s for s in ex.get("sets", []) if s.get("completed", True)]
            weighted = [s for s in sets if s.get("weight_kg") is not None]
            target = ex.get("target_reps") or 0
            if weighted:
                top_weight = max(s["weight_kg"] for s in weighted)
                reps_at_top = [s.get("reps") or 0 for s in weighted if s["weight_kg"] == top_weight]
                top_reps = min(reps_at_top) if reps_at_top else 0
                out.append({
                    "weight_kg": top_weight, "top_reps": top_reps,
                    "target_reps": target, "hit": target and top_reps >= target,
                })
            elif sets:  # bodyweight / unweighted
                top_reps = max((s.get("reps") or 0) for s in sets)
                out.append({
                    "weight_kg": None, "top_reps": top_reps,
                    "target_reps": target, "hit": target and top_reps >= target,
                })
    return out


def next_target(perf: list[dict], is_compound: bool) -> tuple[float | None, str]:
    """Suggest the next working weight (kg) and a short coaching note.

    Linear progression: hit the target last time → add weight; miss twice in a
    row → deload 10%; otherwise hold and chase reps.
    """
    if not perf:
        return None, "First time — work up to a challenging weight you can control."

    last = perf[0]
    if last["weight_kg"] is None:
        return None, "Bodyweight — add reps or slow the tempo to progress."

    inc = COMPOUND_INC_KG if is_compound else ACCESSORY_INC_KG

    missed_twice = (
        len(perf) >= 2
        and last.get("target_reps") and perf[1].get("target_reps")
        and not last["hit"] and not perf[1]["hit"]
    )
    if missed_twice:
        return round(last["weight_kg"] * DELOAD_FACTOR, 2), "Deloading 10% to rebuild momentum after two tough sessions."
    if last["hit"]:
        return round(last["weight_kg"] + inc, 2), f"Up {inc} kg from last time — you earned it."
    return round(last["weight_kg"], 2), "Same weight — aim to beat last session's reps."


def build_workout(profile: dict, history: list[dict], library: list, today_focus: str | None = None) -> PlannedWorkout:
    """Build a full planned session from the profile + history."""
    goal = profile.get("goal") or "general"
    focus = today_focus or recommend_focus(goal, history)
    available = available_equipment(profile.get("equipment") or [], profile.get("location") or "both")
    count = _exercise_count(profile.get("session_duration"))

    # Gather candidate pools per source split (compounds first).
    sources = FOCUS_SOURCES.get(focus, ["full"])
    pools = {s: for_split(library, s, available) for s in sources}

    selected: list = []
    used_names: set = set()
    used_patterns: set = set()

    # Round-robin across the source splits, taking the best remaining lift each
    # pass and avoiding duplicate movement patterns until we must repeat.
    while len(selected) < count and any(pools.values()):
        progressed = False
        for s in sources:
            if len(selected) >= count:
                break
            pool = pools.get(s) or []
            pick = None
            for e in pool:
                if e.name in used_names:
                    continue
                if e.movement_pattern in used_patterns and len(used_patterns) < count:
                    continue
                pick = e
                break
            if pick is None:  # relax the pattern constraint
                pick = next((e for e in pool if e.name not in used_names), None)
            if pick:
                selected.append(pick)
                used_names.add(pick.name)
                used_patterns.add(pick.movement_pattern)
                progressed = True
        if not progressed:
            break

    # For strength-focused sessions, finish with a core exercise if there's room.
    if focus != "cardio" and len(selected) < count:
        for e in for_split(library, "core", available):
            if e.name not in used_names:
                selected.append(e)
                used_names.add(e.name)
                break

    planned: list[PlannedExercise] = []
    for i, e in enumerate(selected):
        sets, reps = rep_scheme(goal, e.is_compound)
        if e.exercise_type == "cardio":
            sets, reps = e.default_sets, e.default_reps
            weight, note = None, e.instructions
        else:
            weight, note = next_target(exercise_history(history, e.name), e.is_compound)
            if e.instructions:
                note = f"{note} {e.instructions}".strip()
        planned.append(PlannedExercise(
            name=e.name, target_sets=sets, target_reps=reps, target_weight_kg=weight,
            exercise_type=e.exercise_type, target_muscle_group=e.primary_muscle,
            notes=note, sort_order=i,
        ))

    last = last_completed_focus(history)
    rationale = (
        f"Last completed session was {FOCUS_LABELS.get(last, last)}; "
        f"rotating to {FOCUS_LABELS.get(focus, focus)} today."
        if last else
        f"Starting your program with a {FOCUS_LABELS.get(focus, focus)} session."
    )
    return PlannedWorkout(
        name=FOCUS_LABELS.get(focus, focus.title()), focus=focus,
        exercises=planned, rationale=rationale,
    )
