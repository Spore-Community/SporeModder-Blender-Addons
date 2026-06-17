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

    # Unregister before resetting scene to avoid double-registration on second pass
    addon.unregister()
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
