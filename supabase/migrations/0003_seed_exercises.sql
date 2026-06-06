-- =============================================================================
-- Open-Trainer — 0003_seed_exercises.sql
-- Seed the exercise_library. Idempotent (ON CONFLICT (name) DO NOTHING).
-- Columns: name, exercise_type, primary_muscle, secondary_muscles, equipment,
--          movement_pattern, split, is_compound, default_sets, default_reps, instructions
-- =============================================================================

insert into public.exercise_library
  (name, exercise_type, primary_muscle, secondary_muscles, equipment, movement_pattern, split, is_compound, default_sets, default_reps, instructions)
values
  -- ---------------- PUSH ----------------
  ('Barbell Bench Press','strength','chest','{shoulders,arms}','{barbell}','push_h','push',true,4,8,'Retract shoulder blades, lower bar to mid-chest, drive through the floor.'),
  ('Incline Dumbbell Press','strength','chest','{shoulders,arms}','{dumbbells}','push_h','push',true,3,10,'Bench at 30°, press dumbbells up and slightly together.'),
  ('Dumbbell Bench Press','strength','chest','{shoulders,arms}','{dumbbells}','push_h','push',true,4,10,'Control the descent, keep wrists stacked over elbows.'),
  ('Machine Chest Press','strength','chest','{shoulders,arms}','{machines}','push_h','push',true,3,12,'Set seat so handles align with mid-chest.'),
  ('Overhead Barbell Press','strength','shoulders','{arms,chest}','{barbell}','push_v','push',true,4,8,'Brace core, press overhead without leaning back.'),
  ('Dumbbell Shoulder Press','strength','shoulders','{arms}','{dumbbells}','push_v','push',true,3,10,'Press from ear height to lockout, keep ribs down.'),
  ('Lateral Raise','strength','shoulders','{}','{dumbbells,cables}','push_v','push',false,3,15,'Lead with the elbows, raise to shoulder height.'),
  ('Cable Triceps Pushdown','strength','arms','{}','{cables}','push_v','push',false,3,12,'Pin elbows to sides, extend fully.'),
  ('Push-Up','bodyweight','chest','{shoulders,arms,core}','{bodyweight}','push_h','push',true,3,15,'Body in a straight line, lower until chest nearly touches floor.'),
  ('Dips','bodyweight','chest','{arms,shoulders}','{bodyweight}','push_h','push',true,3,10,'Lean slightly forward for chest, stay upright for triceps.'),

  -- ---------------- PULL ----------------
  ('Deadlift','strength','back','{legs,core}','{barbell}','hinge','pull',true,4,5,'Flat back, push the floor away, lock out hips and knees together.'),
  ('Barbell Row','strength','back','{arms,shoulders}','{barbell}','pull_h','pull',true,4,8,'Hinge to ~45°, row to lower ribs, squeeze shoulder blades.'),
  ('Pull-Up','bodyweight','back','{arms}','{bodyweight}','pull_v','pull',true,4,8,'Full hang to chin over bar, control the descent.'),
  ('Lat Pulldown','strength','back','{arms}','{machines,cables}','pull_v','pull',true,3,12,'Pull bar to upper chest, drive elbows down.'),
  ('Seated Cable Row','strength','back','{arms,shoulders}','{cables,machines}','pull_h','pull',true,3,12,'Tall chest, pull to the navel, avoid heaving.'),
  ('Dumbbell Row','strength','back','{arms}','{dumbbells}','pull_h','pull',true,3,10,'Support on a bench, row dumbbell to hip.'),
  ('Face Pull','strength','shoulders','{back}','{cables,bands}','pull_h','pull',false,3,15,'Pull rope to the face, externally rotate at the end.'),
  ('Dumbbell Bicep Curl','strength','arms','{}','{dumbbells}','pull_v','pull',false,3,12,'Elbows fixed, curl without swinging.'),
  ('Barbell Curl','strength','arms','{}','{barbell}','pull_v','pull',false,3,10,'Keep elbows pinned, control the negative.'),
  ('Inverted Row','bodyweight','back','{arms}','{bodyweight}','pull_h','pull',true,3,12,'Body straight, pull chest to the bar.'),

  -- ---------------- LEGS ----------------
  ('Barbell Back Squat','strength','legs','{core}','{barbell}','squat','legs',true,4,8,'Brace, sit between the hips, knees track over toes, hit depth.'),
  ('Front Squat','strength','legs','{core}','{barbell}','squat','legs',true,4,6,'Elbows high, upright torso, full depth.'),
  ('Goblet Squat','strength','legs','{core}','{dumbbells,kettlebell}','squat','legs',true,3,12,'Hold weight at the chest, sit down tall.'),
  ('Romanian Deadlift','strength','legs','{back}','{barbell,dumbbells}','hinge','legs',true,3,10,'Soft knees, push hips back, feel the hamstring stretch.'),
  ('Leg Press','strength','legs','{}','{machines}','squat','legs',true,3,12,'Feet shoulder-width, lower under control, don''t lock out hard.'),
  ('Walking Lunge','strength','legs','{core}','{dumbbells,bodyweight}','lunge','legs',true,3,10,'Long step, drop the back knee, drive through the front heel.'),
  ('Bulgarian Split Squat','strength','legs','{core}','{dumbbells,bodyweight}','lunge','legs',true,3,10,'Rear foot elevated, torso slightly forward, drive up.'),
  ('Leg Curl','strength','legs','{}','{machines}','hinge','legs',false,3,12,'Curl heels to glutes, control the negative.'),
  ('Leg Extension','strength','legs','{}','{machines}','squat','legs',false,3,15,'Extend to lockout, pause, lower slowly.'),
  ('Calf Raise','strength','legs','{}','{machines,dumbbells,bodyweight}','squat','legs',false,4,15,'Full stretch at the bottom, big squeeze at the top.'),
  ('Kettlebell Swing','strength','legs','{back,core}','{kettlebell}','hinge','legs',true,4,15,'Hike the bell, snap the hips, float to chest height.'),
  ('Bodyweight Squat','bodyweight','legs','{core}','{bodyweight}','squat','legs',true,3,20,'Sit back and down, full depth, stand tall.'),
  ('Glute Bridge','bodyweight','legs','{core}','{bodyweight,barbell}','hinge','legs',false,3,15,'Drive hips up, squeeze glutes at the top.'),

  -- ---------------- CORE ----------------
  ('Plank','bodyweight','core','{}','{bodyweight}','core','core',false,3,1,'Hold a straight line for time (~45s), brace hard.'),
  ('Hanging Leg Raise','bodyweight','core','{}','{bodyweight}','core','core',false,3,12,'Raise legs to hip height without swinging.'),
  ('Cable Crunch','strength','core','{}','{cables}','core','core',false,3,15,'Crunch the rib cage toward the pelvis.'),
  ('Russian Twist','bodyweight','core','{}','{bodyweight,dumbbells}','core','core',false,3,20,'Rotate side to side, keep the chest tall.'),

  -- ---------------- CARDIO ----------------
  ('Treadmill Intervals','cardio','full','{}','{machines}','cardio','cardio',false,1,1,'Alternate 1 min hard / 2 min easy for the session duration.'),
  ('Rowing Machine','cardio','full','{back,legs}','{machines}','cardio','cardio',false,1,1,'Legs–core–arms on the drive, reverse on the recovery.'),
  ('Jump Rope','cardio','full','{}','{bodyweight}','cardio','cardio',false,1,1,'Light bounces, steady rhythm for intervals.'),
  ('Burpees','cardio','full','{chest,legs,core}','{bodyweight}','cardio','cardio',false,4,12,'Chest to floor, explode up to a jump.')
on conflict (name) do nothing;
