"""
动画管理模块 —— 多状态动画（idle/drag/click/talk + 扩展状态 + 定时轮换）
"""

import os
import random

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QMovie, QPainter, QTransform
from PyQt5.QtWidgets import QLabel
from .utils import anim_path


class _FlipLabel(QLabel):
    """支持水平/垂直翻转的 QLabel，用于根据拖拽方向镜像 GIF"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._flip_h = False
        self._flip_v = False
        self.setScaledContents(True)

    def set_flip(self, horizontal=False, vertical=False):
        """设置翻转方向"""
        if self._flip_h != horizontal or self._flip_v != vertical:
            self._flip_h = horizontal
            self._flip_v = vertical
            self.update()

    def paintEvent(self, event):
        movie = self.movie()
        if movie and (self._flip_h or self._flip_v):
            pixmap = movie.currentPixmap()
            if not pixmap.isNull():
                painter = QPainter(self)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)

                w, h = self.width(), self.height()
                transform = QTransform()
                if self._flip_h:
                    transform.translate(w, 0).scale(-1, 1)
                if self._flip_v:
                    transform.translate(0, h).scale(1, -1)

                painter.setTransform(transform)
                painter.drawPixmap(self.rect(), pixmap, pixmap.rect())
                return

        super().paintEvent(event)


class PetAnimator:
    """宠物动画管理器，支持多状态切换和定时轮换"""

    # 基础状态
    BASE_STATES = ("idle", "drag", "click", "talk")

    def __init__(self, parent_widget):
        self.label = _FlipLabel(parent_widget)
        self.label.setAlignment(Qt.AlignCenter)

        self._movie: QMovie | None = None
        self._current_state: str = "idle"

        # 状态 → GIF 文件映射（基础状态 + 扩展状态）
        self._state_files: dict[str, str] = {
            s: f"{s}.gif" for s in self.BASE_STATES
        }
        self._extra_states: dict[str, str] = {}  # "happy": "happy.gif"

        # ── 一次性播放（click / 轮换） ──────────────────
        self._idle_on_finish = False
        self._once_finished_handler = None

        # ── 定时轮换 ──────────────────────────────────
        self._rotate_timer = QTimer(parent_widget)
        self._rotate_timer.timeout.connect(self._on_rotate_tick)
        self._rotation_enabled = False
        self._rotation_interval = 30000   # ms
        self._rotation_pool: list[str] = []  # 参与轮换的扩展状态名

    # ── 配置接口 ──────────────────────────────────────

    def configure_states(self, state_files: dict[str, str]):
        """配置基础状态的 GIF 文件名"""
        for s in self.BASE_STATES:
            if s in state_files:
                self._state_files[s] = state_files[s]
        self._reload_current()

    def set_state_file(self, state: str, filename: str):
        """设置单个状态的 GIF 文件（基础 or 扩展）"""
        if state in self._state_files:
            self._state_files[state] = filename
        elif state in self._extra_states:
            self._extra_states[state] = filename
        else:
            self._extra_states[state] = filename
        if state == self._current_state:
            self._reload_current()

    def get_state_file(self, state: str) -> str:
        """获取指定状态对应的 GIF 文件名"""
        return (self._state_files.get(state)
                or self._extra_states.get(state)
                or f"{state}.gif")

    def configure_extra_states(self, extra: dict[str, str],
                               rotation_enabled: bool = True,
                               rotation_interval: int = 30000,
                               rotation_pool: list[str] | None = None):
        """配置扩展状态及轮换参数"""
        self._extra_states = dict(extra)
        self._rotation_enabled = rotation_enabled
        self._rotation_interval = rotation_interval
        self._rotation_pool = list(rotation_pool or [])
        self._update_rotation_timer()

    # ── 状态切换 ──────────────────────────────────────

    def switch_to(self, state: str) -> bool:
        """切换到指定状态（循环播放），成功返回 True"""
        file = self._resolve_file(state)
        if file is None:
            return False
        if state == self._current_state and self._movie is not None:
            return True

        self._idle_on_finish = False
        self._current_state = state
        self._load_and_play(file, play_once=False)
        self._update_rotation_timer()
        return True

    def switch_to_once(self, state: str) -> bool:
        """切换到指定状态，播放一次后自动回到 idle"""
        file = self._resolve_file(state)
        if file is None:
            return False

        self._idle_on_finish = True
        self._current_state = state
        self._load_and_play(file, play_once=True)
        self._rotate_timer.stop()  # 轮换期间暂停轮换定时器
        return True

    @property
    def current_state(self) -> str:
        return self._current_state

    # ── 内部方法 ──────────────────────────────────────

    def _resolve_file(self, state: str) -> str | None:
        """解析状态对应的 GIF 路径，文件不存在时返回 None"""
        name = (self._state_files.get(state)
                or self._extra_states.get(state)
                or f"{state}.gif")
        path = name if os.path.isabs(name) else anim_path(name)
        if os.path.isfile(path):
            return path
        # 文件不存在 → 尝试 idle 降级
        idle_name = self._state_files.get("idle", "idle.gif")
        idle_path = idle_name if os.path.isabs(idle_name) else anim_path(idle_name)
        return idle_path if os.path.isfile(idle_path) else None

    def _load_and_play(self, path: str, play_once: bool = False):
        """加载并播放 GIF，play_once=True 时播完一帧循环后回到 idle"""
        # 断开之前的信号连接
        self._disconnect_once_handlers()

        self._movie = QMovie(path)
        self.label.setMovie(self._movie)

        if play_once:
            # 通过帧编号回绕检测一次循环完成
            self._movie.frameChanged.connect(self._on_frame_changed_once)
            self._prev_frame = -1
            # 兜底定时器：防止某些 GIF 不触发回绕
            if not hasattr(self, '_once_timer') or self._once_timer is None:
                from PyQt5.QtCore import QTimer
                self._once_timer = QTimer(self.label)
                self._once_timer.setSingleShot(True)
                self._once_timer.timeout.connect(self._on_once_timeout)
            self._once_timer.start(3000)  # 3 秒兜底

        self._movie.start()

    def _disconnect_once_handlers(self):
        """断开一次性播放相关的信号和定时器"""
        if self._movie:
            try:
                self._movie.frameChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            try:
                self._movie.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
        if hasattr(self, '_once_timer') and self._once_timer:
            self._once_timer.stop()

    def _on_frame_changed_once(self, frame: int):
        """检测帧回绕 → 一次循环完成"""
        if self._prev_frame >= 0 and frame <= self._prev_frame and frame == 0:
            # 帧编号从高回绕到 0 → 完成一次循环
            self._movie.stop()
            self._on_once_finished()
        self._prev_frame = frame

    def _on_once_timeout(self):
        """兜底：超时后强制回到 idle"""
        self._on_once_finished()

    def _on_once_finished(self):
        """一次性播放结束 → 回到 idle"""
        self._idle_on_finish = False
        self._disconnect_once_handlers()
        self.switch_to("idle")

    def _reload_current(self):
        """重新加载当前状态的动画"""
        if self._current_state:
            file = self._resolve_file(self._current_state)
            if file:
                self._load_and_play(file, play_once=self._idle_on_finish)

    # ── 定时轮换 ──────────────────────────────────────

    def _on_rotate_tick(self):
        """轮换定时器触发：从轮换池中随机选一个状态播一次"""
        if not self._rotation_enabled or not self._rotation_pool:
            return
        if self._current_state != "idle":
            return  # 非 idle 状态不干扰
        state = random.choice(self._rotation_pool)
        self.switch_to_once(state)

    def _update_rotation_timer(self):
        """根据当前状态更新轮换定时器"""
        self._rotate_timer.stop()
        if (self._rotation_enabled and self._rotation_pool
                and self._current_state == "idle"):
            self._rotate_timer.start(self._rotation_interval)

    # ── 翻转控制 ──────────────────────────────────────

    def set_flip(self, horizontal: bool = False, vertical: bool = False):
        """设置动画翻转方向（用于拖拽时根据方向镜像）"""
        self.label.set_flip(horizontal, vertical)

    # ── 播放控制 ──────────────────────────────────────

    def start(self):
        if self._movie:
            self._movie.start()

    def stop(self):
        if self._movie:
            self._movie.stop()

    def set_size(self, width: int, height: int):
        self.label.setFixedSize(width, height)

    def resize(self, width: int, height: int):
        self.set_size(width, height)

    @property
    def movie(self) -> QMovie | None:
        return self._movie
