import runpy
from pathlib import Path

import pytest

import junction_sim


def test_package_version() -> None:
    assert isinstance(junction_sim.__version__, str)
    assert junction_sim.__version__ == "0.3.0"


def test_all_exports_present() -> None:
    for symbol_name in junction_sim.__all__:
        assert hasattr(junction_sim, symbol_name)
        obj = getattr(junction_sim, symbol_name)
        assert obj is not None


def test_no_duplicate_exports() -> None:
    exports = junction_sim.__all__
    assert len(exports) == len(set(exports))


def test_py_typed_file_exists() -> None:
    mod_file = Path(junction_sim.__file__)
    py_typed = mod_file.parent / "py.typed"
    assert py_typed.exists()
    assert py_typed.is_file()


def test_main_module_execution() -> None:
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("junction_sim.__main__", run_name="__main__")
    assert exc_info.value.code == 0
