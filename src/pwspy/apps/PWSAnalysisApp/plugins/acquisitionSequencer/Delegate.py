from __future__ import annotations

from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPainter, QRegion
from PyQt5.QtWidgets import QStyledItemDelegate, QWidget, QSpinBox, QStyleOptionViewItem, QStyle, QGridLayout, QLabel, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QScrollBar
from PyQt5 import QtCore
import typing
from .steps import SequencerStep, CoordSequencerStep, StepTypeNames


class StepWidget(QWidget):
    def __init__(self, step: SequencerStep):
        super().__init__()
        l = QGridLayout()
        l.addWidget(QLabel(f"F: {str(step)}"))
        self.setLayout(l)


class EditorWidg(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._coordTable = QTableWidget(self)
        self._coordTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._coordTable.setRowCount(1)
        self._coordTable.horizontalHeader().setVisible(False)
        self._coordTable.verticalHeader().setVisible(False)
        self._coordTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self._label = QLabel(self)

        l = QGridLayout()
        l.addWidget(self._label)
        l.addWidget(self._coordTable)
        self.setLayout(l)

    def setFromStep(self, step: CoordSequencerStep):
        self._label.setText(StepTypeNames[step.stepType])
        self._coordTable.setColumnCount(step.stepIterations())
        for i in range(step.stepIterations()):
            self._coordTable.setItem(0, i, QTableWidgetItem(step.getIterationName(i)))
        self._coordTable.resizeColumnsToContents()
        self._coordTable.resizeRowsToContents()


    def sizeHint(self) -> QtCore.QSize:
        # return QtCore.QSize(600, 600)
        # size = self.minimumSize()
        return self.minimumSizeHint()
        # return self.layout().sizeHint()


class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._paintWidget = EditorWidg(None)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QWidget:
        if isinstance(index.data(), CoordSequencerStep):
            widg = EditorWidg(parent)
            widg.setFromStep(index.data())
            return widg
        else:
            super().createEditor(parent, option, index)

    def sizeHint(self, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        if isinstance(index.data(), CoordSequencerStep):
            return self._paintWidget.sizeHint()
        else:
            return super().sizeHint(option, index)

    def displayText(self, value: typing.Any, locale: QtCore.QLocale) -> str:
        if isinstance(value, SequencerStep):
            return StepTypeNames[value.stepType]
        else:
            super().displayText(value, locale)

    def paint(self, painter: QPainter, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> None:
        if isinstance(index.data(), CoordSequencerStep):
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())

            painter.save()
            self._paintWidget.setFromStep(index.data())
            self._paintWidget.resize(option.rect.size())
            painter.translate(option.rect.topLeft())
            self._paintWidget.render(painter, QPoint(), QRegion(), QWidget.DrawChildren)
            painter.restore()
        else:
            super().paint(painter, option, index)
