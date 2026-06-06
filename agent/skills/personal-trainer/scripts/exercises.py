"""Exercise catalogue + selection helpers.

`LIBRARY` mirrors `supabase/migrations/0003_seed_exercises.sql` so the engine can
plan workouts offline (and in unit tests) without a DB round-trip. In production
`load_library()` prefers the DB copy and falls back to this list, so the two
should be kept in sync.
"""
from __future__ import annotations

from models import Exercise

# name, type, primary, equipment, pattern, split, compound, sets, reps, secondary, instructions
_RAW = [
    # PUSH
    ("Barbell Bench Press", "strength", "chest", ("barbell",), "push_h", "push", True, 4, 8, ("shoulders", "arms"), "Retract shoulder blades, lower bar to mid-chest, drive through the floor."),
    ("Incline Dumbbell Press", "strength", "chest", ("dumbbells",), "push_h", "push", True, 3, 10, ("shoulders", "arms"), "Bench at 30°, press dumbbells up and slightly together."),
    ("Dumbbell Bench Press", "strength", "chest", ("dumbbells",), "push_h", "push", True, 4, 10, ("shoulders", "arms"), "Control the descent, keep wrists stacked over elbows."),
    ("Machine Chest Press", "strength", "chest", ("machines",), "push_h", "push", True, 3, 12, ("shoulders", "arms"), "Set seat so handles align with mid-chest."),
    ("Overhead Barbell Press", "strength", "shoulders", ("barbell",), "push_v", "push", True, 4, 8, ("arms", "chest"), "Brace core, press overhead without leaning back."),
    ("Dumbbell Shoulder Press", "strength", "shoulders", ("dumbbells",), "push_v", "push", True, 3, 10, ("arms",), "Press from ear height to lockout, keep ribs down."),
    ("Lateral Raise", "strength", "shoulders", ("dumbbells", "cables"), "push_v", "push", False, 3, 15, (), "Lead with the elbows, raise to shoulder height."),
    ("Cable Triceps Pushdown", "strength", "arms", ("cables",), "push_v", "push", False, 3, 12, (), "Pin elbows to sides, extend fully."),
    ("Push-Up", "bodyweight", "chest", ("bodyweight",), "push_h", "push", True, 3, 15, ("shoulders", "arms", "core"), "Body in a straight line, lower until chest nearly touches floor."),
    ("Dips", "bodyweight", "chest", ("bodyweight",), "push_h", "push", True, 3, 10, ("arms", "shoulders"), "Lean slightly forward for chest, stay upright for triceps."),
    # PULL
    ("Deadlift", "strength", "back", ("barbell",), "hinge", "pull", True, 4, 5, ("legs", "core"), "Flat back, push the floor away, lock out hips and knees together."),
    ("Barbell Row", "strength", "back", ("barbell",), "pull_h", "pull", True, 4, 8, ("arms", "shoulders"), "Hinge to ~45°, row to lower ribs, squeeze shoulder blades."),
    ("Pull-Up", "bodyweight", "back", ("bodyweight",), "pull_v", "pull", True, 4, 8, ("arms",), "Full hang to chin over bar, control the descent."),
    ("Lat Pulldown", "strength", "back", ("machines", "cables"), "pull_v", "pull", True, 3, 12, ("arms",), "Pull bar to upper chest, drive elbows down."),
    ("Seated Cable Row", "strength", "back", ("cables", "machines"), "pull_h", "pull", True, 3, 12, ("arms", "shoulders"), "Tall chest, pull to the navel, avoid heaving."),
    ("Dumbbell Row", "strength", "back", ("dumbbells",), "pull_h", "pull", True, 3, 10, ("arms",), "Support on a bench, row dumbbell to hip."),
    ("Face Pull", "strength", "shoulders", ("cables", "bands"), "pull_h", "pull", False, 3, 15, ("back",), "Pull rope to the face, externally rotate at the end."),
    ("Dumbbell Bicep Curl", "strength", "arms", ("dumbbells",), "pull_v", "pull", False, 3, 12, (), "Elbows fixed, curl without swinging."),
    ("Barbell Curl", "strength", "arms", ("barbell",), "pull_v", "pull", False, 3, 10, (), "Keep elbows pinned, control the negative."),
    ("Inverted Row", "bodyweight", "back", ("bodyweight",), "pull_h", "pull", True, 3, 12, ("arms",), "Body straight, pull chest to the bar."),
    # LEGS
    ("Barbell Back Squat", "strength", "legs", ("barbell",), "squat", "legs", True, 4, 8, ("core",), "Brace, sit between the hips, knees track over toes, hit depth."),
    ("Front Squat", "strength", "legs", ("barbell",), "squat", "legs", True, 4, 6, ("core",), "Elbows high, upright torso, full depth."),
    ("Goblet Squat", "strength", "legs", ("dumbbells", "kettlebell"), "squat", "legs", True, 3, 12, ("core",), "Hold weight at the chest, sit down tall."),
    ("Romanian Deadlift", "strength", "legs", ("barbell", "dumbbells"), "hinge", "legs", True, 3, 10, ("back",), "Soft knees, push hips back, feel the hamstring stretch."),
    ("Leg Press", "strength", "legs", ("machines",), "squat", "legs", True, 3, 12, (), "Feet shoulder-width, lower under control, don't lock out hard."),
    ("Walking Lunge", "strength", "legs", ("dumbbells", "bodyweight"), "lunge", "legs", True, 3, 10, ("core",), "Long step, drop the back knee, drive through the front heel."),
    ("Bulgarian Split Squat", "strength", "legs", ("dumbbells", "bodyweight"), "lunge", "legs", True, 3, 10, ("core",), "Rear foot elevated, torso slightly forward, drive up."),
    ("Leg Curl", "strength", "legs", ("machines",), "hinge", "legs", False, 3, 12, (), "Curl heels to glutes, control the negative."),
    ("Leg Extension", "strength", "legs", ("machines",), "squat", "legs", False, 3, 15, (), "Extend to lockout, pause, lower slowly."),
    ("Calf Raise", "strength", "legs", ("machines", "dumbbells", "bodyweight"), "squat", "legs", False, 4, 15, (), "Full stretch at the bottom, big squeeze at the top."),
    ("Kettlebell Swing", "strength", "legs", ("kettlebell",), "hinge", "legs", True, 4, 15, ("back", "core"), "Hike the bell, snap the hips, float to chest height."),
    ("Bodyweight Squat", "bodyweight", "legs", ("bodyweight",), "squat", "legs", True, 3, 20, ("core",), "Sit back and down, full depth, stand tall."),
    ("Glute Bridge", "bodyweight", "legs", ("bodyweight", "barbell"), "hinge", "legs", False, 3, 15, ("core",), "Drive hips up, squeeze glutes at the top."),
    # CORE
    ("Plank", "bodyweight", "core", ("bodyweight",), "core", "core", False, 3, 1, (), "Hold a straight line for time (~45s), brace hard."),
    ("Hanging Leg Raise", "bodyweight", "core", ("bodyweight",), "core", "core", False, 3, 12, (), "Raise legs to hip height without swinging."),
    ("Cable Crunch", "strength", "core", ("cables",), "core", "core", False, 3, 15, (), "Crunch the rib cage toward the pelvis."),
    ("Russian Twist", "bodyweight", "core", ("bodyweight", "dumbbells"), "core", "core", False, 3, 20, (), "Rotate side to side, keep the chest tall."),
    # CARDIO
    ("Treadmill Intervals", "cardio", "full", ("machines",), "cardio", "cardio", False, 1, 1, (), "Alternate 1 min hard / 2 min easy for the session duration."),
    ("Rowing Machine", "cardio", "full", ("machines",), "cardio", "cardio", False, 1, 1, ("back", "legs"), "Legs–core–arms on the drive, reverse on the recovery."),
    ("Jump Rope", "cardio", "full", ("bodyweight",), "cardio", "cardio", False, 1, 1, (), "Light bounces, steady rhythm for intervals."),
    ("Burpees", "cardio", "full", ("bodyweight",), "cardio", "cardio", False, 4, 12, ("chest", "legs", "core"), "Chest to floor, explode up to a jump."),
]

LIBRARY = [
    Exercise(
        name=r[0], exercise_type=r[1], primary_muscle=r[2], equipment=r[3],
        movement_pattern=r[4], split=r[5], is_compound=r[6],
        default_sets=r[7], default_reps=r[8], secondary_muscles=r[9], instructions=r[10],
    )
    for r in _RAW
]


def from_db_rows(rows: list[dict]) -> list[Exercise]:
    """Map exercise_library rows (from Supabase) into Exercise objects."""
    out = []
    for r in rows:
        out.append(Exercise(
            name=r["name"], exercise_type=r["exercise_type"], primary_muscle=r["primary_muscle"],
            equipment=tuple(r.get("equipment") or ()), movement_pattern=r.get("movement_pattern", ""),
            split=r.get("split", ""), is_compound=bool(r.get("is_compound")),
            default_sets=int(r.get("default_sets", 3)), default_reps=int(r.get("default_reps", 10)),
            secondary_muscles=tuple(r.get("secondary_muscles") or ()),
            instructions=r.get("instructions", ""),
        ))
    return out


def available_equipment(equipment: list[str], location: str) -> set:
    """Resolve the effective equipment set; bodyweight is always available."""
    eq = set(equipment or [])
    eq.add("bodyweight")
    return eq


def for_split(library: list[Exercise], split: str, available: set) -> list[Exercise]:
    """Usable exercises for a split, compounds first then accessories."""
    pool = [e for e in library if e.split == split and e.usable_with(available)]
    pool.sort(key=lambda e: (not e.is_compound, e.name))
    return pool
