"""
动画设置对话框 —— 为各动画状态配置 GIF 文件，管理扩展状态和轮换
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from .utils import anim_path, animations_dir


class AnimationSettingsDialog(QDialog):
    """动画设置对话框"""

    def __init__(self, parent, settings, animator):
        super().__init__(parent)
        self.pet_parent = parent
        self.settings = settings
        self.animator = animator
        self.setWindowTitle("动画设置")
        self.setMinimumWidth(520)

        self._setup_ui()
        self._load_settings()

    # ── 界面构建 ──────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── 基础状态 GIF 配置 ──────────────────────────
        base_group = QGroupBox("基础动画状态")
        base_form = QFormLayout(base_group)

        self._base_paths: dict[str, QLineEdit] = {}
        for state, label in [
            ("idle", "待机 (idle)"),
            ("drag", "拖拽 (drag)"),
            ("click", "点击 (click)"),
            ("talk", "说话 (talk)"),
        ]:
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText("例如 idle.gif")
            browse_btn = QPushButton("浏览...")
            browse_btn.clicked.connect(lambda _, s=state, e=edit: self._browse_gif(s, e))
            row.addWidget(edit)
            row.addWidget(browse_btn)
            base_form.addRow(label, row)
            self._base_paths[state] = edit

        layout.addWidget(base_group)

        # ── 扩展状态 ──────────────────────────────────
        extra_group = QGroupBox("扩展状态（参与定时轮换）")
        extra_layout = QVBoxLayout(extra_group)

        # 扩展状态列表
        self._extra_list = QListWidget()
        self._extra_list.setAlternatingRowColors(True)
        extra_layout.addWidget(QLabel("已添加的扩展状态："))
        extra_layout.addWidget(self._extra_list)

        # 添加扩展状态的行
        add_row = QHBoxLayout()
        self._extra_name_edit = QLineEdit()
        self._extra_name_edit.setPlaceholderText("状态名称（如 happy）")
        self._extra_file_edit = QLineEdit()
        self._extra_file_edit.setPlaceholderText("GIF 文件名或路径")
        add_browse_btn = QPushButton("浏览...")
        add_browse_btn.clicked.connect(lambda: self._browse_extra_gif())
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_extra_state)

        add_row.addWidget(self._extra_name_edit)
        add_row.addWidget(self._extra_file_edit)
        add_row.addWidget(add_browse_btn)
        add_row.addWidget(add_btn)
        extra_layout.addLayout(add_row)

        # 删除按钮
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self._remove_extra_state)
        extra_layout.addWidget(del_btn)

        layout.addWidget(extra_group)

        # ── 定时轮换配置 ──────────────────────────────
        rotate_group = QGroupBox("定时轮换")
        rotate_form = QFormLayout(rotate_group)

        self._rotation_enabled_cb = QCheckBox("启用定时轮换")
        rotate_form.addRow(self._rotation_enabled_cb)

        self._rotation_interval_spin = QSpinBox()
        self._rotation_interval_spin.setRange(5, 3600)
        self._rotation_interval_spin.setSuffix(" 秒")
        self._rotation_interval_spin.setValue(30)
        rotate_form.addRow("轮换间隔", self._rotation_interval_spin)

        layout.addWidget(rotate_group)

        # ── 按钮 ──────────────────────────────────────
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self._apply)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # ── 加载配置 ──────────────────────────────────────

    def _load_settings(self):
        """从 settings 加载当前值到界面"""
        # 基础状态
        self._base_paths["idle"].setText(self.settings.anim_idle)
        self._base_paths["drag"].setText(self.settings.anim_drag)
        self._base_paths["click"].setText(self.settings.anim_click)
        self._base_paths["talk"].setText(self.settings.anim_talk)

        # 扩展状态
        self._extra_list.clear()
        for state, gif in self.settings.anim_extra.items():
            item = QListWidgetItem(f"{state}  →  {gif}")
            item.setData(Qt.UserRole, {"state": state, "gif": gif})
            self._extra_list.addItem(item)

        # 轮换
        self._rotation_enabled_cb.setChecked(self.settings.rotation_enabled)
        self._rotation_interval_spin.setValue(self.settings.rotation_interval // 1000)

    # ── 浏览 GIF 文件 ─────────────────────────────────

    def _browse_gif(self, state: str, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择 {state} 动画文件",
            animations_dir(),
            "GIF 文件 (*.gif);;所有文件 (*.*)",
        )
        if path:
            # 尝试转为相对路径
            rel = self._to_relative(path)
            edit.setText(rel)

    def _browse_extra_gif(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择扩展状态动画文件",
            animations_dir(),
            "GIF 文件 (*.gif);;所有文件 (*.*)",
        )
        if path:
            rel = self._to_relative(path)
            self._extra_file_edit.setText(rel)

    @staticmethod
    def _to_relative(path: str) -> str:
        """将绝对路径转为相对于 animations 目录的路径"""
        anim_dir = animations_dir()
        try:
            rel = os.path.relpath(path, anim_dir)
            # 如果在 animations 目录下，就用相对路径
            if not rel.startswith(".."):
                return rel
        except ValueError:
            pass
        return path

    # ── 扩展状态管理 ──────────────────────────────────

    def _add_extra_state(self):
        name = self._extra_name_edit.text().strip()
        gif = self._extra_file_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入扩展状态名称")
            return
        if not gif:
            QMessageBox.warning(self, "提示", "请选择 GIF 文件")
            return

        # 检查是否已存在
        for i in range(self._extra_list.count()):
            data = self._extra_list.item(i).data(Qt.UserRole)
            if data and data["state"] == name:
                QMessageBox.warning(self, "提示", f"状态 '{name}' 已存在")
                return

        item = QListWidgetItem(f"{name}  →  {gif}")
        item.setData(Qt.UserRole, {"state": name, "gif": gif})
        self._extra_list.addItem(item)
        self._extra_name_edit.clear()
        self._extra_file_edit.clear()

    def _remove_extra_state(self):
        row = self._extra_list.currentRow()
        if row >= 0:
            self._extra_list.takeItem(row)

    # ── 保存 / 应用 ──────────────────────────────────

    def _collect_values(self) -> dict:
        """收集界面上的所有值"""
        # 基础状态
        base = {}
        for state, edit in self._base_paths.items():
            val = edit.text().strip()
            if val:
                base[state] = val

        # 扩展状态
        extra = {}
        for i in range(self._extra_list.count()):
            data = self._extra_list.item(i).data(Qt.UserRole)
            if data:
                extra[data["state"]] = data["gif"]

        # 轮换
        enabled = self._rotation_enabled_cb.isChecked()
        interval = self._rotation_interval_spin.value() * 1000

        return {
            "base": base,
            "extra": extra,
            "rotation_enabled": enabled,
            "rotation_interval": interval,
        }

    def _apply_values(self, values: dict):
        """将配置值应用到 settings 和 animator"""
        base = values["base"]

        # 保存到 settings
        if "idle" in base:
            self.settings.anim_idle = base["idle"]
        if "drag" in base:
            self.settings.anim_drag = base["drag"]
        if "click" in base:
            self.settings.anim_click = base["click"]
        if "talk" in base:
            self.settings.anim_talk = base["talk"]

        self.settings.anim_extra = values["extra"]
        self.settings.rotation_enabled = values["rotation_enabled"]
        self.settings.rotation_interval = values["rotation_interval"]
        self.settings.save()

        # 应用到 animator
        self.animator.configure_states(base)
        self.animator.configure_extra_states(
            extra=values["extra"],
            rotation_enabled=values["rotation_enabled"],
            rotation_interval=values["rotation_interval"],
            rotation_pool=list(values["extra"].keys()),
        )

        # 刷新托盘子菜单
        if hasattr(self.pet_parent, "tray"):
            self.pet_parent.tray.update_anim_menu()

    def _apply(self):
        values = self._collect_values()
        self._apply_values(values)

    def _save(self):
        self._apply()
        self.accept()
