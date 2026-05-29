"""
用户配置模块 —— 窗口大小、开机自启、API Key 等
"""

import json
import os
from .utils import config_dir


class Settings:
    """宠物应用配置管理"""

    DEFAULT_CONFIG = {
        "pet_width": 200,
        "pet_height": 200,
        "animation": "idle.gif",
        "opacity": 1.0,
        "always_on_top": True,
        "auto_start": False,
        "ai_api_key": "sk-a786b91f0dc34a4986c6deb3f80862b4",
        "ai_api_url": "https://api.deepseek.com/v1/chat/completions",
        "ai_model": "deepseek-v4-flash",
        "window_x": None,
        "window_y": None,
        # ── 各动画状态对应的 GIF 文件 ──
        "anim_idle": "idle.gif",
        "anim_drag": "drag.gif",
        "anim_click": "click.gif",
        "anim_talk": "talk.gif",
        # ── 扩展状态（用户自定义） ──
        "anim_extra": {},
        # ── 定时轮换配置 ──
        "rotation_enabled": True,
        "rotation_interval": 30000,
        "rotation_pool": [],
    }

    def __init__(self):
        self.config_path = os.path.join(config_dir(), "config.json")
        self._data = dict(self.DEFAULT_CONFIG)
        self.load()

    def load(self):
        """从 JSON 文件加载配置（空字符串不覆盖默认值）"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # 只覆盖非空值，避免 config.json 中的空字符串覆盖代码默认值
                for k, v in loaded.items():
                    if v != "" or k not in self._data or self._data[k] == "":
                        self._data[k] = v
        except (json.JSONDecodeError, OSError):
            pass

    def save(self):
        """保存配置到 JSON 文件"""
        os.makedirs(config_dir(), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    @property
    def pet_width(self) -> int:
        return self._data.get("pet_width", 200)

    @pet_width.setter
    def pet_width(self, value: int):
        self._data["pet_width"] = value

    @property
    def pet_height(self) -> int:
        return self._data.get("pet_height", 200)

    @pet_height.setter
    def pet_height(self, value: int):
        self._data["pet_height"] = value

    @property
    def animation(self) -> str:
        return self._data.get("animation", "idle.gif")

    @animation.setter
    def animation(self, value: str):
        self._data["animation"] = value

    @property
    def ai_api_key(self) -> str:
        return self._data.get("ai_api_key", "")

    @ai_api_key.setter
    def ai_api_key(self, value: str):
        self._data["ai_api_key"] = value

    @property
    def always_on_top(self) -> bool:
        return self._data.get("always_on_top", True)

    @always_on_top.setter
    def always_on_top(self, value: bool):
        self._data["always_on_top"] = value

    # ── 各动画状态 GIF 文件 ────────────────────────────

    @property
    def anim_idle(self) -> str:
        return self._data.get("anim_idle", "idle.gif")

    @anim_idle.setter
    def anim_idle(self, value: str):
        self._data["anim_idle"] = value

    @property
    def anim_drag(self) -> str:
        return self._data.get("anim_drag", "drag.gif")

    @anim_drag.setter
    def anim_drag(self, value: str):
        self._data["anim_drag"] = value

    @property
    def anim_click(self) -> str:
        return self._data.get("anim_click", "click.gif")

    @anim_click.setter
    def anim_click(self, value: str):
        self._data["anim_click"] = value

    @property
    def anim_talk(self) -> str:
        return self._data.get("anim_talk", "talk.gif")

    @anim_talk.setter
    def anim_talk(self, value: str):
        self._data["anim_talk"] = value

    # ── 扩展状态 ──────────────────────────────────────

    @property
    def anim_extra(self) -> dict:
        return dict(self._data.get("anim_extra", {}))

    @anim_extra.setter
    def anim_extra(self, value: dict):
        self._data["anim_extra"] = value

    # ── 定时轮换 ──────────────────────────────────────

    @property
    def rotation_enabled(self) -> bool:
        return self._data.get("rotation_enabled", True)

    @rotation_enabled.setter
    def rotation_enabled(self, value: bool):
        self._data["rotation_enabled"] = value

    @property
    def rotation_interval(self) -> int:
        return self._data.get("rotation_interval", 30000)

    @rotation_interval.setter
    def rotation_interval(self, value: int):
        self._data["rotation_interval"] = value

    @property
    def rotation_pool(self) -> list:
        return list(self._data.get("rotation_pool", []))

    @rotation_pool.setter
    def rotation_pool(self, value: list):
        self._data["rotation_pool"] = value
