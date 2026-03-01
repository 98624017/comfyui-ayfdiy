"""
AYFdiy 日志入口适配层

目的：
1. 避免 `from logger import logger` 触发跨插件模块名冲突；
2. 始终从当前插件目录加载本地 logger.py。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_AYF_INTERNAL_LOGGER_MODULE = "_ayfdiy_internal_logger"


def _load_local_logger():
    cached = sys.modules.get(_AYF_INTERNAL_LOGGER_MODULE)
    if cached is not None and hasattr(cached, "logger"):
        return cached.logger

    logger_path = Path(__file__).with_name("logger.py")
    spec = importlib.util.spec_from_file_location(_AYF_INTERNAL_LOGGER_MODULE, logger_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载本地 logger.py: {logger_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_AYF_INTERNAL_LOGGER_MODULE] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "logger"):
        raise RuntimeError("本地 logger.py 未导出 logger 实例")
    return module.logger


logger = _load_local_logger()

__all__ = ["logger"]
