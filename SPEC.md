# Open-Trainer — Specification

## 1. Desired Outcomes

1. Users can subscribe via a website (Stripe) and get Telegram bot access
2. Users onboard to set their fitness profile (goals, equipment, duration, personality)
3. Users can message the bot for guided workouts at any time
4. The bot recommends workouts based on history and goals
5. The bot guides through exercises, logging weight/reps per set
6. Users get reminders for scheduled workouts
7. Users can view their progress and history
8. Data is logically separated per user (Supabase RLS)

## 2. Data Model (Supabase)

### Tables

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK, default gen_random_uuid() |
| telegram_id | bigint | Unique, linked during signup |
| stripe_customer_id | text | From Stripe |
| subscription_status | text | active / inactive / trial |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**profiles**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users(id), unique |
| goal | text | build_muscle / lose_weight / general / endurance |
| location | text | home / gym / both |
| equipment | text[] | Array of equipment types |
| session_duration | int | Minutes (30/45/60/0=flexible) |
| personality | text | motivational / nononsense / science |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**workouts**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users(id) |
| date | date | |
| name | text | e.g. "Upper Body Push" |
| status | text | in_progress / completed / abandoned |
| notes | text | User's optional notes |
| started_at | timestamptz | |
| completed_at | timestamptz | Nullable |

**exercises**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| workout_id | uuid | FK → workouts(id) |
| name | text | e.g. "Bench Press" |
| exercise_type | text | strength / cardio / bodyweight |
| target_muscle_group | text | chest / back / legs / etc |
| notes | text | Form cues, instructions |
| sort_order | int | Order in the workout |

**sets**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| exercise_id | uuid | FK → exercises(id) |
| set_number | int | 1, 2, 3... |
| reps | int | Completed |
| weight_kg | decimal | |
| rpe | decimal | Optional, Rate of Perceived Exertion |
| completed | boolean | |
| completed_at | timestamptz | |

**reminders**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users(id) |
| days | text[] | mon/tue/wed/thu/fri/sat/sun |
| time | time | HH:MM |
| enabled | boolean | |

### Row Level Security

- Every table has `user_id` and RLS policy: `user_id = auth.uid()`
- The agent's DB connection uses a service role key or per-user token

## 3. User Flows

### Signup & Subscription

1. User visits landing page → clicks "Subscribe"
2. Stripe checkout → payment → success redirect
3. User enters Telegram handle on success page
4. Bot sends verification code to user's Telegram
5. User enters code on website → linked
6. User record created in Supabase with `telegram_id`
7. Bot sends welcome message

### Onboarding (First Message)

User texts the bot for the first time → onboarding begins:

```
Bot: "Welcome to Open-Trainer! Let's set up your profile."
Bot: "What's your fitness goal? Choose one:
  🎯 Build Muscle
  🔥 Lose Weight
  💪 General Fitness
  🏃 Endurance"
User: "Build Muscle"

Bot: "Where do you work out?
  🏠 Home
  🏋️ Gym
  🔄 Both"
User: "Gym"

Bot: "What equipment do you have access to? (can select multiple)
  🏋️ Barbell
  💪 Dumbbells
  🔧 Machines
  🪶 Cables
  🔗 Bodyweight
  Other..."
User: [responds]

Bot: "How long do you want each session to be?
  ⏱️ 30 min
  ⏱️ 45 min
  ⏱️ 60 min
  ⏱️ Flexible"
User: "45 min"

Bot: "Last thing — pick your trainer personality:
  🗣️ Motivational Coach — high energy, keeps you going
  🗣️ No-Nonsense Trainer — direct, no fluff
  🗣️ Science-Based — explains the why, evidence-driven"
User: "Motivational Coach"

Bot: "All set! Here's your profile:
  Goal: Build Muscle | Gym | 45 min | Motivational Coach
  Want a workout now?"
```

### Active Workout Session

```
User: "Let's work out"

Bot: "Last session you did Upper Body Push (4 days ago, 8.5/10 effort).
Based on your progression, today I recommend Lower Body Push.
Ready? Here's the plan:

1️⃣ Barbell Squats — 4×8
2️⃣ Romanian Deadlifts — 3×10
3️⃣ Leg Press — 3×12
4️⃣ Walking Lunges — 3×10 each

Reply 'start' when you're ready."

User: "start"

Bot: "🏋️ Exercise 1/4: Barbell Squats — 4×8
Set 1 — How many reps at what weight?"
User: "8 at 135"

Bot: "✅ Set 1: 8 reps @ 135 lbs
Set 2 — same weight or increase?"
User: "same"

Bot: "Go for it! How'd it go?"
[... continues through all sets and exercises ...]

Bot: "💪 Workout Complete! Total: 4 exercises, 16 sets.
You're up 5 lbs on squats since last week. Nice.
Want to schedule your next session?"
```

### Reminders

```
Bot (scheduled): "⏰ Reminder: You've got a Push Day scheduled.
Ready to work out? Reply 'go' to start or 'snooze 1h'"

User: "go"
[Workout begins]
```

## 4. Workout Engine Logic

- **Initial workouts** — based on profile (goal → program template, equipment → available exercises)
- **Progression** — linear progression on main lifts (add weight or reps each session)
- **Recommendation** — alternates push/pull/legs or upper/lower split based on last session
- **Rest timer** — bot can set rest timer if user asks ("rest 90s")
- **Modifications** — user can swap exercises mid-session ("swap squats for leg press")
- **Failure handling** — if user can't complete reps, bot suggests deload

## 5. Open Questions (for future)

- Free trial vs paid-only?
- Multi-language support?
- Voice messages for reporting sets?
- Progress charts sent as images?
- Workout sharing / social features?

## 6. Implementation Notes (as built, 2026-06-06)

These choices were made during implementation; rationale in `ARCHITECTURE.md`.

- **Weights** are stored canonically in **kilograms** (`sets.weight_kg`). Each
  profile has a `unit_preference` (default `lbs`) and all I/O happens in the
  user's unit. Reconciles the kg schema with the lbs example dialogs.
- **RLS** uses a **default-deny** model (no anon/authenticated policies) with the
  backend on the service-role key, rather than `user_id = auth.uid()`, because
  identity is the Telegram id, not Supabase Auth.
- **Account linking** adds a `verification_codes` table and is **bot-initiated**
  (user sends a 6-char code to the bot, or taps `t.me/<bot>?start=<code>`), since
  bots can't DM a user by handle until the user starts the chat.
- **Extra schema:** `target_sets`/`target_reps` on `exercises`, `focus` on
  `workouts`, timezone + `last_sent_at` on `reminders`, and an `exercise_library`
  reference table that powers the engine.
- **LLM:** DeepSeek `v4-flash` via Hermes' bundled provider (env-configurable).
- **Hosting:** one shared multi-tenant service (see Key Decisions #1, revised).
