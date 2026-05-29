"""
程序入口 —— 启动桌面宠物应用
"""

import sys
from PyQt5.QtWidgets import QApplication
from src.pet import DesktopPet


def main():
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()