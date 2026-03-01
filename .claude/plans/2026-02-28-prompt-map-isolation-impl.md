# AYF提示词映射助手 — 节点实例隔离实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将映射数据从全局单例改为每个节点实例独立存储在 `node.properties.mapData` 中，随工作流保存/加载。

**Architecture:** 移除 Python 端的 `PromptMapManager` 全局单例、TOML 文件存储和 API 路由。Python 节点通过隐藏的 `_map_data` widget 接收前端序列化的映射 JSON。JS 前端的 CRUD 操作改为直接操作 `node.properties.mapData`，不再调用 HTTP API。

**Tech Stack:** Python 3.12 / ComfyUI / LiteGraph.js / aiohttp(移除)

---

### Task 1: Python 后端 — 重写 `ayf_prompt_map_node.py`

**Files:**
- Modify: `ayf_prompt_map_node.py` (全部重写，从 315 行精简到约 50 行)
- Delete: `prompt_maps.toml` (如存在)

**Step 1: 重写 Python 节点文件**

删除以下全部内容（第 1-276 行）：
- `_normalize_kw()` 函数
- `PromptMapManager` 类
- `PROMPT_MAP_MANAGER` 全局单例
- `_ensure_api_routes()` 及所有 API 路由
- 所有不再需要的 import（`os`, `threading`, `uuid`, `typing`, `aiohttp`, `datetime`, `tomllib`）

保留并改造 `AYFPromptMapNode`（第 280-314 行）：

```python
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
```

**Step 2: 删除旧 TOML 数据文件（如存在）**

```bash
rm -f /home/feng/project/ComfyUI/custom_nodes/AYFdiy/prompt_maps.toml
```

**Step 3: 运行 Python 语法检查**

```bash
cd /home/feng/project/ComfyUI/custom_nodes/AYFdiy
python -c "import py_compile; py_compile.compile('ayf_prompt_map_node.py', doraise=True)"
```

Expected: 无错误

---

### Task 2: Python 测试 — 验证 execute 逻辑

**Files:**
- Create: `tests/test_ayf_prompt_map_node.py`

**Step 1: 编写测试**

```python
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
```

**Step 2: 运行测试验证通过**

```bash
cd /home/feng/project/ComfyUI/custom_nodes/AYFdiy
python -m pytest tests/test_ayf_prompt_map_node.py -v
```

Expected: 全部 PASS

---

### Task 3: JS 前端 — 移除 API 层，改用 node.properties

**Files:**
- Modify: `web/extensions/ayf_prompt_map_manager.js` (大量改造)

**Step 1: 移除 `PromptMapApi` 对象**

删除第 36-85 行的 `PromptMapApi` 常量。

**Step 2: 改造 `PromptMapWidget` 类**

将构造函数中的 `this.maps = []` 改为从 `node.properties.mapData` 读取：

```javascript
class PromptMapWidget {
  constructor(node) {
    this.node = node;
    // 从 node.properties 读取映射数据（而非 API）
    if (!this.node.properties) this.node.properties = {};
    if (!Array.isArray(this.node.properties.mapData)) {
      this.node.properties.mapData = [];
    }
    this.chips = [];
    this.tags = ["全部"];
    this.activeTag = "全部";
    this.editMode = false;

    this.hoveredChip = null;
    this.hoverStartTime = 0;
    this.hoverTimer = null;

    this.lastCalculatedHeight = undefined;

    this.addBtnHitbox = null;
    this.editBtnHitbox = null;
    this.tagHitboxes = [];
    this.chipHitboxes = [];

    // 初始构建 UI 数据
    this.updateTags();
    this._buildChips();
  }
```

移除 `isLoading` 状态（不再有异步加载）。
移除 `refreshBtnHitbox`（不再需要刷新按钮）。
移除 `async loadMaps()` 方法。

**Step 3: 添加本地 CRUD 方法到 `PromptMapWidget`**

```javascript
  // --- 本地 CRUD（替代 PromptMapApi）---

  get maps() {
    return this.node.properties.mapData || [];
  }

  _syncMapDataWidget() {
    const w = this.node.widgets?.find((w) => w.name === "_map_data");
    if (w) w.value = JSON.stringify(this.maps);
  }

  _afterDataChange() {
    this.updateTags();
    this._buildChips();
    this._syncMapDataWidget();
    this.node.setDirtyCanvas(true, true);
  }

  addMap(keywords, content, category, color) {
    const id = crypto.randomUUID
      ? crypto.randomUUID()
      : "id-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
    const map = { id, keywords, content, category, color };
    this.node.properties.mapData.push(map);
    this._afterDataChange();
    return map;
  }

  updateMap(id, keywords, content, category, color) {
    const maps = this.node.properties.mapData;
    const idx = maps.findIndex((m) => m.id === id);
    if (idx >= 0) {
      maps[idx] = { ...maps[idx], keywords, content, category, color };
      this._afterDataChange();
      return maps[idx];
    }
    return null;
  }

  deleteMap(id) {
    const maps = this.node.properties.mapData;
    const idx = maps.findIndex((m) => m.id === id);
    if (idx >= 0) {
      maps.splice(idx, 1);
      this._afterDataChange();
      return true;
    }
    return false;
  }
```

**Step 4: 更新 `updateTags()` 和 `_buildChips()` 使用 `this.maps` getter**

```javascript
  updateTags() {
    const cats = new Set(this.maps.map((m) => m.category || "默认"));
    const others = Array.from(cats).filter((c) => c !== "默认").sort();
    this.tags = ["全部"];
    if (cats.has("默认")) this.tags.push("默认");
    this.tags.push(...others);
  }

  _buildChips() {
    this.chips = [];
    for (const m of this.maps) {
      for (const kw of m.keywords || []) {
        this.chips.push({ keyword: kw, map: m });
      }
    }
  }
```

**Step 5: 更新 `draw()` 方法**

移除刷新按钮相关渲染代码（第 568-603 行的 refreshBtn 绘制、`isLoading` 旋转动画）。
移除 `refreshBtnHitbox` 的使用。
调整 `buttonsReservedWidth` 计算（不再包含 refreshBtnWidth）。

**Step 6: 更新 `onClick()` 方法**

移除刷新按钮点击处理（第 780-784 行的 `rb` 检测块）。

**Step 7: 更新 `openAddDialog()` — 改用本地 CRUD**

```javascript
  openAddDialog() {
    MODAL.create(
      "添加映射关系",
      {
        keywords: [],
        content: "",
        category: this.activeTag === "全部" ? "默认" : this.activeTag,
        color: COLOR_PALETTE[5],
      },
      this.tags,
      (data) => {
        // 本节点关键词冲突检查
        const conflict = this._checkKeywordConflict(data.keywords);
        if (conflict) return conflict;
        this.addMap(data.keywords, data.content, data.category, data.color);
        return null; // 成功
      },
    );
  }
```

**Step 8: 更新 `openEditDialog()` — 改用本地 CRUD**

```javascript
  openEditDialog(map) {
    const { btnRow } = MODAL.create(
      "编辑映射关系",
      {
        keywords: map.keywords || [],
        content: map.content || "",
        category: map.category || "默认",
        color: map.color || COLOR_PALETTE[5],
      },
      this.tags,
      (data) => {
        const conflict = this._checkKeywordConflict(data.keywords, map.id);
        if (conflict) return conflict;
        this.updateMap(map.id, data.keywords, data.content, data.category, data.color);
        return null;
      },
    );

    const delBtn = document.createElement("button");
    delBtn.innerText = "删除";
    Object.assign(delBtn.style, {
      padding: "5px 15px",
      borderRadius: "4px",
      border: "none",
      backgroundColor: "#D32F2F",
      color: "#fff",
      cursor: "pointer",
      marginRight: "auto",
    });
    delBtn.onclick = () => {
      this.deleteMap(map.id);
      MODAL.close();
    };
    btnRow.insertBefore(delBtn, btnRow.firstChild);
  }
```

**Step 9: 添加本节点内关键词冲突检查**

```javascript
  _checkKeywordConflict(keywords, excludeId = null) {
    const normalizedNew = new Set(keywords.map((k) => k.trim().toLowerCase()));
    for (const m of this.maps) {
      if (excludeId && m.id === excludeId) continue;
      for (const kw of m.keywords || []) {
        if (normalizedNew.has(kw.trim().toLowerCase())) {
          const preview = (m.content || "").slice(0, 20);
          const cat = m.category || "默认";
          return `关键词 "${kw}" 已被 [${cat}] / "${preview}..." 使用`;
        }
      }
    }
    return null;
  }
```

**Step 10: 更新扩展注册代码 — 添加 `_map_data` 隐藏 widget 和生命周期**

在 `onNodeCreated` 中添加：

```javascript
// 初始化 properties.mapData
if (!this.properties) this.properties = {};
if (!Array.isArray(this.properties.mapData)) {
  this.properties.mapData = [];
}

// 添加隐藏 widget 用于传数据到 Python 后端
const mapDataWidget = this.addWidget("text", "_map_data", "[]", () => {}, {
  serialize: true,
});
// 隐藏该 widget 不占据可见空间
if (mapDataWidget) {
  mapDataWidget.computeSize = () => [0, -4];
  mapDataWidget.type = "converted-widget";
}
```

在 `onConfigure` 中添加数据同步：

```javascript
nodeType.prototype.onConfigure = function (_configData) {
  // ... 原有逻辑 ...
  // 从 properties 恢复后同步隐藏 widget
  try {
    const w = this.widgets?.find((w) => w.name === "_map_data");
    if (w) w.value = JSON.stringify(this.properties?.mapData || []);
  } catch (_) {}
  // 重建 PromptMapWidget 数据
  try {
    if (this.promptMapWidget) {
      this.promptMapWidget.updateTags();
      this.promptMapWidget._buildChips();
    }
  } catch (_) {}
  return r;
};
```

添加 `onExecutionStart` 钩子确保执行前数据同步：

```javascript
const onExecutionStart = nodeType.prototype.onExecutionStart;
nodeType.prototype.onExecutionStart = function () {
  let r;
  try {
    r = onExecutionStart ? onExecutionStart.apply(this, arguments) : undefined;
  } catch (_) {}
  // 确保最新映射数据已同步到隐藏 widget
  try {
    const w = this.widgets?.find((w) => w.name === "_map_data");
    if (w) w.value = JSON.stringify(this.properties?.mapData || []);
  } catch (_) {}
  return r;
};
```

**Step 11: 移除 `api` import（如不再被其他代码使用）**

第 2 行 `import { api } from "/scripts/api.js";` — 移除。

---

### Task 4: 冒烟测试

**Files:** 无新文件

**Step 1: 启动 ComfyUI**

```bash
cd /home/feng/project/ComfyUI
python main.py --listen
```

检查控制台无加载错误。

**Step 2: 创建工作流测试**

1. 在画布添加一个 `AYF提示词映射助手` 节点
2. 点击"添加"按钮，创建一条映射（如 keyword: "裤子"，content: "下半身描述"）
3. 验证 chip 正确显示

**Step 3: 测试隔离性**

1. 复制该节点（Ctrl+C / Ctrl+V）
2. 验证副本节点有相同的映射数据
3. 在副本中添加/删除一条映射
4. 验证原节点的映射不受影响

**Step 4: 测试持久化**

1. 保存工作流
2. 关闭 ComfyUI 重启
3. 加载工作流
4. 验证两个节点各自的映射数据都完整恢复

**Step 5: 测试执行**

1. 连接上游文本节点或手动输入 keyword
2. 连接下游的 "展示任何" 节点
3. 运行工作流
4. 验证输出正确的 content

---

### Task 5: 清理残留文件

**Files:**
- Delete: `prompt_maps.toml` (如存在)

**Step 1: 检查并删除**

```bash
rm -f /home/feng/project/ComfyUI/custom_nodes/AYFdiy/prompt_maps.toml
```

**Step 2: 确认无残留引用**

```bash
cd /home/feng/project/ComfyUI/custom_nodes/AYFdiy
grep -rn "prompt_maps.toml" . --include="*.py" --include="*.js"
grep -rn "PromptMapManager" . --include="*.py" --include="*.js"
grep -rn "PROMPT_MAP_MANAGER" . --include="*.py" --include="*.js"
grep -rn "PromptMapApi" . --include="*.js"
grep -rn "/ayf/prompt-maps" . --include="*.py" --include="*.js"
```

Expected: 全部无输出（或只在计划文件中出现）
