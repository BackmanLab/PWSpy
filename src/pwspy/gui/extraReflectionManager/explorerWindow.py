from PyQt5.QtWidgets import QDialog

from .manager import ERManager


class explorerWindow(QDialog):
    def __init__(self, filePath: str):
        self.manager = ERManager(filePath)