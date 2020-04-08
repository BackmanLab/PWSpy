# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 16:24:11 2020

@author: backman05
"""
import typing

import numpy as np
import skan
import matplotlib.pyplot as plt
import pandas as pd
import skimage.morphology as morph
from scipy.ndimage import binary_hit_or_miss


class Skel(skan.Skeleton):
    def __init__(self, img):
        super().__init__(img)
        self.summary = skan.summarize(self)
        self.summary['branch-type'] = self.summary['branch-type'].astype(int)

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
        print(f"Found {isoPixels.sum()} isolated pixels of {img.sum()}")
        img[isoPixels]=False
        img = morph.skeletonize(img) #Without this step we get hard crashes when creating a new Skel
        print('rem')
        s = Skel(img)  # Re create the skeleton object.
        print('done')
        return s



class AnnotFig:
    """Pass a Skel to this class and it will plot all the paths with annotation giving the type and length."""
    def __init__(self, skel, title=''):
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
            text = f"type:{self.skel.path_type(idx)}, length:{self.skel.path_length(idx):.1f}"
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


# The types are: - tip-tip (0) - tip-junction (1) - junction-junction (2) - path-path (3)
# TODO a curviness parameter based on distance/vs euclidian distance

def prune2dIm(s):
    """Take Skel, s, and recursively prune unwanted paths."""
    j = 0
    did = True
    while True:
        if not did:
            break
        print(f"Iteration {j + 1}")

        did = False
        j += 1
        idxes = []

        s.summary['ids'] = s.summary.apply(lambda row: tuple(sorted((row['node-id-src'], row['node-id-dst']))), axis=1)

        #Generate all the unique IDs
        ids = pd.concat([s.summary['node-id-src'], s.summary['node-id-dst']])
        ids = ids.drop_duplicates()

        print(f"IDs to scan: {len(ids)}")
        for i in ids:
            matchArr = s.summary.apply(lambda row: i in row['ids'], axis=1)
            a = s.summary[matchArr]  # Select all rows using this endpoint
            if len(a) > 1:  # multiple branches use this endpoint.
                a = a[a['branch-type'] == 1]
                if len(a) == 0:
                    continue
                idx = a['branch-distance'].idxmin()  # delete the shortest one
                if a['branch-distance'].min() < 50:
                    idxes.append(idx)
            elif len(a) == 1:
                if a['branch-type'].iloc[0] == 0 and a['branch-distance'].iloc[0] < 50:  # short Stray segment
                    idxes.append(a.index[0])
            else:
                print(f"No paths found for id {i}")  # This shouldn't happen

        print(f"Found Step1 {len(idxes)}")
        if len(idxes) > 0:
            s = s.remove_path(idxes)
            if s is None:  # All paths were removed
                break
            else:
                did = True
                continue

        g = s.summary.groupby('ids')
        for i, group in g:  # Groups of paths that share both end points
            loopIdxes = list(group[(group['branch-type'] == 3) & (group['branch-distance'] <= 40)].index)
            group = group.drop(loopIdxes)
            group = group[group['branch-type'] == 2]
            a = group.sort_values('branch-distance')
            twinIdxes = list(a.index)[1:]
            idxes += loopIdxes + twinIdxes

        print(f"Found Step2 {len(idxes)}")
        if len(idxes) > 0:
            s = s.remove_path(idxes)
            if s is None:  # All paths were removed
                break
            else:
                did = True
                continue
    return s




def prune3dIm(skelIm, plotEveryN=3):
    """Loop through the planes of a 3d array and prune each 2d plane using prune2dIm"""
    skel = skelIm.copy()
    out = np.zeros_like(skel)

    for z in range(skelIm.shape[2]):
        print(F"Z={z}")
        if np.sum(skel[:, :, z]) == 0:
            continue
        s = Skel(skel[:, :, z].copy())

        if z % plotEveryN == 0:
            beforeIm = AnnotFig(s, title=f'before {z}')

        s = prune2dIm(s)

        if s is None:
            continue  #:Leave this plane of the image as zeros since the whole skeleton was removed
        else:
            if z % plotEveryN == 0:
                afterIm = AnnotFig(s, title=f'after {z}')
            out[:, :, z] = s.skeleton_image
    return out



if __name__ == '__main__':
    skel = np.load('skel.npy')
    out = prune3dIm(skel)