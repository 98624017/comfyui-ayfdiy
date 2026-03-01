# AYF提示词映射助手 — 节点实例隔离设计

**日期**: 2026-02-28
**状态**: 已批准

## 问题

当前 `AYFPromptMapNode` 使用全局单例 `PROMPT_MAP_MANAGER` 管理映射数据，
所有节点实例共享同一份映射表（存储在 `prompt_maps.toml` 中）。
用户在工作流中放置多个映射节点时，它们的数据互相同步，无法独立配置。

## 目标

- 每个 `AYFPromptMapNode` 实例拥有**独立的映射表**
- 不同节点的关键词**可以重复**，各自映射到不同内容
- 映射数据随**工作流 JSON 保存/加载**，无需外部文件
- 复制节点时映射数据**自动复制且独立**

## 方案

**工作流内嵌存储 — 基于 `node.properties`**

利用 ComfyUI 的 `node.properties` 持久化机制：
- `properties` 对象随工作流 JSON 自动序列化/反序列化
- 复制节点时 `properties` 自动深拷贝
- 不参与 Python 执行管线，不污染 widget

## 架构

### 数据存储

映射数据存储在每个节点实例的 `node.properties.mapData` 中：

```javascript
node.properties = {
  mapData: [
    {
      id: "uuid",
      keywords: ["裤子", "连衣裙"],
      content: "完整提示词文本...",
      category: "默认",
      color: "#2196F3"
    }
  ]
}
```

工作流 JSON 中的表现：

```json
{
  "id": 42,
  "type": "AYFPromptMapNode",
  "properties": {
    "mapData": [...]
  },
  "widgets_values": ["裤子", "[]"]
}
```

### Python 后端

移除：
- `PromptMapManager` 类及全局单例
- `prompt_maps.toml` 文件读写逻辑
- `/ayf/prompt-maps` 全部 API 路由
- `_normalize_kw()` 辅助函数（保留或内联到 `execute()` 中）

改造 `AYFPromptMapNode`：

```python
class AYFPromptMapNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyword": ("STRING", {"multiline": False, "default": ""})
            },
            "hidden": {
                "_map_data": ("STRING",)
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("content",)
    FUNCTION = "execute"
    CATEGORY = "AYFdiy/"

    def execute(self, keyword, _map_data="[]"):
        kw = keyword.strip() if isinstance(keyword, str) else ""
        if not kw:
            raise ValueError("关键词不能为空")

        maps = json.loads(_map_data)
        normalized = kw.lower().strip()
        for m in maps:
            for k in m.get("keywords", []):
                if k.lower().strip() == normalized:
                    return (m.get("content", ""),)

        raise ValueError(f'关键词 "{kw}" 未找到任何映射')
```

### JS 前端

移除：
- `PromptMapApi` 模块（HTTP API 客户端）
- 所有 `api.fetchApi("/ayf/prompt-maps")` 调用

改造数据操作：
- CRUD 操作直接操作 `node.properties.mapData` 数组
- 每次修改后同步到隐藏 widget `_map_data`

关键生命周期：

```javascript
// 初始化
onNodeCreated() {
    if (!this.properties.mapData) {
        this.properties.mapData = [];
    }
    // 添加隐藏 widget
    this._mapDataWidget = this.addWidget(
        "text", "_map_data", "[]", () => {},
        { serialize: true, hidden: true }
    );
    this._syncMapData();
}

// 恢复
onConfigure(info) {
    // properties 已自动恢复
    this._syncMapData();
}

// 执行前同步
onExecutionStart() {
    this._syncMapData();
}

// 同步函数
_syncMapData() {
    if (this._mapDataWidget) {
        this._mapDataWidget.value = JSON.stringify(
            this.properties.mapData || []
        );
    }
}
```

CRUD 操作改为本地：

```javascript
// 添加映射（替代 PromptMapApi.addMap）
addMap(keywords, content, category, color) {
    const map = {
        id: crypto.randomUUID(),
        keywords, content, category, color
    };
    this.node.properties.mapData.push(map);
    this._syncMapData();
    return map;
}

// 更新映射（替代 PromptMapApi.updateMap）
updateMap(id, keywords, content, category, color) {
    const maps = this.node.properties.mapData;
    const idx = maps.findIndex(m => m.id === id);
    if (idx >= 0) {
        maps[idx] = { ...maps[idx], keywords, content, category, color };
        this._syncMapData();
    }
}

// 删除映射（替代 PromptMapApi.deleteMap）
deleteMap(id) {
    const maps = this.node.properties.mapData;
    const idx = maps.findIndex(m => m.id === id);
    if (idx >= 0) {
        maps.splice(idx, 1);
        this._syncMapData();
    }
}
```

### 数据流

**编辑时：**

```
用户点击 UI 添加/编辑/删除
  -> JS 修改 node.properties.mapData（内存）
  -> 同步到隐藏 widget _map_data
  -> 用户保存工作流 -> properties 自动持久化
```

**执行时：**

```
ComfyUI 执行管线启动
  -> onExecutionStart: 同步 properties.mapData -> _map_data widget
  -> Python execute(keyword, _map_data):
      解析 JSON，在本节点映射中查找 keyword
  -> 输出 content
```

**加载工作流时：**

```
ComfyUI 加载工作流 JSON
  -> 自动恢复 node.properties（含 mapData）
  -> onConfigure: 同步到 _map_data widget
  -> PromptMapWidget 从 properties.mapData 读取数据渲染 UI
```

## 隔离保证

| 场景 | 行为 |
|------|------|
| 创建新节点 | `properties.mapData = []`，空白开始 |
| 复制节点 | `properties` 自动深拷贝，映射数据独立 |
| 编辑节点 A 的映射 | 只修改 A 的 `properties.mapData`，B 不受影响 |
| 删除节点 | `properties` 随节点销毁，无残留 |
| 保存/加载工作流 | 每个节点的 `properties` 独立序列化/恢复 |

## 删除清单

以下代码/文件将被完全移除：

- `PromptMapManager` 类（`ayf_prompt_map_node.py` 第 32-201 行）
- `PROMPT_MAP_MANAGER` 全局单例（第 205 行）
- `_normalize_kw()` 函数（第 27-29 行）
- `_ensure_api_routes()` 函数及所有 API 路由（第 207-276 行）
- `prompt_maps.toml` 文件
- `PromptMapApi` 对象（JS 第 37-85 行）
- 所有 `api.fetchApi("/ayf/prompt-maps")` 调用

## 不变项

- 节点名称 `AYFPromptMapNode` 不变
- 节点分类 `AYFdiy/` 不变
- 输入 `keyword`（STRING）不变
- 输出 `content`（STRING）不变
- UI 外观（chip 展示、分类标签、编辑模态框）不变
- 关键词标准化逻辑（大小写不敏感）不变
