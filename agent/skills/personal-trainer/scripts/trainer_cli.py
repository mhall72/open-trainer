#!/usr/bin/env python3
"""trainer_cli — the tool surface the Hermes agent calls to run Open-Trainer.

Every subcommand prints a single JSON object to stdout:
  {"ok": true, "text": "<human-readable, already in the user's unit>", ...data}
  {"ok": false, "error": "..."}

The agent relays `text` to the user and may use the structured fields (ids, etc.)
for follow-up calls. Weights are accepted/returned in the user's unit and stored
canonically in kg.

Examples:
  trainer_cli.py whoami --telegram-id 555
  trainer_cli.py link --telegram-id 555 --code 9F3A2C --username mike
  trainer_cli.py save-profile --telegram-id 555 --goal build_muscle --location gym \
      --equipment barbell,dumbbells,machines --duration 45 --personality motivational --unit lbs --complete
  trainer_cli.py recommend --telegram-id 555
  trainer_cli.py start --telegram-id 555
  trainer_cli.py log --telegram-id 555 --exercise-id <uuid> --set 1 --reps 8 --weight 135
  trainer_cli.py complete --telegram-id 555
  trainer_cli.py history --telegram-id 555
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import exercises as exlib                     # noqa: E402
import onboarding as ob                       # noqa: E402
import workout_engine as we                   # noqa: E402
from access import access_state, gate_message  # noqa: E402
from models import (from_kg, to_kg, format_weight, PERSONALITY_LABELS)  # noqa: E402
from personalities import persona              # noqa: E402

SUBSCRIBE_URL = os.environ.get("OPEN_TRAINER_SUBSCRIBE_URL", "https://open-trainer.app")


def emit(obj: dict, code: int = 0):
    print(json.dumps(obj, default=str))
    sys.exit(code)


def fail(msg: str):
    emit({"ok": False, "error": msg}, code=1)


def _client():
    from supabase_client import SupabaseClient, SupabaseError
    try:
        return SupabaseClient()
    except SupabaseError as e:
        fail(str(e))


def _resolve(db, telegram_id: int):
    """Return (user, profile) or gate out if the user can't proceed."""
    user = db.get_user_by_telegram(telegram_id)
    state = access_state(user)
    if state != "ok":
        emit({"ok": True, "access": state, "text": gate_message(state, SUBSCRIBE_URL)})
    profile = db.get_profile(user["id"]) or {}
    return user, profile


def _load_library(db):
    try:
        rows = db.exercise_library()
        if rows:
            return exlib.from_db_rows(rows)
    except Exception:
        pass
    return exlib.LIBRARY   # offline fallback


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_persona(a):
    emit({"ok": True, "key": a.key, "system_prompt": persona(a.key)})


def cmd_parse_onboarding(a):
    val = ob.parse_answer(a.step, a.text)
    emit({"ok": True, "step": a.step, "value": val,
          "understood": val not in (None, [], "")})


def cmd_whoami(a):
    db = _client()
    user = db.get_user_by_telegram(a.telegram_id)
    state = access_state(user)
    if state != "ok":
        emit({"ok": True, "access": state, "text": gate_message(state, SUBSCRIBE_URL)})
    profile = db.get_profile(user["id"]) or {}
    step = ob.next_step(profile)
    text = (f"Welcome back! Onboarding next: {ob.QUESTIONS[step]}" if step
            else "You're all set up. Say 'let's work out' when you're ready.")
    emit({"ok": True, "access": "ok", "user_id": user["id"],
          "onboarding_complete": step is None, "next_step": step,
          "next_question": ob.QUESTIONS.get(step), "profile": profile, "text": text})


def cmd_link(a):
    db = _client()
    from supabase_client import SupabaseError
    try:
        user = db.link_telegram(a.code.strip().upper(), a.telegram_id, a.username)
    except SupabaseError as e:
        emit({"ok": False, "error": str(e),
              "text": "That code didn't work — it may be expired or already used. "
                      "Double-check the 6 characters from your checkout page."}, code=0)
    emit({"ok": True, "user_id": user["id"], "next_step": "goal",
          "text": "🎉 You're linked and active! Let's set up your profile. "
                  + ob.QUESTIONS["goal"]})


def cmd_save_profile(a):
    db = _client()
    user, _ = _resolve(db, a.telegram_id)
    fields = {}
    if a.goal:        fields["goal"] = a.goal
    if a.location:    fields["location"] = a.location
    if a.personality: fields["personality"] = a.personality
    if a.unit:        fields["unit_preference"] = a.unit
    if a.duration is not None: fields["session_duration"] = a.duration
    if a.equipment:   fields["equipment"] = [e.strip() for e in a.equipment.split(",") if e.strip()]
    if a.complete:
        fields["onboarding_complete"] = True
        fields["onboarding_step"] = None
    profile = db.upsert_profile(user["id"], **fields)
    step = ob.next_step(profile)
    if step:
        text = ob.QUESTIONS[step]
    else:
        text = f"All set! Here's your profile:\n{ob.summary(profile)}\nWant a workout now?"
        if not profile.get("onboarding_complete"):
            db.upsert_profile(user["id"], onboarding_complete=True)
    emit({"ok": True, "profile": profile, "next_step": step,
          "next_question": ob.QUESTIONS.get(step), "text": text})


def _format_plan(plan, unit: str) -> str:
    lines = [f"💪 {plan.name} — here's the plan:", "", plan.rationale, ""]
    for i, e in enumerate(plan.exercises, 1):
        if e.exercise_type == "cardio":
            lines.append(f"{i}️⃣ {e.name} — {e.notes or 'intervals'}")
        else:
            w = f" @ {format_weight(e.target_weight_kg, unit)}" if e.target_weight_kg else ""
            lines.append(f"{i}️⃣ {e.name} — {e.target_sets}×{e.target_reps}{w}")
    return "\n".join(lines)


def _plan_payload(plan, unit: str) -> list:
    out = []
    for e in plan.exercises:
        out.append({
            "name": e.name, "target_sets": e.target_sets, "target_reps": e.target_reps,
            "target_weight_kg": e.target_weight_kg,
            "target_weight_display": format_weight(e.target_weight_kg, unit),
            "exercise_type": e.exercise_type, "target_muscle_group": e.target_muscle_group,
            "notes": e.notes, "sort_order": e.sort_order,
        })
    return out


def cmd_recommend(a):
    db = _client()
    user, profile = _resolve(db, a.telegram_id)
    if not profile.get("goal"):
        emit({"ok": True, "text": "Let's finish your profile first. " + ob.QUESTIONS[ob.next_step(profile) or "goal"]})
    history = db.list_history(user["id"], limit=10)
    plan = we.build_workout(profile, history, _load_library(db), today_focus=a.focus)
    unit = profile.get("unit_preference", "lbs")
    emit({"ok": True, "focus": plan.focus, "name": plan.name,
          "exercises": _plan_payload(plan, unit),
          "text": _format_plan(plan, unit) + "\n\nReply 'start' when you're ready."})


def cmd_start(a):
    db = _client()
    user, profile = _resolve(db, a.telegram_id)
    existing = db.active_workout(user["id"])
    if existing and not a.restart:
        unit = profile.get("unit_preference", "lbs")
        emit({"ok": True, "workout": existing,
              "text": "You've already got a session in progress — let's keep going. "
                      "Tell me your reps and weight for the current set."})
    history = db.list_history(user["id"], limit=10)
    plan = we.build_workout(profile, history, _load_library(db), today_focus=a.focus)
    unit = profile.get("unit_preference", "lbs")
    workout = db.create_workout(user["id"], plan.name, plan.focus, _plan_payload(plan, unit))
    ex = sorted(workout.get("exercises", []), key=lambda x: x.get("sort_order", 0))
    first = ex[0] if ex else None
    text = f"🏋️ {plan.name} started! Exercise 1/{len(ex)}: {first['name']}" if first else "Workout started!"
    if first:
        text += f" — {first.get('target_sets')}×{first.get('target_reps')}\nSet 1 — how many reps at what weight?"
    emit({"ok": True, "workout_id": workout["id"], "exercises": ex, "text": text})


def cmd_log(a):
    db = _client()
    user, profile = _resolve(db, a.telegram_id)
    unit = profile.get("unit_preference", "lbs")
    weight_kg = to_kg(a.weight, unit) if a.weight is not None else None
    db.log_set(a.exercise_id, a.set, a.reps, weight_kg, a.rpe)
    shown = format_weight(weight_kg, unit) if weight_kg is not None else f"{a.reps} reps"
    emit({"ok": True, "text": f"✅ Set {a.set}: {a.reps} reps"
          + (f" @ {shown}" if weight_kg is not None else "") + ". Next set?"})


def _progress_notes(history, unit) -> list[str]:
    """Compare the just-finished session (history[0]) with the prior one."""
    if not history:
        return []
    notes = []
    current = history[0]
    for ex in current.get("exercises", []):
        perf = we.exercise_history(history, ex.get("name"))
        if len(perf) >= 2 and perf[0]["weight_kg"] and perf[1]["weight_kg"]:
            delta = perf[0]["weight_kg"] - perf[1]["weight_kg"]
            if delta > 0:
                notes.append(f"⬆️ {ex['name']}: +{format_weight(delta, unit)} vs last time")
    return notes


def cmd_complete(a):
    db = _client()
    user, profile = _resolve(db, a.telegram_id)
    workout = db.active_workout(user["id"])
    if not workout:
        emit({"ok": True, "text": "No active workout to finish — say 'let's work out' to start one."})
    db.complete_workout(workout["id"], a.notes)
    history = db.list_history(user["id"], limit=10)
    unit = profile.get("unit_preference", "lbs")
    n_ex = len(workout.get("exercises", []))
    n_sets = sum(len(e.get("sets", [])) for e in workout.get("exercises", []))
    text = f"💪 Workout complete! {n_ex} exercises, {n_sets} sets logged."
    for note in _progress_notes(history, unit):
        text += "\n" + note
    text += "\nWant to schedule your next session?"
    emit({"ok": True, "workout_id": workout["id"], "text": text})


def cmd_history(a):
    db = _client()
    user, profile = _resolve(db, a.telegram_id)
    unit = profile.get("unit_preference", "lbs")
    workouts = db.list_history(user["id"], limit=a.limit)
    if not workouts:
        emit({"ok": True, "text": "No sessions logged yet — let's change that. Say 'let's work out'."})
    lines = ["📈 Recent sessions:"]
    for w in workouts:
        n_sets = sum(len(e.get("sets", [])) for e in w.get("exercises", []))
        lines.append(f"• {w.get('date')} — {w.get('name')} ({w.get('status')}, {n_sets} sets)")
    emit({"ok": True, "workouts": workouts, "text": "\n".join(lines)})


def cmd_add_reminder(a):
    db = _client()
    user, _ = _resolve(db, a.telegram_id)
    days = [d.strip().lower()[:3] for d in a.days.split(",") if d.strip()]
    r = db.add_reminder(user["id"], days, a.time, a.timezone)
    emit({"ok": True, "reminder": r,
          "text": f"⏰ Reminder set for {', '.join(days)} at {a.time} ({a.timezone})."})


def cmd_list_reminders(a):
    db = _client()
    user, _ = _resolve(db, a.telegram_id)
    rs = db.list_reminders(user["id"])
    if not rs:
        emit({"ok": True, "text": "No reminders set. Want me to schedule one?"})
    lines = ["⏰ Your reminders:"]
    for r in rs:
        state = "on" if r.get("enabled") else "off"
        lines.append(f"• {', '.join(r.get('days') or [])} at {r.get('time')} ({state})")
    emit({"ok": True, "reminders": rs, "text": "\n".join(lines)})


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trainer_cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    def tg(sp):
        sp.add_argument("--telegram-id", dest="telegram_id", type=int, required=True)

    sp = sub.add_parser("persona"); sp.add_argument("--key", default="motivational"); sp.set_defaults(fn=cmd_persona)
    sp = sub.add_parser("parse-onboarding")
    sp.add_argument("--step", required=True, choices=ob.STEPS); sp.add_argument("--text", required=True)
    sp.set_defaults(fn=cmd_parse_onboarding)

    sp = sub.add_parser("whoami"); tg(sp); sp.set_defaults(fn=cmd_whoami)
    sp = sub.add_parser("link"); tg(sp)
    sp.add_argument("--code", required=True); sp.add_argument("--username", default=None)
    sp.set_defaults(fn=cmd_link)

    sp = sub.add_parser("save-profile"); tg(sp)
    sp.add_argument("--goal", choices=["build_muscle", "lose_weight", "general", "endurance"])
    sp.add_argument("--location", choices=["home", "gym", "both"])
    sp.add_argument("--equipment"); sp.add_argument("--duration", type=int)
    sp.add_argument("--personality", choices=["motivational", "nononsense", "science"])
    sp.add_argument("--unit", choices=["kg", "lbs"])
    sp.add_argument("--complete", action="store_true"); sp.set_defaults(fn=cmd_save_profile)

    sp = sub.add_parser("recommend"); tg(sp); sp.add_argument("--focus", default=None); sp.set_defaults(fn=cmd_recommend)
    sp = sub.add_parser("start"); tg(sp); sp.add_argument("--focus", default=None)
    sp.add_argument("--restart", action="store_true"); sp.set_defaults(fn=cmd_start)

    sp = sub.add_parser("log"); tg(sp)
    sp.add_argument("--exercise-id", dest="exercise_id", required=True)
    sp.add_argument("--set", type=int, required=True); sp.add_argument("--reps", type=int, required=True)
    sp.add_argument("--weight", type=float, default=None); sp.add_argument("--rpe", type=float, default=None)
    sp.set_defaults(fn=cmd_log)

    sp = sub.add_parser("complete"); tg(sp); sp.add_argument("--notes", default=None); sp.set_defaults(fn=cmd_complete)
    sp = sub.add_parser("history"); tg(sp); sp.add_argument("--limit", type=int, default=5); sp.set_defaults(fn=cmd_history)

    sp = sub.add_parser("add-reminder"); tg(sp)
    sp.add_argument("--days", required=True); sp.add_argument("--time", required=True)
    sp.add_argument("--timezone", default="UTC"); sp.set_defaults(fn=cmd_add_reminder)
    sp = sub.add_parser("list-reminders"); tg(sp); sp.set_defaults(fn=cmd_list_reminders)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except SystemExit:
        raise
    except Exception as e:  # never leak a traceback into the chat
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
