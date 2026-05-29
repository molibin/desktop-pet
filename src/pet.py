"""
桌面宠物主窗口类（继承 QWidget）
"""

import os

from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QApplication, QLabel

# type: ignore
from .animator import PetAnimator # type: ignore
from .tray_menu import TrayMenu
from .settings import Settings
from .utils import icon_path


class DesktopPet(QWidget):
    """桌面宠物主窗口——透明、无边框、可拖拽、可缩放"""

    def __init__(self):
        super().__init__()
        self.settings = Settings()

        # 窗口设置
        flags = Qt.FramelessWindowHint
        if self.settings.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("桌面宠物")

        # 动画管理器
        self.animator = PetAnimator(self)
        self.animator.set_size(self.settings.pet_width, self.settings.pet_height)
        self.setFixedSize(self.settings.pet_width, self.settings.pet_height)

        # 配置各状态动画文件
        self.animator.configure_states({
            "idle": self.settings.anim_idle,
            "drag": self.settings.anim_drag,
            "click": self.settings.anim_click,
            "talk": self.settings.anim_talk,
        })
        # 配置扩展状态和轮换
        self.animator.configure_extra_states(
            extra=self.settings.anim_extra,
            rotation_enabled=self.settings.rotation_enabled,
            rotation_interval=self.settings.rotation_interval,
            rotation_pool=self.settings.rotation_pool,
        )
        # 启动 idle 动画
        self.animator.switch_to("idle")
        self.animator.start()

        # 拖拽相关
        self.drag_position: QPoint | None = None
        self._press_pos: QPoint | None = None    # 按下时鼠标位置（用于区分点击/拖拽）
        self._was_dragged: bool = False

        # 恢复上次窗口位置
        wx = self.settings.get("window_x")
        wy = self.settings.get("window_y")
        if wx is not None and wy is not None:
            self.move(wx, wy)

        # 托盘菜单
        self.tray = TrayMenu(self, icon_path("tray.png"), "桌面宠物")

        # ── 吃文件功能 ──────────────────────────────────
        self.setAcceptDrops(True)

        # 让动画标签也响应拖拽（它覆盖了整个宠物窗口）
        self.animator.label.setAcceptDrops(True)
        self.animator.label.installEventFilter(self)

        # 吃文件的提示标签
        self._eat_label = QLabel(self)
        self._eat_label.setAlignment(Qt.AlignCenter)
        self._eat_label.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 28px;
                font-weight: bold;
                background: rgba(255, 255, 255, 180);
                border-radius: 12px;
                padding: 6px 14px;
            }
        """)
        self._eat_label.hide()

        # 抖动动画定时器
        self._shake_timer = QTimer(self)
        self._shake_timer.setSingleShot(True)
        self._shake_timer.timeout.connect(self._stop_shake)
        self._shake_offset = 0
        self._shake_count = 0

        # 记录当前吃了多少文件
        self._eaten_count = 0

    # ── 事件过滤器（转发标签拖拽事件） ────────────────

    def eventFilter(self, obj, event):
        """将动画标签上的拖拽事件转发给窗口处理"""
        if obj == self.animator.label:
            etype = event.type()
            if etype == QEvent.DragEnter:
                self.dragEnterEvent(event)
                return True
            elif etype == QEvent.DragMove:
                self.dragMoveEvent(event)
                return True
            elif etype == QEvent.DragLeave:
                self.dragLeaveEvent(event)
                return True
            elif etype == QEvent.Drop:
                self.dropEvent(event)
                return True
        return super().eventFilter(obj, event)

    # ── 吃文件（拖拽） ─────────────────────────────────

    def dragEnterEvent(self, event):
        """鼠标拖入文件时接受"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._on_drag_hover(True)

    def dragMoveEvent(self, event):
        """拖拽过程中持续接受"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """拖拽离开时恢复外观"""
        self._on_drag_hover(False)

    def dropEvent(self, event):
        """文件被丢到宠物身上 → 吃掉！"""
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                files.append(path)

        if files:
            self._eat_files(files)

        self._on_drag_hover(False)
        event.acceptProposedAction()

    def _on_drag_hover(self, hovering: bool):
        """拖拽悬停时的视觉反馈"""
        if hovering:
            self.setWindowOpacity(0.85)
        else:
            self.setWindowOpacity(1.0)

    def _eat_files(self, file_paths: list[str]):
        """吃掉文件——移到回收站"""
        import send2trash
        import traceback

        eaten = []
        failed = []

        for path in file_paths:
            # 标准化路径：正斜杠 → 反斜杠，避免 Windows API 报错
            norm_path = os.path.normpath(path)
            if os.path.isfile(norm_path) or os.path.isdir(norm_path):
                try:
                    send2trash.send2trash(norm_path)
                    eaten.append(norm_path)
                except Exception as e:
                    failed.append((path, str(e)))
                    print(f"[吃文件失败] {path}: {e}")
                    traceback.print_exc()

        # 更新计数
        self._eaten_count += len(eaten)

        # 显示吃掉的反馈
        if eaten:
            names = [os.path.basename(p) for p in eaten[:3]]
            summary = "、".join(names)
            if len(eaten) > 3:
                summary += f" 等 {len(eaten)} 个文件"
            text = f"嗷呜~ 🍽️\n{summary}"
            if failed:
                text += f"\n({len(failed)} 个失败)"
        elif failed:
            text = f"😵 咬不动!\n{failed[0][1][:40]}"
        else:
            text = "🤔 这不是文件哦"

        self._show_eat_effect(text)

        # 抖动效果
        self._start_shake()

    def _show_eat_effect(self, text: str):
        """显示吃掉的文字反馈（2 秒后自动消失）"""
        self._eat_label.setText(text)
        self._eat_label.adjustSize()

        # 居中显示
        x = (self.width() - self._eat_label.width()) // 2
        y = -self._eat_label.height() - 10
        self._eat_label.move(x, y)
        self._eat_label.show()

        QTimer.singleShot(2000, self._eat_label.hide)

    def _start_shake(self):
        """抖动效果：左右快速晃动"""
        self._shake_count = 6
        self._shake_offset = 4
        self._do_shake()

    def _do_shake(self):
        if self._shake_count <= 0:
            return
        direction = 1 if self._shake_count % 2 == 0 else -1
        self.move(self.x() + direction * self._shake_offset, self.y())
        self._shake_count -= 1
        QTimer.singleShot(30, self._do_shake)

    def _stop_shake(self):
        """停止抖动（备用）"""
        self._shake_count = 0

    # ── 缩放 ──────────────────────────────────────────────

    def enlarge(self):
        """放大宠物"""
        new_w = self.width() + 10
        new_h = self.height() + 10
        self._resize_pet(new_w, new_h)

    def shrink(self):
        """缩小宠物，最小 50x50"""
        new_w = max(50, self.width() - 10)
        new_h = max(50, self.height() - 10)
        self._resize_pet(new_w, new_h)

    def _resize_pet(self, new_w: int, new_h: int):
        """调整宠物大小，并保持窗口中心位置不变"""
        old_center = self.geometry().center()
        self.animator.set_size(new_w, new_h)
        self.setFixedSize(new_w, new_h)
        self.move(old_center.x() - self.width() // 2,
                  old_center.y() - self.height() // 2)
        # 更新设置
        self.settings.pet_width = new_w
        self.settings.pet_height = new_h

    def wheelEvent(self, event):
        """鼠标滚轮触发缩放"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.enlarge()
        else:
            self.shrink()

    # ── 拖拽 & 点击 ──────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self._press_pos = event.globalPos()
            self._was_dragged = False
            # 切换到拖拽动画
            self.animator.switch_to("drag")
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            self._was_dragged = True
            # 根据水平移动方向翻转 GIF：往左正常，往右镜像
            if self._press_pos is not None:
                dx = event.globalPos().x() - self._press_pos.x()
                self.animator.set_flip(horizontal=(dx > 0))
            event.accept()

    def mouseReleaseEvent(self, event):
        """松开鼠标时记录窗口位置，并判断是点击还是拖拽"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            self.settings.set("window_x", self.x())
            self.settings.set("window_y", self.y())

            # 重置翻转
            self.animator.set_flip(horizontal=False, vertical=False)

            if self._was_dragged:
                # 拖拽结束 → 回到 idle
                self.animator.switch_to("idle")
            else:
                # 点击 → 播放 click 动画一次
                self.animator.switch_to_once("click")

            self._press_pos = None
            event.accept()

    # ── 双击打开聊天 ─────────────────────────────────────

    def mouseDoubleClickEvent(self, event):
        """双击宠物打开聊天对话框"""
        if event.button() == Qt.LeftButton:
            from .chat_dialog import ChatDialog
            self._chat_dlg = ChatDialog(self, self.settings)
            self._chat_dlg.show()

    # ── 外部接口 ──────────────────────────────────────────

    def set_animation_state(self, state: str):
        """供外部（如 AI 模块）切换宠物动画状态"""
        if state in ("idle", "drag", "click", "talk"):
            if state == "click":
                self.animator.switch_to_once("click")
            else:
                self.animator.switch_to(state)
        else:
            # 尝试作为扩展状态（一次性播放）
            self.animator.switch_to_once(state)

    # ── 设置 ──────────────────────────────────────────────

    def open_settings(self):
        """打开动画设置对话框"""
        from .animation_settings import AnimationSettingsDialog
        dlg = AnimationSettingsDialog(self, self.settings, self.animator)
        dlg.exec_()

    # ── 退出 ──────────────────────────────────────────────

    def quit_app(self):
        """退出应用"""
        self.tray.hide()
        QApplication.quit()
