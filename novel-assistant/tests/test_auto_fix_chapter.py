import importlib.util
import unittest
from pathlib import Path


ROOT = Path(r"D:\AI\AI小说创作系统")
AUTO_FIX = ROOT / "novel-assistant" / "scripts" / "auto_fix_chapter.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


AUTO_FIX_MOD = load_module(AUTO_FIX, "auto_fix_chapter")


class AutoFixStructuralNoiseTests(unittest.TestCase):
    def test_fix_structural_noise_removes_summary_and_bookkeeping_lines(self) -> None:
        raw = "\n".join([
            "三十二株天麻，加起来差不多一斤，陈大山算了一笔账，一斤天麻，张德贵给的价是四十块一斤。",
            "这不只是赚钱的事，这意味着他可以大规模培育药材了。",
            "“张老板，你先掌眼。”",
            "张德贵接过去，先没吭声。",
        ])

        cleaned, changes = AUTO_FIX_MOD.fix_structural_noise(raw)

        self.assertGreaterEqual(changes, 2)
        self.assertNotIn("算了一笔账", cleaned)
        self.assertNotIn("这意味着", cleaned)
        self.assertIn("“张老板，你先掌眼。”", cleaned)
        self.assertIn("张德贵接过去，先没吭声。", cleaned)
        self.assertEqual(AUTO_FIX_MOD.get_publish_blockers(cleaned), [])

    def test_fix_structural_noise_keeps_sceneful_lines(self) -> None:
        raw = "\n".join([
            "张德贵把那块天麻翻过来，指甲在底部轻轻一刮。",
            "“这货是从哪儿挖的？”",
            "陈大山没接话，只把布袋往回拽了一寸。",
        ])

        cleaned, changes = AUTO_FIX_MOD.fix_structural_noise(raw)

        self.assertEqual(changes, 0)
        self.assertEqual(cleaned, raw)


if __name__ == "__main__":
    unittest.main()
