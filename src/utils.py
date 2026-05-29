"""
工具函数模块 —— 路径、资源读取等
"""

import os
import sys


def _is_frozen() -> bool:
    """判断是否处于 PyInstaller 打包后的环境"""
    return getattr(sys, "frozen", False)


def project_root() -> str:
    """返回项目根目录的绝对路径（src/ 的父目录）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle_dir() -> str:
    """PyInstaller 打包后，资源被解压到的临时目录"""
    return sys._MEIPASS if _is_frozen() else project_root()


def resource_dir() -> str:
    """返回资源文件夹的绝对路径（打包后从临时目录读取）"""
    return os.path.join(_bundle_dir(), "resources")


def animations_dir() -> str:
    """返回动画素材文件夹的绝对路径"""
    return os.path.join(resource_dir(), "animations")


def icons_dir() -> str:
    """返回图标文件夹的绝对路径"""
    return os.path.join(resource_dir(), "icons")


def config_dir() -> str:
    """返回配置文件夹的绝对路径（放在项目根目录下，可读写）"""
    return os.path.join(project_root(), "resources", "config")


def logs_dir() -> str:
    """返回日志文件夹的绝对路径（放在项目根目录下，可读写）"""
    return os.path.join(project_root(), "logs")


def resource_path(relative_path: str) -> str:
    """根据相对路径（相对于 resources/）获取完整路径"""
    return os.path.join(resource_dir(), relative_path)


def anim_path(filename: str) -> str:
    """获取 animations 目录下某个动画文件的完整路径"""
    return os.path.join(animations_dir(), filename)


def icon_path(filename: str) -> str:
    """获取 icons 目录下某个图标文件的完整路径"""
    return os.path.join(icons_dir(), filename)
