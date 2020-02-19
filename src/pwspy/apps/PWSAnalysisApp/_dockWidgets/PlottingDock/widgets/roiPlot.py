from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.bigPlot import BigPlot


class RoiPlot(BigPlot):

    def __init__(self, acqDir: AcqDir, data: np.ndarray, title: str, parent=None):