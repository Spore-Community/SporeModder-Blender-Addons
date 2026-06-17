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
