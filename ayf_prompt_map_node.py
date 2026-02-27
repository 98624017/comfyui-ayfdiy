# prompt_map_node.py
import os
import json
import threading
import uuid
from typing import Dict, List, Optional
from aiohttp import web
from datetime import datetime

try:
    from server import PromptServer
except ImportError:
    class _DummyPromptServer:
        instance = None
        routes = None
    PromptServer = _DummyPromptServer()

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        tomllib = None


def _normalize_kw(kw: str) -> str:
    """关键词标准化：去首尾空格 + 全小写，用于唯一性比对"""
    return kw.strip().lower()


class PromptMapManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_maps.toml")
        self._allow_overwrite_without_toml = not os.path.exists(self.file_path)
        self._last_mtime = 0
        if not tomllib:
            print("PromptMapNode: Warning - Python 3.11+ or 'toml' package required. Using memory-only mode.")
        self._cache: List[Dict] = self._load()

    def _get_mtime(self) -> float:
        if os.path.exists(self.file_path):
            return os.path.getmtime(self.file_path)
        return 0.0

    def _reload_if_needed(self):
        if not tomllib:
            return
        current_mtime = self._get_mtime()
        if current_mtime != self._last_mtime:
            print(f"PromptMapManager: File changed, reloading prompt_maps.toml...")
            self._cache = self._load()

    def _load(self) -> List[Dict]:
        if not tomllib:
            return []
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, "rb") as f:
                data = tomllib.load(f)
                maps = data.get("maps", [])
                for m in maps:
                    if isinstance(m.get("keywords"), str):
                        m["keywords"] = [m["keywords"]]
                    elif not isinstance(m.get("keywords"), list):
                        m["keywords"] = []
                return maps
        except Exception as e:
            print(f"PromptMapManager: Failed to load prompt_maps.toml: {e}")
            return []
        finally:
            self._last_mtime = self._get_mtime()

    def _save(self):
        if not tomllib and os.path.exists(self.file_path) and not self._allow_overwrite_without_toml:
            print("PromptMapManager: Warning - TOML 解析器不可用，已跳过保存。")
            return
        header = """# ==========================================
# AYF Prompt Maps 配置文件
# ==========================================
# 字段说明:
# - [[maps]]: 定义一条关键词→完整文本的映射
# - id: 唯一标识符 (UUID4格式) [必选]
# - keywords: 关键词列表，匹配任意一个即命中 [必选]
# - content: 映射输出的完整提示词文本 [必选]
# - category: 分类名称 [可选，默认: "默认"]
# - color: 显示颜色 (Hex格式) [可选，默认: "#2196F3"]
# - created_at: 创建时间 (YYYY-MM-DD HH:MM) [可选]
#
# 示例:
# [[maps]]
# id = "my-map-001"
# keywords = ["1girl", "girl", "一个女生"]
# content = "a beautiful young woman in a fantasy forest..."
# category = "人物"
# color = "#2196F3"
# created_at = "2026-01-01 12:00"
# ==========================================

"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(header)
                for m in self._cache:
                    f.write("[[maps]]\n")
                    f.write(f"id = {json.dumps(m['id'])}\n")
                    f.write(f"keywords = {json.dumps(m.get('keywords', []), ensure_ascii=False)}\n")
                    f.write(f"content = {json.dumps(m.get('content', ''), ensure_ascii=False)}\n")
                    f.write(f"category = {json.dumps(m.get('category', '默认'), ensure_ascii=False)}\n")
                    f.write(f"color = {json.dumps(m.get('color', '#2196F3'))}\n")
                    f.write(f"created_at = {json.dumps(m.get('created_at', ''))}\n\n")
            self._allow_overwrite_without_toml = True
        except Exception as e:
            print(f"PromptMapManager: Failed to save prompt_maps.toml: {e}")

    def _check_keyword_conflicts(self, keywords: List[str], exclude_id: Optional[str] = None) -> Optional[str]:
        """检查关键词冲突，返回冲突描述或 None"""
        normalized_new = {_normalize_kw(kw) for kw in keywords if kw.strip()}
        for m in self._cache:
            if exclude_id and m["id"] == exclude_id:
                continue
            for existing_kw in m.get("keywords", []):
                if _normalize_kw(existing_kw) in normalized_new:
                    content_preview = m.get("content", "")[:20]
                    category = m.get("category", "默认")
                    return f'关键词 "{existing_kw}" 已被 [{category}] / "{content_preview}..." 使用'
        return None

    def list_maps(self) -> List[Dict]:
        with self.lock:
            self._reload_if_needed()
            return list(self._cache)

    def add_map(self, keywords: List[str], content: str, category: str = "默认", color: str = "#2196F3") -> Dict | str:
        """新增映射。若关键词冲突返回错误字符串，否则返回新 map dict。"""
        with self.lock:
            self._reload_if_needed()
            clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
            if not clean_keywords:
                return "关键词列表不能为空"
            conflict = self._check_keyword_conflicts(clean_keywords)
            if conflict:
                return conflict
            m = {
                "id": str(uuid.uuid4()),
                "keywords": clean_keywords,
                "content": content,
                "category": category,
                "color": color,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            self._cache.append(m)
            self._save()
            return m

    def update_map(self, map_id: str, keywords: List[str], content: str, category: str, color: str) -> Dict | str | None:
        """更新映射。关键词冲突返回错误字符串，未找到返回 None，成功返回更新后的 dict。"""
        with self.lock:
            self._reload_if_needed()
            clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
            if not clean_keywords:
                return "关键词列表不能为空"
            conflict = self._check_keyword_conflicts(clean_keywords, exclude_id=map_id)
            if conflict:
                return conflict
            for i, m in enumerate(self._cache):
                if m["id"] == map_id:
                    updated = {
                        **m,
                        "keywords": clean_keywords,
                        "content": content,
                        "category": category,
                        "color": color,
                    }
                    self._cache[i] = updated
                    self._save()
                    return updated
        return None

    def delete_map(self, map_id: str) -> bool:
        with self.lock:
            self._reload_if_needed()
            initial_len = len(self._cache)
            self._cache = [m for m in self._cache if m["id"] != map_id]
            if len(self._cache) != initial_len:
                self._save()
                return True
        return False

    def resolve(self, keyword: str) -> Optional[str]:
        """关键词 → 完整文本（标准化匹配，未匹配返回 None）"""
        normalized = _normalize_kw(keyword)
        with self.lock:
            self._reload_if_needed()
            for m in self._cache:
                for kw in m.get("keywords", []):
                    if _normalize_kw(kw) == normalized:
                        return m.get("content", "")
        return None


# Global Instance
PROMPT_MAP_MANAGER = PromptMapManager()

# --- API Routes ---
_ROUTE_REGISTERED = False
_ROUTE_TIMER: threading.Timer | None = None

def _ensure_api_routes(prompt_server_provider):
    global _ROUTE_REGISTERED, _ROUTE_TIMER
    if _ROUTE_REGISTERED:
        return

    prompt_server = prompt_server_provider()
    if prompt_server is None:
        if _ROUTE_TIMER is None or not _ROUTE_TIMER.is_alive() or threading.current_thread() is _ROUTE_TIMER:
            timer = threading.Timer(1.0, lambda: _ensure_api_routes(prompt_server_provider))
            timer.daemon = True
            _ROUTE_TIMER = timer
            timer.start()
        return

    @prompt_server.routes.get("/ayf/prompt-maps")
    async def list_maps_handler(request):
        maps = PROMPT_MAP_MANAGER.list_maps()
        return web.json_response({"success": True, "data": maps})

    @prompt_server.routes.post("/ayf/prompt-maps")
    async def save_map_handler(request):
        try:
            data = await request.json()
            map_id = data.get("id")
            keywords_raw = data.get("keywords", [])
            if isinstance(keywords_raw, str):
                keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
            else:
                keywords = keywords_raw
            content = data.get("content", "")
            category = data.get("category", "默认")
            color = data.get("color", "#2196F3")

            if map_id:
                result = PROMPT_MAP_MANAGER.update_map(map_id, keywords, content, category, color)
            else:
                result = PROMPT_MAP_MANAGER.add_map(keywords, content, category, color)

            if isinstance(result, str):
                return web.json_response({"success": False, "message": result}, status=409)
            if result is None:
                return web.json_response({"success": False, "message": "未找到对应映射"}, status=404)
            return web.json_response({"success": True, "data": result})
        except Exception as e:
            return web.json_response({"success": False, "message": str(e)}, status=500)

    @prompt_server.routes.delete("/ayf/prompt-maps")
    async def delete_map_handler(request):
        try:
            data = await request.json()
            map_id = data.get("id")
        except Exception:
            map_id = request.rel_url.query.get("id")

        if not map_id:
            return web.json_response({"success": False, "message": "Missing id"}, status=400)

        success = PROMPT_MAP_MANAGER.delete_map(map_id)
        if success:
            return web.json_response({"success": True})
        return web.json_response({"success": False, "message": "Not found"}, status=404)

    _ROUTE_REGISTERED = True


_ensure_api_routes(lambda: getattr(PromptServer, "instance", None))


# --- ComfyUI Node ---
class AYFPromptMapNode:
    """
    提示层映射助手
    输入关键词，输出预设的完整提示词文本
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyword": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("content",)
    FUNCTION = "execute"
    CATEGORY = "AYFdiy/"

    def execute(self, keyword):
        kw = keyword.strip() if isinstance(keyword, str) else ""
        if not kw:
            raise ValueError("关键词不能为空")
        result = PROMPT_MAP_MANAGER.resolve(kw)
        if result is None:
            raise ValueError(f'关键词 "{kw}" 未找到任何映射，请先在节点下方添加映射关系')
        return (result,)


NODE_CLASS_MAPPINGS = {
    "AYFPromptMapNode": AYFPromptMapNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AYFPromptMapNode": "AYF提示词映射助手"
}
