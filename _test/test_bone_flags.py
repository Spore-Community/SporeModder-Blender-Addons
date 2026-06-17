"""Regression test for the multi-child bone-flag export bug (Valla's Bug 1).

The skeleton is stored as a flat DFS list; the importer rebuilds the hierarchy
with a flag-driven stack (rw4_importer.process_animation). If process_bone emits
flags that don't balance that stack, sibling bones get reparented and the
animation glitches on re-import. This test exports each model and replays the
importer's stack over the exported skeleton, asserting every bone's stack-parent
matches its explicit parent (zero desync).
"""
import sys, os, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from _harness import load_addon, TESTDIR, TEST_FILES

B = None  # set after load


def do_import(path):
    from sporemodder_addons.rw4_importer import RW4ImporterSettings, import_rw4
    s = RW4ImporterSettings()
    s.import_materials = False
    s.import_skeleton = True
    s.import_animations = True
    s.extract_textures = False
    with open(path, 'rb') as f:
        import_rw4(f, path, s)


def stack_desyncs(path):
    from sporemodder_addons import rw4_base
    from sporemodder_addons.file_io import FileReader, get_name
    global B
    B = rw4_base.SkeletonBone
    with open(path, 'rb') as f:
        reader = FileReader(f)
        rw = rw4_base.RenderWare4()
        rw.read(reader)
        sks = rw.get_objects(rw4_base.Skeleton.type_code)
    desyncs = []
    for sk in sks:
        branches = []
        cur = None
        for b in sk.bones:
            name = get_name(b.name)
            explicit = get_name(b.parent.name) if b.parent else None
            if cur != explicit:
                desyncs.append((name, explicit, cur))
            if b.flags == B.TYPE_ROOT:
                cur = name
            elif b.flags == B.TYPE_LEAF:
                if branches:
                    cur = branches.pop()
            elif b.flags == B.TYPE_BRANCH:
                branches.append(cur)
                cur = name
            # TYPE_BRANCH_LEAF: no-op
    return desyncs


def main():
    failures = []
    for fn in TEST_FILES:
        src = os.path.join(TESTDIR, fn)
        if not os.path.exists(src):
            print(f"SKIP {fn} (missing)")
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        addon = load_addon(register=True)
        from sporemodder_addons.rw4_exporter import export_rw4
        try:
            do_import(src)
            out = os.path.join(tempfile.gettempdir(), "flags_" + fn)
            with open(out, 'wb') as f:
                export_rw4(f, False, False)
        finally:
            addon.unregister()
        ds = stack_desyncs(out)
        status = "OK" if not ds else f"{len(ds)} DESYNC"
        print(f"  {fn:40} {status}")
        for name, ep, sp in ds:
            print(f"       {name} explicit={ep} stack={sp}")
        if ds:
            failures.append(fn)
    if failures:
        print(f"TEST_BONE_FLAGS_FAIL: {failures}")
        raise SystemExit(1)
    print("TEST_BONE_FLAGS_OK")


try:
    main()
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    print("TEST_BONE_FLAGS_FAIL")
    raise
