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
