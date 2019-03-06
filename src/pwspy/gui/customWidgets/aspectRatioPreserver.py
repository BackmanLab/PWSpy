from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QBoxLayout, QSpacerItem


class AspectRatioWidget(QWidget):
    def __init__(self, widget: QWidget, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self.aspect = aspect
        self.layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.widget = widget
        # add spacer, then your widget, then spacer
        self.layout.addItem(QSpacerItem(0, 0))
        self.layout.addWidget(widget)
        self.layout.addItem(QSpacerItem(0, 0))

    def resizeEvent(self, event: QtGui.QResizeEvent):
        thisAspectRatio = event.size().width() / event.size().height()

        if thisAspectRatio > self.aspect:  # too wide
            self.layout.setDirection(QBoxLayout.LeftToRight)
            widgetStretch = self.height() * self.aspect  # i.e., my width
            outerStretch = (self.width() - widgetStretch) / 2 + 0.5
        else:  # too tall
            self.layout.setDirection(QBoxLayout.TopToBottom)
            widgetStretch = self.width() * (1 / self.aspect)  # i.e., my height
            outerStretch = (self.height() - widgetStretch) / 2 + 0.5

        self.layout.setStretch(0, outerStretch)
        self.layout.setStretch(1, widgetStretch)
        self.layout.setStretch(2, outerStretch)

    def setAspect(self, aspect: float):
        self.aspect = aspect