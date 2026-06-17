# Blender 5.x Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the whole SporeModder add-on so it registers and runs on Blender 5.x, without changing animation behavior.

**Architecture:** Replace removed `bgl` calls with the `gpu` module so the add-on registers; introduce a thin `anim_compat.py` layer mapping the removed legacy-Action API (`fcurves`/`groups`/`id_root`) onto 5.x slotted actions, and route all animation call sites through it; clean up dead version branches in materials/updater. A headless round-trip harness over the 4 RW4 test files gates the work on Blender 5.1.

**Tech Stack:** Python, Blender 5.1 Python API (`bpy`, `bpy_extras.anim_utils`, `gpu`), run headless via `blender --background --factory-startup --python`.

## Global Constraints

- Target Blender floor: **5.0** (`bl_info["blender"] = (5, 0, 0)`). 4.x support is dropped; remove dead `bpy.app.version` branches for versions < 5.
- Animation **behavior must not change** — only the Blender API plumbing. No edits to the transform math in `process_animation`, `process_skeleton_action`, keyframe read/write, or `rw4_base.py`.
- Blender executable for all tests: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`.
- The add-on folder has hyphens; tests load it as module name `sporemodder_addons` via `importlib` (see Task 1 harness).
- Test RW4 files live in `_test/`: `trg_seamon.rw4`, `ce_mouth_jaw_carnivore_01.rw4`, `ce_weapon_horn_01.rw4`, `ce_details_playful_01.rw4`.
- Out of scope: Bug 1 (export shared-parent) and Bug 2 (morph import) fixes.

---

### Task 1: Test harness + `bgl`→`gpu` so the add-on registers on 5.1

**Files:**
- Create: `_test/_harness.py`
- Create: `_test/test_register.py`
- Modify: `rw4_animation_config.py:10-13` (imports), `:227-230` (shader fetch), `:274-277` (bgl calls)
- Modify: `__init__.py:11` (`bl_info` version)

**Interfaces:**
- Produces: `_test/_harness.py` with `load_addon(register=True) -> module` — does the `importlib` load under name `sporemodder_addons` and (optionally) calls the add-on's real `register()`. Returns the loaded add-on module. Used by every later test.

- [ ] **Step 1: Write the harness helper**

Create `_test/_harness.py`:

```python
import sys, os, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTDIR = os.path.join(REPO, "_test")
TEST_FILES = ["trg_seamon.rw4", "ce_mouth_jaw_carnivore_01.rw4",
              "ce_weapon_horn_01.rw4", "ce_details_playful_01.rw4"]


def load_addon(register=True):
    spec = importlib.util.spec_from_file_location(
        "sporemodder_addons", os.path.join(REPO, "__init__.py"),
        submodule_search_locations=[REPO])
    addon = importlib.util.module_from_spec(spec)
    sys.modules["sporemodder_addons"] = addon
    spec.loader.exec_module(addon)
    if register:
        addon.register()
    return addon
```

- [ ] **Step 2: Write the failing test**

Create `_test/test_register.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon

bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)

# The add-on must register cleanly and expose its custom Action property group.
assert hasattr(bpy.types.Action, "rw4"), "Action.rw4 not registered"
a = bpy.data.actions.new("t")
assert hasattr(a.rw4, "is_morph_handle"), "rw4.is_morph_handle missing"
print("TEST_REGISTER_OK")
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_register.py 2>&1 | grep -E "TEST_REGISTER_OK|Error|bgl"
```
Expected: FAIL — `ModuleNotFoundError: No module named 'bgl'` (raised while importing `rw4_animation_config`), no `TEST_REGISTER_OK`.

- [ ] **Step 4: Fix imports in `rw4_animation_config.py`**

Replace lines 10-13:
```python
import bpy
import gpu
import bgl
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
```
with:
```python
import bpy
import gpu
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
```

- [ ] **Step 5: Fix the shader fetch (lines 227-230)**

Replace:
```python
if bpy.app.version[0] == 4:
	shader = gpu.shader.from_builtin('UNIFORM_COLOR')
else:
	shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
```
with:
```python
shader = gpu.shader.from_builtin('UNIFORM_COLOR')
```
(The `2D_`/`3D_` shader-name prefixes were removed in Blender 4.0; `'UNIFORM_COLOR'` is correct for 5.x.)

- [ ] **Step 6: Replace the bgl blend calls (lines 274-277)**

Replace:
```python
	bgl.glEnable(bgl.GL_BLEND)
	bgl.glEnable(bgl.GL_LINE_SMOOTH)
	bgl.glEnable(bgl.GL_POLYGON_SMOOTH)
	bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
```
with:
```python
	gpu.state.blend_set('ALPHA')
```
(Line/polygon smoothing has no 1:1 `gpu` replacement and is not load-bearing; drop it.)

- [ ] **Step 7: Bump `bl_info` in `__init__.py` (line 11)**

Replace:
```python
	"blender": (4, 5, 0), # 2.8 - 4.5
```
with:
```python
	"blender": (5, 0, 0), # 5.x
```

- [ ] **Step 8: Run test to verify it passes**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_register.py 2>&1 | grep -E "TEST_REGISTER_OK|Error"
```
Expected: PASS — prints `TEST_REGISTER_OK`. (A non-fatal `addon_updater` network warning is acceptable; an `Error`/traceback is not.)

- [ ] **Step 9: Commit**

```bash
git add _test/_harness.py _test/test_register.py rw4_animation_config.py __init__.py
git commit -m "Register add-on on Blender 5.x: drop bgl, fix shader name, bump bl_info"
```

---

### Task 2: `anim_compat.py` — slotted-action compatibility layer

**Files:**
- Create: `anim_compat.py`
- Create: `_test/test_anim_compat.py`

**Interfaces:**
- Consumes: nothing (leaf module; depends only on `bpy`, `bpy_extras.anim_utils`).
- Produces:
  - `channelbag_for(action, id_type) -> ActionChannelbag` — ensure a slot of `id_type` ('OBJECT'|'KEY') exists on `action`, return its channelbag (which exposes `.fcurves` with `.new(...)` and `.groups` with `.new(...)`). Idempotent: reuses the existing slot of that type.
  - `assign_action(id_data, action, id_type) -> ActionSlot` — `id_data.animation_data_create()` if needed, set `.action` and `.action_slot`, return the slot.
  - `get_target_id_type(action) -> str` — return the first slot's `target_id_type`, or `''` if the action has no slot.
  - `iter_fcurves(action)` — yield every F-curve across the action's slot channelbags.

- [ ] **Step 1: Write the failing test**

Create `_test/test_anim_compat.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon

bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons import anim_compat

# channelbag_for is idempotent and exposes legacy-shaped fcurves/groups
act = bpy.data.actions.new("a")
cb1 = anim_compat.channelbag_for(act, 'OBJECT')
cb2 = anim_compat.channelbag_for(act, 'OBJECT')
assert cb1 == cb2, "channelbag_for not idempotent"
assert len(act.slots) == 1, f"expected 1 slot, got {len(act.slots)}"
assert hasattr(cb1.fcurves, "new") and hasattr(cb1.groups, "new")

# get_target_id_type reflects the slot
assert anim_compat.get_target_id_type(act) == 'OBJECT'
assert anim_compat.get_target_id_type(bpy.data.actions.new("empty")) == ''

# fcurves created via the channelbag are visible through iter_fcurves
grp = cb1.groups.new("g")
fc = cb1.fcurves.new("location", index=0)
fc.group = grp
fc.keyframe_points.insert(1, 5.0)
assert [f.data_path for f in anim_compat.iter_fcurves(act)] == ["location"]

# assign_action binds action+slot to a datablock
o = bpy.data.objects.new("o", None)
bpy.context.scene.collection.objects.link(o)
slot = anim_compat.assign_action(o, act, 'OBJECT')
assert o.animation_data.action == act
assert o.animation_data.action_slot == slot
print("TEST_ANIM_COMPAT_OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_anim_compat.py 2>&1 | grep -E "TEST_ANIM_COMPAT_OK|Error|ModuleNotFound"
```
Expected: FAIL — `ModuleNotFoundError: No module named 'sporemodder_addons.anim_compat'`.

- [ ] **Step 3: Write `anim_compat.py`**

```python
"""Compatibility shim mapping the legacy (pre-5.0) Blender Action API onto
slotted actions. Keeps the animation import/export call sites behavior-preserving."""
import bpy

try:
    from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
except ImportError:  # Blender < 4.4
    action_ensure_channelbag_for_slot = None


def _require():
    if action_ensure_channelbag_for_slot is None:
        raise RuntimeError(
            "This add-on requires Blender 5.x (slotted actions / "
            "bpy_extras.anim_utils.action_ensure_channelbag_for_slot).")


def _find_slot(action, id_type):
    for slot in action.slots:
        if slot.target_id_type == id_type:
            return slot
    return None


def channelbag_for(action, id_type):
    """Ensure a slot of id_type exists on action; return its channelbag."""
    _require()
    slot = _find_slot(action, id_type) or action.slots.new(id_type, "Slot")
    return action_ensure_channelbag_for_slot(action, slot)


def assign_action(id_data, action, id_type):
    """Bind action (with a slot of id_type) to id_data; return the slot."""
    _require()
    if id_data.animation_data is None:
        id_data.animation_data_create()
    slot = _find_slot(action, id_type) or action.slots.new(id_type, "Slot")
    id_data.animation_data.action = action
    id_data.animation_data.action_slot = slot
    return slot


def get_target_id_type(action):
    """First slot's target_id_type, or '' if the action has no slots."""
    return action.slots[0].target_id_type if len(action.slots) else ''


def iter_fcurves(action):
    """Yield every F-curve across the action's slot channelbags."""
    _require()
    for slot in action.slots:
        cb = action_ensure_channelbag_for_slot(action, slot)
        for fc in cb.fcurves:
            yield fc
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_anim_compat.py 2>&1 | grep -E "TEST_ANIM_COMPAT_OK|Error"
```
Expected: PASS — prints `TEST_ANIM_COMPAT_OK`.

- [ ] **Step 5: Commit**

```bash
git add anim_compat.py _test/test_anim_compat.py
git commit -m "Add anim_compat: slotted-action compatibility layer"
```

---

### Task 3: Migrate `rw4_importer.py` animation import to `anim_compat`

**Files:**
- Modify: `rw4_importer.py` — import line; `import_animation_shape_key` (519-527); `import_animation_channel` (529-558 signature + fcurve creation); `import_animation` (632-669); `add_nla_strips` (679-707).
- Create: `_test/test_import.py`

**Interfaces:**
- Consumes: `anim_compat.channelbag_for`, `anim_compat.assign_action`, `anim_compat.get_target_id_type` from Task 2.
- Produces: imports of the 4 test files run without exception; armature/shape-key actions carry F-curves through the new channelbag.

**Migration rule:** legacy `b_action.fcurves` / `b_action.groups` become channelbag access. Obtain the channelbag once where the action is set up, then use `channelbag.fcurves.new(...)` / `channelbag.groups.new(...)`. Replace `b_action.id_root = X` and `animation_data.action = X` with `anim_compat.assign_action(...)`. Replace `action.id_root` reads with `anim_compat.get_target_id_type(action)`.

- [ ] **Step 1: Write the failing test**

Create `_test/test_import.py`:

```python
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon, TEST_FILES, TESTDIR

target = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4

s = RW4ImporterSettings()
s.import_materials = False; s.import_skeleton = True
s.import_animations = True; s.extract_textures = False
path = os.path.join(TESTDIR, target)
try:
    with open(path, 'rb') as f:
        import_rw4(f, path, s)
except Exception:
    traceback.print_exc(); print("IMPORT_FAIL"); raise

n_actions = len(bpy.data.actions)
print(f"actions={n_actions}")
assert n_actions > 0, "no actions imported"
print("TEST_IMPORT_OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_import.py 2>&1 -- ce_weapon_horn_01.rw4 | grep -E "TEST_IMPORT_OK|id_root|fcurves|Error"
```
Expected: FAIL — `AttributeError: 'Action' object has no attribute 'id_root'` (or `fcurves`).

- [ ] **Step 3: Add the import**

At the top of `rw4_importer.py`, alongside the other `from . import ...` lines, add:
```python
from . import anim_compat
```

- [ ] **Step 4: Migrate `import_animation_shape_key` (519-527)**

Replace:
```python
	def import_animation_shape_key(self, animation, b_action):
		for channel in animation.channels:
			#TODO get from animation skeleton id? Theorically there should be a single mesh object
			key = self.b_meshes[0].shape_keys.key_blocks[get_name(channel.channel_id)]
			data_path = key.path_from_id('value')
			fcurve = b_action.fcurves.new(data_path)
			for keyframe in channel.keyframes:
				time = keyframe.time * rw4_base.KeyframeAnim.FPS
				fcurve.keyframe_points.insert(time, keyframe.factor)
```
with:
```python
	def import_animation_shape_key(self, animation, b_action):
		channelbag = anim_compat.channelbag_for(b_action, 'KEY')
		for channel in animation.channels:
			#TODO get from animation skeleton id? Theorically there should be a single mesh object
			key = self.b_meshes[0].shape_keys.key_blocks[get_name(channel.channel_id)]
			data_path = key.path_from_id('value')
			fcurve = channelbag.fcurves.new(data_path)
			for keyframe in channel.keyframes:
				time = keyframe.time * rw4_base.KeyframeAnim.FPS
				fcurve.keyframe_points.insert(time, keyframe.factor)
```

- [ ] **Step 5: Migrate `import_animation_channel` signature + fcurve creation (529-558)**

Change the signature to take a `channelbag` instead of `b_action`, and create groups/fcurves on it. Replace lines 529-558:
```python
	@staticmethod
	def import_animation_channel(
			b_pose_bone, b_action, b_action_group, channel, index, channel_keyframes):

		import_locrot = channel.keyframe_class in (rw4_base.LocRotScaleKeyframe, rw4_base.LocRotKeyframe)
		import_scale = channel.keyframe_class == rw4_base.LocRotScaleKeyframe

		fcurves_qr = []
		fcurves_vt = []
		fcurves_vs = []

		if import_locrot:
			data_path = b_pose_bone.path_from_id('rotation_quaternion')
			for i in range(4):
				fcurve = b_action.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_qr.append(fcurve)

			data_path = b_pose_bone.path_from_id('location')
			for i in range(3):
				fcurve = b_action.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_vt.append(fcurve)

		if import_scale:
			data_path = b_pose_bone.path_from_id('scale')
			for i in range(3):
				fcurve = b_action.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_vs.append(fcurve)
```
with (only `b_action` → `channelbag` in the signature and the three `.fcurves.new` calls):
```python
	@staticmethod
	def import_animation_channel(
			b_pose_bone, channelbag, b_action_group, channel, index, channel_keyframes):

		import_locrot = channel.keyframe_class in (rw4_base.LocRotScaleKeyframe, rw4_base.LocRotKeyframe)
		import_scale = channel.keyframe_class == rw4_base.LocRotScaleKeyframe

		fcurves_qr = []
		fcurves_vt = []
		fcurves_vs = []

		if import_locrot:
			data_path = b_pose_bone.path_from_id('rotation_quaternion')
			for i in range(4):
				fcurve = channelbag.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_qr.append(fcurve)

			data_path = b_pose_bone.path_from_id('location')
			for i in range(3):
				fcurve = channelbag.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_vt.append(fcurve)

		if import_scale:
			data_path = b_pose_bone.path_from_id('scale')
			for i in range(3):
				fcurve = channelbag.fcurves.new(data_path, index=i)
				fcurve.group = b_action_group
				fcurves_vs.append(fcurve)
```
The rest of `import_animation_channel` (the `keyframe_points.insert` loop, 560-617) is unchanged — it uses the local `fcurves_qr/vt/vs` lists.

- [ ] **Step 6: Migrate `import_animation` (632-669)**

Replace the shape-key branch (632-639):
```python
		if is_shape_key:
			bpy.context.view_layer.objects.active = self.b_mesh_objects[0]
			self.b_meshes[0].shape_keys.animation_data_create()
			self.b_meshes[0].shape_keys.animation_data.action = b_action

			b_action.id_root = 'KEY'

			self.import_animation_shape_key(animation, b_action)
```
with:
```python
		if is_shape_key:
			bpy.context.view_layer.objects.active = self.b_mesh_objects[0]
			anim_compat.assign_action(self.b_meshes[0].shape_keys, b_action, 'KEY')

			self.import_animation_shape_key(animation, b_action)
```

Replace the armature branch's action setup + group/channel loop (641-667). Replace:
```python
		else:
			b_action.id_root = 'OBJECT'

			bpy.context.view_layer.objects.active = self.b_armature_object
			bpy.ops.object.mode_set(mode='POSE')

			self.b_armature_object.animation_data_create()
			self.b_armature_object.animation_data.action = b_action

			bpy.ops.object.mode_set(mode='POSE')
			bpy.context.scene.frame_set(0)
			for bone in self.b_armature.bones:
				bone.select = True
			bpy.ops.pose.transforms_clear()

			channel_keyframes = self.process_animation(animation)
			for c, channel in enumerate(animation.channels):
				b_pose_bone = self.b_armature_object.pose.bones[c]
				b_action_group = b_action.groups.new(b_pose_bone.name)

				RW4Importer.import_animation_channel(
					b_pose_bone,
					b_action,
					b_action_group,
					channel,
					c,
					channel_keyframes)

			bpy.ops.object.mode_set(mode='OBJECT')
```
with (set up action+slot via compat, get the channelbag once, create groups + pass channelbag down):
```python
		else:
			bpy.context.view_layer.objects.active = self.b_armature_object
			bpy.ops.object.mode_set(mode='POSE')

			anim_compat.assign_action(self.b_armature_object, b_action, 'OBJECT')
			channelbag = anim_compat.channelbag_for(b_action, 'OBJECT')

			bpy.ops.object.mode_set(mode='POSE')
			bpy.context.scene.frame_set(0)
			for bone in self.b_armature.bones:
				bone.select = True
			bpy.ops.pose.transforms_clear()

			channel_keyframes = self.process_animation(animation)
			for c, channel in enumerate(animation.channels):
				b_pose_bone = self.b_armature_object.pose.bones[c]
				b_action_group = channelbag.groups.new(b_pose_bone.name)

				RW4Importer.import_animation_channel(
					b_pose_bone,
					channelbag,
					b_action_group,
					channel,
					c,
					channel_keyframes)

			bpy.ops.object.mode_set(mode='OBJECT')
```

- [ ] **Step 7: Migrate `add_nla_strips` id_root reads (686, 702)**

In `add_nla_strips`, replace the two `action.id_root` comparisons. Replace line 686:
```python
				if action.id_root != 'KEY':
```
with:
```python
				if anim_compat.get_target_id_type(action) != 'KEY':
```
and replace line 702:
```python
					if action.id_root == 'KEY':
```
with:
```python
					if anim_compat.get_target_id_type(action) == 'KEY':
```
The duplicate `animation_data_create()` calls at 683/699 remain valid (guarded by `if not ...animation_data`). NLA `nla_tracks` / `strips.new` calls stay unchanged.

- [ ] **Step 8: Run test to verify it passes (all 4 files)**

Run:
```bash
for f in trg_seamon ce_mouth_jaw_carnivore_01 ce_weapon_horn_01 ce_details_playful_01; do
  echo "== $f =="
  "/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_import.py 2>&1 -- "$f.rw4" | grep -E "TEST_IMPORT_OK|IMPORT_FAIL|actions=|Error"
done
```
Expected: each file prints `actions=<n>` (n>0) and `TEST_IMPORT_OK`, no `IMPORT_FAIL`/traceback.

- [ ] **Step 9: Commit**

```bash
git add rw4_importer.py _test/test_import.py
git commit -m "Migrate rw4_importer animation import to slotted actions via anim_compat"
```

---

### Task 4: Migrate `rw4_exporter.py` and `anim_exporter.py` to `anim_compat`

**Files:**
- Modify: `rw4_exporter.py` — import line; `id_root` read (1167); `action.fcurves` checks/iteration (999, 1058-1059, 1154); `animation_data.action` assignments (1205, 1575, 1618).
- Modify: `anim_exporter.py` — `action.fcurves` iteration (318).
- Create: `_test/test_export.py`

**Interfaces:**
- Consumes: `anim_compat.iter_fcurves`, `anim_compat.get_target_id_type`, `anim_compat.assign_action`, `anim_compat.channelbag_for`.
- Produces: a re-import of an exported file runs without exception (round-trip used in Task 6).

**Migration rule:** `action.id_root` reads → `anim_compat.get_target_id_type(action)`. `for fc in action.fcurves` → `for fc in anim_compat.iter_fcurves(action)`. `if not action.fcurves` → `if not any(anim_compat.iter_fcurves(action))`. `action.groups` iteration → channelbag groups. `animation_data.action = X` assignments → `anim_compat.assign_action(obj, X, 'OBJECT')`.

- [ ] **Step 1: Write the failing test**

Create `_test/test_export.py`:

```python
import sys, os, traceback, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon, TESTDIR

target = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4
from sporemodder_addons.rw4_exporter import export_rw4

s = RW4ImporterSettings()
s.import_materials = False; s.import_skeleton = True
s.import_animations = True; s.extract_textures = False
with open(os.path.join(TESTDIR, target), 'rb') as f:
    import_rw4(f, os.path.join(TESTDIR, target), s)

out = os.path.join(tempfile.gettempdir(), "out.rw4")
try:
    with open(out, 'wb') as f:
        export_rw4(f, False, False)
except Exception:
    traceback.print_exc(); print("EXPORT_FAIL"); raise
assert os.path.getsize(out) > 0, "empty export"
print("TEST_EXPORT_OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_export.py 2>&1 -- trg_seamon.rw4 | grep -E "TEST_EXPORT_OK|EXPORT_FAIL|id_root|fcurves|Error"
```
Expected: FAIL — `AttributeError` on `id_root` or `fcurves`.

- [ ] **Step 3: Add the import to `rw4_exporter.py`**

Alongside the other `from . import ...` lines, add:
```python
from . import anim_compat
```

- [ ] **Step 4: Migrate the `id_root` read (1167)**

Replace:
```python
		is_shape_key = action.id_root == 'KEY'
```
with:
```python
		is_shape_key = anim_compat.get_target_id_type(action) == 'KEY'
```

- [ ] **Step 5: Migrate `action.fcurves` iteration (999) and check (1154)**

Replace line 999 `for fcurve in action.fcurves:` with:
```python
		for fcurve in anim_compat.iter_fcurves(action):
```
Replace line 1154 `if not action.fcurves or action in ignored_actions:` with:
```python
		if not any(anim_compat.iter_fcurves(action)) or action in ignored_actions:
```

- [ ] **Step 6: Migrate the `action.groups` iteration (1058-1059)**

Replace:
```python
		for group in action.groups:
			for channel in group.channels:
```
with (read groups from the OBJECT channelbag):
```python
		for group in anim_compat.channelbag_for(action, 'OBJECT').groups:
			for channel in group.channels:
```

- [ ] **Step 7: Migrate the three `animation_data.action` assignments (1205, 1575, 1618)**

Replace line 1205:
```python
		self.b_armature_object.animation_data.action = action
```
with:
```python
		anim_compat.assign_action(self.b_armature_object, action, 'OBJECT')
```
Replace line 1575:
```python
		armature_obj.animation_data.action = mirrored_action
```
with:
```python
		anim_compat.assign_action(armature_obj, mirrored_action, 'OBJECT')
```
Replace line 1618:
```python
		armature_obj.animation_data.action = action
```
with:
```python
		anim_compat.assign_action(armature_obj, action, 'OBJECT')
```
The `animation_data_create()` calls at 1401/1574 and the NLA `nla_tracks`/`strips` iteration stay unchanged (still valid in 5.x). Note: after these edits there may be a now-redundant `animation_data_create()` immediately preceding an `assign_action` call — leave it; `assign_action` is a no-op when `animation_data` already exists.

- [ ] **Step 8: Migrate `anim_exporter.py` fcurves iteration (318)**

Add near the top of `anim_exporter.py` (with the other imports):
```python
from . import anim_compat
```
Replace line 318 `for fcurve in action.fcurves:` with:
```python
	for fcurve in anim_compat.iter_fcurves(action):
```

- [ ] **Step 9: Run test to verify it passes (skeletal + morph files)**

Run:
```bash
for f in trg_seamon ce_mouth_jaw_carnivore_01 ce_weapon_horn_01; do
  echo "== $f =="
  "/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_export.py 2>&1 -- "$f.rw4" | grep -E "TEST_EXPORT_OK|EXPORT_FAIL|Error"
done
```
Expected: each prints `TEST_EXPORT_OK`, no `EXPORT_FAIL`.

- [ ] **Step 10: Commit**

```bash
git add rw4_exporter.py anim_exporter.py _test/test_export.py
git commit -m "Migrate rw4_exporter and anim_exporter to slotted actions via anim_compat"
```

---

### Task 5: Materials, geo_nodes, updater — dead-branch cleanup for 5.x floor

**Files:**
- Modify: `gmdl_importer.py` (specular socket version branch ~229-242).
- Modify: `geo_nodes.py` (Blender-2.x branches ~12-13, 47-51, 101-125).
- Modify: `addon_updater_ops.py` (`scene_update_post` pre-4.x branches).

**Interfaces:**
- Consumes: nothing from prior tasks.
- Produces: no dead `bpy.app.version` branches for < 5; importing a model with materials runs clean.

- [ ] **Step 1: Write the failing/guard test**

Create `_test/test_materials.py`:

```python
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon, TESTDIR

bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4

s = RW4ImporterSettings()
s.import_materials = True; s.import_skeleton = True
s.import_animations = False; s.extract_textures = False
p = os.path.join(TESTDIR, "ce_mouth_jaw_carnivore_01.rw4")
try:
    with open(p, 'rb') as f:
        import_rw4(f, p, s)
except Exception:
    traceback.print_exc(); print("MAT_FAIL"); raise
print("TEST_MATERIALS_OK")
```

- [ ] **Step 2: Run it to see the current state**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_materials.py 2>&1 | grep -E "TEST_MATERIALS_OK|MAT_FAIL|Specular|Error"
```
Expected: note whether it passes or fails on a Principled BSDF socket name (`"Specular"` no longer exists; 5.x uses `"Specular IOR Level"`).

- [ ] **Step 3: Collapse the gmdl specular branch (gmdl_importer.py ~229-242)**

Replace the version-guarded block:
```python
		if bpy.app.version < (3, 6):
			material.node_tree.links.new(
				material.node_tree.nodes["Principled BSDF"].inputs["Specular"],
				texture_node.outputs["Color"]
			)
		else:
			material.node_tree.links.new(
				material.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"],
				texture_node.outputs["Color"]
			)
```
with the 5.x-only form:
```python
		material.node_tree.links.new(
			material.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"],
			texture_node.outputs["Color"]
		)
```

- [ ] **Step 4: Remove Blender-2.x branches in geo_nodes.py**

At lines 12-13, replace:
```python
	if bpy.app.version[0] != 2:
		geo_mod.show_in_editmode = False
```
with:
```python
	geo_mod.show_in_editmode = False
```
At lines 47-51, delete the legacy `node_group.outputs.new(...)` / `node_group.inputs.new(...)` pair, keeping only the `node_group.interface.new_socket(...)` calls. At lines 101-125, delete the `PointInstance` (Blender-2.x) branch, keeping only the `InstanceOnPoints` path. (If these are inside `if bpy.app.version... else:` blocks, keep the modern branch's body and drop the conditional.)

- [ ] **Step 5: Remove `scene_update_post` branches in addon_updater_ops.py**

For each `if bpy.app.version[0] < 4: ... scene_update_post ... else: ... depsgraph_update_post ...` block, keep only the `depsgraph_update_post` body and drop the conditional + the `scene_update_post` branch.

- [ ] **Step 6: Run the materials test to verify it passes**

Run:
```bash
"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_materials.py 2>&1 | grep -E "TEST_MATERIALS_OK|MAT_FAIL|Error"
```
Expected: PASS — `TEST_MATERIALS_OK`, no traceback.

- [ ] **Step 7: Commit**

```bash
git add gmdl_importer.py geo_nodes.py addon_updater_ops.py _test/test_materials.py
git commit -m "Drop pre-5.x version branches in materials, geo_nodes, updater"
```

---

### Task 6: Round-trip regression harness over all 4 files

**Files:**
- Create: `_test/test_roundtrip.py`

**Interfaces:**
- Consumes: the full migrated import+export pipeline.
- Produces: a single gate asserting structural parity import → export → re-import for every test file.

- [ ] **Step 1: Write the round-trip test**

Create `_test/test_roundtrip.py`:

```python
import sys, os, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon, TESTDIR

target = sys.argv[-1]


def counts():
    return {
        "armatures": len(bpy.data.armatures),
        "meshes": len(bpy.data.meshes),
        "actions": len(bpy.data.actions),
        "bones": sum(len(a.bones) for a in bpy.data.armatures),
        "shapekeys": sum(len(m.shape_keys.key_blocks) for m in bpy.data.meshes if m.shape_keys),
    }


def do_import(path):
    from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4
    s = RW4ImporterSettings()
    s.import_materials = False; s.import_skeleton = True
    s.import_animations = True; s.extract_textures = False
    with open(path, 'rb') as f:
        import_rw4(f, path, s)


bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons.rw4_exporter import export_rw4

src = os.path.join(TESTDIR, target)
try:
    do_import(src)
    first = counts()
    out = os.path.join(tempfile.gettempdir(), "rt_" + target)
    with open(out, 'wb') as f:
        export_rw4(f, False, False)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    load_addon(register=True)
    do_import(out)
    second = counts()
except Exception:
    traceback.print_exc(); print("ROUNDTRIP_FAIL"); raise

print("first ", first)
print("second", second)
for k in ("bones", "shapekeys", "actions"):
    assert first[k] == second[k], f"{k}: {first[k]} != {second[k]}"
print("TEST_ROUNDTRIP_OK")
```

- [ ] **Step 2: Run it across all 4 files**

Run:
```bash
for f in trg_seamon ce_mouth_jaw_carnivore_01 ce_weapon_horn_01 ce_details_playful_01; do
  echo "== $f =="
  "/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup --python _test/test_roundtrip.py 2>&1 -- "$f.rw4" | grep -E "TEST_ROUNDTRIP_OK|ROUNDTRIP_FAIL|first |second|!=|Error"
done
```
Expected: each file prints matching `first`/`second` counts and `TEST_ROUNDTRIP_OK`. If a file legitimately can't export (e.g. needs materials), document it in the harness with a `log`-style skip note rather than silently passing.

- [ ] **Step 3: Commit**

```bash
git add _test/test_roundtrip.py
git commit -m "Add round-trip regression harness for the 4 RW4 test files"
```

---

### Task 7: Manual GUI smoke check + finalize

**Files:**
- Modify: `docs/superpowers/specs/2026-06-17-blender-5x-migration-design.md` (mark status Done) — optional.

- [ ] **Step 1: Launch Blender 5.1 GUI and enable the add-on**

Install/enable the add-on folder in Blender 5.1's preferences (or load via the test-startup script). Confirm it enables with no error in the system console.

- [ ] **Step 2: Import a creature with handles**

File → Import → Spore RenderWare 4, import `_test/ce_weapon_horn_01.rw4` with animations on. Confirm: no console errors; the armature + actions appear; selecting a morph-handle action draws the handle box in the viewport (validates the `gpu` shader name `'UNIFORM_COLOR'` at runtime). If the shader name errors, switch to the correct 5.x built-in name reported in the console and re-test.

- [ ] **Step 3: Commit any shader-name fix**

```bash
git add rw4_animation_config.py
git commit -m "Fix gpu builtin shader name for Blender 5.x handle drawing"
```
(Skip if Step 2 showed no error.)

- [ ] **Step 4: Finishing**

Use the `superpowers:finishing-a-development-branch` skill to decide how to integrate `blender-5x-migration` (merge / PR).

---

## Notes for the implementer

- The add-on uses **tabs** for indentation. Match the surrounding file exactly when editing (the `anim_compat.py` snippets above use 4-space indent because it is a new file with no existing convention — but match PEP8/4-space there consistently).
- `addon_updater_ops` may emit a network/JSON warning under `--factory-startup`; that is not a failure. Only tracebacks / `*_FAIL` markers fail a test.
- Never edit transform math (`process_animation`, `process_skeleton_action`, keyframe read/write). If a round-trip count mismatches, the cause is plumbing, not math — re-check the `anim_compat` slot/channelbag wiring.
