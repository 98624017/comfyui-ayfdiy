import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const EXTENSION_NAME = "ayf.promptMapManager";
const TARGET_NODE = "AYFPromptMapNode";
const DEFAULT_NODE_SIZE = [760, 340];

// --- Color Palette (共用 snippet_manager 配色) ---
const COLOR_PALETTE = [
  "#F44336",
  "#E91E63",
  "#9C27B0",
  "#673AB7",
  "#3F51B5",
  "#2196F3",
  "#009688",
  "#4CAF50",
  "#FF9800",
  "#795548",
];

// --- Utils ---
function drawRoundedRect(ctx, x, y, width, height, radius, fill, stroke) {
  ctx.beginPath();
  ctx.roundRect(x, y, width, height, radius);
  if (fill) {
    ctx.fillStyle = fill;
    ctx.fill();
  }
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.stroke();
  }
}

// --- API ---
const PromptMapApi = {
  async getMaps() {
    try {
      const resp = await api.fetchApi("/ayf/prompt-maps");
      if (!resp.ok) return [];
      const data = await resp.json();
      return data.success ? data.data : [];
    } catch (e) {
      console.error("[AYFPromptMap] getMaps 失败:", e.message);
      return [];
    }
  },
  async addMap(keywords, content, category, color) {
    try {
      const resp = await api.fetchApi("/ayf/prompt-maps", {
        method: "POST",
        body: JSON.stringify({ keywords, content, category, color }),
      });
      if (!resp.ok) return { success: false, message: `HTTP ${resp.status}` };
      return await resp.json();
    } catch (e) {
      return { success: false, message: e.message };
    }
  },
  async updateMap(id, keywords, content, category, color) {
    try {
      const resp = await api.fetchApi("/ayf/prompt-maps", {
        method: "POST",
        body: JSON.stringify({ id, keywords, content, category, color }),
      });
      if (!resp.ok) return { success: false, message: `HTTP ${resp.status}` };
      return await resp.json();
    } catch (e) {
      return { success: false, message: e.message };
    }
  },
  async deleteMap(id) {
    try {
      const resp = await api.fetchApi("/ayf/prompt-maps", {
        method: "DELETE",
        body: JSON.stringify({ id }),
      });
      if (!resp.ok) return { success: false, message: `HTTP ${resp.status}` };
      return await resp.json();
    } catch (e) {
      return { success: false, message: e.message };
    }
  },
};

// --- Modal ---
class PromptMapModal {
  constructor() {
    this.element = null;
  }

  create(title, defaultData, existingCategories, onSave) {
    if (this.element) this.close();

    const overlay = document.createElement("div");
    Object.assign(overlay.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100%",
      height: "100%",
      backgroundColor: "rgba(0,0,0,0.5)",
      zIndex: "1000",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
    });

    const panel = document.createElement("div");
    Object.assign(panel.style, {
      backgroundColor: "#222",
      padding: "20px",
      borderRadius: "8px",
      width: "420px",
      display: "flex",
      flexDirection: "column",
      gap: "10px",
      color: "#fff",
      fontFamily: "sans-serif",
      boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
    });

    // Title
    const titleEl = document.createElement("h3");
    titleEl.innerText = title;
    titleEl.style.margin = "0 0 6px 0";
    panel.appendChild(titleEl);

    // Error message area (initially hidden)
    const errorEl = document.createElement("div");
    Object.assign(errorEl.style, {
      color: "#F44336",
      fontSize: "12px",
      padding: "6px 8px",
      backgroundColor: "rgba(244,67,54,0.1)",
      borderRadius: "4px",
      border: "1px solid rgba(244,67,54,0.3)",
      display: "none",
    });
    panel.appendChild(errorEl);

    // Keywords input (single line, comma-separated)
    const kwLabel = document.createElement("div");
    kwLabel.innerText = "关键词（多个用逗号分隔）:";
    kwLabel.style.fontSize = "12px";
    panel.appendChild(kwLabel);

    const kwInput = document.createElement("input");
    kwInput.placeholder = "例: 1girl, girl, 一个女生";
    kwInput.value = (defaultData.keywords || []).join(", ");
    Object.assign(kwInput.style, {
      width: "100%",
      padding: "8px",
      borderRadius: "4px",
      border: "1px solid #444",
      backgroundColor: "#333",
      color: "#fff",
      boxSizing: "border-box",
    });
    panel.appendChild(kwInput);

    // Content textarea (multi-line)
    const contentLabel = document.createElement("div");
    contentLabel.innerText = "完整提示词文本:";
    contentLabel.style.fontSize = "12px";
    panel.appendChild(contentLabel);

    const contentInput = document.createElement("textarea");
    contentInput.placeholder = "输出的完整提示词内容...";
    contentInput.value = defaultData.content || "";
    contentInput.rows = 5;
    Object.assign(contentInput.style, {
      width: "100%",
      padding: "8px",
      borderRadius: "4px",
      border: "1px solid #444",
      backgroundColor: "#333",
      color: "#fff",
      resize: "vertical",
      boxSizing: "border-box",
    });
    panel.appendChild(contentInput);

    // Category row
    const catContainer = document.createElement("div");
    Object.assign(catContainer.style, { display: "flex", gap: "10px" });

    const customCatInput = document.createElement("input");
    customCatInput.placeholder = "自定义分类";
    customCatInput.value = "";
    Object.assign(customCatInput.style, {
      flex: "1",
      padding: "8px",
      borderRadius: "4px",
      border: "1px solid #FFC107",
      backgroundColor: "#333",
      color: "#fff",
    });

    const catSelect = document.createElement("select");
    Object.assign(catSelect.style, {
      flex: "1",
      padding: "8px",
      borderRadius: "4px",
      border: "1px solid #FFC107",
      backgroundColor: "#333",
      color: "#fff",
    });

    const availableTags = existingCategories.filter((t) => t !== "全部");
    if (!availableTags.includes("默认")) availableTags.unshift("默认");
    availableTags.forEach((tag) => {
      const opt = document.createElement("option");
      opt.value = tag;
      opt.innerText = tag;
      if (tag === defaultData.category) opt.selected = true;
      catSelect.appendChild(opt);
    });

    if (defaultData.category && !availableTags.includes(defaultData.category)) {
      customCatInput.value = defaultData.category;
    }

    catContainer.appendChild(customCatInput);
    catContainer.appendChild(catSelect);
    panel.appendChild(catContainer);

    // Color picker
    const colorLabel = document.createElement("div");
    colorLabel.innerText = "选择颜色:";
    colorLabel.style.fontSize = "12px";
    panel.appendChild(colorLabel);

    const colorContainer = document.createElement("div");
    Object.assign(colorContainer.style, {
      display: "flex",
      flexWrap: "wrap",
      gap: "5px",
    });

    let selectedColor = defaultData.color || COLOR_PALETTE[5]; // Default: Blue
    COLOR_PALETTE.forEach((c) => {
      const swatch = document.createElement("div");
      Object.assign(swatch.style, {
        width: "24px",
        height: "24px",
        borderRadius: "50%",
        backgroundColor: c,
        cursor: "pointer",
        border:
          selectedColor === c ? "2px solid #fff" : "2px solid transparent",
      });
      swatch.onclick = () => {
        selectedColor = c;
        Array.from(colorContainer.children).forEach(
          (ch) => (ch.style.border = "2px solid transparent"),
        );
        swatch.style.border = "2px solid #fff";
      };
      colorContainer.appendChild(swatch);
    });
    panel.appendChild(colorContainer);

    // Buttons
    const btnRow = document.createElement("div");
    Object.assign(btnRow.style, {
      display: "flex",
      justifyContent: "flex-end",
      gap: "10px",
      marginTop: "10px",
    });

    const cancelBtn = document.createElement("button");
    cancelBtn.innerText = "取消";
    Object.assign(cancelBtn.style, {
      padding: "5px 15px",
      borderRadius: "4px",
      border: "none",
      backgroundColor: "#555",
      color: "#fff",
      cursor: "pointer",
    });
    cancelBtn.onclick = () => this.close();

    const saveBtn = document.createElement("button");
    saveBtn.innerText = "保存";
    Object.assign(saveBtn.style, {
      padding: "5px 15px",
      borderRadius: "4px",
      border: "none",
      backgroundColor: "#2196F3",
      color: "#fff",
      cursor: "pointer",
    });
    saveBtn.onclick = async () => {
      const finalCategory =
        customCatInput.value.trim() || catSelect.value || "默认";
      const kwRaw = kwInput.value;
      const keywords = kwRaw
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k.length > 0);
      if (keywords.length === 0) {
        errorEl.innerText = "关键词不能为空";
        errorEl.style.display = "block";
        return;
      }
      if (!contentInput.value.trim()) {
        errorEl.innerText = "完整文本内容不能为空";
        errorEl.style.display = "block";
        return;
      }
      errorEl.style.display = "none";
      const result = await onSave({
        keywords,
        content: contentInput.value,
        category: finalCategory,
        color: selectedColor,
      });
      // result: null = success, string = error message
      if (result) {
        errorEl.innerText = result;
        errorEl.style.display = "block";
      } else {
        this.close();
      }
    };

    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(saveBtn);
    panel.appendChild(btnRow);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    this.element = overlay;

    // 返回 panel 引用以便外部插入删除按钮
    return { panel, btnRow };
  }

  close() {
    if (this.element) {
      document.body.removeChild(this.element);
      this.element = null;
    }
  }
}

const MODAL = new PromptMapModal();

// --- Main Widget ---
class PromptMapWidget {
  constructor(node) {
    this.node = node;
    this.maps = []; // raw map objects from server
    this.chips = []; // flat list: { keyword, map } for rendering
    this.tags = ["全部"];
    this.activeTag = "全部";
    this.editMode = false;

    this.hoveredChip = null;
    this.hoverStartTime = 0;
    this.hoverTimer = null;

    this.lastCalculatedHeight = undefined;
    this.isLoading = false;

    this.addBtnHitbox = null;
    this.editBtnHitbox = null;
    this.refreshBtnHitbox = null;
    this.tagHitboxes = [];
    this.chipHitboxes = [];

    this.loadMaps();
  }

  async loadMaps() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.node.setDirtyCanvas(true, true);
    try {
      this.maps = await PromptMapApi.getMaps();
      this.updateTags();
      this._buildChips();
    } catch (e) {
      console.error("[AYFPromptMap] Load failed", e);
    } finally {
      this.isLoading = false;
      this.node.setDirtyCanvas(true, true);
    }
  }

  updateTags() {
    const cats = new Set(this.maps.map((m) => m.category || "默认"));
    const others = Array.from(cats)
      .filter((c) => c !== "默认")
      .sort();
    this.tags = ["全部"];
    if (cats.has("默认")) this.tags.push("默认");
    this.tags.push(...others);
  }

  _buildChips() {
    // 每条 map 的每个关键词展开为独立 chip
    this.chips = [];
    for (const m of this.maps) {
      for (const kw of m.keywords || []) {
        this.chips.push({ keyword: kw, map: m });
      }
    }
  }

  getFilteredChips() {
    if (this.activeTag === "全部") return this.chips;
    return this.chips.filter(
      (c) => (c.map.category || "默认") === this.activeTag,
    );
  }

  calculateContentHeight(widgetWidth, ctx) {
    const contentStartX = 15;
    const contentWidth = widgetWidth - 30;
    const tagHeight = 24;
    const tagGap = 8;

    ctx.font = "12px sans-serif";

    const editBtnText = this.editMode ? "退出编辑" : "编辑模式";
    const editBtnWidth = ctx.measureText(editBtnText).width + 20;
    const addBtnWidth = 40;
    const refreshBtnWidth = 24;
    const buttonsReservedWidth =
      editBtnWidth + addBtnWidth + refreshBtnWidth + 30;

    let tagX = contentStartX;
    let tagY = 10;
    this.tags.forEach((tag) => {
      const tw = ctx.measureText(tag).width + 16;
      const reserved = tagY === 10 ? buttonsReservedWidth : 0;
      if (tagX + tw > 10 + contentWidth + 15 - reserved) {
        tagX = contentStartX;
        tagY += tagHeight + tagGap;
      }
      tagX += tw + tagGap;
    });

    let currentY = Math.max(tagY + tagHeight + 10, 45);
    currentY += 10; // separator + margin

    const filtered = this.getFilteredChips();
    let chipX = contentStartX;
    let chipY = currentY;
    const chipH = 28;
    const gap = 8;

    filtered.forEach((chip) => {
      const label = chip.keyword;
      const tw = ctx.measureText(label).width + 20;
      if (chipX + tw > widgetWidth - 15) {
        chipX = contentStartX;
        chipY += chipH + gap;
      }
      chipX += tw + gap;
    });

    const requiredH =
      filtered.length === 0 ? currentY + 10 : chipY + chipH + 10;
    return requiredH;
  }

  draw(ctx, node, widgetWidth, y, _height) {
    const neededHeight = this.calculateContentHeight(widgetWidth, ctx);

    // Store layout info
    try {
      node.__bananaPromptMapWidgetTopY = y;
      node.__bananaPromptMapWidgetNeededHeight = neededHeight;
    } catch (_) {}

    // Initialize
    if (this.lastCalculatedHeight === undefined) {
      this.lastCalculatedHeight = neededHeight;
    }

    // Delta resize
    const diff = neededHeight - this.lastCalculatedHeight;
    if (Math.abs(diff) > 1) {
      const newH = Math.max(node.size[1] + diff, 200);
      try {
        node.__bananaPromptMapResizing = true;
        node.setSize([node.size[0], newH]);
      } finally {
        node.__bananaPromptMapResizing = false;
      }
      this.lastCalculatedHeight = neededHeight;
    }

    // Fill slack to keyword textarea
    try {
      const slack = node.size[1] - (y + neededHeight) - 10;
      if (Math.abs(slack) > 4) {
        const kwWidget = node.widgets.find((w) => w.name === "keyword");
        if (kwWidget) {
          let curH = 60;
          if (kwWidget.computeSize)
            curH = kwWidget.computeSize(node.size[0])[1];
          const newH = Math.max(curH + slack, 30);
          if (Math.abs(newH - curH) > 2) {
            try {
              if (kwWidget.options) kwWidget.options.height = newH;
              kwWidget.height = newH;
            } catch (_) {}
          }
        }
      }
    } catch (_) {}

    // Background
    ctx.fillStyle = "#1a1a1a";
    ctx.beginPath();
    ctx.rect(10, y, widgetWidth - 20, neededHeight);
    ctx.fill();

    const contentStartX = 15;
    const contentWidth = widgetWidth - 30;
    let currentY = y + 10;

    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Buttons
    const editBtnText = this.editMode ? "退出编辑" : "编辑模式";
    const editBtnWidth = ctx.measureText(editBtnText).width + 20;
    const editBtnX = 10 + contentWidth + 15 - editBtnWidth - 5;

    const addBtnWidth = 40;
    const addBtnX = editBtnX - addBtnWidth - 10;
    drawRoundedRect(
      ctx,
      addBtnX,
      currentY,
      addBtnWidth,
      24,
      4,
      "#2E7D32",
      "#4caf50",
    );
    ctx.fillStyle = "#fff";
    ctx.fillText("添加", addBtnX + addBtnWidth / 2, currentY + 11);
    this.addBtnHitbox = { x: addBtnX, y: currentY, w: addBtnWidth, h: 24 };

    drawRoundedRect(
      ctx,
      editBtnX,
      currentY,
      editBtnWidth,
      24,
      4,
      this.editMode ? "#D84315" : "#333",
      "#555",
    );
    ctx.fillStyle = "#fff";
    ctx.fillText(editBtnText, editBtnX + editBtnWidth / 2, currentY + 11);
    this.editBtnHitbox = { x: editBtnX, y: currentY, w: editBtnWidth, h: 24 };

    const refreshBtnWidth = 24;
    const refreshBtnX = addBtnX - refreshBtnWidth - 10;
    drawRoundedRect(
      ctx,
      refreshBtnX,
      currentY,
      refreshBtnWidth,
      24,
      4,
      "#555",
      "#777",
    );
    ctx.save();
    if (this.isLoading) {
      const cx = refreshBtnX + refreshBtnWidth / 2;
      const cy = currentY + 12;
      const angle = (performance.now() / 300) * 2 * Math.PI;
      ctx.translate(cx, cy);
      ctx.rotate(angle);
      ctx.fillStyle = "#81C784";
      ctx.font = "16px sans-serif";
      ctx.fillText("↻", 0, 0);
      this.node.setDirtyCanvas(true, false);
    } else {
      ctx.fillStyle = "#fff";
      ctx.font = "16px sans-serif";
      ctx.fillText("↻", refreshBtnX + refreshBtnWidth / 2, currentY + 12);
    }
    ctx.restore();
    ctx.font = "12px sans-serif";
    this.refreshBtnHitbox = {
      x: refreshBtnX,
      y: currentY,
      w: refreshBtnWidth,
      h: 24,
    };

    const buttonsReservedWidth =
      editBtnWidth + addBtnWidth + refreshBtnWidth + 30;

    // Tags
    let tagX = contentStartX;
    let tagY = currentY;
    const tagHeight = 24;
    const tagGap = 8;
    this.tagHitboxes = [];

    this.tags.forEach((tag) => {
      const tw = ctx.measureText(tag).width + 16;
      const isFirst = tagY === currentY;
      const reserved = isFirst ? buttonsReservedWidth : 0;
      if (tagX + tw > 10 + contentWidth + 15 - reserved) {
        tagX = contentStartX;
        tagY += tagHeight + tagGap;
      }
      const selected = tag === this.activeTag;
      drawRoundedRect(
        ctx,
        tagX,
        tagY,
        tw,
        tagHeight,
        4,
        selected ? "#555" : null,
        selected ? "#666" : "#383838",
      );
      ctx.fillStyle = selected ? "#fff" : "#aaa";
      ctx.fillText(tag, tagX + tw / 2, tagY + 11);
      this.tagHitboxes.push({ x: tagX, y: tagY, w: tw, h: tagHeight, tag });
      tagX += tw + tagGap;
    });

    currentY = Math.max(tagY + tagHeight + 10, currentY + 35);

    // Separator
    ctx.beginPath();
    ctx.moveTo(15, currentY);
    ctx.lineTo(widgetWidth - 15, currentY);
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 1;
    ctx.stroke();
    currentY += 10;

    // Keyword Chips
    const filtered = this.getFilteredChips();
    let chipX = contentStartX;
    let chipY = currentY;
    const chipH = 28;
    const gap = 8;
    this.chipHitboxes = [];

    filtered.forEach((chip) => {
      const label = chip.keyword;
      const tw = ctx.measureText(label).width + 20;
      if (chipX + tw > widgetWidth - 15) {
        chipX = contentStartX;
        chipY += chipH + gap;
      }
      const color = chip.map.color || "#2196F3";
      drawRoundedRect(ctx, chipX, chipY, tw, chipH, 14, color, null);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, chipX + tw / 2, chipY + 13);
      this.chipHitboxes.push({ x: chipX, y: chipY, w: tw, h: chipH, chip });
      chipX += tw + gap;
    });

    // Tooltip
    if (this.hoveredChip) {
      const box = this.chipHitboxes.find((b) => b.chip === this.hoveredChip);
      if (box && performance.now() - this.hoverStartTime > 600) {
        this._drawTooltip(
          ctx,
          this.hoveredChip.map.content || "",
          box.x,
          box.y,
          box.w,
          box.h,
          widgetWidth,
        );
      }
    }
  }

  _drawTooltip(ctx, text, x, y, w, _h, widgetWidth) {
    if (!text) return;
    const MAX_WIDTH = 300;
    const LINE_HEIGHT = 16;
    const PADDING = 8;

    ctx.save();
    ctx.font = "12px sans-serif";
    ctx.textBaseline = "top";
    ctx.textAlign = "left";

    const lines = [];
    let line = "";
    for (const char of text) {
      const test = line + char;
      if (ctx.measureText(test).width > MAX_WIDTH && line.length > 0) {
        lines.push(line);
        line = char;
      } else {
        line = test;
      }
      if (lines.length >= 5) break; // 最多5行
    }
    // 无论 lines.length 是多少，只要 line 非空就补上（但不超过5行）
    if (line && lines.length < 5) lines.push(line);
    // 若文本过长，在最后一行末尾加省略号
    if (line && lines.length >= 5) lines[4] = lines[4] + "…";

    let maxW = 0;
    lines.forEach((l) => (maxW = Math.max(maxW, ctx.measureText(l).width)));
    const boxW = maxW + PADDING * 2;
    const boxH = lines.length * LINE_HEIGHT + PADDING * 2;

    let boxX = Math.max(
      10,
      Math.min(x + w / 2 - boxW / 2, widgetWidth - 10 - boxW),
    );
    let boxY = y - boxH - 5;

    ctx.shadowColor = "rgba(0,0,0,0.5)";
    ctx.shadowBlur = 8;
    ctx.fillStyle = "rgba(30,30,30,0.95)";
    ctx.strokeStyle = "#FFC107";
    drawRoundedRect(
      ctx,
      boxX,
      boxY,
      boxW,
      boxH,
      6,
      ctx.fillStyle,
      ctx.strokeStyle,
    );
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
    ctx.fillStyle = "#fff";
    lines.forEach((l, i) =>
      ctx.fillText(l, boxX + PADDING, boxY + PADDING + i * LINE_HEIGHT),
    );
    ctx.restore();
  }

  onClick(x, y, _event) {
    // Tags
    for (const box of this.tagHitboxes) {
      if (
        x >= box.x &&
        x <= box.x + box.w &&
        y >= box.y &&
        y <= box.y + box.h
      ) {
        this.activeTag = box.tag;
        this.node.setDirtyCanvas(true, true);
        return;
      }
    }

    // Buttons
    const eb = this.editBtnHitbox;
    if (eb && x >= eb.x && x <= eb.x + eb.w && y >= eb.y && y <= eb.y + eb.h) {
      this.editMode = !this.editMode;
      this.node.setDirtyCanvas(true, true);
      return;
    }
    const ab = this.addBtnHitbox;
    if (ab && x >= ab.x && x <= ab.x + ab.w && y >= ab.y && y <= ab.y + ab.h) {
      this.openAddDialog();
      return;
    }
    const rb = this.refreshBtnHitbox;
    if (rb && x >= rb.x && x <= rb.x + rb.w && y >= rb.y && y <= rb.y + rb.h) {
      this.loadMaps();
      return;
    }

    // Chips
    for (const box of this.chipHitboxes) {
      if (
        x >= box.x &&
        x <= box.x + box.w &&
        y >= box.y &&
        y <= box.y + box.h
      ) {
        if (this.editMode) {
          this.openEditDialog(box.chip.map);
        } else {
          // 替换 keyword 输入框（而非追加）
          const kwWidget = this.node.widgets.find((w) => w.name === "keyword");
          if (kwWidget) {
            kwWidget.value = box.chip.keyword;
            this.node.setDirtyCanvas(true, true);
          }
        }
        return;
      }
    }
  }

  onMove(x, y) {
    let hit = null;
    for (const box of this.chipHitboxes) {
      if (
        x >= box.x &&
        x <= box.x + box.w &&
        y >= box.y &&
        y <= box.y + box.h
      ) {
        hit = box.chip;
        break;
      }
    }
    if (this.hoverTimer) {
      clearTimeout(this.hoverTimer);
      this.hoverTimer = null;
    }
    if (this.hoveredChip !== hit) {
      this.hoveredChip = hit;
      this.node.setDirtyCanvas(true, false);
    }
    if (this.hoveredChip) {
      this.hoverStartTime = performance.now();
      this.hoverTimer = setTimeout(
        () => this.node.setDirtyCanvas(true, false),
        600,
      );
    }
  }

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
      async (data) => {
        const result = await PromptMapApi.addMap(
          data.keywords,
          data.content,
          data.category,
          data.color,
        );
        if (!result.success) return result.message || "保存失败";
        this.loadMaps();
        return null;
      },
    );
  }

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
      async (data) => {
        const result = await PromptMapApi.updateMap(
          map.id,
          data.keywords,
          data.content,
          data.category,
          data.color,
        );
        if (!result.success) return result.message || "保存失败";
        this.loadMaps();
        return null;
      },
    );

    // 插入删除按钮
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
    delBtn.onclick = async () => {
      const result = await PromptMapApi.deleteMap(map.id);
      if (!result.success) {
        console.error("[AYFPromptMap] 删除失败:", result.message);
        return;
      }
      this.loadMaps();
      MODAL.close();
    };
    btnRow.insertBefore(delBtn, btnRow.firstChild);
  }
}

// --- Register Extension ---
app.registerExtension({
  name: EXTENSION_NAME,
  async beforeRegisterNodeDef(nodeType, nodeData, _appCtx) {
    if (nodeData.name !== TARGET_NODE) return;

    try {
      if (nodeType?.prototype?.__bananaPromptMapPatched) return;
      nodeType.prototype.__bananaPromptMapPatched = true;
    } catch (e) {
      console.warn(`[${EXTENSION_NAME}] patch guard 失败`, e);
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      let r;
      try {
        r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
      } catch (e) {
        console.warn(`[${EXTENSION_NAME}] onNodeCreated 原逻辑失败`, e);
        r = undefined;
      }

      // Hook onMouseMove for tooltip
      try {
        const origMove = this.onMouseMove;
        this.onMouseMove = function (_event, pos) {
          try {
            if (origMove) origMove.apply(this, arguments);
          } catch (_) {}
          try {
            if (this.promptMapWidget)
              this.promptMapWidget.onMove(pos[0], pos[1]);
          } catch (_) {}
        };
      } catch (e) {
        console.warn(`[${EXTENSION_NAME}] onMouseMove hook 失败`, e);
      }

      // Add custom widget
      try {
        const widgetDef = {
          name: "prompt_map_ui",
          type: "prompt_map_debug",
          computeSize: (width) => {
            let h = 300;
            if (this.promptMapWidget?.lastCalculatedHeight)
              h = this.promptMapWidget.lastCalculatedHeight;
            return [width, h];
          },
          draw: (ctx, node, width, y, height) => {
            if (!this.promptMapWidget)
              this.promptMapWidget = new PromptMapWidget(this);
            this.promptMapWidget.draw(ctx, node, width, y, height);
          },
          mouse: (event, pos, _node) => {
            if (event.type === "pointerdown" && this.promptMapWidget) {
              this.promptMapWidget.onClick(pos[0], pos[1], event);
            }
            return false;
          },
        };
        const widget = this.addCustomWidget(widgetDef);
        try {
          if (widget) widget.computeSize = widgetDef.computeSize;
        } catch (_) {}
      } catch (e) {
        console.warn(`[${EXTENSION_NAME}] widget 创建失败`, e);
      }

      // Default size (delayed to avoid overriding deserialized size)
      try {
        if (!this.__bananaPromptMapDefaultSizeScheduled) {
          this.__bananaPromptMapDefaultSizeScheduled = true;
          setTimeout(() => {
            try {
              if (
                !this.__bananaPromptMapHasSerializedSize &&
                typeof this.setSize === "function"
              ) {
                this.setSize(DEFAULT_NODE_SIZE);
              }
            } catch (e) {
              console.warn(`[${EXTENSION_NAME}] 默认尺寸设置失败`, e);
            }
          }, 0);
        }
      } catch (e) {
        console.warn(`[${EXTENSION_NAME}] 默认尺寸调度失败`, e);
      }

      return r;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (_configData) {
      let r;
      try {
        r = onConfigure ? onConfigure.apply(this, arguments) : undefined;
      } catch (_) {}
      try {
        this.__bananaPromptMapHasSerializedSize = true;
      } catch (_) {}
      return r;
    };

    const onResize = nodeType.prototype.onResize;
    nodeType.prototype.onResize = function () {
      let r;
      try {
        r = onResize ? onResize.apply(this, arguments) : undefined;
      } catch (_) {}
      try {
        if (!this.__bananaPromptMapResizing) {
          const graph = this.graph || app?.graph;
          if (graph?.change)
            setTimeout(() => {
              try {
                graph.change();
              } catch (_) {}
            }, 200);
        }
      } catch (_) {}
      return r;
    };
  },
});
