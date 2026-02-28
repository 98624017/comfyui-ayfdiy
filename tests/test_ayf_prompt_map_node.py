# tests/test_ayf_prompt_map_node.py
"""AYFPromptMapNode 单元测试"""
import json
import pytest
import sys
from pathlib import Path

# 将项目根目录加入 sys.path 以便导入
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAYFPromptMapNode:
    """测试 AYFPromptMapNode.execute()"""

    def _make_node(self):
        from ayf_prompt_map_node import AYFPromptMapNode
        return AYFPromptMapNode()

    def _make_map_data(self, maps):
        return json.dumps(maps, ensure_ascii=False)

    def test_basic_keyword_match(self):
        """关键词精确匹配应返回对应 content"""
        node = self._make_node()
        maps = [{"keywords": ["裤子", "连衣裙"], "content": "下半身描述文本"}]
        result = node.execute("裤子", self._make_map_data(maps))
        assert result == ("下半身描述文本",)

    def test_case_insensitive_match(self):
        """关键词匹配应忽略大小写"""
        node = self._make_node()
        maps = [{"keywords": ["Girl"], "content": "a girl description"}]
        result = node.execute("girl", self._make_map_data(maps))
        assert result == ("a girl description",)

    def test_whitespace_trimmed(self):
        """关键词前后空格应被忽略"""
        node = self._make_node()
        maps = [{"keywords": ["裤子"], "content": "下半身描述"}]
        result = node.execute("  裤子  ", self._make_map_data(maps))
        assert result == ("下半身描述",)

    def test_keyword_not_found_raises(self):
        """未匹配关键词应抛出 ValueError"""
        node = self._make_node()
        maps = [{"keywords": ["裤子"], "content": "下半身描述"}]
        with pytest.raises(ValueError, match="未找到任何映射"):
            node.execute("不存在的关键词", self._make_map_data(maps))

    def test_empty_keyword_raises(self):
        """空关键词应抛出 ValueError"""
        node = self._make_node()
        with pytest.raises(ValueError, match="关键词不能为空"):
            node.execute("", "[]")

    def test_empty_map_data_raises(self):
        """空映射数据 + 任意关键词应抛出 ValueError"""
        node = self._make_node()
        with pytest.raises(ValueError, match="未找到任何映射"):
            node.execute("anything", "[]")

    def test_invalid_json_treated_as_empty(self):
        """无效 JSON 应被安全处理为空映射"""
        node = self._make_node()
        with pytest.raises(ValueError, match="未找到任何映射"):
            node.execute("keyword", "not valid json")

    def test_multiple_maps_isolation(self):
        """多条映射条目应各自独立匹配"""
        node = self._make_node()
        maps = [
            {"keywords": ["裤子"], "content": "裤子描述"},
            {"keywords": ["衬衫"], "content": "衬衫描述"},
        ]
        data = self._make_map_data(maps)
        assert node.execute("裤子", data) == ("裤子描述",)
        assert node.execute("衬衫", data) == ("衬衫描述",)

    def test_first_match_wins(self):
        """多条映射有相同关键词时，第一个匹配生效"""
        node = self._make_node()
        maps = [
            {"keywords": ["裤子"], "content": "第一条描述"},
            {"keywords": ["裤子"], "content": "第二条描述"},
        ]
        result = node.execute("裤子", self._make_map_data(maps))
        assert result == ("第一条描述",)

    def test_input_types_has_hidden_map_data(self):
        """INPUT_TYPES 应包含隐藏的 _map_data 字段"""
        from ayf_prompt_map_node import AYFPromptMapNode
        types = AYFPromptMapNode.INPUT_TYPES()
        assert "hidden" in types
        assert "_map_data" in types["hidden"]

    def test_default_map_data_parameter(self):
        """_map_data 参数默认值为 '[]'"""
        node = self._make_node()
        with pytest.raises(ValueError, match="未找到任何映射"):
            node.execute("keyword")
