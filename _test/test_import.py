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
