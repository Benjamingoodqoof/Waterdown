# The Stand-in (floor 2)

The floor-2 monster for REM CYCLE: an 8.3 ft display mannequin still wearing a faded
Orange Court work uniform. She has no face, so she can pass for anyone. She copies the
players and their friends, moving the way they move. Built procedurally in Blender 5.2
(`bpy`) as a Roblox R15 character, so player animations and emotes play on her as they are.

![turnaround](renders/studio_turnaround.png)

## Look

- **Body:** satin orange fiberglass, like an old store mannequin. It has mold seams down the
  sides of the limbs, scuffs, patches of grime and a few paint chips.
- **Head:**
  - A smooth egg with only a ghost of a face: a brow, a nose ridge, shallow eye sockets and a
    hint of lips, as if the face was sanded off. It's blank from across a room, and close up
    it nearly looks like someone.
  - The neck is short, with a seam ring and a metal bolt where the head screws on.
- **Hair:** a wig with a center part, sitting slightly crooked on the head. Long panels hang
  over the shoulders and down the back, and stay off the face.
- **Joints:** ball joints with visible gaps at the shoulders, elbows, wrists, hips, knees and
  ankles, so she reads as jointed even standing still.
- **Hands:** plain mitten hands with the fingers molded together (grooves only) and a separate
  thumb.
- **Uniform:**
  - A faded rust Orange Court dress: a bodice with a Peter Pan collar, four buttons, puff
    sleeves and a pleated skirt.
  - A cream half apron with the Orange Court sun logo on its pocket and a bow at the back.
  - It's dusty across the shoulders, stained, and has a small tear near the hem.
- **Shoes:** flat, molded onto the feet.
- **Badge ("her last copy"):**
  - A crooked "ORANGE COURT / HELLO, MY NAME IS" tag. The names Ashley, Marcus, Dev and Jen
    are written one under another, and each is crossed out: everyone she has been so far.
  - The photo window shows a flash snapshot of a blocky avatar dated 10 29 '03. It's a
    separate part, `BadgePhoto`, so the game can swap in the headshot of the player she's
    copying (see below).

## Files

| Path | What it is |
|---|---|
| `export/StandIn.fbx` | R15 character for Roblox's 3D Importer: 7.4 studs tall, origin at the pelvis, textures embedded |
| `export/StandIn_Roblox.blend` | The same 7.4-stud model and rig, for adding animations and exporting them with a Roblox plugin |
| `export/StandIn.glb` | Same model as glTF with 1024 px PBR textures |
| `stand_in.blend` | Blender source at real-world size (2.53 m), with rig, weights and materials |
| `textures/roblox/` | 1024 px maps for SurfaceAppearance (`standin_color`, `standin_normal`, `standin_roughness`) and the default `badge_photo` |
| `textures/` | 2048 px authoring maps, plus `orange_court_logo.png` (usable as a decal or sign) |
| `renders/` | Previews: `studio_*` is the rest pose Studio shows, `mimic_dorfic_*` her waving like a friend in a dim Orange Court room. `rom_sheet.png` is the deformation test |
| `src/` | Scripts that generate all of the above |

## Budget

| MeshPart | Triangles |
|---|---|
| Head (head, neck, wig and hair) | 6,596 |
| UpperTorso (bodice, collar, buttons, badge) | 3,026 |
| LowerTorso (skirt, apron, pelvis) | 6,784 |
| Left/RightUpperArm (shoulder ball, puff sleeve) | 2,164 each |
| Left/RightLowerArm | 588 each |
| Left/RightHand | 872 each |
| Left/RightUpperLeg | 860 each |
| Left/RightLowerLeg | 864 each |
| Left/RightFoot | 712 each |
| BadgePhoto | 2 |
| **Total** | **28,528** |

Every part uses one texture atlas, except BadgePhoto, which has its own image. The rig has
17 bones, and vertices have at most 3 bone weights.

## Importing into Roblox Studio

1. Open the 3D Importer (**Import 3D**) and choose `export/StandIn.fbx`. The body parts and
   bones use R15 names. If the importer doesn't detect the rig as R15 by itself, set
   **Rig Type** to **R15** under **Rig General**.
2. **Size:** she's 7.4 studs tall, the same scale as the poster monster (8.3 ft next to a
   6 ft explorer). Use `Model:ScaleTo()` to adjust, or re-export with another height (see
   Rebuilding).
3. **Standing on the floor:** the rig's root is at the pelvis, 4.5 studs above the feet. If
   her feet don't touch the ground, set the Humanoid's HipHeight. Run this once in the command
   bar with the model selected:

   ```lua
   local m = game.Selection:Get()[1]
   local hum = m:FindFirstChildOfClass("Humanoid")
   local root = hum.RootPart or m:FindFirstChild("HumanoidRootPart")
   local cf, size = m:GetBoundingBox()
   hum.HipHeight = (root.Position.Y - root.Size.Y / 2) - (cf.Position.Y - size.Y / 2)
   print("HipHeight", hum.HipHeight)
   ```
4. **Facing:** she's exported with −Z forward, Roblox's forward direction. If she faces away,
   rotate her 180°.
5. **Textures:** upload `standin_color`, `standin_normal` and `standin_roughness` from
   `textures/roblox/`. Make one `SurfaceAppearance` with ColorMap, NormalMap and RoughnessMap
   set to them, then put a copy in each of the 15 body parts.
6. **BadgePhoto** doesn't get a SurfaceAppearance (that would hide its TextureID). Upload
   `badge_photo.png` and set it as its `TextureID`.

## Posing as players

Her joints match a Roblox R15 player's, so anything made for R15 characters plays on her:
the default walk, run, idle, jump and sit animations, animation packs and emote animations.

- **Moving like a player:** give her a Humanoid with an Animator and an Animate script. To
  get one, press Play, copy the `Animate` script from your own character, stop, and paste
  its source into a server `Script` named `Animate` inside her.
- **Moving like one specific player:** the `Animate` script in each player's character holds
  their animation pack's ids. Copy them onto hers:

  ```lua
  -- Make the Stand-in use the same walk, run, idle, jump and sit animations as `player`.
  local function copyAnimations(standIn: Model, player: Player)
      local theirs = player.Character and player.Character:FindFirstChild("Animate")
      local mine = standIn:FindFirstChild("Animate")
      if not (theirs and mine) then
          return
      end
      for _, group in theirs:GetChildren() do
          local target = mine:FindFirstChild(group.Name)
          for _, anim in group:GetChildren() do
              local copy = target and target:FindFirstChild(anim.Name)
              if anim:IsA("Animation") and copy and copy:IsA("Animation") then
                  copy.AnimationId = anim.AnimationId
              end
          end
      end
  end
  ```

  Emotes play the same way: load the emote's animation id with
  `Animator:LoadAnimation()`.
- **Their face on her badge:** set BadgePhoto's texture to the player's headshot.

  ```lua
  local Players = game:GetService("Players")

  local function setBadgePhoto(standIn: Model, userId: number)
      local ok, image = pcall(Players.GetUserThumbnailAsync, Players, userId,
          Enum.ThumbnailType.HeadShot, Enum.ThumbnailSize.Size150x150)
      if ok then
          (standIn:FindFirstChild("BadgePhoto", true) :: MeshPart).TextureID = image
      end
  end
  ```

  I haven't been able to test this in Studio. If the photo stays blank, put a `SurfaceGui`
  with an `ImageLabel` on BadgePhoto and set the label's `Image` instead.

Don't use `Humanoid:ApplyDescription()` to copy a player, because it would replace her body
parts with theirs.

## Rig

- **Root:** `Root` → `HumanoidRootNode` → `LowerTorso`, all at the pelvis, the bone layout
  Roblox uses for skinned characters.
- **Body:** `LowerTorso` → `UpperTorso` → `Head`
- **Arms:** `UpperTorso` → `Left/RightUpperArm` → `LowerArm` → `Hand`
- **Legs:** `LowerTorso` → `Left/RightUpperLeg` → `LowerLeg` → `Foot`

The bones point straight up with no roll, like Roblox's own R15 rigs, so an R15 animation
turns each joint about the same axis it would on a player. Each body part is weighted to its
own bone only, except two areas:

- **Hair:** blends from `Head` to `UpperTorso` at the shoulders, so it stays draped when she
  turns her head.
- **Skirt and apron:** blend from `LowerTorso` into the thighs toward the hem, so the skirt
  follows the legs when she walks, runs or sits.

`renders/rom_sheet.png` shows her in rest, run, sit, arms up, twist and mimic poses.

## Rebuilding

Needs `pip install bpy` (Blender as a Python module), Pillow and numpy. The scripts reuse
helpers from `../poster_monster/src`. Run from `src/`:

```bash
python3 standin_textures.py ../textures                  # paint the atlas, badge photo and logo
python3 standin_build.py ../stand_in.blend               # model, rig and weights
python3 standin_render.py ../stand_in.blend ../renders   # previews (--look studio|dorfic, --pose rest|mimic)
python3 standin_rig_check.py ../stand_in.blend ../renders/rom_sheet.png
python3 standin_export.py ../stand_in.blend ../export    # FBX, GLB and Roblox .blend (--height-studs 7.38)
```

Everything is seeded, so a rebuild gives the same mannequin.

- **Joint positions, rig and atlas layout:** `standin_common.py`
- **Mimic pose:** `MIMIC` in `standin_render.py`
