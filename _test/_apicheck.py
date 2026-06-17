import bpy
print("\n===== BLENDER", bpy.app.version_string, "=====")

# --- Action / slotted actions API ---
act = bpy.data.actions.new("probe")
print("action attrs:", [a for a in ('fcurves','groups','id_root','slots','layers') if hasattr(act, a)])
print("has slots.new:", hasattr(act.slots, 'new'))
try:
    slot = act.slots.new('OBJECT', "Slot")
    print("slot created:", slot, "target_id_type:", getattr(slot, 'target_id_type', 'N/A'))
    print("slot attrs of interest:", [a for a in ('target_id_type','identifier','handle','name_display') if hasattr(slot, a)])
except Exception as e:
    print("slots.new error:", repr(e))

# anim_utils helper
try:
    from bpy_extras import anim_utils
    print("anim_utils has action_ensure_channelbag_for_slot:", hasattr(anim_utils, 'action_ensure_channelbag_for_slot'))
    cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)
    print("channelbag:", cb, "has fcurves:", hasattr(cb, 'fcurves'), "fcurves.ensure:", hasattr(cb.fcurves, 'ensure'), "fcurves.new:", hasattr(cb.fcurves, 'new'))
    print("channelbag has groups:", hasattr(cb, 'groups'))
except Exception as e:
    print("anim_utils error:", repr(e))

# How to assign action+slot to an object's animation_data
o = bpy.data.objects.new("o", None)
bpy.context.scene.collection.objects.link(o)
o.animation_data_create()
print("animation_data has action_slot:", hasattr(o.animation_data, 'action_slot'))
o.animation_data.action = act
try:
    o.animation_data.action_slot = slot
    print("assigned action_slot OK")
except Exception as e:
    print("assign action_slot error:", repr(e))

# gpu shader names
import gpu
for nm in ('UNIFORM_COLOR','3D_UNIFORM_COLOR','POLYLINE_UNIFORM_COLOR'):
    try:
        gpu.shader.from_builtin(nm); print(f"shader '{nm}': OK")
    except Exception as e:
        print(f"shader '{nm}': {type(e).__name__}")

# gpu.state (bgl replacement)
print("gpu.state.blend_set:", hasattr(gpu.state, 'blend_set'))
