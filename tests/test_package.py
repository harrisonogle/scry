import importlib
import importlib.util
import pkgutil

import scry
import scry.schemas

GONE_MODULES = ["merge", "correspond", "coalesce", "diff", "perceive", "hierarchy", "agent", "diagnostics", "stage2a"]
GONE_SCHEMAS = ["Line", "Region", "FrameRecord", "Transition", "DiffOp", "VlmRegion", "VlmPerception", "PerceptionRecord"]


def test_old_machinery_is_gone():
    for name in GONE_MODULES:
        assert importlib.util.find_spec("scry." + name) is None, name
    for attr in GONE_SCHEMAS:
        assert not hasattr(scry.schemas, attr), attr
    assert importlib.util.find_spec("scry.stage1") is None
    assert not hasattr(scry.schemas, "Stage1Record")


def test_every_module_imports():
    for info in pkgutil.walk_packages(scry.__path__, "scry."):
        importlib.import_module(info.name)
