import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preflight_env.py"
SPEC = importlib.util.spec_from_file_location("preflight_env", SCRIPT_PATH)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def test_preflight_reports_supported_macos_runtime():
    with patch.object(PREFLIGHT.platform, "system", return_value="Darwin"), patch.object(
        PREFLIGHT.platform, "machine", return_value="arm64"
    ):
        ok, detail, fix = PREFLIGHT.check_platform()
    assert ok
    assert detail == "Darwin (arm64)"
    assert fix == ""


def test_preflight_install_commands_use_current_interpreter():
    command = PREFLIGHT._python_command("-m", "pip", "install", "playwright")
    assert command.startswith(sys.executable)
    assert command.endswith("-m pip install playwright")
