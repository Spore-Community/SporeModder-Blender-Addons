import sys, os, importlib.util

REPO = r"C:\CodingProjects\Personal\SporeModder-Blender-Addons"
TESTDIR = os.path.join(REPO, "_test")

spec = importlib.util.spec_from_file_location(
    "sporemodder_addons", os.path.join(REPO, "__init__.py"),
    submodule_search_locations=[REPO])
addon = importlib.util.module_from_spec(spec)
sys.modules["sporemodder_addons"] = addon
spec.loader.exec_module(addon)

from sporemodder_addons import rw4_base
from sporemodder_addons.file_io import FileReader, get_name

target = sys.argv[-1]
path = os.path.join(TESTDIR, target)
print("\n========== PARSING:", target, "==========")

with open(path, 'rb') as f:
    reader = FileReader(f)
    rw = rw4_base.RenderWare4()
    rw.read(reader)

    def cls_name(c):
        return c.__name__ if c else None

    skeletons = rw.get_objects(rw4_base.Skeleton.type_code)
    print(f"\nSkeletons: {len(skeletons)}")
    for sk in skeletons:
        print(f"  skeleton_id={sk.skeleton_id} bones={len(sk.bones)}")
        for b in sk.bones:
            par = get_name(b.parent.name) if b.parent else None
            print(f"     bone {get_name(b.name)!r:20} flags={b.flags} parent={par}")

    blendshapes = rw.get_objects(rw4_base.BlendShape.type_code)
    print(f"\nBlendShapes: {len(blendshapes)}")
    shape_id_names = set()
    for bs in blendshapes:
        print(f"  BlendShape id={get_name(bs.id)} shape_count={len(bs.shape_ids)}")
        for sid in bs.shape_ids:
            shape_id_names.add(get_name(sid))
            print(f"     shape_id {sid:#010x} -> {get_name(sid)!r}")

    anims = rw.get_objects(rw4_base.KeyframeAnim.type_code)
    print(f"\nKeyframeAnims (standalone): {len(anims)}")

    handles = rw.get_objects(rw4_base.MorphHandle.type_code)
    print(f"\nMorphHandles: {len(handles)}")
    for h in handles:
        a = h.animation
        chans = a.channels if a else []
        print(f"  handle_id={h.handle_id:#010x} -> {get_name(h.handle_id)!r} "
              f"default_progress={h.default_progress} channels={len(chans)}")
        for ch in chans:
            cid = get_name(ch.channel_id)
            match = "OK-matches-shapekey" if cid in shape_id_names else "!!! NO MATCHING SHAPE KEY"
            print(f"     channel_id {ch.channel_id:#010x} -> {cid!r}  "
                  f"keyframe_class={cls_name(ch.keyframe_class)}  nkeys={len(ch.keyframes)}  [{match}]")
            for kf in ch.keyframes[:4]:
                if ch.keyframe_class == rw4_base.BlendFactorKeyframe:
                    print(f"          t={kf.time:.3f} factor={kf.factor:.3f}")
