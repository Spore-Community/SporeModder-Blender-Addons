# SporeModder Blender Add-ons — Blender 5.x Migration Design

Date: 2026-06-17
Status: Approved (design); pending implementation plan

## Goal

Port the entire add-on so it registers and runs on **Blender 5.x only** (clean break; 4.x
support is dropped). This unblocks observing/fixing the two known RW4 animation bugs (export
shared-parent glitch; morph import), which are explicitly **out of scope** for this work — this
migration must not change animation *behavior*, only the Blender API plumbing it sits on.

Target: Blender 5.1 (the installed/test version). `bl_info["blender"]` set to `(5, 0, 0)`.

## Scope

In scope: make the whole add-on load and its import/export operators run on Blender 5.x —
RW4 (mesh, skeleton, animation, morph handles, materials), GMDL, muscle, citywall, materials,
add-on updater, and the viewport handle drawing.

Out of scope: fixing Bug 1 (export, bones sharing a parent) and Bug 2 (morph import). These get
their own spec afterward, once the add-on runs on 5.1 and the bugs are observable. No unrelated
refactoring.

## Confirmed API facts (verified on Blender 5.1.2 via `_test/_apicheck.py`)

- `Action.fcurves`, `Action.groups`, `Action.id_root` are **removed**. An Action now exposes only
  `slots` and `layers`.
- A slot is created with `slot = action.slots.new('OBJECT'|'KEY', name)`; `slot.target_id_type`
  ('OBJECT'/'KEY') replaces the old `action.id_root`.
- `bpy_extras.anim_utils.action_ensure_channelbag_for_slot(action, slot)` returns an
  `ActionChannelbag` that **still exposes `.fcurves` (with `.new(...)`) and `.groups`**. So once we
  obtain the channelbag, the existing F-curve / group / `keyframe_points.insert` code works almost
  unchanged.
- Action is bound to a datablock via `ad.action = act; ad.action_slot = slot`
  (where `ad = id_data.animation_data` after `id_data.animation_data_create()`).
- `animation_data.nla_tracks` / `track.strips.new(...)` still exist (slotted actions do not remove
  NLA); strips just need the action's slot set.
- `gpu.state.blend_set('ALPHA')` exists and replaces the removed `bgl` blend calls.
- Built-in GPU shader names could not be validated headless (no GPU context in `--background`);
  the correct name for 5.x must be confirmed at runtime. This only affects viewport handle drawing,
  not import/export or headless tests.

## False positives (audited, do NOT change)

These were flagged by the audit but remain valid in Blender 5.x: `mesh.from_pydata(...)`,
`mesh.update(calc_edges=True)`, `mesh.*.foreach_set(...)`, `obj.shape_key_add(...)`,
`shape_keys.key_blocks`, `shape_keys.use_relative`, `bpy.ops.object.mode_set(...)` and the pose/mesh
operators, curve `splines.new` / `dimensions`. The harness round-trip confirms they still behave.

## Components

### 1. `anim_compat.py` (new) — thin compatibility layer for the slotted-Action API

Single responsibility: map the removed legacy-Action ergonomics onto the 5.x slotted-action API so
the animation import/export logic stays intact and readable. Public surface:

- `channelbag_for(action, id_type) -> ActionChannelbag`
  Ensure the action has a slot of `id_type` ('OBJECT' or 'KEY'); return its channelbag (exposes
  `.fcurves`, `.groups`). Idempotent — reuses an existing matching slot.
- `assign_action(id_data, action, id_type) -> ActionSlot`
  `id_data.animation_data_create()` (if needed), set `.action` and `.action_slot`; return the slot.
- `get_target_id_type(action) -> str`
  Read the (single) slot's `target_id_type`; replaces reads of `action.id_root`. Returns `''` if no
  slot. Used by the exporter to classify shape-key vs armature actions.
- `iter_fcurves(action) -> Iterable[FCurve]`
  Iterate the F-curves across the action's slot channelbag(s); replaces `for fc in action.fcurves`.

Depends on: `bpy`, `bpy_extras.anim_utils`. Testable in isolation headless.

### 2. Animation call-site migration (3 files, behavior-preserving)

- `rw4_importer.py` (~18 sites): replace `action.fcurves.new(...)`/`action.groups.new(...)` with
  calls on `anim_compat.channelbag_for(action, id_type)`; replace `action.id_root = X` with
  `anim_compat.assign_action(...)`/slot creation; replace `animation_data.action = act` assignments
  with `anim_compat.assign_action(...)`; keep NLA strip code but ensure slot is set; replace
  `action.id_root` reads in `add_nla_strips` with `anim_compat.get_target_id_type(action)`.
- `rw4_exporter.py` (~9 sites): replace `action.id_root == 'KEY'` with
  `anim_compat.get_target_id_type(action) == 'KEY'`; replace `for fc in action.fcurves` /
  `for group in action.groups` iteration with `anim_compat.iter_fcurves(action)` / channelbag
  groups; replace `animation_data.action = action` with `anim_compat.assign_action(...)`; NLA
  iteration stays.
- `anim_exporter.py` (2 sites): `for fc in action.fcurves` → `anim_compat.iter_fcurves(action)`.

### 3. `rw4_animation_config.py` — bgl → gpu

- Remove `import bgl`.
- Replace the 4 `bgl.glEnable/glBlendFunc` calls in the draw callback with `gpu.state.blend_set('ALPHA')`
  (and reset to `'NONE'` after drawing). Drop the line/polygon smooth calls (no 1:1 replacement;
  not load-bearing).
- Centralize the built-in shader fetch in one helper and use the 5.x-correct shader name (confirm at
  runtime); remove the dead `bpy.app.version[0] == 4` branch.
- `PointerProperty` on `bpy.types.Action`, `draw_handler_add/remove`, and the PropertyGroup
  register/unregister pattern stay (still valid in 5.x).

### 4. Materials & other importers — socket names + dead-branch cleanup

- `gmdl_importer.py`, `materials/static_model.py`, `materials/skinpaint_part.py`,
  `materials/mineral_paint_part.py`: confirm Principled BSDF socket names against 5.x ("Base Color",
  "Normal", "Specular IOR Level"); remove dead `bpy.app.version < (3, 6)` / `version[0] == 4`
  branches now that 5.x is the floor.
- `geo_nodes.py`: keep the `interface.new_socket(...)` path; remove the Blender-2.x branches and the
  legacy `node_group.outputs/inputs.new` path.
- `muscle_importer.py` / `muscle_exporter.py`, `citywall_importer.py`/`exporter.py`: verified largely
  via harness; fix only what the harness/run surfaces.

### 5. `__init__.py` and updater

- `bl_info["blender"]` → `(5, 0, 0)`; update the comment.
- `addon_updater_ops.py`: remove dead `scene_update_post` (pre-4.x) branches, keeping
  `depsgraph_update_post`. `bgl`-free already.

### 6. Verification harness (`_test/`)

Extend the existing `_test/_parse.py` (binary-only) and `_test/_repro.py` (full import via the add-on)
into a round-trip smoke test driven by Blender 5.1 headless:

- For each of the 4 test files (`trg_seamon`, `ce_mouth_jaw_carnivore_01`, `ce_weapon_horn_01`,
  `ce_details_playful_01`): **import → export → re-import**.
- Assert structural parity between the first import and the re-import: counts of bones, animation
  channels, keyframes per channel, shape keys, morph handles; and that no exception is raised.
- This is a regression gate for the migration plumbing — it asserts the pipeline still runs and is
  structurally stable. It deliberately does **not** assert the animation bugs are fixed (correctness
  of transforms is the next spec's concern).
- The harness must register the real add-on on 5.1 (no stubs) once bgl/Action migration lands;
  until then the stubbed `_repro.py` remains for incremental testing.

## Data flow (animation, post-migration)

Import: RW4 `KeyframeAnim`/`MorphHandle` → `import_animation` → `anim_compat.assign_action(id_data,
action, id_type)` + `anim_compat.channelbag_for(action, id_type)` → `channelbag.fcurves.new(...)` +
`keyframe_points.insert(...)` (unchanged math) → NLA strip.

Export: Blender Action → `anim_compat.get_target_id_type` (classify) → `anim_compat.iter_fcurves` to
read keys → existing RW4 keyframe writer (unchanged math).

## Error handling

- `anim_compat` helpers raise a clear `RuntimeError` if `bpy_extras.anim_utils` lacks
  `action_ensure_channelbag_for_slot` (i.e. Blender < 4.4) so a too-old Blender fails loudly at the
  first animation op rather than mysteriously.
- Existing `rw4_base.ModelError` handling in `import_rw4` is preserved.

## Testing strategy

1. Unit-level: `anim_compat` helpers exercised headless on a throwaway action (slot creation,
   channelbag reuse, target type read).
2. Smoke/round-trip: the `_test/` harness over the 4 files on Blender 5.1.
3. Manual: load the add-on in Blender 5.1 GUI, import one creature, confirm no console errors and
   handles draw.

## Sequencing

1. `rw4_animation_config.py` bgl→gpu so the add-on registers on 5.1.
2. `anim_compat.py` + migrate the 3 animation files; get import working headless.
3. Materials/other importers + dead-branch cleanup; `__init__`/updater.
4. Harness round-trip green on 5.1.

## Out-of-scope follow-ups (tracked, not done here)

- Bug 1: export glitch when bones share a parent (`rw4_exporter.py` keyframe loop iterates dict
  order; must process parents before children).
- Bug 2: morph import (skeletal-deform morph handles mapped to bones positionally, ignoring
  `channel_id`).
