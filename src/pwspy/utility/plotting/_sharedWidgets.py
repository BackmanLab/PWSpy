import os
import traceback
from enum import Enum
from typing import List, Union, Callable, Tuple, Iterable

from PyQt5 import QtGui
from PyQt5.QtWidgets import QDialog, QWidget, QSpinBox, QLineEdit, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QFileDialog
from matplotlib import animation
from matplotlib.artist import Artist

from pwspy.apps import resources


class AnimationDlg(QDialog):
    """A dialog box that facilitates the saving an animation.
    Args:
        fig (Figure): The figure to save the animation from.
        input (list(list(Artists)) or tuple(Callable, Iterable)): If this is a list of lists of Artists then it will be passed to matplotlib.animation.ArtistAnimation which
            will be used to save the animation. If this is a tuple of a function and an iterable then the function will be passed to FuncAnimation where the iterable will be passed
            to the `frames` argument.
        parent (QWidget): The widget that this dialog will act as the child for.
    """
    class SaveMethods(Enum):
        GIF = 'pillow'
        HTML = 'html'
        MP4 = 'ffmpeg'

    def __init__(self, fig, input: Union[List[List[Artist]], Tuple[Callable, Iterable]], parent: QWidget):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Save Animation")

        self.input = input
        self.figure = fig

        self.intervalSpinBox = QSpinBox(self)
        self.intervalSpinBox.setMinimum(0)
        self.intervalSpinBox.setMaximum(10000)
        self.intervalSpinBox.setSingleStep(50)
        self.intervalSpinBox.setValue(100)

        self.fPath = QLineEdit(self)
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.browseButton.released.connect(self.browseFile)


        self.methodCombo = QComboBox(self)
        [self.methodCombo.addItem(i.name, i) for i in self.SaveMethods]

        self.saveButton = QPushButton("Save", self)
        self.saveButton.released.connect(self.save)

        layout = QVBoxLayout()
        bottomLay = QHBoxLayout()

        lay = QHBoxLayout()
        lay.addWidget(QLabel("Frame Interval (ms):"))
        lay.addWidget(self.intervalSpinBox)
        layout.addLayout(lay)

        lay = QHBoxLayout()
        lay.addWidget(self.fPath)
        lay.addWidget(self.browseButton)
        layout.addLayout(lay)

        bottomLay.addStretch()
        bottomLay.addWidget(self.methodCombo)
        bottomLay.addWidget(self.saveButton)
        bottomLay.addStretch()
        layout.addLayout(bottomLay)

        self.setLayout(layout)

    def save(self): #TODO frame interval doesn't seem to work. Automatically fix the file name to match the accepted extension.
        """Save the animation to file depending on the settings of the dialog."""
        if callable(self.input[0]):
            ani = animation.FuncAnimation(self.figure, self.input[0], frames=self.input[1], interval=self.intervalSpinBox.value())
        else:
            ani = animation.ArtistAnimation(self.figure, self.input, interval=self.intervalSpinBox.value())
        Writer = animation.writers[self.methodCombo.currentData().value]
        if Writer is animation.FFMpegWriter:
            writer = Writer(bitrate=-1)  # This should improve quality
        else:
            writer = Writer()
        try:
            ani.save(self.fPath.text(), writer=writer)
        except Exception as e:
            traceback.print_exc()
            msg = QMessageBox.warning(self, 'Warning', str(e))
        self.accept()

    def browseFile(self):
        fname, extension = QFileDialog.getSaveFileName(self, 'Save Location', os.getcwd())
        if fname != '':
            self.fPath.setText(fname)