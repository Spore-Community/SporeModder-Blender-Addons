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
