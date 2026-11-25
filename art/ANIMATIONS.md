# REM CYCLE: animation notes

Every animation made for the monsters, in one place: what each one is, how long it is, whether
it loops, the files, and what the game has to do with it. More detail lives in each monster's
README and in [KILLS.md](KILLS.md) (the kills, with the Studio code).

Everything is 30 fps.

## At a glance

| Monster | Animation | Frames | Seconds | Loops | File |
|---|---|---|---|---|---|
| Dewey (poster monster, floor 1) | Idle | 120 | 4.0 | yes | `poster_monster/export/PosterMonster_Idle.fbx` |
| | Walk | 34 | 1.13 | yes | `PosterMonster_Walk.fbx` |
| | Run | 20 | 0.67 | yes | `PosterMonster_Run.fbx` |
| | Kill: Neck snap | 100 | 3.3 | no | `PosterMonster_Kill.fbx` + `PosterMonster_Kill_Victim.blend` |
| CRT Man (Stand-In, floor 2) | Idle | 120 | 4.0 | yes | `stand_in/export/StandIn_Idle.fbx` |
| | Walk | 48 | 1.6 | yes | `StandIn_Walk.fbx` |
| | Run | 26 | 0.87 | yes | `StandIn_Run.fbx` |
| | Transform | 60 | 2.0 | no | `StandIn_Transform.fbx` |
| | TransformLoop | 60 | 2.0 | yes | `StandIn_TransformLoop.fbx` |
| | Kill: Collar grab | 130 | 4.3 | no | `StandIn_Kill.fbx` + `StandIn_Kill_Victim.blend` |
| | Disguised kill: Choke lift (R6 vs R6) | 206 | 6.9 | no | `StandIn_DisguisedKill.blend` |
| The Litter: stack (floor 3) | Idle | 120 | 4.0 | yes | `litter/export/Stack_Idle.fbx` |
| | Walk | 40 | 1.33 | yes | `Stack_Walk.fbx` |
| | Run | 24 | 0.8 | yes | `Stack_Run.fbx` |
| | Form | 120 | 4.0 | no | `Stack_Form.fbx` |
| | Scatter | 84 | 2.8 | no | `Stack_Scatter.fbx` |
| | Kill: Bite | 110 | 3.7 | no | `Stack_Kill.fbx` + `Stack_Kill_Victim.blend` |
| The Litter: litterling | Idle | 120 | 4.0 | yes | `litter/export/Litterling_Idle.fbx` |
| | Walk | 16 | 0.53 | yes | `Litterling_Walk.fbx` |
| | Run | 8 | 0.27 | yes | `Litterling_Run.fbx` |
| The Receiver (floor 4) | Idle | 120 | 4.0 | yes | `receiver/export/Receiver_Idle.fbx` |
| | Walk | 36 | 1.2 | yes | `Receiver_Walk.fbx` |
| | Run | 20 | 0.67 | yes | `Receiver_Run.fbx` |
| | CallStart | 45 | 1.5 | no | `Receiver_CallStart.fbx` |
| | CallLoop | 120 | 4.0 | yes | `Receiver_CallLoop.fbx` |
| | Kill: Neck grab and stab | 120 | 4.0 | no | `Receiver_Kill.fbx` + `Receiver_Kill_Victim.blend` |

Every action is also in each monster's `export/<Monster>_Roblox.blend` on its rig
(`PosterMonster_Rig`, `StandIn_Rig`, `Stack_Rig`, `Litterling_Rig`, `Receiver_Rig`), so you can
export them yourself with your plugin.

## General rules for the monster animations

- **In place.** The Humanoid (or your script) does the moving; no animation moves the root.
- **Loops are seamless:** the last frame equals the first.
- **Plain keys.** Legs (and hands holding things) were solved with IK while animating, then
  baked to plain rotation keys, so nothing needs constraints or a special exporter.
- **Only the pelvis moves.** `LowerTorso` (litterling: `Body`) has translation keys for the
  bob and sway; every other bone is rotation only. The one exception is the stack's `Slot_`
  bones, which also move in `Form` and `Scatter`.
- **One-shots hand off cleanly:** `Transform` ends on `TransformLoop`'s first frame, and
  `CallStart` ends on `CallLoop`'s. `Form` ends on `Idle`'s first frame, and `Scatter` starts
  from it.
- **Exported at each model's export scale**, so they play on your scaled-up models the same
  way the walk and run do.

### Matching speed

The feet are matched to these ground speeds. At any other WalkSpeed, scale the track:
`track:AdjustSpeed(humanoid.WalkSpeed / <speed>)`.

| Monster | Walk (studs/s) | Run (studs/s) |
|---|---|---|
| Dewey | 3.7 | 11.1 |
| CRT Man | 3.3 | 14.1 |
| Stack | 3.2 | 12.2 |
| Litterling | 1.7 | 8.2 |
| Receiver | 4.3 (average; it comes in bursts) | 15.6 |

## Dewey (poster monster)

He's paper, so his steps are light: toes land first, the body barely dips, and the run floats
between steps.

- **Idle:** hunched and still, with a slow sway. The head drifts from side to side, the fingers
  twitch, one shoulder shrugs, and the peeling sheets flutter.
- **Walk:** a slow, crouched stalk with light toe-first steps. The arms drag behind and the head
  stays steady and tilted.
- **Run:** a predatory run, leaning in. The shoulders counter-twist and the arms swing loose
  like pendulums with relaxed elbows. The claws ease open at the front of each swing, and the
  head stays locked ahead.

## CRT Man (Stand-In)

He walks slow and stooped. When he chases, he straightens up into long strides that are faster
than they look.

- **Idle:** stooped, swaying a little. The monitor drifts and tips as if he's watching you, and
  his long fingers curl and uncurl, one hand then the other.
- **Walk:** long, slow, stooped strides. The arms hang and barely swing.
- **Run:** tall, upright and relentless. He barely leans, and the monitor stays locked on you,
  tipped slightly. His huge smooth strides have almost no bounce. His arms hang long, swinging
  only a little and slightly late, like dead weight.
- **Transform** (one-shot): he stiffens and straightens, then both hands fly up and clamp onto
  the sides of his monitor. It jolts down in his grip, and he hunches over it and wrenches it
  side to side.
- **TransformLoop:** the wrenching hold. The monitor shakes in his hands, his body heaves and
  trembles, and his fingers clench.

## The Litter

**Stack.** The stack is always heaving. Every creature keeps shifting and looking about on its
slot, a few turn right round, and each footstep sends a wobble up through them, reaching the
higher ones later.

- **Idle:** hunched and heaving, two slow breaths. The head turns, looking about, the finger
  legs flex, and the creatures fidget.
- **Walk:** a heavy, hunched lumber with flat-footed steps. The arms swing low.
- **Run:** a heavy, rolling charge that throws its weight from foot to foot, so every thud jolts
  the creatures. The long arms reach up in front, finger legs spread as if clawing at you, and
  curl as they pull back.
- **Form** (one-shot): the creatures stand in a ring round it, facing in. The dark mass rises out
  of the floor. From the legs up, they scuttle in, turn up onto it, crawl up over the ones
  already in place and settle. The head creatures go on last. It rears up, arms wide and mouth
  open, and settles into `Idle`.
- **Scatter** (one-shot): from `Idle`, it shudders and crouches, then lets go and keeps sinking
  (it doesn't straighten up again). From the top down, the creatures crawl fast to the floor,
  turn the right way up, scuttle out and stop in a ring, facing out. Meanwhile the mass slumps
  and sinks into the floor.
- In `Form` and `Scatter`, nothing hops and nothing floats. On the floor each creature rests on
  it; climbing, it keeps to the outside of the stack, belly to it.

**Litterling.**

- **Idle:** still and breathing, turning to look about. A front leg taps twice, then it rears up
  with its front legs feeling the air, and settles.
- **Walk:** a spider-like alternating gait. Left legs 1 and 3 and right legs 2 and 4 step
  together, then the other four.
- **Run:** the same gait, fast and low, leaning in.

**Swapping litterlings and the stack in the game:**

- **Into the stack:** run litterlings to the creatures' places on `Form`'s first frame, swap
  them for the stack playing `Form`, and blend into `Idle` at the end.
- **Out of the stack:** play `Scatter`. At its end, swap the stack for litterlings where its
  creatures stopped, in a ring about 5 to 7 studs from the centre (with the stack 10 studs tall).
- **Reading each creature's place:** each of the 30 creatures rides its own `Slot_` bone. Read
  `bone.TransformedWorldCFrame` just before the track ends, or pause it on its last frame. The
  bone sits at the creature's centre, and its -Z is the way the creature faces. Hide the stack
  and spawn the litterlings in the same frame.
- **Scaling the litterlings:** the creatures are 0.85 to 1.3 times a litterling's size. With the
  stack at 10 studs, scale a litterling at its export size by about 1.1 to 1.7 to match.
- **The floor hides the mass:** it's under the floor at the start of `Form` and the end of
  `Scatter`, so a solid floor covers it. The hands and feet (and the creatures on them) stay on
  the mass.
- **Re-import `Stack.fbx`** together with `Form` and `Scatter`. Each creature's legs are now
  skinned to that creature only, so they can leave the body cleanly.
- **Litterling rig:** `Root` → `HumanoidRootNode` (static) → `Body`. Always import litterling
  animations onto the current model; the old model's animations leave the body frozen.

## The Receiver

- **Idle:** hunched, two slow heavy breaths. The phone head tilts as if listening, the claw
  slowly closes and opens, and the handset stays still.
- **Walk:** "quick bursts". Hunched strides that hurry and catch, so the steps come in spurts.
  The claw arm swings and the handset arm holds on.
- **Run:** low, loose and predatory, like a cord monster. He's bent far over with the phone head
  up, rolling side to side over each foot. The long arms hang low and wide, and the elbows and
  claw whip a beat behind like coiled cord. Every step sends a springy wobble through him.
- **CallStart** (one-shot): he looks down at the handset and lifts it, elbow leading up and out.
  The handset turns up against his head, which tips over to meet it.
- **CallLoop:** listening, with the handset against his head. Two slow breaths. The head leans
  into the handset and eases off, the claw's fingers drum one after another, and the dial in his
  chest dials three digits.

## The kills

Each kill is a pair: the monster's half (an FBX) and the R6 player's half (a .blend keyed on
your R6 rig). Start both on the same frame, with the player's HumanoidRootPart a set distance in
front of the monster's, facing it, and both anchored. The markers are timeline markers on the
player's .blend. Add them in Studio and listen with `GetMarkerReachedSignal`.

### How they're animated

- **Pose to pose**, like a hand-animated shot. Every big move has an anticipation (a wind-up),
  then a fast strike that eases into its hold. Reaches and throws follow arcs. There's
  follow-through: the player's head and limbs drag behind, and the monster's head and spine lag
  its hips.
- **The monster's face stays locked on the player**, so a first-person camera on the player's
  head gets the scare.
- **Real grips:** the palm sits flat on the R6 part it grabs, and each finger closes joint by
  joint until it touches the part, so fingers wrap round it instead of floating or going
  through.
- **The R6 half uses sparse key poses**, not a key every frame (about 34 to 46 per kill).
  Blender's Bezier eases between them.
- **Hits stop hard:** the stab, snap, bite, death and floor impact have vector handles.
- **Falls look heavy.** They accelerate into the floor, hit hard and bounce once. Then the body
  lies flat in the pose it landed in and holds it: no floating, no raised leg, and no switching
  poses after death.
- **Reactions come after the hit,** never before it.

### The kills, one by one

| Kill | Frames | Distance (studs) | Markers (frame) |
|---|---|---|---|
| Dewey: Neck snap | 100 | 3.4 | `Grab` 18 (QTE starts), `Snap` 51 (QTE ends, crack), `Drop` 60, `End` 100 |
| CRT Man: Collar grab | 130 | 3.6 | `Grab` 17 (avatar on screen, static starts, QTE starts), `Death` 72 (QTE ends), `Drop` 90, `End` 130 |
| Stack: Bite | 110 | 3.6 | `Grab` 18 (save window opens), `Bite` 45 (black + crunch, window closes), `Throw` 70, `End` 110 |
| Receiver: Neck grab and stab | 120 | 3.8 | `Grab` 16 (QTE starts), `Stab` 43 (blood, QTE ends), `RipOut` 68, `Drop` 74, `End` 120 |
| CRT Man disguised: Choke lift | 206 | 1.9 (walks in from 6 studs further back) | `Grab` 104 (QTE starts), `Death` 158 (QTE ends), `Drop` 172, `Reveal` 196 (glitch back to the suit), `End` 206 |

**Dewey, Neck snap**

1. His head tilts, curious. He sinks low, long arms swung back with the claws spread, and holds a
   beat.
2. He lunges, swinging both claws round in a wide arc, and clamps them on the sides of the
   player's head.
3. He rises tall, yanking the player off their feet and up to his mask, and studies their face
   while they claw at his forearms and kick.
4. Wind-up: his body coils one way as he slowly turns their head the same way.
5. He snaps it violently the other way. He lets go: the body lands, folds and tips back with the
   head still turned the wrong way.

**CRT Man, Collar grab**

1. His monitor jerks round. He draws up and back, right hand drawn back, and holds a beat.
2. One long lunge: he seizes the player's collar and hoists them up to his screen.
3. The monitor cocks from side to side, studying them, with sharp twitches, while they kick and
   shove at the screen.
4. He pulls them close and they convulse and go limp.
5. He drops them: they buckle and slam onto their back. He ends standing upright over the body,
   looking down at it.

**Stack, Bite**

1. It draws up to full height, leaning back with arms flung wide and every creature bristling.
2. It crashes forward, pins the player's arms at the shoulders and hoists them to its head.
3. The head creature draws back, mouth gaping, trembling, then bites down on the player's head.
4. It thrashes them left, right and left, then throws them down on their back.
5. It chews, and the creatures turn to look at the body.

**Receiver, Neck grab and stab**

1. His phone head snaps round. He coils, his free right hand drawn back.
2. One long step: he grabs the player's neck with the right hand (the one without the phone) and
   hoists them off their feet.
3. The left claw goes up overhead: elbow out, claw hooked toward them, chest leaning back. They
   see it and reach for it.
4. He drives it down through their chest. They jolt, grab at it and look down at it.
5. He twists it, they go slack, he pushes it in again, rips it out wide, flings them aside and
   flicks the claw clean.

His animation includes your hand edits: they're kept untouched as `Kill_source` in
`receiver/receiver.blend`. Only his right hand and its fingers are rebuilt on top, so they grip
the throat.

**CRT Man in disguise, Choke lift** (R6 against R6, both in `StandIn_DisguisedKill.blend`)

1. The "teammate" stares a beat, then walks over like a normal player.
2. It grabs the player by the throat and lifts them one-handed in two jolts.
3. It holds them up, squeezing every few beats, its head tipping over more each time.
4. They go limp. It lets go and they land, buckle, fall onto their back, bounce and settle.
5. Its arm comes down in two drops and its head snaps upright.

The disguise is stop motion: held poses that snap from one to the next, with constant
interpolation and a key only where the pose changes. The player moves smoothly. In the file,
`InternalArmature` is the killer (`StandIn_DisguisedKill_Killer`) and `InternalArmature.001`
is the player (`StandIn_DisguisedKill_Victim`). Trigger it when the disguise is about 8 studs
away.

### The R6 .blend files

- **Each `*_Kill_Victim.blend` is a copy of your `Blender_R6.blend`.** The action
  `<Monster>_Kill_Victim` is on `InternalArmature`, frames 0 to `End`. Export it with your R6
  exporter.
- **The control rig is off.** `__PrimaryArmature` is hidden, and its constraints on
  `InternalArmature` are muted, so the keys drive the body directly. Unmute them to pose with
  the controls again.
- **The monster is there for reference.** It sits in the `Monster (reference)` collection,
  playing its half at in-game size. Hide or delete it before exporting if your exporter picks it
  up.
- **A `KILL_README` text block** in each file explains the same things.

### In Studio

1. Import `<Monster>_Kill.fbx` onto the monster with the Animation Editor and publish it.
2. Export the player's action from the .blend, bring it in on an R6 rig, add the markers and
   publish it.
3. Line them up and play both at Action4 priority. On the dying player's client, lock the camera
   to their head. [KILLS.md](KILLS.md) has the ready-made `playKill` and `lockCameraToHead`
   functions.
4. If the player escapes a QTE, stop both tracks with a short fade and unanchor them.

The in-game sizes the kills are made for: Dewey 10 studs, CRT Man 11, the stack 10, the Receiver
10, next to a standard 5-stud R6 player.

## Rebuilding

The scripts are in each monster's `src/`, plus the shared tools in `shared/`:

- **Walks, runs and idles:** `anim_core.py`.
- **Kills:** `kill_core.py` and `kill_anim.py`.
- **Hand grips:** `grip.py`.
- **Still contact sheets:** `anim_sheet.py` (walks, runs and idles) and `kill_sheet.py` (kills).

Each README's "Rebuilding" section has the exact commands. To change the Receiver's kill by
hand, edit `Kill_source` and re-run `receiver/src/receiver_kill.py`.
