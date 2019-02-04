# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 19:37:35 2019

@author: Nick
"""
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.gridspec as gridspec
import scipy.ndimage as ndi


class PlotNd(object):
    def __init__(self, X, names, initialCoords=None):
        fig = plt.figure(figsize=(6,6)) 
        h,w =X.shape[:2]
        self.names=names
        self.extraDims = len(X.shape[2:])
        gs = gridspec.GridSpec(3, 2+self.extraDims+1,hspace=0,width_ratios=[w*.2/(self.extraDims+1)]*(self.extraDims+1)+[w,w*.2], height_ratios=[h*.1,h,h*.2], wspace=0)
        ax = {'im':plt.subplot(gs[1,self.extraDims+1])}
        ax['y'] = plt.subplot(gs[1,self.extraDims+2], sharey=ax['im'])
        ax['x'] = plt.subplot(gs[2,self.extraDims+1], sharex=ax['im'])
        ax['extra'] = [plt.subplot(gs[1,i]) for i in range(self.extraDims)]
        ax['c'] = plt.subplot(gs[0,self.extraDims+1])
        fig.suptitle(names[1]+names[0])
        ax['y'].set_title(names[0])
        ax['x'].set_xlabel(names[1])
        ax['y'].yaxis.set_ticks_position('right')
        [ax['extra'][i].set_ylim(0,X.shape[2+i]-1) for i in range(self.extraDims)]
        [ax['extra'][i].set_title(names[2+i]) for i in range(self.extraDims)]
        fig.canvas.mpl_connect('key_press_event', self.onpress)
        fig.canvas.mpl_connect('scroll_event', self.onscroll)
        fig.canvas.mpl_connect('button_press_event', self.onclick)
        fig.canvas.mpl_connect('motion_notify_event', self.ondrag)
        self.timer = fig.canvas.new_timer(interval=100)
        self.timer.add_callback(self.increment)
        self.timerRunning = False
        self.ax = ax
        self.fig = fig
        print('''Scroll to navigate stacks.\n\nPress "a" to automatically scroll.\n\nLeft click the color bar to set the max color range.\n\nRight click to set the mininum.\n\nPress "r" to reset the color range.\n\nPress 't' to swap the two primary axes.\n\nPress 'y' to rotate the order of the secondary axes.\n\nPress 'u' to rotate the order of all axes, allowing\n\a secondary axis to become a primary axis\n\n\n''')
        self.X = X
        self.resetColor()
        
        self.coords = tuple(i//2 for i in X.shape) if initialCoords is None else initialCoords
        self.ax['im'].get_xaxis().set_visible(False)
        self.ax['im'].get_yaxis().set_visible(False)
        lw=0.5
        self.vline = ax['im'].plot([100,100],[0,X.shape[0]],'r',linewidth = lw)[0]
        self.hline = ax['im'].plot([0,X.shape[1]],[100,100],'r',linewidth = lw)[0]
        self.line2 = ax['y'].plot([0,X.shape[1]],[100,100],'r',linewidth = lw)[0]
        self.line3 = ax['x'].plot([100,100],[0,X.shape[2]],'r',linewidth = lw)[0]
        self.line4 = [ax['extra'][i].plot([self.min,self.max],[100,100],'r',linewidth = lw)[0] for i in range(self.extraDims)]
        self.yplot = ax['y'].plot(self.X[(slice(None),)+self.coords[1:]], np.arange(self.X.shape[0]))[0]
        self.xplot = ax['x'].plot(np.arange(self.X.shape[1]),self.X[(self.coords[0],slice(None))+self.coords[2:]])[0]
        self.zplots = [ax['extra'][i].plot(self.X[self.coords[:2+i]+(slice(None),)+self.coords[3+i:]], np.arange(self.X.shape[2+i]))[0] for i in range(self.extraDims)]
        self.im = ax['im'].imshow(np.squeeze(self.X[(slice(None),slice(None))+self.coords[2:]]), aspect='auto')
        self.im.set_clim(self.min,self.max)
        self.cbar = plt.colorbar(self.im, cax=ax['c'], orientation='horizontal')
        self.update()  
        
    def update(self):
        self.im.set_data(np.squeeze(self.X[(slice(None),slice(None))+self.coords[2:]]))
        self.im.set_clim(self.min,self.max)
        self.yplot.set_data(self.X[(slice(None),)+tuple(i for i in self.coords[1:])],np.arange(self.X.shape[0]))
        self.ax['y'].set_xlim(self.min,self.max)
        self.xplot.set_data(np.arange(self.X.shape[1]),self.X[(self.coords[0],slice(None))+self.coords[2:]])
        self.ax['x'].set_ylim(self.min,self.max)
        [self.zplots[i].set_data(self.X[self.coords[:2+i]+(slice(None),)+self.coords[3+i:]],np.arange(self.X.shape[2+i])) for i in range(self.extraDims)]
        [self.ax['extra'][i].set_xlim(self.min,self.max) for i in range(self.extraDims)]
        self.ax['c'].xaxis.set_ticks_position("top")
        self.hline.set_data(self.hline.get_data()[0],[self.coords[0],self.coords[0]] )
        self.vline.set_data([self.coords[1],self.coords[1]],  self.vline.get_data()[1])
        self.line3.set_data([self.coords[1],self.coords[1]], self.ax['x'].get_ylim())
        self.line2.set_data( self.ax['y'].get_xlim(),[self.coords[0],self.coords[0]])
        [self.line4[i].set_data(self.line4[i].get_data()[0], [self.coords[2+i], self.coords[2+i]]) for i in range(self.extraDims)]
        self.im.axes.figure.canvas.draw()
        
    def resetColor(self):
        self.max = np.percentile(self.X[np.logical_not(np.isnan(self.X))],99.99)
        self.min = np.percentile(self.X[np.logical_not(np.isnan(self.X))],0.01)
        
    def onscroll(self, event):
        if ((event.button == 'up') or (event.button=='down')):
            self.coords = self.coords[:2] + ((self.coords[2] + int(event.step)) % self.X.shape[2],) + (self.coords[3:])
        self.update() 
        
    def onpress(self,event):
        print(event.key)
        if event.key == 'a':
            if self.timerRunning:
                self.timer.stop() 
                self.timerRunning = False
            else:
                self.timer.start()
                self.timerRunning = True
        elif event.key == 'r':
            self.resetColor()
            self.update()
        elif event.key == 'u':
            axes = np.roll(np.arange(len(self.X.shape)),1)
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX,names, coords)
        elif event.key == 't':
            axes = [1,0]+list(range(2,len(self.X.shape)))
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX,names, coords)
        elif event.key == 'y':
            axes = [0,1]+list(np.roll(np.arange(2,len(self.X.shape)),1))
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX,names, coords)
    def onclick(self,event):
#            print(event.button)
        if event.inaxes is None:
            return
        ax = event.inaxes
        x, y = event.xdata, event.ydata
        button = event.button
        self.processMouse(ax,x,y, button,colorbar=True)
        
    def processMouse(self,ax,x,y, button, colorbar):
        if ax==self.ax['im']:
            self.coords = (int(y), int(x))+self.coords[2:]
        elif ax==self.ax['y']:
            self.coords = (int(y),)+self.coords[1:]
        elif ax==self.ax['x']:
            self.coords = (self.coords[0],int(x))+self.coords[2:]
        elif ax in self.ax['extra']:
            idx = self.ax['extra'].index(ax)
            self.coords = self.coords[:2+idx]+(int(y),)+self.coords[3+idx:]
        if colorbar:
            if ax==self.ax['c']:
                if button==1:
                    self.max = x
                elif button==3:
                    self.min = x
        self.update()
        
    def ondrag(self, event):
        if event.inaxes is None:
            return
        if event.button != 1:
            return
        ax = event.inaxes
        x, y = event.xdata, event.ydata
        button = event.button
        self.processMouse(ax,x,y, button,colorbar=False)
        
    def increment(self):
        self.coords = (self.coords[0], self.coords[1], (self.coords[2]+1)%self.X.shape[2])+self.coords[3:]
        self.update()
        


    
if __name__ == '__main__':
    x = np.linspace(-1,1, num=100)
    y = np.linspace(-1,1, num=100)
    z = np.linspace(-1,1,num=80)
    t = np.linspace(0,20,num=30)
    Y,X,Z,T = np.meshgrid(y,x,z,t)
    names=['y','x','z','t']
    R = np.sqrt(X**2 + Y**2 + Z**2)
    A = np.exp(-R)*(.75+.25*np.sin(T))
    crop = np.sqrt(X**2+Y**2)>.75
    
    '''We can also rotate the array if needed'''
    degrees = 35
    plane = (0,2) #rotating in the yz plane
    A = ndi.rotate(A,degrees, axes=plane)
    crop = ndi.rotate(crop,degrees, axes=plane,order = 0,output=np.bool, cval=True)
    
    A[crop] = np.nan


    PlotNd(A,names)   #Input array dimensions should be [y,x,z]
