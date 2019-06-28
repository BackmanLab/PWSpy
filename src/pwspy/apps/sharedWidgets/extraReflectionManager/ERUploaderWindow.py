from PyQt5.QtWidgets import QDialog


class ERUploaderWindow(QDialog):
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Extra Reflectance Selector")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setRowCount(0)
        self.table.setColumnCount(3)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalHeaderLabels([" ", "System", "Date"])
        self.table.setColumnWidth(0, 10)

        self.downloadButton = QPushButton("Download Checked Items")
        self.downloadButton.released.connect(self._downloadCheckedItems)
        self.updateButton = QPushButton('Update Index')
        self.updateButton.setToolTip(
            "Update the index containing information about which Extra Reflectance Cubes are available for download.")
        self.updateButton.released.connect(self._updateIndex)
        self.acceptSelectionButton = QPushButton("Accept Selection")
        self.acceptSelectionButton.released.connect(self.accept)
        self.layout().addWidget(self.table)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.downloadButton)
        l.addWidget(self.updateButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self.layout().addWidget(self.acceptSelectionButton)
        self._initialize()