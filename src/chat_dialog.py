"""
AI 聊天对话框 —— 与桌面宠物对话
"""

import json
import os
import re
import shlex

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ai_chat import AIChat
from .commands import execute as exec_cmd, list_commands as list_cmds
from .utils import logs_dir


# ── 气泡样式 ──────────────────────────────────────────

_BUBBLE_USER = """
    QLabel {
        background-color: #95EC69;
        border-radius: 12px;
        padding: 10px 14px;
        color: #1a1a1a;
        font-size: 14px;
    }
"""
_BUBBLE_AI = """
    QLabel {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 10px 14px;
        color: #1a1a1a;
        font-size: 14px;
    }
"""
_BUBBLE_ERROR = """
    QLabel {
        background-color: #FFE0E0;
        border-radius: 12px;
        padding: 10px 14px;
        color: #CC3333;
        font-size: 14px;
    }
"""

# 气泡内的文本部件样式（用 QTextEdit 替代 QLabel，文字显示更可靠）
_TEXT_EDITOR_STYLE = """
    QTextEdit {
        background: transparent;
        border: none;
        color: #1a1a1a;
        font-size: 14px;
        padding: 0;
    }
"""


def _fix_editor_height(editor: QTextEdit):
    """根据 QTextEdit 实际渲染宽度矫正高度"""
    doc = editor.document()
    available_w = editor.viewport().width() - 4
    if available_w > 50:
        doc.setTextWidth(available_w)
    h = int(doc.size().height()) + 14
    editor.setFixedHeight(max(h, 28))


class _BubbleWidget(QWidget):
    """单个聊天气泡"""

    def __init__(self, text: str, is_user: bool,
                 is_error: bool = False, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

        # 外层：控制靠左/靠右
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 3, 12, 3)

        # 气泡容器（带背景的 QFrame）
        frame = QFrame()
        frame.setObjectName("bubbleFrame")
        if is_error:
            frame.setStyleSheet(
                "#bubbleFrame { background: #FFE0E0; border-radius: 12px; }"
            )
        elif is_user:
            frame.setStyleSheet(
                "#bubbleFrame { background: #95EC69; border-radius: 12px; }"
            )
        else:
            frame.setStyleSheet(
                "#bubbleFrame { background: #FFFFFF;"
                " border: 1px solid #E0E0E0; border-radius: 12px; }"
            )

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(14, 10, 14, 10)

        # 用 QTextEdit 代替 QLabel，文字显示更可靠
        editor = QTextEdit()
        editor.setPlainText(text)
        editor.setReadOnly(True)
        editor.setStyleSheet(_TEXT_EDITOR_STYLE)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        editor.setMinimumWidth(100)
        editor.setMaximumWidth(480)
        editor.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # ── 用 QTextDocument 精确计算文字高度 ─────────
        from PyQt5.QtGui import QFont, QTextDocument

        doc = QTextDocument()
        doc.setDefaultFont(editor.font())
        doc.setPlainText(text)
        doc.setDocumentMargin(0)
        # 按实际可用宽度计算（最大宽度减去 QFrame 内边距）
        doc.setTextWidth(480 - 28)

        # 高度 = 文档内容高度 + 上下 padding
        editor_height = int(doc.size().height()) + 14
        editor.setFixedHeight(max(editor_height, 28))

        # 显示后再次矫正高度（确保布局后宽度准确）
        editor._adjust_timer = QTimer(editor)
        editor._adjust_timer.setSingleShot(True)
        editor._adjust_timer.timeout.connect(
            lambda e=editor: _fix_editor_height(e))
        editor._adjust_timer.start(50)

        frame_layout.addWidget(editor)

        if is_user:
            outer.addStretch()
            outer.addWidget(frame)
        else:
            outer.addWidget(frame)
            outer.addStretch()


class ChatDialog(QDialog):
    """AI 对话窗口"""

    _HISTORY_FILE = "chat_history.json"

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.pet_parent = parent
        self.settings = settings

        # AI 聊天客户端（含本地命令能力）
        self._ai = AIChat(
            api_key=settings.ai_api_key,
            api_url=settings.get("ai_api_url", ""),
            model=settings.get("ai_model", "gpt-3.5-turbo"),
        )
        self._ai.set_system_prompt(list_cmds())

        self.setWindowTitle("和宠物聊天")
        self.setMinimumSize(520, 520)
        self.resize(560, 560)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._setup_ui()

        # 加载历史记录
        history = self._load_history()
        if history:
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    self._add_bubble(content, is_user=True)
                else:
                    self._add_bubble(content)
            # 恢复 AI 上下文
            self._ai._messages = list(history)
        else:
            self._add_bubble("你好呀！我是你的桌面宠物 🐾 想聊点什么呢？")
            # 将问候语保存到历史中，后续对话有完整上下文
            self._ai.add_message("assistant", "你好呀！我是你的桌面宠物 🐾 想聊点什么呢？")
            self._save_history()

    # ── 界面构建 ──────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        # ── 消息滚动区 ────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #E8E8E8; }")
        scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                width: 6px; background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0; border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: #E8E8E8;")
        self._msg_layout = QVBoxLayout(self._container)
        self._msg_layout.setContentsMargins(0, 8, 0, 8)
        self._msg_layout.setSpacing(4)
        self._msg_layout.addStretch()  # 顶部弹簧，让消息从底部开始

        scroll.setWidget(self._container)
        layout.addWidget(scroll, stretch=1)
        self._scroll_area = scroll

        # ── 输入区域 ──────────────────────────────────
        input_bg = QWidget()
        input_bg.setStyleSheet("background: #F0F0F0;")
        input_row = QHBoxLayout(input_bg)
        input_row.setContentsMargins(10, 8, 10, 8)
        input_row.setSpacing(8)

        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("输入消息...")
        self._input_edit.setFixedHeight(56)
        self._input_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D0D0D0;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 14px;
                background: white;
            }
        """)
        self._input_edit.installEventFilter(self)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(68, 56)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #4A90D9;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background: #357ABD; }
            QPushButton:disabled { background: #B0B0B0; }
        """)
        self._send_btn.clicked.connect(self._send_message)

        input_row.addWidget(self._input_edit)
        input_row.addWidget(self._send_btn)
        layout.addWidget(input_bg)

    # ── 聊天记录持久化 ────────────────────────────────

    @classmethod
    def _history_path(cls) -> str:
        """聊天记录文件路径"""
        return os.path.join(logs_dir(), cls._HISTORY_FILE)

    def _save_history(self):
        """保存聊天记录到 JSON 文件"""
        try:
            path = self._history_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._ai._messages, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[保存聊天记录失败] {e}")

    def _load_history(self) -> list[dict]:
        """从 JSON 文件加载聊天记录"""
        path = self._history_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    # ── 消息管理 ──────────────────────────────────────

    def _add_bubble(self, text: str, is_user=False, is_error=False):
        """添加一条聊天气泡"""
        bubble = _BubbleWidget(text, is_user, is_error)
        # 插入到 stretch 之前
        self._msg_layout.insertWidget(
            self._msg_layout.count() - 1, bubble
        )

        # 自动滚到底部
        vsb = self._scroll_area.verticalScrollBar()
        QTimer.singleShot(30, lambda: vsb.setValue(vsb.maximum()))

    def _set_input_enabled(self, enabled: bool):
        self._send_btn.setEnabled(enabled)
        self._input_edit.setEnabled(enabled)
        if enabled:
            self._input_edit.setFocus()

    def _send_message(self):
        text = self._input_edit.toPlainText().strip()
        if not text:
            return

        self._input_edit.clear()
        self._add_bubble(text, is_user=True)

        # 立即保存用户消息到记录（确保即使 AI 失败也不会丢）
        self._ai.add_message("user", text)
        self._save_history()

        self._set_input_enabled(False)

        if self.pet_parent:
            self.pet_parent.set_animation_state("talk")

        QTimer.singleShot(0, lambda: self._do_chat(text))

    def _do_chat(self, text: str):
        reply = self._ai.chat(text)
        if not reply:
            reply = "（没有收到回复）"

        # 解析并执行 AI 回复中的命令
        result_text = self._process_commands(reply)

        # 显示 AI 的原始回复
        is_error = "错误" in reply or "失败" in reply
        self._add_bubble(reply, is_error=is_error)

        # 如果有命令执行结果，额外显示
        if result_text:
            self._add_bubble(f"⚡ {result_text}", is_user=False)
            # 把执行结果也喂给 AI，让它能基于结果继续对话
            self._ai.add_message("user",
                                 f"命令执行结果：{result_text}\n请根据这个结果继续回答用户。")
            follow_up = self._ai.chat("")
            if follow_up:
                self._add_bubble(follow_up, is_user=False)

        self._save_history()
        self._set_input_enabled(True)

        if self.pet_parent:
            self.pet_parent.set_animation_state("idle")

    def _process_commands(self, text: str) -> str:
        """解析并执行文本中的 [cmd:xxx] 命令，返回执行结果汇总"""
        results = []
        pattern = r'\[cmd:\s*(\w+)\](.*?)\[/cmd\]'
        for match in re.finditer(pattern, text, re.DOTALL):
            cmd_name = match.group(1).strip()
            args_str = match.group(2).strip()
            args = shlex.split(args_str) if args_str else []
            result = exec_cmd(cmd_name, args)
            results.append(f"{cmd_name}: {result}")
        return "\n".join(results)

    # ── 事件 ──────────────────────────────────────────

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent

        if obj == self._input_edit and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if not event.modifiers() & Qt.ShiftModifier:
                    self._send_message()
                    return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        """窗口显示后自动滚动到底部"""
        super().showEvent(event)
        # 等布局完成后滚动（0 延时 = 排队到事件队列末尾）
        QTimer.singleShot(0, self._scroll_to_bottom)
        # 二次保险：窗口可能还没完成首次渲染
        QTimer.singleShot(200, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """滚动消息区域到底部"""
        vsb = self._scroll_area.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def closeEvent(self, event):
        if self.pet_parent:
            self.pet_parent.set_animation_state("idle")
        super().closeEvent(event)
