"""
是否为空（AYF定制版）节点

修复了原 easy isNone 节点的核心痛点：
  - 原节点输入为 required，上游文本节点不执行时整个节点被跳过
  - 原节点仅判断严格空字符串 ""，无法处理 " " / "\n" 等空白字符串
  - 某些上游文本节点文本框为空时，输出的是含空白的字符串而非纯 ""

增强点：
  1. 输入改为 optional forceInput → 未连接时 value=None，正确返回"是空"
  2. trim_whitespace 开关 → 空白字符串也视为空（默认开启）
  3. treat_zero_as_empty 开关 → 控制数字 0 是否视为空（默认关闭）
  4. invert 开关 → 反转输出结果，开启后等价于原 not_empty（默认关闭）
"""


# any_type 用于接受任意 ComfyUI 类型的连线
class _AnyType(str):
    """占位类型，接受任意类型的连线（等价于 EasyUse 的 AlwaysEqualProxy）"""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


any_type = _AnyType("*")


class AYFIsEmpty:
    """
    是否为空（AYF定制版）

    相比原版 easy isNone 的改进：
    - optional 输入：上游未连接 / 上游节点不执行时，value=None，正确返回 True
    - 支持 trim_whitespace：" " / "\\n" 等纯空白字符串也视为空（默认开启）
    - 支持 treat_zero_as_empty：数字 0 是否视为空（默认关闭，保持兼容）
    - 支持 invert：反转输出，开启后等价于"非空"判断（默认关闭）
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trim_whitespace": (
                    "BOOLEAN",
                    {"default": True, "label_on": "空格内容视为空", "label_off": "严格匹配"},
                ),
                "treat_zero_as_empty": (
                    "BOOLEAN",
                    {"default": False, "label_on": "0视为空", "label_off": "0不为空"},
                ),
                "invert": (
                    "BOOLEAN",
                    {"default": False, "label_on": "反转输出", "label_off": "正常输出"},
                ),
            },
            "optional": {
                # forceInput=True：强制显示为输入端口而非文本框控件，
                # 未连接时 value=None（上游节点文本框为空/上游不执行 均可正确返回 True）
                "value": (any_type, {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("is_empty",)
    FUNCTION = "execute"
    CATEGORY = "AYFdiy/"

    def execute(self, trim_whitespace=True, treat_zero_as_empty=False, invert=False, value=None):
        """
        判断 value 是否为"空"，再根据 invert 决定是否取反：
          - None                   → 空
          - ""                     → 空
          - " " / "\\n" 等         → trim_whitespace=True 时为空
          - 0 / 0.0                → treat_zero_as_empty=True 时为空
          - 其他（图像/张量/列表等）→ 非空
          invert=True 时，最终结果取反（等价于"非空"判断）
        """
        # ── 判断是否为空 ──────────────────────────────────────────────────────
        if value is None:
            is_empty = True

        elif isinstance(value, str):
            check_val = value.strip() if trim_whitespace else value
            is_empty = check_val == ""

        elif isinstance(value, (int, float)):
            is_empty = treat_zero_as_empty and value == 0

        else:
            is_empty = False

        # ── invert 反转 ───────────────────────────────────────────────────────
        result = (not is_empty) if invert else is_empty

        return (result,)


# ── ComfyUI 注册 ────────────────────────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "AYFIsEmpty": AYFIsEmpty,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AYFIsEmpty": "是否为空（AYF定制版）",
}
