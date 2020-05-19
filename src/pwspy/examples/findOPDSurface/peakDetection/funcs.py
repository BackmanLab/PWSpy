# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 16:24:11 2020

@author: backman05
"""
import typing
from time import time

import numpy as np
import skan
import matplotlib.pyplot as plt
import pandas as pd
import skimage.morphology as morph
from scipy.ndimage import binary_hit_or_miss

from pwspy.utility.misc import cached_property


class Skel(skan.Skeleton):
    """Extends skan.Skeleton to allow for removing branches. Also conveniently packages the `summary` dataframe along with the skeleton.
    Can analyze a 2d or 3d array. Represents the full array which may contain multiple independent skeletons."""
    def __init__(self, img):
        super().__init__(img)
        self.summary = skan.summarize(self)
        self.summary['branch-type'] = self.summary['branch-type'].astype(int)
        self.summary['ids'] = self.summary.apply(lambda row: tuple(sorted((row['node-id-src'], row['node-id-dst']))), axis=1)

    def path_type(self, i):
        return self.summary.loc[i]['branch-type']

    def path_length(self, i):
        return self.path_lengths()[i]

    def remove_path(self, idxes: typing.List[int]):
        """Strip the paths assotiated with the indexes in idxes"""
        if isinstance(idxes, int):
            idxes = [idxes]
        idxes = set(idxes) #Make sure the indexes are unique
        if len(idxes) == self.n_paths:
            return None
        Coords = ([], [])
        for idx in idxes:
            indices = self.path(idx)
            ep1Deg = self.degrees[indices[0]] #Get the degrees (connectedness) of both endpoints
            ep2Deg = self.degrees[indices[-1]]
            if ep1Deg < 3:
                start = 0
            else:
                start = 1 #If this endpoint is shared with other paths don't delete it (It's coordinates are likly not integers anyway due to Skan's handling of clustered ponits at junctions)
            if ep2Deg < 3:
                end = None
            else:
                end = -1
            coords = self.path_coordinates(idx)
            coords = coords[start:end].astype(int)
            Coords = (Coords[0] + list(coords[:, 0]), Coords[1] + list(coords[:, 1]))
        img = self.skeleton_image
        img[Coords] = 0 # Set all the pixels associated with a deleted path to 0.
        #Remove isolated pixels
        struct = np.array([[0,0,0],[0,1,0],[0,0,0]], dtype=bool)
        isoPixels = binary_hit_or_miss(img, struct)
        img[isoPixels]=False
        img = morph.skeletonize(img) #Without this step we get hard crashes when creating a new Skel
        s = Skel(img)  # Re create the skeleton object.
        return s

    def plot(self):
        ndim = self.path_coordinates(1).shape[1]
        if ndim == 2:
            a = AnnotFig(self)
        elif ndim == 3:
            from mpl_toolkits.mplot3d import Axes3D
            import matplotlib as mpl
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            groups = self.summary.groupby('skeleton-id')
            colors = mpl.cm.get_cmap('gist_rainbow')(np.linspace(0, 1, num=len(groups)))
            for i, (n, group) in enumerate(groups):
                for idx in group.index:
                    coords = self.path_coordinates(idx)
                    coords = (coords[:,0], coords[:,1], coords[:,2])
                    ax.plot(*coords, c=colors[i])
            fig.show()
        else:
            raise ValueError(f"Not sure what to do with a {ndim} dimensional skeleton")

class SingleSkeleton:
    """Represents a single connect skeleton from the Skel class.
    This class is not used. the idea was to reject whole skeletons
    as the first step based on their geometry."""
    def __init__(self, parent: Skel, id: int):
        self.s = parent
        self.id = id
        from shapely.geometry import MultiLineString
        linesCoords = []
        for i in self.indices:
            c = self.s.path_coordinates(i)
            c = tuple(tuple(c[i, :]) for i in range(c.shape[0]))
            linesCoords.append(c)
        self.mls = MultiLineString(linesCoords)

    @cached_property
    def indices(self):
        return list(self.s.summary[self.s.summary['skeleton-id'] == self.id].index)

    @property
    def convexHull(self):
        return self.mls.convex_hull.area

    @property
    def length(self):
        return self.mls.length


class AnnotFig:
    """Pass a Skel to this class and it will plot all the paths with annotation giving the type and length."""
    def __init__(self, skel: Skel, title=''):
        self.fig, self.ax = plt.subplots()
        self.fig.annotfigref = self
        self.fig.suptitle(title)
        self.annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                                      bbox=dict(boxstyle="round", fc="w"),
                                      arrowprops=dict(arrowstyle="->"))

        self.lines = self.plotLines(skel)

        self.skel = skel

        cid = self.fig.canvas.mpl_connect('motion_notify_event', self._hoverCallback)

    def _hoverCallback(self, event):  # Show an annotation about the ROI when the mouse hovers over it.
        def update_annot(line, idx):
            self.annot.xy = line.get_xydata()[0, :]
            sid = self.skel.summary.iloc[idx]['skeleton-id']
            ss = SingleSkeleton(self.skel, sid)
            text = f"type:{self.skel.path_type(idx)}, length:{self.skel.path_length(idx):.1f}, skel_length:{ss.length},skel_rat:{ss.convexHull/ss.length}"
            self.annot.set_text(text)
            self.annot.get_bbox_patch().set_alpha(0.4)

        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            for line, index in self.lines:
                contained, _ = line.contains(event)
                if contained:
                    if not vis:
                        update_annot(line, index)
                        self.annot.set_visible(True)
                        self.fig.canvas.draw_idle()
                    return
            if vis:  # If we got here then no hover actions were found.
                self.annot.set_visible(False)
                self.fig.canvas.draw_idle()

    def plotLines(self, skeleton):
        lines = []
        for n in range(skeleton.n_paths):
            coords = skeleton.path_coordinates(n)
            coords = (coords[:, 0], coords[:, 1])
            line = self.ax.plot(*coords)[0]
            lines.append((line, n))
        return lines

    def show(self):
        self.fig.show()


def _scanIds(s: Skel, ids: typing.List[int]):
    """Returns a list of indexes of skeleton paths to be removed"""
    idxes = []
    for i in ids:
        matchArr = np.any(s.summary[['node-id-src', 'node-id-dst']] == i, axis=1) #Find all row with an endpoint matching `i`. this is kinda slow. this is the main place that would benefit from optimization
        a = s.summary[matchArr]  # Select all rows using this endpoint
        if len(a) > 1:  # multiple branches use this endpoint.
            a = a[a['branch-type'] == 1]
            if len(a) == 0:
                continue
            idx = a['branch-distance'].idxmin()  # delete the shortest one
            if a['branch-distance'].min() < 50:
                idxes.append(idx)
        elif len(a) == 1:
            if a['branch-type'].iloc[0] == 0:  # This is an isolated segment
                if a['branch-distance'].iloc[0] < 50:  # short Stray segment
                    idxes.append(a.index[0])
        else:
            print(f"No paths found for id {i}")  # This shouldn't happen
    return idxes

def _scanSharedEndpoints(s):
    """Returns a list of indexes of skeleton paths to be removed"""
    g = s.summary.groupby('ids')
    idxes = []
    for i, group in g:  # Groups of paths that share both end points. These could be loops or groups of branches that start and stop in the same place
        loops = group[group['branch-type'] == 3]
        loopIdxes = list(loops[loops['branch-distance'] <= 40].index)  # We're going to discard all loops that are too short.

        juncs = group[group['branch-type'] == 2]  # Junction-junction branches
        juncs = juncs.sort_values('branch-distance')
        twinIdxes = list(juncs.index)[1:]  # We're going to discard all paths except for the shortest path.
        idxes += loopIdxes + twinIdxes
    return idxes

# The types are: - tip-tip (0) - tip-junction (1) - junction-junction (2) - path-path (3)
# TODO a curviness parameter based on distance/vs euclidian distance

def prune2dIm(s):
    """Take Skel, s, and recursively prune unwanted paths."""
    iteration = 0
    while True:
        print(f"Iteration {iteration + 1}")
        iteration += 1

        #Generate all the unique IDs
        ids = pd.concat([s.summary['node-id-src'], s.summary['node-id-dst']]).drop_duplicates()
        print(f"IDs to scan: {len(ids)}")
        idxes = _scanIds(s, ids)

        print(f"Found Step1 {len(idxes)}")
        if len(idxes) > 0:
            s = s.remove_path(idxes)
            if s is None:  # All paths were removed, no more recursion needed
                break
            else:
                continue

        idxes = _scanSharedEndpoints(s)

        print(f"Found Step2 {len(idxes)}")
        if len(idxes) > 0:
            s = s.remove_path(idxes)
            if s is None:  # All paths were removed, no more recursion needed
                break
            else:
                continue

        break #We only get to this point if we didn't take any action above. We are, therefore, done.
    return s




def prune3dIm(skelIm, plotEveryN=3):
    """Loop through the planes of a 3d array and prune each 2d plane using prune2dIm"""
    skel = skelIm.copy()
    out = np.zeros_like(skel)

    try:
        for z in range(skelIm.shape[2]):
            print(F"Z={z}")
            if np.sum(skel[:, :, z]) == 0:
                continue
            s = Skel(skel[:, :, z].copy())

            if z % plotEveryN == 0:
                beforeIm = AnnotFig(s, title=f'Before pruning {z}')
                beforeIm.show()

            s = prune2dIm(s)

            if s is None:
                continue  #:Leave this plane of the image as zeros since the whole skeleton was removed
            else:
                if z % plotEveryN == 0:
                    afterIm = AnnotFig(s, title=f'After pruning {z}')
                    afterIm.show()
                out[:, :, z] = s.skeleton_image
    except KeyboardInterrupt: # Allow early stopping though keybord interrupt
        pass
    return out


def _concaveHull3d(coords: typing.List[typing.Tuple[int, int]], alpha):
    """
    Found here: https://gist.github.com/dwyerk/10561690
    Compute the alpha shape (concave hull) of a set
    of points.

    Args:
        coords: nx2 array of points.
        alpha: alpha value to influence the
            gooeyness of the border. Smaller numbers
            don't fall inward as much as larger numbers.
            Too large, and you lose everything!
    """
    from scipy.spatial.qhull import Delaunay
    from shapely import geometry
    from shapely.ops import cascaded_union, polygonize
    if len(coords) < 4:
        # When you have a triangle, there is no sense
        # in computing an alpha shape.
        return geometry.MultiPoint(coords).convex_hull
    coords = np.array(coords)
    tri = Delaunay(coords)
    triangles = coords[tri.simplices]
    # Lengths of sides of triangle
    a = ((triangles[:, 0, 0] - triangles[:, 1, 0]) ** 2 + (triangles[:, 0, 1] - triangles[:, 1, 1]) ** 2) ** 0.5
    b = ((triangles[:, 1, 0] - triangles[:, 2, 0]) ** 2 + (triangles[:, 1, 1] - triangles[:, 2, 1]) ** 2) ** 0.5
    c = ((triangles[:, 2, 0] - triangles[:, 0, 0]) ** 2 + (triangles[:, 2, 1] - triangles[:, 0, 1]) ** 2) ** 0.5
    s = (a + b + c) / 2.0  # Semiperimeter of triangle

    areas = (s * (s - a) * (s - b) * (s - c)) ** 0.5  # Area of triangle by Heron's formula

    circums = a * b * c / (4.0 * areas)
    filtered = triangles[circums < alpha]  # Here's the radius filter.

    edge1 = filtered[:, (0, 1)]
    edge2 = filtered[:, (1, 2)]
    edge3 = filtered[:, (2, 0)]
    edge_points = np.unique(np.concatenate((edge1, edge2, edge3)), axis=0).tolist()
    m = geometry.MultiLineString(edge_points)
    triangles = list(polygonize(m))
    return cascaded_union(triangles), edge_points


if __name__ == '__main__':
    skel = np.load(r'C:\Users\backman05\Desktop\findsurface\skel.npy')
    s = Skel(skel[:,:,13])
    stime = time()
    s = prune2dIm(s)
    print("HHAHAHA", time()-stime)
    out = prune3dIm(skel)