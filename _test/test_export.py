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
