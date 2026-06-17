import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon

bpy.ops.wm.read_factory_settings(use_empty=True)
addon = load_addon(register=True)
from sporemodder_addons import anim_compat
import sporemodder_addons.rw4_animation_config  # must import without error

# Action with an fcurve (OBJECT slot)
act_with_fcurve = bpy.data.actions.new("WithFCurve")
anim_compat.channelbag_for(act_with_fcurve, 'OBJECT').fcurves.new("location", index=0)

# Empty action
empty_act = bpy.data.actions.new("Empty")

assert any(anim_compat.iter_fcurves(act_with_fcurve)), "Expected fcurves in act_with_fcurve"
assert not any(anim_compat.iter_fcurves(empty_act)), "Expected no fcurves in empty_act"

print("TEST_FILTER_OK")
