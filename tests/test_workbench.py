from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch

from robot_calibration.data import read_json

try:
    import tkinter as tk
    from robot_calibration.app import Workbench
except ImportError:
    tk = None


@unittest.skipIf(tk is None, "Tkinter is unavailable")
class WorkbenchTest(unittest.TestCase):
    def test_gui_demo_run_switch_and_export(self):
        try:
            window = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.addCleanup(window.destroy)
        window.withdraw()
        root = Path(self.enterContext(TemporaryDirectory(prefix="calibration-gui-test-")))
        executor = self.enterContext(ThreadPoolExecutor(max_workers=1))
        app = Workbench(window, root / "demos", executor)

        def finish():
            end = monotonic() + 15
            while app.busy and monotonic() < end:
                window.update()
                sleep(0.02)
            self.assertFalse(app.busy, "GUI job timed out")

        with patch("robot_calibration.app.messagebox.showerror", side_effect=AssertionError("unexpected GUI error")):
            for mode in ("intrinsics", "eye-in-hand", "eye-to-hand"):
                with self.subTest(mode=mode):
                    app.select_mode(mode)
                    self.assertIsNone(app.result)
                    app.load_demo()
                    finish()
                    self.assertEqual(len(app.table.get_children()), 15)
                    app.run()
                    finish()
                    self.assertEqual(len(app.result["views"]), 15)
                    self.assertEqual(app.export.cget("state"), "normal")
                    output = root / f"{mode}-export.json"
                    with patch("robot_calibration.app.filedialog.asksaveasfilename", return_value=str(output)):
                        app.export_result()
                    record = read_json(output)
                    if mode == "intrinsics":
                        self.assertIn("camera_matrix", record)
                    else:
                        self.assertEqual(record["mode"], mode)
                    app.board_vars[2].set("25")
                    self.assertIsNone(app.result)
                    self.assertEqual(app.export.cget("state"), "disabled")

        app.load_demo()
        finish()
        app.threshold.set("0.000001")
        with patch("robot_calibration.app.messagebox.showerror") as show_error:
            app.run()
            finish()
            show_error.assert_called_once()
        self.assertIsNone(app.result)
        self.assertEqual(app.export.cget("state"), "disabled")
        self.assertTrue(all(row["accepted"] is False for row in app.failed_views))
        self.assertEqual(len(app.table.get_children()), 15)
