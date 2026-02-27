# AYFdiy 工具节点集

AYF 定制的 ComfyUI 工具节点集，提供常用辅助功能。

## 安装

将本目录放置到 `ComfyUI/custom_nodes/` 下，重启 ComfyUI 即可自动加载。

```
ComfyUI/custom_nodes/AYFdiy/
```

如需安装依赖：

```bash
pip install -r requirements.txt
```

## 节点列表

| 节点名 | 显示名 | 功能 |
|--------|--------|------|
| `AYFIsEmpty` | 是否为空（AYF定制版） | 判断输入是否为空，输出布尔值，支持多种数据类型 |
| `AYFPathLoader` | AYF路径加载 | 从指定目录加载文件路径，支持通配符过滤和排序 |
| `AYFPromptMapNode` | AYF提示词映射助手 | 关键词匹配提示词映射，支持 TOML 配置和前端管理界面 |

## 节点说明

### 是否为空（AYFIsEmpty）

判断输入数据是否为空值。支持字符串、图像张量、列表等多种类型的空值检测。

- **输入**：任意类型数据
- **输出**：布尔值（`True` = 为空，`False` = 不为空）

### 路径加载（AYFPathLoader）

从指定目录加载文件路径列表，适合批量处理场景。

- **输入**：目录路径、文件过滤模式（glob）、排序方式
- **输出**：文件路径列表

### 提示词映射助手（AYFPromptMapNode）

基于关键词匹配自动替换提示词。映射规则存储在 `prompt_maps.toml` 中，可通过 ComfyUI 前端管理界面进行增删改查。

- **输入**：原始提示词文本
- **输出**：映射后的提示词文本
- **配置**：`prompt_maps.toml`（支持分类、颜色标记）

## 分类

所有节点位于 ComfyUI 节点菜单的 `AYFdiy` 分类下。
