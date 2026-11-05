# Kill animations

Each monster has a kill: a pair of animations, one for the monster and one for the R6 player
it kills, made to play together. They're short (3.3 to 4.3 s) and keyed pose to pose like a
hand-animated shot: an anticipation before every big move, fast strikes that ease into their
holds, arcs on every reach and throw, follow-through (the player's head and limbs drag behind
when they're jerked around, and the monster's head and spine lag its hips), and weighty falls
that accelerate into the floor and bounce once. The monster's face stays locked on the player
while its body twists, so a camera on the player's head gets the scare.

| Monster | Kill | Monster animation | Player animation (R6, Blender) |
|---|---|---|---|
| Dewey (poster monster, floor 1) | Neck snap | `poster_monster/export/PosterMonster_Kill.fbx` | `poster_monster/export/PosterMonster_Kill_Victim.blend` |
| CRT Man (Stand-In, floor 2) | Collar grab | `stand_in/export/StandIn_Kill.fbx` | `stand_in/export/StandIn_Kill_Victim.blend` |
| The Litter (stack, floor 3) | Bite | `litter/export/Stack_Kill.fbx` | `litter/export/Stack_Kill_Victim.blend` |
| The Receiver (floor 4) | Neck grab and stab | `receiver/export/Receiver_Kill.fbx` | `receiver/export/Receiver_Kill_Victim.blend` |

From the player's eyes: Dewey's cracked mask looms in and fills the view, then the view whips
round as he snaps your neck; CRT Man holds your face to his screen (your avatar on it, static
building); the stack's needle-toothed head creature rears back and bites down over the camera;
the Receiver's phone head stares you down, then you look down at his claw in your chest.

They're made for the heights you set in Studio: Dewey 10 studs, CRT Man 11, the stack 10, the
Receiver 10, next to a standard 5-stud R6 player. The monster animations are exported at the
same scale as each monster's other animations, so they play on your scaled models the way the
walk and run do.

## The player's half: the R6 .blend files

Each `*_Kill_Victim.blend` is a copy of your `Blender_R6.blend` with the kill keyed on it:

- **The animation** is the action `<Monster>_Kill_Victim` on `InternalArmature` (the armature
  with a bone per R6 part), 30 fps, frames 0 to the end marker. Export it with your R6 exporter as usual.
- **It's keyed as key poses, not a key on every frame.** The whole body is keyed on the same
  frames (the key poses, plus a few breakdowns where the monster's hand moves fast and the
  body has to stay in it), and Blender's Bezier eases between them. The hits (the stab, the
  snap, the bite, the moment of death, and the body hitting the floor) have vector handles, so
  they stop hard instead of easing. Each fall ends in the pose it lands in, flat on the floor,
  and holds it.
- **The control rig** (`__PrimaryArmature`) is hidden, and InternalArmature's constraints to it
  are muted, so the keys drive the body directly. To pose it with the controls again, unmute
  them (the keys then stop showing).
- **The beats** are timeline markers, with the same names as the markers below.
- **The monster** is in the `Monster (reference)` collection, at your in-game size, playing
  its half of the kill, standing where the game should put it. Hide or delete it before
  exporting if your exporter picks up other objects.
- A `KILL_README` text block in each file says the same.

The kill scripts also keep the player's pose in a preview .blend with the player as blocks and
a camera on their head, for rendering checks (see Rebuilding).

## What happens, and the markers

Put a keyframe marker (or a named keyframe) at each of these frames when you set the player's
animation up in Studio, and the game can start its screen effects, sounds and QTEs on cue with
`track:GetMarkerReachedSignal(name)` (or `KeyframeReached` for named keyframes). Frames are at
30 fps.

**Dewey: "Neck snap"** (100 frames). His head tilts slowly, curious. He sinks low, his neck
jutting and his long arms swung back behind him with the claws spread; a beat. Then he lunges,
swings both rolled-poster claws round in a wide arc and clamps them on the sides of the player's
head, and rises up tall, yanking them off their feet to his mask. He studies their face, the
mask tilting slowly from side to side, while they claw at his forearms and kick. The wind-up:
his elbows rise and his whole body coils one way as he turns their head slowly the same way,
and holds it while they kick wildly; then a violent snap the other way. The body jerks and goes
slack. He lets go: it lands on its feet, folds and tips back, the head still turned the wrong
way. His hands stay up a beat, then he straightens, watching it.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 18 | **QTE starts.** The slowed jingle |
| `Snap` | 51 | **QTE ends.** The crack; cut to black, or slap the posters over the camera ("WELCOME!") |
| `Drop` | 60 | He lets go |
| `End` | 100 | |

**CRT Man: "Collar grab"** (130 frames). His monitor jerks round to the player. He draws
himself up and back, the monitor tipped back to look down at them, his right hand drawn back; a
beat. Then one long lunge and he seizes them by the collar, gathers them in and hoists them up
to his screen at arm's length. The monitor cocks slowly from side to side, studying them, with
a sharp twitch now and then, while they kick, pull at his wrist and shove at the screen. He
pulls them in close to it; they convulse and go limp. He holds the body up a beat, tilting the
monitor at it, lifts it a little and opens his hand: it lands on its feet, the knees buckle and
it slams onto its back. He steps back and stands over it, his monitor looking down at it.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 17 | Show the player's avatar on his `Screen` and start the static, getting louder. **QTE starts** |
| `Death` | 72 | The static peaks: they die. **QTE ends** |
| `Drop` | 90 | He lets go |
| `End` | 130 | |

If he was disguised as a teammate, glitch him back to the suit at `Grab`.

**The Litter: "Bite"** (110 frames). It draws itself up to its full height, leaning back, arms
flung wide and every creature in it bristling; a beat. Then it crashes forward and clamps both
hands on the player's shoulders, pinning their arms, and hoists them up to its head. The head
creature draws slowly back, mouth gaping, the whole stack coiling back with it while they
strain away and kick; it holds there, trembling, then lunges and bites down on their head. It
thrashes them left, right and left, swings them back across itself and throws them: they
tumble and slam down on their back. The head creature chews, and the creatures in the pile turn
to look at the body.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 18 | **The save window opens:** a teammate's light on the stack now makes it drop them |
| `Bite` | 45 | The mouth closes over the camera: black, crunch, skittering. **The window closes** |
| `Throw` | 70 | |
| `End` | 110 | |

**The Receiver: "Neck grab and stab"** (120 frames). His phone head snaps round to the player.
He coils (chest back, hips turned, his free right hand drawn back with the fingers splayed), then
lunges with one long step and seizes them by the neck with it, straightens up and hoists them
off their feet while they kick and pull at his wrist. He raises his left arm, the one holding
the handset, high: the elbow out to the side, the claw up above his head and hooked toward them,
his chest leaning back and turned away. They see it and reach out at it. He holds it, then
drives it down through their chest. Their body jolts back and the knees jerk up; they grab at
the arm in them and look down at it. He lifts them higher on it, twists it, and they go slack.
He pushes it in once more, rips it out with a wide sweep, swings them across and flings them
aside, then flicks the claw clean and watches them.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 16 | **QTE starts** |
| `Stab` | 43 | Blood on the player's screen. **QTE ends** |
| `RipOut` | 68 | |
| `Drop` | 74 | He throws them |
| `End` | 120 | |

**CRT Man in disguise: "Choke lift"** (R6 against R6, 206 frames). Used when he kills while
still disguised as a teammate. The "teammate" stands still for a beat, staring, then walks over
to the player like a normal player would, stops in front of them, reaches out and grabs them by
the throat, and lifts them off the floor one-handed in two jolts. It holds them up while they
kick and claw at its arm, squeezing every few beats, its head tipping over a little more each
time. They go limp; it opens its hand and they drop, land on their feet, buckle and fall onto
their back, bounce and settle flat. Its arm comes down in two drops and its head snaps
upright.

The disguise is stop motion, like its other disguise animations: distinct poses held for 4 to
6 frames that snap from one to the next with no in-betweens (the walk is four held poses a
step). Parts are moved as well as rotated, as in your own animations: an arm swinging forward
crosses in front of the body, a lifted leg rises to fake a bent knee. The player moves smoothly.
In the .blend the killer's action has a key only where its pose changes, with constant
interpolation (held until the next key), and the player's has key poses that Blender eases
between.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 104 | **QTE starts** |
| `Death` | 158 | **QTE ends** |
| `Drop` | 172 | |
| `Reveal` | 196 | Glitch him back into the suit |
| `End` | 206 | |

Both halves are in `stand_in/export/StandIn_DisguisedKill.blend`, a copy of your two-rig file:
`InternalArmature` is the disguise (action `StandIn_DisguisedKill_Killer`) and
`InternalArmature.001` the player (action `StandIn_DisguisedKill_Victim`). Their constraints to
the control rigs are muted and the control rigs hidden; your poses are still on the control
rigs. Place the killer's HumanoidRootPart **1.9 studs** in front of the player's, facing them;
its body starts 6 studs further back and walks onto it, so trigger the kill when the disguise
is about 8 studs away (or hide the gap with the screen effects).

If the player escapes a QTE, stop both tracks (with a short fade) and unanchor them.

## Setting up in Studio

1. **The monster's half:** import `<Monster>_Kill.fbx` with the Animation Editor's FBX import
   onto your monster (as with its other animations), and publish it.
2. **The player's half:** open `<Monster>_Kill_Victim.blend`, export the action on
   `InternalArmature` with your R6 exporter, bring it into Studio on an R6 rig as you usually
   do, add the markers above, and publish it.

## Playing a kill

Both halves start at the same moment, with the two characters in place: the player's
HumanoidRootPart a set distance in front of the monster's, at floor level, facing it. Anchor
both for the kill so nothing pushes them apart.

| Monster | Distance (studs) |
|---|---|
| Dewey | 3.4 |
| CRT Man | 3.6 |
| The stack | 3.6 |
| The Receiver | 3.8 |
| CRT Man in disguise | 1.9 (its body walks in from 6 studs further back) |

On the server:

```lua
--!strict
-- Lines the player up in front of the monster and plays both halves of a kill.
local function playKill(monster: Model, victim: Model, monsterAnim: Animation, victimAnim: Animation,
    distance: number): (AnimationTrack, AnimationTrack)
    local mHum = monster:FindFirstChildOfClass("Humanoid") :: Humanoid
    local mRoot = mHum.RootPart :: BasePart
    local vHum = victim:FindFirstChildOfClass("Humanoid") :: Humanoid
    local vRoot = vHum.RootPart :: BasePart

    -- the floor under the monster, and the way it faces (level)
    local floorY = mRoot.Position.Y - mRoot.Size.Y / 2 - mHum.HipHeight
    local flat = Vector3.new(mRoot.CFrame.LookVector.X, 0, mRoot.CFrame.LookVector.Z).Unit
    local base = CFrame.lookAt(Vector3.new(mRoot.Position.X, floorY, mRoot.Position.Z),
        Vector3.new(mRoot.Position.X, floorY, mRoot.Position.Z) + flat)

    mRoot.Anchored = true
    vRoot.Anchored = true
    mRoot.CFrame = base + Vector3.new(0, mRoot.Position.Y - floorY, 0)
    -- an R6 HumanoidRootPart sits 3 studs above the floor
    vRoot.CFrame = base * CFrame.new(0, 3, -distance) * CFrame.Angles(0, math.pi, 0)

    local mTrack = (mHum:FindFirstChildOfClass("Animator") :: Animator):LoadAnimation(monsterAnim)
    local vTrack = (vHum:FindFirstChildOfClass("Animator") :: Animator):LoadAnimation(victimAnim)
    mTrack.Priority = Enum.AnimationPriority.Action4
    vTrack.Priority = Enum.AnimationPriority.Action4
    mTrack.Looped = false
    vTrack.Looped = false
    mTrack:Play(0.1)
    vTrack:Play(0.1)
    return mTrack, vTrack
end
```

Listen for the markers on the player's track:

```lua
vTrack:GetMarkerReachedSignal("Grab"):Connect(function()
    -- start the QTE, the static, ...
end)
```

**First person:** on the dying player's client, lock the camera to their head for the kill, so
it rides every jolt, lift and lean-in. Hide their own head, as Roblox does in first person:

```lua
--!strict
local RunService = game:GetService("RunService")

-- Rides the camera on the character's head until the returned function is called.
local function lockCameraToHead(character: Model): () -> ()
    local camera = workspace.CurrentCamera
    local head = character:WaitForChild("Head") :: BasePart
    head.LocalTransparencyModifier = 1
    camera.CameraType = Enum.CameraType.Scriptable
    RunService:BindToRenderStep("KillCamera", Enum.RenderPriority.Camera.Value + 1, function()
        camera.CFrame = head.CFrame * CFrame.new(0, 0.15, -0.55)
    end)
    return function()
        RunService:UnbindFromRenderStep("KillCamera")
        camera.CameraType = Enum.CameraType.Custom
        head.LocalTransparencyModifier = 0
    end
end
```

Everyone else sees it in third person, as it plays.

I haven't been able to test any of this in Studio.

## Rebuilding

The kills are keyed pose to pose with `shared/kill_anim.py` (eased tracks, arcs, lagged follow-through) on top of `shared/kill_core.py`: the R6 player is posed with the
standard R6 joints (the same Motor6D C0s and C1s as a Roblox R6 character) and placed in the
monster's scene at the in-game scale, so whatever the monster grabs, the player's body follows.
Impacts shake the player's head, so a camera locked to it shakes too.

```bash
python3 poster_monster/src/poster_kill.py poster_monster/poster_monster.blend poster_monster/export PREVIEW.blend
python3 stand_in/src/standin_kill.py stand_in/stand_in.blend stand_in/export PREVIEW.blend
python3 litter/src/litter_kill.py litter PREVIEW.blend
python3 receiver/src/receiver_kill.py receiver/receiver.blend receiver/export PREVIEW.blend
# then each monster's export script, and to look at one:
python3 shared/kill_sheet.py PREVIEW.blend sheet.png   # a third-person row and a first-person row
```

Each kill script keys the monster's `Kill` action into its .blend, writes the player's half
onto a copy of `shared/r6/Blender_R6.blend` (your R6 rig), and saves a preview .blend with the
player as blocks and a camera on their head.

The Receiver's `Kill` action has been edited by hand in Blender, so `receiver_kill.py` keeps it
exactly as it is and only works out the player's half against it (their neck in his right hand,
their chest on his claw while it's in them). `--regenerate-monster` replaces it with the
generated version. To edit his animation again, change the `Kill` action in
`receiver/receiver.blend` and re-run the script to fit the player to it.
