from __future__ import annotations

from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtGui import QPainter, QRegion, QTextDocument, QAbstractTextDocumentLayout, QPalette
from PyQt5.QtWidgets import QStyledItemDelegate, QWidget, QSpinBox, QStyleOptionViewItem, QStyle, QGridLayout, QLabel, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QScrollBar, QSizePolicy, QFrame, QApplication
from PyQt5 import QtCore, QtGui
import typing
from .steps import SequencerStep, CoordSequencerStep, StepTypeNames, ContainerStep


class EditorWidg(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAutoFillBackground(True)  # Prevents us from getting double vision with the painted version of the widget behind.
        self._coordTable = QTableWidget(self)
        self._coordTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # This makes the items stay looking selected even when the table is inactive
        self._coordTable.setStyleSheet("""QTableWidget::item:active {   
                                        selection-background-color: darkblue;
                                        selection-color: white;}
                                        QTableWidget::item:inactive {
                                        selection-background-color: darkblue;
                                        selection-color: white;}""")

        self._coordTable.setRowCount(1)
        self._coordTable.horizontalHeader().setVisible(False)
        self._coordTable.verticalHeader().setVisible(False)
        self._coordTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)  # Always show scrollbar
        self._coordTable.horizontalScrollBar().setStyleSheet(
            "QScrollBar:horizontal { height: 15px; }"  # For some reason setting the height directly doesn't work.
        )
        self._coordTable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)  # Smooth scrolling
        self._coordTable.sizePolicy().setHorizontalPolicy(QSizePolicy.Expanding)

        self._requiredHeight = self._coordTable.horizontalScrollBar().height() + self._coordTable.rowHeight(0)

        l = QGridLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.setVerticalSpacing(0)
        l.addWidget(self._coordTable, 0, 0, 1, 1, alignment=QtCore.Qt.AlignLeft)
        l.setRowStretch(1, 1)  # Allow the actual wigdets to sit at the top of the layout without getting stretched out.
        self.setLayout(l)

    def setFromStep(self, step: CoordSequencerStep):
        self._coordTable.setColumnCount(step.stepIterations())
        for i in range(step.stepIterations()):
            self._coordTable.setItem(0, i, QTableWidgetItem(step.getIterationName(i)))
        self._coordTable.resizeColumnsToContents()
        self._coordTable.resizeRowsToContents()

        h2 = self._coordTable.rowHeight(0)
        h1 = self._coordTable.horizontalScrollBar().sizeHint().height()  # Just getting the current height doesn't work for some reason.
        self._coordTable.setMaximumHeight(h1+h2)
        self._coordTable.setMinimumHeight(h1+h2)
        #

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
        h2 = self._coordTable.height()
        return QtCore.QSize(1, h2)  # Width doesn't seem to matter


class HTMLDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        style = option.widget.style() if option.widget else QApplication.style()
        doc = QTextDocument()
        doc.setHtml(option.text)

        # Painting item without text
        option.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, option, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (option.state & QStyle.State_Selected):
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, option)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        self.initStyleOption(option, index)

        doc = QTextDocument()
        doc.setHtml(option.text)
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())


class MyDelegate(HTMLDelegate):
    def __init__(self, parent: QWidget=None):
        super().__init__(parent=parent)
        self._paintWidgetRenderedOnce = False
        self._paintWidget = EditorWidg(parent)
        self._paintWidget.setVisible(False)
        self._editing = False

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
        self._editing = None
        self.sizeHintChanged.emit(index)

    def editorEvent(self, event: QtCore.QEvent, model: QtCore.QAbstractItemModel, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> bool:
        self._editing = index
        self.sizeHintChanged.emit(index)
        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        if isinstance(index.data(), CoordSequencerStep) and self._editing == index:
            self.initStyleOption(option, index)
            editor = self.createEditor(None, option, index)
            s = editor.sizeHint()
            return s
        else:
            return super().sizeHint(option, index)

    def displayText(self, value: typing.Any, locale: QtCore.QLocale) -> str:
        if isinstance(value, CoordSequencerStep):
            if len(value.getSelectedIterations()) == 0 or len(value.getSelectedIterations()) == value.stepIterations():
                s = ": all coords"
            else:
                s = f": {len(value.getSelectedIterations())} coords"
            return "<html>" + StepTypeNames[value.stepType] + "<b>" + s + "</b>" + "</html>"
        if isinstance(value, ContainerStep):
            return StepTypeNames[value.stepType]  # Just return the name.
        if isinstance(value, SequencerStep):
            return "\u2022" + StepTypeNames[value.stepType]  # For endpoint steps add a bullet
        else:
            super().displayText(value, locale)
