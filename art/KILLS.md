# Kill animations

Each monster has a kill: a pair of animations, one for the monster and one for the R6 player
it kills, made to play together. Each kill is 4 s long and works in first and third person:
the player's head is aimed at the monster's face at every key moment, so a camera locked to
their head gets the jumpscare.

| Monster | Kill | Monster animation | Player animation (R6, Blender) |
|---|---|---|---|
| Dewey (poster monster, floor 1) | Snatch | `poster_monster/export/PosterMonster_Kill.fbx` | `poster_monster/export/PosterMonster_Kill_Victim.blend` |
| CRT Man (Stand-In, floor 2) | Broadcast into Channel change | `stand_in/export/StandIn_Kill.fbx` | `stand_in/export/StandIn_Kill_Victim.blend` |
| The Litter (stack, floor 3) | Pulled in | `litter/export/Stack_Kill.fbx` | `litter/export/Stack_Kill_Victim.blend` |
| The Receiver (floor 4) | Hang up | `receiver/export/Receiver_Kill.fbx` | `receiver/export/Receiver_Kill_Victim.blend` |

Each one feels different from the player's eyes: CRT Man holds you up to his screen and turns
your head like a channel knob, so the view rolls round; Dewey hangs you upside down in front
of his mask; the stack drags you along the floor and up to its head creature's mouth; the
Receiver slams you onto your back and hangs the handset up on your face.

They're made for the heights you set in Studio: Dewey 10 studs, CRT Man 11, the stack 10, the
Receiver 10, next to a standard 5-stud R6 player. The monster animations are exported at the
same scale as each monster's other animations, so they play on your scaled models the way the
walk and run do.

## The player's half: the R6 .blend files

Each `*_Kill_Victim.blend` is a copy of your `Blender_R6.blend` with the kill keyed on it:

- **The animation** is the action `<Monster>_Kill_Victim` on `InternalArmature` (the armature
  with a bone per R6 part), 30 fps, frames 0-120. Export it with your R6 exporter as usual.
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

**Dewey: "Snatch".** He drops into a crouch, darts in low and snatches the player by the ankle,
whipping them off their feet and up. He dangles them upside down in front of his mask,
turning them slowly, his own head tipped right over to match theirs, grinning. Then he swings
them up and slams them into the floor, and crouches over them, claws pinning them, his mask
sinking down over their face.

| Marker | Frame | Use it for |
|---|---|---|
| `Snatch` | 12 | |
| `Dangle` | 34 | **QTE starts.** The slowed jingle |
| `Slam` | 76 | **QTE ends.** They hit the floor |
| `Wrap` | 84 | Start slapping wet posters over the camera, one at a time |
| `Covered` | 104 | The last poster, "WELCOME!" |
| `End` | 120 | |

**CRT Man: "Broadcast" into "Channel change".** His monitor snaps round to the player, he
lunges and clamps both hands on their head, the way he grips his own monitor, and yanks them
off their feet up to his screen. He smacks the side of their head twice, like a broken TV,
then turns their head like a channel knob, click by click, so the view rolls round. The signal
cuts and he hurls them to the floor.

| Marker | Frame | Use it for |
|---|---|---|
| `Grip` | 14 | **QTE starts.** If he was disguised, glitch him back to the suit here |
| `Broadcast` | 30 | Put the player's face on his `Screen`, live |
| `Smack` | 50, 60 | A burst of static and color split on each |
| `Channel` | 66 | **QTE ends.** The view glitches into his slices as it rolls |
| `NoSignal` | 88 | His screen and the player's camcorder cut to NO SIGNAL |
| `Thrown` | 100 | They hit the floor |
| `End` | 120 | |

**The Litter: "Pulled in".** It rears up, then its right arm shoots out, stretching as the
creatures in it spread apart, and yanks the player off their feet, face down on the floor. It
drags them in, tug by tug, then hauls them up to its head creature's open mouth and pulls them
face first into its body, closing its other arm over them while the pile writhes.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 14 | **The save window opens:** a teammate's light on the stack now makes it drop them |
| `Floor` | 22 | They hit the floor |
| `Tug` | 32, 42, 52 | Each pull: skittering, a jolt |
| `Lift` | 58 | **The window closes** |
| `Mouth` | 66 | The head creature's mouth is in their face |
| `Black` | 74 | The camera is inside the stack: cut to black, skittering, blinking eyes |
| `End` | 120 | |

**The Receiver: "Hang up".** His phone head snaps round, he lunges and seizes the player by the
throat with his claw, lifts them and slams them down on their back. He crouches over them,
the phone head hanging over their face, and holds the handset to their ear while the dial in
his chest dials, digit after digit. Then he raises the handset high and slams it down on
their face, like hanging up a phone.

| Marker | Frame | Use it for |
|---|---|---|
| `Grab` | 12 | |
| `Slammed` | 26 | They hit the floor |
| `Handset` | 44 | The handset is at their ear: play their voice line back, crackly |
| `DialStart` | 48 | **QTE starts.** Each dial click darkens the screen |
| `DialEnd` | 86 | **QTE ends** |
| `HangUp` | 98 | The handset hits the camera: dial tone, black |
| `End` | 120 | |

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
| Dewey | 4.6 |
| CRT Man | 4.2 |
| The stack | 4.8 |
| The Receiver | 4.5 |

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
