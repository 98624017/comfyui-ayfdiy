# ayf_prompt_map_node.py
"""AYF 提示词映射助手 — 节点实例隔离版"""
import json


class AYFPromptMapNode:
    """
    提示词映射助手
    输入关键词，输出预设的完整提示词文本。
    映射数据存储在节点 properties 中，随工作流保存/加载，各节点实例独立。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyword": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "_map_data": ("STRING",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("content",)
    FUNCTION = "execute"
    CATEGORY = "AYFdiy/"

    def execute(self, keyword, _map_data="[]"):
        kw = keyword.strip() if isinstance(keyword, str) else ""
        if not kw:
            raise ValueError("关键词不能为空")

        try:
            maps = json.loads(_map_data)
        except (json.JSONDecodeError, TypeError):
            maps = []

        normalized = kw.lower().strip()
        for m in maps:
            for k in m.get("keywords", []):
                if k.strip().lower() == normalized:
                    content = m.get("content", "")
                    if content:
                        return (content,)

        raise ValueError(f'关键词 "{kw}" 未找到任何映射，请先在节点下方添加映射关系')


NODE_CLASS_MAPPINGS = {"AYFPromptMapNode": AYFPromptMapNode}
NODE_DISPLAY_NAME_MAPPINGS = {"AYFPromptMapNode": "AYF提示词映射助手"}
