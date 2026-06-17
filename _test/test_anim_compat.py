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
