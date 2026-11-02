# Kill animations

Each monster has a kill: a pair of animations, one for the monster and one for the R6 player
it kills, made to play together. They're short (100 frames, 3.3 s), simple and grounded: one
clear grab, a hold while the game's effects play, then the player dies and crumples. The
player's head stays on the monster at the key moments, so a camera locked to it gets the
scare.

| Monster | Kill | Monster animation | Player animation (R6, Blender) |
|---|---|---|---|
| Dewey (poster monster, floor 1) | Poster wrap | `poster_monster/export/PosterMonster_Kill.fbx` | `poster_monster/export/PosterMonster_Kill_Victim.blend` |
| CRT Man (Stand-In, floor 2) | Collar grab | `stand_in/export/StandIn_Kill.fbx` | `stand_in/export/StandIn_Kill_Victim.blend` |
| The Litter (stack, floor 3) | Swarmed | `litter/export/Stack_Kill.fbx` | `litter/export/Stack_Kill_Victim.blend` |
| The Receiver (floor 4) | Neck grab and stab | `receiver/export/Receiver_Kill.fbx` | `receiver/export/Receiver_Kill_Victim.blend` |

From the player's eyes: CRT Man holds you face to face with his screen (your avatar on it,
static building); Dewey crushes your face into his wet posters; the stack shoves you onto your
back and its head creature's mouth comes down on you before the pile goes over the camera; the
Receiver lifts you by the neck, then you look down at his claw in your chest.

They're made for the heights you set in Studio: Dewey 10 studs, CRT Man 11, the stack 10, the
Receiver 10, next to a standard 5-stud R6 player. The monster animations are exported at the
same scale as each monster's other animations, so they play on your scaled models the way the
walk and run do.

## The player's half: the R6 .blend files

Each `*_Kill_Victim.blend` is a copy of your `Blender_R6.blend` with the kill keyed on it:

- **The animation** is the action `<Monster>_Kill_Victim` on `InternalArmature` (the armature
  with a bone per R6 part), 30 fps, frames 0-100. Export it with your R6 exporter as usual.
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

**Dewey: "Poster wrap".** He steps in, clamps his rolled-poster claws on the player's
shoulders and yanks them up against his chest, face first into the wet posters, wrapping his
long arms round them, his mask bent down over their head. He squeezes, tighter with each
breath, while they struggle less and less, then lets them slide down and crumple at his feet.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 10 | **QTE starts** |
| `Wrap` | 22 | Their face hits his chest: start slapping wet posters over the camera, one at a time |
| `Covered` | 66 | The last poster, "WELCOME!". **QTE ends** |
| `Drop` | 72 | He lets go |
| `End` | 100 | |

**CRT Man: "Collar grab".** He takes one long step in, grabs the player by the collar and hauls
them up onto their toes, holding their face a forearm's length from his screen, his monitor
bent down at them. He holds them there, still, while they pull at his wrist. Then they go limp,
he lets go, and they crumple at his feet.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 12 | Show the player's avatar on his `Screen` and start the static, getting louder. **QTE starts** |
| `Death` | 74 | The static peaks: they die. **QTE ends** |
| `Drop` | 80 | He lets go |
| `End` | 100 | |

If he was disguised as a teammate, glitch him back to the suit at `Grab`.

**The Litter: "Swarmed".** It lurches in and slams both hands onto the player's shoulders,
shoves them over onto their back and collapses on top of them, its head creature's open mouth
coming down at their face as the pile goes over them. Pinned underneath, they push at it while
the creatures writhe and turn to look at them, until they stop moving.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 10 | **The save window opens:** a teammate's light on the stack now makes it drop them |
| `Floor` | 24 | They hit the floor |
| `Swarm` | 34 | The pile lands on them: dark, skittering, pairs of eyes blinking. **The window closes** |
| `End` | 100 | |

**The Receiver: "Neck grab and stab".** His phone head snaps round, he steps in and seizes the
player by the neck with his left hand (the handset pressed across their throat), lifting them
onto their toes. He holds them a moment, head cocked, drawing his claw back, then drives it
through their torso. They look down at it. He pulls it out and drops them.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 12 | **QTE starts** |
| `Stab` | 44 | Blood on the player's screen. **QTE ends** |
| `Drop` | 74 | He lets go |
| `End` | 100 | |

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
| Dewey | 3.8 |
| CRT Man | 3.6 |
| The stack | 3.6 |
| The Receiver | 3.8 |

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
vTrack:GetMarkerReachedSignal("Wrap"):Connect(function()
    -- start the posters, ...
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

The kills are made in Blender with `shared/kill_core.py`: the R6 player is posed with the
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
