from __future__ import annotations

from PyQt5.QtGui import QPainter, QRegion
from PyQt5.QtWidgets import QStyledItemDelegate, QWidget, QSpinBox, QStyleOptionViewItem, QStyle, QGridLayout, QLabel, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QScrollBar, QSizePolicy
from PyQt5 import QtCore
import typing
from .steps import SequencerStep, CoordSequencerStep, StepTypeNames


# class StepWidget(QWidget):
#     def __init__(self, step: SequencerStep):
#         super().__init__()
#         l = QGridLayout()
#         l.addWidget(QLabel(f"F: {str(step)}"))
#         self.setLayout(l)


class EditorWidg(QWidget): #TODO make disabled highlight color the same as active color
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAutoFillBackground(True)  # Prevents us from getting double vision with the painted version of the widget behind.
        self._coordTable = QTableWidget(self)
        self._coordTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self._coordTable.setRowCount(1)
        self._coordTable.horizontalHeader().setVisible(False)
        self._coordTable.verticalHeader().setVisible(False)
        self._coordTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)  # Always show scrollbar
        self._coordTable.horizontalScrollBar().setStyleSheet(
            "QScrollBar:horizontal { height: 20px; }"  # For some reason setting the height directly doesn't work.
        )
        self._coordTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)  # Smooth scrolling
        self._label = QLabel(self)
        # self._label.sizePolicy().setVerticalPolicy(QSizePolicy.Minimum)
        # self.sizePolicy().setVerticalPolicy(QSizePolicy.Maximum)

        self._requiredHeight = self._label.height() + self._coordTable.horizontalScrollBar().height() + self._coordTable.rowHeight(0)

        l = QGridLayout()
        l.setVerticalSpacing(0)
        l.addWidget(self._label, 0, 0, 1, 1)
        l.addWidget(self._coordTable, 1, 0, 1, 1, alignment=QtCore.Qt.AlignLeft)
        l.setRowStretch(2, 1)  # Allow the actual wigdets to sit at the top of the layout without getting stretched out.
        self.setLayout(l)

    def setFromStep(self, step: CoordSequencerStep):
        self._label.setText(StepTypeNames[step.stepType])
        self._coordTable.setColumnCount(step.stepIterations())
        for i in range(step.stepIterations()):
            self._coordTable.setItem(0, i, QTableWidgetItem(step.getIterationName(i)))
        self._coordTable.resizeColumnsToContents()
        self._coordTable.resizeRowsToContents()

        h2 = self._coordTable.rowHeight(0)
        h1 = self._coordTable.horizontalScrollBar().sizeHint().height()  # Just getting the current height doesn't work for some reason.
        self._coordTable.setMaximumHeight(h1+h2)
        #
        h1 = self._label.minimumSizeHint().height()
        h2 = self._coordTable.height()

        w = 0
        for i in range(step.stepIterations()):
            w += self._coordTable.columnWidth(i)
        self._coordTable.setMaximumWidth(w+2)  # The plus one gets rid of the scrollbar.

        #Make the selection match
        for i in range(step.stepIterations()):
            if i in step.getSelectedIterations():
                sel = True
            else:
                sel = False
            self._coordTable.item(0, i).setSelected(sel)

    def getSelection(self):
        return [i.column() for i in self._coordTable.selectedIndexes()]

    def sizeHint(self) -> QtCore.QSize:
        # return QtCore.QSize(1, self._requiredHeight)  # Width doesn't matter here.
        # return self.minimumSizeHint()
        h1 = self._label.minimumSizeHint().height()
        h2 = self._coordTable.height()
        return QtCore.QSize(1, h1+h2)  # Width doesn't seem to matter

class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent: QWidget=None):
        super().__init__(parent=parent)
        self._paintWidget = EditorWidg(parent)
        self._paintWidget.setVisible(False)
        # parent.setStyleSheet("""QAbstractItemView::item { padding: 0; }""")

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QWidget:
        if isinstance(index.data(), CoordSequencerStep):
            widg = EditorWidg(parent)
            widg.setFromStep(index.data())
            widg.resize(option.rect.size())
            return widg
        else:
            return None # Don't allow handling other types of values. # super().createEditor(parent, option, index)

    def setModelData(self, editor: EditorWidg, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex) -> None:
        step: SequencerStep = model.itemData(index)[0]  # TODO add notion of DataRole
        if isinstance(step, CoordSequencerStep):
            step.setSelectedIterations(editor.getSelection())

    def sizeHint(self, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        if isinstance(index.data(), CoordSequencerStep):
            s = self._paintWidget.sizeHint()
            s.setHeight(s.height() + 40)  #TODO idk how to find out what this paddnig should be
            return s
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
