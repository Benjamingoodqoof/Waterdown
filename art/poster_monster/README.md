# Poster Monster (floor 1)

The floor-1 monster for REM CYCLE: a 9 ft figure made of the building's soaked promo posters,
wearing a cracked plastic mask of the company's droplet mascot. Built procedurally in
Blender 5.2 (`bpy`), rigged for Roblox. Animations are not made yet.

![turnaround](renders/turnaround.png)

## Changes from the concept

- **Body:** gaunt and hunched, with a pinched waist, a long thin neck, and arms long enough that
  the rolled-poster claws hang past the knees.
- **Posters:** water-damaged, with tide-line stains, ink running, mold, fold cracks, and dark wet
  pulp showing between the sheets. The lower body is the most soaked.
- **Mask:** sun-faded and chipped, sitting crooked and taped onto a balled-up head of posters.
  - The eye holes are deep, empty sockets with black streaks running from them.
  - The painted grin is knife-cut open, with paint dripping from it.
  - It's cracked through, and one piece is bent out with a chunk missing.
- **Chest:** torn open on the front-left, with ribs made of rolled posters across a black hollow.
- **Loose paper:** wet sheets hang from the back, hips, head, one arm and one thigh. Thin strips
  drip from under the mask, the forearms and one thigh.
- **Posters on the body:** cheerful 2000s eco-tech promos ("A CLEANER TOMORROW", "JOIN THE
  FLOW"…). One has the mascot's eyes scribbled out.

## Files

| Path | What it is |
|---|---|
| `export/PosterMonster.fbx` | Rigged model for Roblox's 3D Importer, rest pose, textures embedded |
| `export/PosterMonster.glb` | Same model as glTF, with 1024 px PBR textures |
| `poster_monster.blend` | Blender source with rig, weights and materials (textures packed) |
| `textures/roblox/` | 1024 px maps for SurfaceAppearance (color, normal, roughness) |
| `textures/` | 2048 px authoring maps, plus `posters_clean_sheet.png` (undamaged poster art, usable as decals) |
| `renders/` | Previews, plus `rig_range_of_motion.png` (deformation test poses) |
| `src/` | Scripts that generate all of the above |

## Budget

| MeshPart | Triangles | Material |
|---|---|---|
| Body_Torso | 7,884 | paper atlas |
| Body_Arms | 6,460 | paper atlas |
| Body_Legs | 5,276 | paper atlas |
| Mask | 1,517 | mask |
| EyeGlow | 128 | plain (no texture) |
| **Total** | **21,265** | |

Each mesh is under 10k triangles. The skin has 68 bones and at most 4 bone weights per vertex.

## Importing into Roblox Studio

1. Open the 3D Importer (**Import 3D**) and choose `export/PosterMonster.fbx`.
2. **Size:** the model is built at real-world size, 2.72 m (9 ft). Check its height after
   import. The concept has it at 1.5× a 6 ft explorer, so aim for about 1.5× your avatar's
   height. Adjust with the importer's scale unit setting or `Model:ScaleTo()`.
3. **Facing:** it is exported with −Z forward, Roblox's forward direction. If it faces away in
   your setup, rotate it 180°.
4. **Textures:** upload the six PNGs in `textures/roblox/`, then add a `SurfaceAppearance` to
   each MeshPart:
   - `Body_Torso`, `Body_Arms`, `Body_Legs`: ColorMap `paper_color`, NormalMap
     `paper_normal`, RoughnessMap `paper_roughness`
   - `Mask`: `mask_color`, `mask_normal`, `mask_roughness`
5. **EyeGlow** is a tiny glint at the back of each eye socket. Set it to Neon to make it
   catch the light, or delete it for completely black holes.
6. To play animations later, add an `AnimationController` with an `Animator`. Use a
   `Humanoid` instead if you want `Humanoid:MoveTo()` pathing.

## Rig

- **Spine:** `Root` → `LowerTorso` → `Spine` → `UpperTorso` → `Neck` → `Head`
- **Arms:** `Left/RightShoulder` → `UpperArm` → `LowerArm` → `Hand` → `Index`, `Middle`,
  `Ring`, `Pinky`, `Thumb` (each `1`–`3`)
- **Legs:** `Left/RightUpperLeg` → `LowerLeg` → `Foot`
- **Loose sheets:** two bones each for flutter, `Flap…1` and `Flap…2`, on `FlapBackL`,
  `FlapBackR`, `FlapHipF`, `FlapHipR`, `FlapHipB`, `FlapHead`, `FlapArmL`, `FlapForearmR` and
  `FlapThighL`.

Names follow R15 where a matching bone exists. All bones deform.

## Rebuilding

Needs `pip install bpy` (Blender as a Python module), Pillow and numpy. Run from `src/`:

```bash
python3 textures.py ../textures                          # paint the textures
python3 build_model.py ../poster_monster.blend           # model, rig and weights
python3 render.py ../poster_monster.blend ../renders     # previews (--look studio|atrium)
python3 rig_check.py ../poster_monster.blend ../renders/rig_range_of_motion.png
python3 export.py ../poster_monster.blend ../export      # FBX + GLB for Roblox
```

Everything is seeded, so a rebuild gives the same monster. Proportions are in `skeleton.py`.
The mask shape is in `common.py`.
