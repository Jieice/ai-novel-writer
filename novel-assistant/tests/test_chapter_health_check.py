import contextlib
import importlib.util
import io
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(r"D:\AI\AI小说创作系统")
PROJECT = ROOT / "山村小神医"
HEALTH = ROOT / "novel-assistant" / "scripts" / "chapter_health_check.py"
PUBLISH = ROOT / "novel-assistant" / "scripts" / "publish_readiness_audit.py"


def run_py(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HEALTH_MOD = load_module(HEALTH, "chapter_health_check")


class ChapterHealthCheckRegressionTests(unittest.TestCase):
    def test_publish_ready_chapter13_is_not_flagged_for_fake_ai_rate(self) -> None:
        publish = run_py(PUBLISH, "--project", str(PROJECT), "--chapter", "13")
        self.assertEqual(
            publish.returncode,
            0,
            msg=f"chapter 13 should be publish-ready before this regression test.\n{publish.stdout}\n{publish.stderr}",
        )

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = HEALTH_MOD.run_check(str(PROJECT), 13, strict=False)
        self.assertIn(code, (0, 2))
        output = buf.getvalue()
        self.assertNotIn("AI 率偏高", output)
        self.assertNotIn("口语化略低", output)

    def test_scene_stuffed_chapter18_is_still_flagged(self) -> None:
        publish = run_py(PUBLISH, "--project", str(PROJECT), "--chapter", "18")
        self.assertNotEqual(publish.returncode, 0)
        self.assertIn("场景过多", publish.stdout)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = HEALTH_MOD.run_check(str(PROJECT), 18, strict=False)
        self.assertIn(code, (0, 2))
        self.assertIn("场景过多", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
