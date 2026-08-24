import importlib.util
import os
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "macos" / "gui_app.py"
SPEC = importlib.util.spec_from_file_location("macos_gui_app", SCRIPT_PATH)
assert SPEC and SPEC.loader
GUI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUI)


def test_registration_window_initializes_with_safe_defaults(tmp_path):
    mailbox_lines = "user@example.com----password----client----refresh\n"
    app = GUI.create_application([])
    window = GUI.RegistrationWindow(repo_root=tmp_path)
    window.mailbox_text_edit.setPlainText(mailbox_lines)

    options = window.collect_options()

    assert window.windowTitle() == "GPT Register Tool · macOS"
    assert options.source == "pool"
    assert options.mailbox_text == mailbox_lines
    assert options.registration_at_only is True
    assert window.start_button.isEnabled()
    assert not window.stop_button.isEnabled()
    assert "--chatai-mailbox-file" in window.command_preview()
    window.close()
    app.quit()
