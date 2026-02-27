import sys
import importlib.util
from pathlib import Path

current_dir = Path(__file__).parent

if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

SKIP_FILES = {
    "__init__.py",
    "logger.py",
}

print("[AYFdiy] Loading nodes...")

all_files = {}
for pattern in ["*.py"]:
    for file_path in current_dir.glob(pattern):
        if file_path.name in SKIP_FILES:
            continue
        module_name = file_path.stem
        all_files[module_name] = file_path

for module_name, py_file in all_files.items():
    try:
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, 'NODE_CLASS_MAPPINGS'):
                NODE_CLASS_MAPPINGS.update(module.NODE_CLASS_MAPPINGS)
            if hasattr(module, 'NODE_DISPLAY_NAME_MAPPINGS'):
                NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)

            print(f"  [AYFdiy] Loaded: {py_file.name}")
        else:
            print(f"  [AYFdiy] Warning: cannot create spec for {py_file.name}")
    except Exception as e:
        sys.modules.pop(module_name, None)
        print(f"  [AYFdiy] Failed to load {py_file.name}: {e}")

if NODE_CLASS_MAPPINGS:
    print(f"[AYFdiy] Total {len(NODE_CLASS_MAPPINGS)} nodes loaded")
    for node_name in NODE_CLASS_MAPPINGS.keys():
        display_name = NODE_DISPLAY_NAME_MAPPINGS.get(node_name, node_name)
        print(f"   - {display_name} ({node_name})")
else:
    print("[AYFdiy] Warning: no nodes found")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
WEB_DIRECTORY = "./web"
