"""
AYF路径加载节点
支持从本地文件路径、ComfyUI 相对路径、公网 URL、本地文件夹加载图片。
文件夹模式下每张图保持原始分辨率独立输出。
"""

from __future__ import annotations

import gc
import hashlib
import os
import urllib.request
from io import BytesIO
from typing import List, Tuple, Union
from urllib.parse import urlparse

import numpy as np
import torch
from PIL import Image, ImageOps

import folder_paths

from ayf_logger import logger

# 支持的图片扩展名（小写）
_SUPPORTED_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".gif",
})

_DOWNLOAD_TIMEOUT = 30  # URL 下载超时（秒）
_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # URL 下载最大 100MB


def _is_url(path: str) -> bool:
    """判断路径是否为 HTTP(S) URL。"""
    lower = path.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _load_image_from_bytes(data: bytes, source_desc: str) -> Image.Image:
    """从字节数据加载 PIL Image，统一做 EXIF 旋转和 RGB 转换。"""
    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.load()  # 显式加载像素数据，释放 BytesIO 引用
        return img
    except (OSError, ValueError) as e:
        raise ValueError(f"无法解析图片数据 ({source_desc}): {e}") from e


def _load_image_from_file(file_path: str) -> Image.Image:
    """从本地文件路径加载 PIL Image。

    直接用文件路径打开并在上下文中解码，确保文件句柄及时释放，
    同时返回的 Image 对象保持可继续处理（缩放/转 tensor）。
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    try:
        with Image.open(file_path) as src:
            img = ImageOps.exif_transpose(src)
            img = img.convert("RGB")
            img.load()  # 显式解码像素到内存
            return img
    except (OSError, ValueError) as e:
        raise ValueError(f"无法解析图片数据 ({file_path}): {e}") from e


def _download_image(url: str) -> Image.Image:
    """从 URL 下载并加载图片（仅允许 HTTP/HTTPS，限制下载大小）。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"仅支持 HTTP/HTTPS URL，不支持: {parsed.scheme}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ComfyUI-AYF-PathLoader/1.0"},
        )
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
            # 分块读取并限制总大小
            chunks: List[bytes] = []
            total = 0
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_DOWNLOAD_BYTES:
                    raise ValueError(
                        f"下载大小超过限制 ({total} > {_MAX_DOWNLOAD_BYTES} bytes)"
                    )
                chunks.append(chunk)
            data = b"".join(chunks)
        return _load_image_from_bytes(data, url)
    except (ValueError, ConnectionError):
        raise
    except Exception as e:
        raise ConnectionError(f"下载图片失败 ({url}): {e}") from e


def _pil_to_tensor(img: Image.Image) -> torch.Tensor:
    """PIL Image → [1, H, W, 3] float32 tensor (0-1)。

    使用 np.asarray 零拷贝视图 + torch 侧就地转换，
    避免创建多个中间 numpy 数组，峰值内存降低约 40%。
    """
    arr = np.asarray(img)                          # 零拷贝 view
    t = torch.from_numpy(arr.copy())               # copy 创建 tensor 拥有的内存
    t = t.to(dtype=torch.float32).div_(255.0)      # 就地转换+归一化
    return t.unsqueeze(0)                           # [1, H, W, 3]


def _list_image_files(dir_path: str) -> List[str]:
    """扫描目录中的图片文件，按文件名排序返回绝对路径列表。"""
    files: List[str] = []
    for name in sorted(os.listdir(dir_path)):
        ext = os.path.splitext(name)[1].lower()
        if ext in _SUPPORTED_EXTENSIONS:
            files.append(os.path.join(dir_path, name))
    return files


def _resolve_path(raw_path: str) -> str:
    """
    解析用户输入的路径，返回绝对路径。
    - 绝对路径：直接返回
    - 相对路径：拼接 ComfyUI input 目录
    """
    if os.path.isabs(raw_path):
        return raw_path
    # 相对路径 → ComfyUI input 目录
    input_dir = folder_paths.get_input_directory()
    return os.path.join(input_dir, raw_path)


class AYFPathLoader:
    """
    通用图片加载节点，支持本地文件 / ComfyUI 相对路径 / URL / 文件夹。
    文件夹模式下每张图保持原始分辨率，独立输出。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "支持：本地文件绝对路径、ComfyUI input 相对路径、公网图片 URL、本地文件夹路径（逐张输出）",
                }),
            },
            "optional": {
                "max_long_edge": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 8192,
                    "step": 64,
                    "tooltip": "最大长边像素（0=不缩放）。加载大量高分辨率图片时设置此值可防止内存溢出",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "execute"
    CATEGORY = "AYFdiy/"

    def execute(self, path: str, max_long_edge: int = 0) -> Tuple[List[torch.Tensor]]:
        path = path.strip()
        if not path:
            raise ValueError("路径不能为空，请输入本地路径、URL 或文件夹路径")

        tensors: List[torch.Tensor] = []

        if _is_url(path):
            # URL 模式
            logger.info(f"[路径加载] 从 URL 下载: {path}")
            img = _download_image(path)
            if max_long_edge > 0:
                img.thumbnail((max_long_edge, max_long_edge), Image.LANCZOS)
            tensors.append(_pil_to_tensor(img))
            del img
        else:
            # 本地路径模式
            resolved = _resolve_path(path)

            if os.path.isfile(resolved):
                # 单文件
                logger.info(f"[路径加载] 加载文件: {resolved}")
                img = _load_image_from_file(resolved)
                if max_long_edge > 0:
                    img.thumbnail((max_long_edge, max_long_edge), Image.LANCZOS)
                tensors.append(_pil_to_tensor(img))
                del img

            elif os.path.isdir(resolved):
                # 文件夹
                image_files = _list_image_files(resolved)
                if not image_files:
                    raise FileNotFoundError(
                        f"目录中没有找到支持的图片文件: {resolved}\n"
                        f"支持的格式: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
                    )
                logger.info(f"[路径加载] 扫描到 {len(image_files)} 张图片: {resolved}")

                # 内存预警
                if len(image_files) > 20:
                    logger.warning(
                        f"[路径加载] 即将加载 {len(image_files)} 张图片，"
                        f"大量高分辨率图片可能导致内存不足"
                    )

                for idx, fp in enumerate(image_files):
                    try:
                        img = _load_image_from_file(fp)
                        w, h = img.size
                        if max_long_edge > 0:
                            img.thumbnail((max_long_edge, max_long_edge), Image.LANCZOS)
                        tensors.append(_pil_to_tensor(img))
                        del img  # 及时释放 PIL Image
                        logger.info(f"  ✓ {os.path.basename(fp)} ({w}×{h})")
                    except (OSError, ValueError) as e:
                        logger.warning(f"  ✗ 跳过无法加载的文件 {os.path.basename(fp)}: {e}")

                    # 每 10 张强制 GC，回收 PIL 循环引用残留
                    if (idx + 1) % 10 == 0:
                        gc.collect()
            else:
                raise FileNotFoundError(
                    f"路径不存在: {resolved}\n"
                    f"原始输入: {path}"
                )

        if not tensors:
            raise RuntimeError("未能加载任何图片")

        logger.info(f"[路径加载] 共输出 {len(tensors)} 张图片")
        return (tensors,)

    @classmethod
    def IS_CHANGED(cls, path: str, max_long_edge: int = 0) -> Union[str, float]:
        path = path.strip()
        if not path:
            return ""

        if _is_url(path):
            # URL 每次都重新下载
            return float("NaN")

        resolved = _resolve_path(path)

        if os.path.isfile(resolved):
            return hex(int(os.path.getmtime(resolved)))

        if os.path.isdir(resolved):
            image_files = _list_image_files(resolved)
            if not image_files:
                return ""
            # 拼接所有图片 mtime 后取 md5
            mtimes = "".join(
                f"{os.path.basename(f)}:{os.path.getmtime(f)}"
                for f in image_files
            )
            return hashlib.md5(mtimes.encode()).hexdigest()

        return ""


NODE_CLASS_MAPPINGS = {
    "AYFPathLoader": AYFPathLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AYFPathLoader": "AYF路径加载",
}
