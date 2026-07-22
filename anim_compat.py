"""Compatibility shim for the Blender Action API across versions.

Two eras are supported behind one interface so the import/export call sites stay
version-agnostic:

* **Legacy actions** (Blender < 4.4): an Action owns ``fcurves``/``groups``
  directly and carries an ``id_root`` enum. This is the original API the add-on
  shipped with (back to 2.8).
* **Slotted actions** (Blender >= 4.4, mandatory in 5.x): channels live in a
  per-slot channelbag obtained via
  ``bpy_extras.anim_utils.action_ensure_channelbag_for_slot``; binding also needs
  ``animation_data.action_slot``.

The presence of ``action_ensure_channelbag_for_slot`` is the version gate.
"""
import bpy

try:
    from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
except ImportError:  # Blender < 4.4
    action_ensure_channelbag_for_slot = None

SLOTTED = action_ensure_channelbag_for_slot is not None


def _find_slot(action, id_type):
    for slot in action.slots:
        if slot.target_id_type == id_type:
            return slot
    return None


def channelbag_for(action, id_type):
    """Return the container exposing ``fcurves`` and ``groups`` for id_type.

    Slotted: ensures a slot of id_type exists and returns its channelbag.
    Legacy: the action itself already exposes ``fcurves``/``groups``; we just
    make sure ``id_root`` is tagged so fresh fcurves bind to the right id type.
    """
    if SLOTTED:
        slot = _find_slot(action, id_type) or action.slots.new(id_type, "Slot")
        return action_ensure_channelbag_for_slot(action, slot)
    # Legacy: id_root can only be set while the action has no data; setting it to
    # the value it already holds is a harmless no-op.
    try:
        if action.id_root in ('EMPTY', id_type):
            action.id_root = id_type
    except (AttributeError, TypeError):
        pass
    return action


def assign_action(id_data, action, id_type):
    """Bind action (with a slot/id_root of id_type) to id_data; return the slot
    on slotted Blender, or None on legacy."""
    if id_data.animation_data is None:
        id_data.animation_data_create()
    if SLOTTED:
        slot = _find_slot(action, id_type) or action.slots.new(id_type, "Slot")
        id_data.animation_data.action = action
        id_data.animation_data.action_slot = slot
        return slot
    # Legacy
    try:
        if action.id_root in ('EMPTY', id_type):
            action.id_root = id_type
    except (AttributeError, TypeError):
        pass
    id_data.animation_data.action = action
    return None


def get_target_id_type(action):
    """Slotted: first slot's target_id_type ('' if none).
    Legacy: the action's id_root."""
    if SLOTTED:
        return action.slots[0].target_id_type if len(action.slots) else ''
    return action.id_root


def iter_fcurves(action):
    """Yield every F-curve of the action across all its channelbags (slotted)
    or directly (legacy)."""
    if SLOTTED:
        for slot in action.slots:
            cb = action_ensure_channelbag_for_slot(action, slot)
            for fc in cb.fcurves:
                yield fc
    else:
        for fc in action.fcurves:
            yield fc
