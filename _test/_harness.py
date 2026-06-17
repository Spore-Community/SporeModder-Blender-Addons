import sys, os, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTDIR = os.path.join(REPO, "_test")
TEST_FILES = ["trg_seamon.rw4", "ce_mouth_jaw_carnivore_01.rw4",
              "ce_weapon_horn_01.rw4", "ce_details_playful_01.rw4"]


def load_addon(register=True):
    spec = importlib.util.spec_from_file_location(
        "sporemodder_addons", os.path.join(REPO, "__init__.py"),
        submodule_search_locations=[REPO])
    addon = importlib.util.module_from_spec(spec)
    sys.modules["sporemodder_addons"] = addon
    spec.loader.exec_module(addon)
    if register:
        addon.register()
    return addon
