from matplotlib.axes import Axes


class AxManager:
    """An object to manage multiple selector tools on a single axes. only one of these should exist per Axes object."""
    def __init__(self, ax: Axes):
        self.artists = []
        self.ax = ax
        self.canvas = self.ax.figure.canvas
        self.useblit = self.canvas.supports_blit
        self.canvas.mpl_connect('draw_event', self._update_background)
        self.background = None

    def update(self):
        """Re-render the axes."""
        if not self.ax.get_visible():
            return False
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            for artist in self.artists:
                if artist.get_visible():
                    self.ax.draw_artist(artist)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw_idle()
        return False

    def _update_background(self, event):
        """force an update of the background"""
        # If you add a call to `ignore` here, you'll want to check edge case:
        # `release` can call a draw event even when `ignore` is True.
        if self.useblit:
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)