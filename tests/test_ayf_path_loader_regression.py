import importlib
import os
import sys
import tempfile
import types
import unittest

from PIL import Image


def _ensure_stubbed_dependencies() -> None:
    """为最小单元测试注入缺失依赖，避免依赖完整 ComfyUI 环境。"""
    if "numpy" not in sys.modules:
        numpy_stub = types.ModuleType("numpy")
        numpy_stub.asarray = lambda _img: None
        sys.modules["numpy"] = numpy_stub

    if "torch" not in sys.modules:
        torch_stub = types.ModuleType("torch")
        torch_stub.Tensor = object
        sys.modules["torch"] = torch_stub

    if "folder_paths" not in sys.modules:
        folder_paths_stub = types.ModuleType("folder_paths")
        folder_paths_stub.get_input_directory = lambda: "."
        sys.modules["folder_paths"] = folder_paths_stub


class TestAYFPathLoaderRegression(unittest.TestCase):
    def test_load_image_from_file_returns_usable_image(self):
        _ensure_stubbed_dependencies()
        module = importlib.import_module("ayf_path_loader")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fp:
            temp_path = fp.name
        try:
            Image.new("RGB", (100, 50), (255, 0, 0)).save(temp_path)
            img = module._load_image_from_file(temp_path)

            # 回归断言：加载后的图像必须可继续执行 PIL 操作。
            img.thumbnail((64, 64), Image.LANCZOS)
            raw = img.tobytes()

            self.assertTrue(len(raw) > 0)
            self.assertEqual(img.mode, "RGB")
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
