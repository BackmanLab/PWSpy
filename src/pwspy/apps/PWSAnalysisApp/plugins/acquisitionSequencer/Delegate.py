from __future__ import annotations

from PyQt5.QtGui import QPainter, QRegion
from PyQt5.QtWidgets import QStyledItemDelegate, QWidget, QSpinBox, QStyleOptionViewItem, QStyle, QGridLayout, QLabel, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QScrollBar
from PyQt5 import QtCore
import typing
from .steps import SequencerStep, CoordSequencerStep, StepTypeNames


# class StepWidget(QWidget):
#     def __init__(self, step: SequencerStep):
#         super().__init__()
#         l = QGridLayout()
#         l.addWidget(QLabel(f"F: {str(step)}"))
#         self.setLayout(l)


class EditorWidg(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAutoFillBackground(True)  # Prevents us from getting double vision with the painted version of the widget behind.
        self._coordTable = QTableWidget(self)
        self._coordTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._coordTable.setRowCount(1)
        self._coordTable.horizontalHeader().setVisible(False)
        self._coordTable.verticalHeader().setVisible(False)
        self._coordTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)  # Always show scrollbar
        self._coordTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)  # Smooth scrolling
        self._label = QLabel(self)

        self._requiredHeight = self._label.height() + self._coordTable.horizontalScrollBar().height() + self._coordTable.rowHeight(0)
        self._coordTable.setFixedHeight(self._coordTable.horizontalScrollBar().height() + self._coordTable.rowHeight(0))
        l = QGridLayout()
        l.addWidget(self._label, 0, 0, 1, 1)
        l.addWidget(self._coordTable, 1, 0, 1, 1, alignment=QtCore.Qt.AlignLeft)
        # l.addWidget(QWidget(self), )
        self.setLayout(l)

    def setFromStep(self, step: CoordSequencerStep):
        self._label.setText(StepTypeNames[step.stepType])
        self._coordTable.setColumnCount(step.stepIterations())
        for i in range(step.stepIterations()):
            self._coordTable.setItem(0, i, QTableWidgetItem(step.getIterationName(i)))
        self._coordTable.resizeColumnsToContents()
        self._coordTable.resizeRowsToContents()
        w = 0
        for i in range(step.stepIterations()):
            w += self._coordTable.columnWidth(i)
        self._coordTable.setMaximumWidth(w+5)


    def sizeHint(self) -> QtCore.QSize:
        # return QtCore.QSize(1, self._requiredHeight)  # Width doesn't matter here.
        return self.minimumSizeHint()


class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._paintWidget = EditorWidg(None)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QWidget:
        if isinstance(index.data(), CoordSequencerStep):
            widg = EditorWidg(parent)
            widg.setFromStep(index.data())
            widg.resize(option.rect.size())
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
            self._paintWidget.render(painter)#, None, None, None)#, QPoint(), QRegion(), QWidget.DrawChildren)
            painter.restore()
        else:
            super().paint(painter, option, index)
