from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


class AxManager:
    """An object to manage multiple selector tools on a single axes. Only one of these should exist per Axes object.

    Args:
        ax: The matplotlib Axes object to draw on.

    """
    def __init__(self, ax: Axes):
        self.artists = []
        self.ax = ax
        if hasattr(ax, 'pwspyAxisManager'):
            raise Exception("Axes already has an AxManager assiged.")
        ax.pwspyAxisManager = self
        self.canvas = self.ax.figure.canvas
        self.canvas.mpl_connect('draw_event', self._update_background)
        self.background = None

    def addArtist(self, artist):
        #TODO implement more cases here.
        self.artists.append(artist)
        if isinstance(artist, Patch):
            self.ax.add_patch(artist)
        elif isinstance(artist, Line2D):
            self.ax.add_line(artist)
        else:
            self.ax.add_artist(artist)

    def removeArtists(self):
        for artist in self.artists:
            artist.remove()
        self.artists = []
        self.update()

    def removeArtist(self, artist):
        self.artists.remove(artist)
        artist.remove()
        self.update()

    def update(self):
        """Re-render the axes. Call this after you know that something has changed with the plot."""
        if not self.ax.get_visible():
            return False
        if self.canvas.supports_blit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            for artist in self.artists:
                if artist.get_visible():
                    self.ax.draw_artist(artist)
            try:
                self.canvas.blit(self.ax.bbox)
            except AttributeError: #Sometimes this happens when first opening
                self.canvas.draw_idle()
        else:
            self.canvas.draw_idle()
        return False

    def _update_background(self, event):
        """force an update of the background"""
        # If you add a call to `ignore` here, you'll want to check edge case:
        # `release` can call a draw event even when `ignore` is True.
        if self.canvas.supports_blit:
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)