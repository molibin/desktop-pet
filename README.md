# 桌面宠物 🐾

一个基于 PyQt5 的桌面宠物应用，支持透明窗口、拖拽移动、滚轮缩放、系统托盘和 AI 对话功能。

## 项目结构

```
pet_project/
├── main.py                 # 程序入口
├── src/                    # 源代码包
│   ├── __init__.py
│   ├── pet.py              # 桌面宠物主窗口类
│   ├── animator.py         # 动画管理类
│   ├── ai_chat.py          # AI 对话模块
│   ├── settings.py         # 用户配置管理
│   ├── tray_menu.py        # 系统托盘菜单
│   └── utils.py            # 工具函数
├── resources/
│   ├── animations/         # 宠物动画素材
│   ├── icons/              # 图标文件
│   └── config/             # 配置文件
├── logs/                   # 日志文件夹
├── requirements.txt        # 依赖列表
└── README.md               # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行

```bash
python main.py
```

## 功能

- ✨ 透明无边框窗口，始终置顶
- 🖱️ 鼠标拖拽移动
- 🔍 滚轮缩放（或托盘菜单缩放）
- 🎬 GIF 动画播放
- 🗂️ 系统托盘（右键菜单）
- 🗑️ 拖拽文件到宠物身上 → 吃掉（移到回收站）
- 🤖 AI 对话（需配置 API Key）
- ⚙️ 配置持久化（窗口位置、大小等）

## 配置

配置文件位于 `resources/config/config.json`，也可在应用中通过设置界面修改。

## 打包成 exe

使用 PyInstaller 打包为单个可执行文件：

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 打包（在项目根目录下执行）
pyinstaller --windowed --onefile `
    --name "桌面宠物" `
    --icon resources/icons/tray.png `
    --add-data "resources;resources" `
    main.py
```

打包完成后，exe 文件位于 `dist/桌面宠物.exe`，可直接运行。

## 许可证

MIT
