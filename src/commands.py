"""
本地命令执行模块 —— 供 AI 调用打开程序、操作文件等
"""

import os
import subprocess
import shlex
from typing import Callable


# ── 命令注册表 ──────────────────────────────────────

_commands: dict[str, tuple[str, Callable[[list[str]], str]]] = {}


def _reg(name: str, desc: str, fn: Callable[[list[str]], str]):
    _commands[name] = (desc, fn)


def list_commands() -> str:
    """返回所有可用命令的描述（给 AI 系统提示词用）"""
    lines = []
    for name, (desc, _) in _commands.items():
        lines.append(f"  - {name}：{desc}")
    return "\n".join(lines)


def execute(cmd_name: str, args: list[str]) -> str:
    """执行命令，返回执行结果文本"""
    entry = _commands.get(cmd_name)
    if entry is None:
        return f"未知命令：{cmd_name}"
    _, fn = entry
    try:
        return fn(args)
    except Exception as e:
        return f"执行失败：{e}"


# ── 命令实现 ─────────────────────────────────────────

def _open_app(args: list[str]) -> str:
    """打开系统应用"""
    apps = {
        "计算器": "calc.exe",
        "calc": "calc.exe",
        "记事本": "notepad.exe",
        "notepad": "notepad.exe",
        "画图": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "cmd": "cmd.exe",
        "命令提示符": "cmd.exe",
        "powershell": "powershell.exe",
    }
    target = args[0].lower() if args else ""
    app_path = apps.get(target, target)
    try:
        subprocess.Popen(app_path, shell=True)
        return f"已打开 {target or app_path}"
    except Exception as e:
        return f"打开失败：{e}"


def _create_file(args: list[str]) -> str:
    """创建文件"""
    if not args:
        return "请指定文件名"
    filepath = args[0]
    content = " ".join(args[1:]) if len(args) > 1 else ""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已创建文件：{os.path.abspath(filepath)}"
    except Exception as e:
        return f"创建文件失败：{e}"


def _read_file(args: list[str]) -> str:
    """读取文件内容"""
    if not args:
        return "请指定文件名"
    try:
        with open(args[0], "r", encoding="utf-8") as f:
            content = f.read()
        return f"文件 {args[0]} 的内容：\n{content[:2000]}"
    except Exception as e:
        return f"读取文件失败：{e}"


def _notify(args: list[str]) -> str:
    """显示系统通知"""
    if not args:
        return "请指定通知内容"
    msg = " ".join(args)
    try:
        # Windows 通知
        subprocess.Popen(
            ["powershell", "-Command",
             f'New-BurntToastNotification -Text "{msg}"'],
            shell=True
        )
        return f"已发送通知：{msg}"
    except Exception:
        # 降级：使用 msg 命令
        try:
            subprocess.Popen(["msg", "*", msg], shell=True)
        except Exception:
            pass
        return f"通知内容：{msg}"


def _open_url(args: list[str]) -> str:
    """打开 URL"""
    if not args:
        return "请指定 URL"
    url = args[0]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        os.startfile(url)
        return f"已打开：{url}"
    except Exception as e:
        return f"打开链接失败：{e}"


def _explore(args: list[str]) -> str:
    """打开文件夹"""
    path = args[0] if args else "."
    try:
        os.startfile(os.path.abspath(path))
        return f"已打开文件夹：{os.path.abspath(path)}"
    except Exception as e:
        return f"打开文件夹失败：{e}"


def _run_cmd(args: list[str]) -> str:
    """执行任意 PowerShell 命令"""
    if not args:
        return "请指定要执行的命令"
    cmd = " ".join(args)
    try:
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout or result.stderr or "(无输出)"
        return f"执行结果：\n{output[:1500]}"
    except subprocess.TimeoutExpired:
        return "命令执行超时（30 秒）"
    except Exception as e:
        return f"执行失败：{e}"


# ── 注册命令 ─────────────────────────────────────────

_reg("open", "打开程序：open 计算器 / open notepad / open 画图", _open_app)
_reg("create_file", "创建文件：create_file path [内容]", _create_file)
_reg("read_file", "读取文件：read_file path", _read_file)
_reg("notify", "发送系统通知：notify 消息内容", _notify)
_reg("open_url", "打开网页：open_url URL", _open_url)
_reg("explore", "打开文件夹：explore [路径]", _explore)
_reg("run", "执行 PowerShell 命令：run 命令", _run_cmd)
