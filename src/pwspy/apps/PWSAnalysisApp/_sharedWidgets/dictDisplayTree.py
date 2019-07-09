from PyQt5.QtWidgets import QTreeWidget, QWidget, QTreeWidgetItem, QDialog, QGridLayout


class DictDisplayTree(QTreeWidget):
    def __init__(self, parent: QWidget, value: dict):
      super().__init__(parent)
      self.setHeaderHidden(True)
      self.fillItem(self.invisibleRootItem(), value)

    def fillItem(self, item, value):
      item.setExpanded(True)
      if type(value) is dict:
        for key, val in sorted(value.items()):
          child = QTreeWidgetItem()
          if isinstance(val, (tuple, list, dict)):
              child.setText(0, key)
              item.addChild(child)
              self.fillItem(child, val)
          else:
              child.setText(0, f"{key}: {str(val)}")
              item.addChild(child)
      elif isinstance(value, (tuple, list)):
        for val in value:
          child = QTreeWidgetItem()
          item.addChild(child)
          if type(val) is dict:
            child.setText(0, '[dict]')
            self.fillItem(child, val)
          elif type(val) is list:
            child.setText(0, '[list]')
            self.fillItem(child, val)
          else:
            child.setText(0, str(val))
          child.setExpanded(True)
      else:
        child = QTreeWidgetItem()
        child.setText(0, str(value))
        item.addChild(child)

class DictDisplayTreeDialog(QDialog):
    def __init__(self, parent: QWidget, value: dict, title: str = None):
        super().__init__(parent)
        if title is not None:
            self.setWindowTitle(title)
        l = QGridLayout()
        l.addWidget(DictDisplayTree(self, value))
        self.setLayout(l)
