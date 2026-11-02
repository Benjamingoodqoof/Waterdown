# Kill animations

Each monster has a kill: a pair of animations, one for the monster and one for the R6 player
it kills, made to play together. Each kill is 4 s long and works in first and third person:
the player's head is aimed at the monster's face at every key moment, so a camera locked to
their head gets the jumpscare.

| Monster | Kill | Monster animation | Player animation (R6) |
|---|---|---|---|
| Dewey (poster monster, floor 1) | Close-up into Poster wrap | `poster_monster/export/PosterMonster_Kill.fbx` | `poster_monster/export/PosterMonster_Kill_Victim.rbxmx` |
| CRT Man (Stand-In, floor 2) | Broadcast | `stand_in/export/StandIn_Kill.fbx` | `stand_in/export/StandIn_Kill_Victim.rbxmx` |
| The Litter (stack, floor 3) | Pulled in | `litter/export/Stack_Kill.fbx` | `litter/export/Stack_Kill_Victim.rbxmx` |
| The Receiver (floor 4) | Hold the line into Dial | `receiver/export/Receiver_Kill.fbx` | `receiver/export/Receiver_Kill_Victim.rbxmx` |

They're made for the heights you set in Studio: Dewey 10 studs, CRT Man 11, the stack 10, the
Receiver 10, next to a standard 5-stud R6 player. The monster animations are exported at the
same scale as each monster's other animations, so they play on your scaled models the way the
walk and run do.

## What happens, and the markers

The player's animation has named keyframes at each beat. `track.KeyframeReached` fires with
the name, so the game can start its screen effects, sounds and QTEs on cue.

**Dewey: "Close-up" into "Poster wrap".** He lunges and clamps his rolled-poster claws on the
player's shoulders, then bends all the way down until his cracked mask is a hand's width from
their face, the empty eye holes staring into the lens, his head slowly tipping over. Then he
straightens and pulls them into his chest, wrapping his arms round them.

| Marker | Time | Use it for |
|---|---|---|
| `Grab` | 0.67 s | |
| `LeanIn` | 1.13 s | The mask fills the view. **QTE starts.** The slowed jingle |
| `Wrap` | 2.07 s | **QTE ends.** Start slapping wet posters over the camera, one at a time |
| `Covered` | 3.33 s | The last poster, "WELCOME!" |
| `End` | 4.0 s | |

**CRT Man: "Broadcast".** He goes still and watches, then takes one long stride in and grips
the player's head with both hands, the way he grips his own monitor. He lifts them off their
feet and holds their face up to his screen, looking them over, then drops them.

| Marker | Time | Use it for |
|---|---|---|
| `Grip` | 0.87 s | **QTE starts.** If he was disguised, glitch him back to the suit here |
| `Broadcast` | 1.93 s | Put the player's face on his `Screen`, live |
| `NoSignal` | 2.87 s | His screen and the player's camcorder cut to NO SIGNAL; the monitor jolts. **QTE ends** |
| `Drop` | 3.27 s | He lets go |
| `End` | 4.0 s | |

**The Litter: "Pulled in".** The stack rears up, then its right arm shoots out, stretching as
the creatures in it spread apart, and closes on the player's chest. It drags them in, tug by
tug, its head creature's open mouth turned on them, then yanks them face first into its body
and closes its other arm over them while the pile writhes.

| Marker | Time | Use it for |
|---|---|---|
| `Grab` | 0.87 s | **The save window opens:** a teammate's light on the stack now makes it drop them |
| `Yank` | 1.93 s | **The window closes** |
| `Black` | 2.33 s | The camera is inside the stack: cut to black, skittering, blinking eyes. Hide the player's body if you like |
| `End` | 4.0 s | |

**The Receiver: "Hold the line" into "Dial".** His phone head snaps round to the player. He
lunges, grabs them round the chest with his claw and lifts them to his face, presses his
handset to their ear, and turns the empty dial socket in his head right up to their face while
the dial in his chest dials, digit after digit. Then his head drives into theirs and he drops
them.

| Marker | Time | Use it for |
|---|---|---|
| `Grab` | 0.8 s | |
| `Handset` | 1.53 s | The handset is at their ear: play their voice line back, crackly |
| `DialStart` | 1.93 s | **QTE starts.** Each dial click darkens the screen |
| `DialEnd` | 3.27 s | **QTE ends.** Busy signal |
| `Black` | 3.47 s | His head hits the camera |
| `Drop` | 3.53 s | He lets go |
| `End` | 4.0 s | |

If the player escapes a QTE, stop both tracks (with a short fade) and unanchor them.

## Setting up in Studio

1. **The monster's half:** import `<Monster>_Kill.fbx` with the Animation Editor's FBX import
   onto your monster (as with its other animations), and publish it.
2. **The player's half:** in Studio, right-click ServerStorage and choose **Insert from
   File...**, then pick the `.rbxmx`. It adds a KeyframeSequence. Right-click it and choose
   **Save to Roblox** to publish it as an animation. (Or put it under
   `ServerStorage.RBX_ANIMSAVES.<an R6 dummy's name>` and open it in the Animation Editor to
   look at it first.)

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
vTrack.KeyframeReached:Connect(function(name: string)
    if name == "Wrap" then
        -- start the posters, close the QTE, ...
    end
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

```bash
python3 poster_monster/src/poster_kill.py poster_monster/poster_monster.blend poster_monster/export PREVIEW.blend
python3 stand_in/src/standin_kill.py stand_in/stand_in.blend stand_in/export PREVIEW.blend
python3 litter/src/litter_kill.py litter PREVIEW.blend
python3 receiver/src/receiver_kill.py receiver/receiver.blend receiver/export PREVIEW.blend
# then each monster's export script, and to look at one:
python3 shared/kill_sheet.py PREVIEW.blend sheet.png   # a third-person row and a first-person row
```

Each kill script keys the monster's `Kill` action into its .blend, writes the player's
`.rbxmx`, and saves a preview .blend with the player as blocks and a camera on their head.
