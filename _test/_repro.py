import sys, os, importlib.util, traceback

REPO = r"C:\CodingProjects\Personal\SporeModder-Blender-Addons"
TESTDIR = os.path.join(REPO, "_test")

# Load the hyphenated addon folder under a clean module name
spec = importlib.util.spec_from_file_location(
    "sporemodder_addons",
    os.path.join(REPO, "__init__.py"),
    submodule_search_locations=[REPO])
addon = importlib.util.module_from_spec(spec)
sys.modules["sporemodder_addons"] = addon
spec.loader.exec_module(addon)

import bpy

# fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Stub the Action.rw4 PropertyGroup directly (rw4_animation_config imports bgl, removed in Blender 4.0+,
# and only provides viewport drawing for handles — not needed to test import logic).
class _RW4AnimStub(bpy.types.PropertyGroup):
    is_morph_handle: bpy.props.BoolProperty(default=False)
    initial_pos: bpy.props.FloatVectorProperty(size=3)
    final_pos: bpy.props.FloatVectorProperty(size=3)
    default_progress: bpy.props.FloatProperty(default=0.0)
bpy.utils.register_class(_RW4AnimStub)
bpy.types.Action.rw4 = bpy.props.PointerProperty(type=_RW4AnimStub)

from sporemodder_addons import mod_paths as _mp
try:
    _mp.register()
except Exception as e:
    print("mod_paths register warning:", e)

from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4
from sporemodder_addons import rw4_base
from sporemodder_addons.file_io import get_name

target = sys.argv[-1]
path = os.path.join(TESTDIR, target)
print("\n\n========== IMPORTING:", target, "==========")

settings = RW4ImporterSettings()
settings.import_materials = False
settings.import_skeleton = True
settings.import_animations = True
settings.extract_textures = False

try:
    with open(path, 'rb') as f:
        import_rw4(f, path, settings)
    print("IMPORT RETURNED OK")
except Exception:
    print("!!! IMPORT RAISED EXCEPTION:")
    traceback.print_exc()

print("\n----- MESHES / SHAPE KEYS -----")
for m in bpy.data.meshes:
    if m.shape_keys:
        names = [kb.name for kb in m.shape_keys.key_blocks]
        print(f"  mesh '{m.name}': {len(names)} shape keys -> {names}")
    else:
        print(f"  mesh '{m.name}': (no shape keys)")

print("\n----- ACTIONS -----")
for a in bpy.data.actions:
    rw4 = getattr(a, 'rw4', None)
    is_morph = getattr(rw4, 'is_morph_handle', None) if rw4 else None
    paths = sorted({fc.data_path for fc in a.fcurves})
    print(f"  action '{a.name}': id_root={a.id_root} is_morph_handle={is_morph} fcurves={len(a.fcurves)}")
    for p in paths:
        print(f"       data_path: {p}")
