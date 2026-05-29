"""
系统托盘菜单模块 —— 退出、缩放、动画切换、设置等
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon


class TrayMenu:
    """系统托盘图标及右键菜单管理"""

    def __init__(self, parent, icon_path: str, tooltip: str = "桌面宠物"):
        self.parent = parent
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip(tooltip)
        parent.setWindowIcon(QIcon(icon_path))

        # 构建菜单
        self.menu = QMenu()
        self._state_actions: list[QAction] = []
        self._build_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def _build_menu(self):
        """构建托盘右键菜单项"""
        # ── 动画切换子菜单 ────────────────────────────────
        self.anim_menu = QMenu("动画状态", self.menu)
        self._rebuild_anim_menu()
        self.menu.addMenu(self.anim_menu)

        self.menu.addSeparator()

        # 放大
        self.enlarge_action = QAction("放大 (+)", self.parent)
        self.enlarge_action.triggered.connect(self.parent.enlarge)
        self.menu.addAction(self.enlarge_action)

        # 缩小
        self.shrink_action = QAction("缩小 (-)", self.parent)
        self.shrink_action.triggered.connect(self.parent.shrink)
        self.menu.addAction(self.shrink_action)

        self.menu.addSeparator()

        # 设置
        self.settings_action = QAction("动画设置 ...", self.parent)
        self.settings_action.triggered.connect(self.parent.open_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # 退出
        self.quit_action = QAction("退出", self.parent)
        self.quit_action.triggered.connect(self.parent.quit_app)
        self.menu.addAction(self.quit_action)

    def _rebuild_anim_menu(self):
        """重构动画子菜单（根据当前配置的扩展状态）"""
        self.anim_menu.clear()
        self._state_actions.clear()

        # 基础状态
        base_states = [
            ("idle", "待机"),
            ("drag", "拖拽"),
            ("click", "点击"),
            ("talk", "说话"),
        ]
        for state, label in base_states:
            action = QAction(f"{label} ({state})", self.parent)
            action.setCheckable(True)
            action.setData(state)
            action.triggered.connect(
                lambda checked, s=state: self.parent.set_animation_state(s)
            )
            self.anim_menu.addAction(action)
            self._state_actions.append(action)

        # 扩展状态
        extra = self.parent.settings.anim_extra
        if extra:
            self.anim_menu.addSeparator()
            for state in extra:
                action = QAction(f"{state}", self.parent)
                action.setCheckable(True)
                action.setData(state)
                action.triggered.connect(
                    lambda checked, s=state: self.parent.set_animation_state(s)
                )
                self.anim_menu.addAction(action)
                self._state_actions.append(action)

    def update_anim_menu(self):
        """刷新动画子菜单（添加了新的扩展状态后调用）"""
        self._rebuild_anim_menu()

    def hide(self):
        """隐藏托盘图标"""
        self.tray_icon.hide()

    def show_message(self, title: str, message: str):
        """显示托盘气泡通知"""
        self.tray_icon.showMessage(title, message)
