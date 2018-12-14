# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick
"""
from __future__ import annotations

import numpy as np
from scipy.io import loadmat,savemat
import tifffile as tf
import os
import json
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib import path
from glob import glob
import typing
import scipy.interpolate as spi

class ImCube:
    ''' A class representing a single acquisition of PWS. Contains methods for loading and saving to multiple formats as well as common operations used in analysis.'''
    def __init__(self,data,metadata, dtype = np.float32):
        assert isinstance(data,np.ndarray)
        assert isinstance(metadata,dict)
        self._hasBeenNormalized = False #Keeps track of whether or not we have normalized by exposure so that we don't do it twice.
        self.data = data.astype(dtype)
        self.metadata = metadata
        try:
            self.wavelengths = self.metadata['wavelengths']
        except:
            self.wavelengths = self.metadata["waveLengths"]
        if self.data.shape[2] != len(self.wavelengths):
            raise ValueError("The length of the wavelengths list doesn't match the wavelength axis of the data array")
        
    @classmethod
    def loadAny(cls, directory):
        try:
            return ImCube.fromTiff(directory)
        except Exception as e:
            try:
                files = glob(os.path.join(directory,'*.comp.tif'))
                return ImCube.decompress(files[0])
            except:
                try:
                    return ImCube.fromOldPWS(directory)
                except:
                    raise Exception("Could not find a valid PWS image cube file.")
    @classmethod
    def fromOldPWS(cls,directory):
        try:
            md = json.load(open(os.path.join(directory,'pwsmetadata.txt')))
        except: #have to use the old metadata
            print("Json metadata not found")
            info2 = list(loadmat(os.path.join(directory,'info2.mat'))['info2'].squeeze())
            info3 = list(loadmat(os.path.join(directory,'info3.mat'))['info3'].squeeze())
            wv = list(loadmat(os.path.join(directory,'wv.mat'))['WV'].squeeze())
            md = {'startWv':info2[0],'stepWv':info2[1],'stopWv':info2[2],
                 'exposure':info2[3],'time':'{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(*[int(i) for i in [info3[8],info3[7],info3[6],info3[9],info3[10],info3[11]]]),'systemId':info3[0],
                 'imgHeight':int(info3[2]),'imgWidth':int(info3[3]),'wavelengths':wv}
        with open(os.path.join(directory,'image_cube'),'rb') as f:
            data = np.frombuffer(f.read(),dtype=np.uint16)
        data = data.reshape((md['imgHeight'],md['imgWidth'],len(md['wavelengths'])),order='F')
        return cls(data, md)

    @classmethod
    def fromTiff(cls,directory):
        if os.path.exists(os.path.join(directory,'MMStack.ome.tif')):
            path = os.path.join(directory,'MMStack.ome.tif')
        elif os.path.exists(os.path.join(directory,'pws.tif')):
            path = os.path.join(directory,'pws.tif')
        else:
            raise OSError("No Tiff file was found at:", directory)    
        with tf.TiffFile(path) as tif:
            data = np.rollaxis(tif.asarray(),0,3) #Swap axes to match y,x,lambda convention.
        if os.path.exists(os.path.join(directory,'pwsmetadata.json')):
            metadata = json.load(open(os.path.join(directory,'pwsmetadata.json'),'r'))
        else:
            try:
                metadata = json.loads(tif.pages[0].description)
            except:
                metadata = json.loads(tif.imagej_metadata['Info']) #The micromanager saves metadata as the info property of the imagej imageplus object.
        return cls(data,metadata)
        
    def toOldPWS(self,directory):
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        info2 = {'info2':np.array([m['wavelengths'][0],0,m['wavelengths'][-1],m['exposure'],0,0,0,0,0,0], dtype=object)}

        try:
            info3 = {'info3':np.array([m['systemId'],m['exposure'],m['imgHeight'],m['imgWidth'],0,0,0,0,0,0,0,0], dtype=object)} #the old way
        except:
            info3 = {'info3':np.array([m['system'],m['exposure'],self.data.shape[0],self.data.shape[1],0,0,0,0,0,0,0,0], dtype=object)}    #The new way
        wv = {"WV":[float(i) for i in m['wavelengths']]}
        savemat(os.path.join(directory,'info2'),info2)
        savemat(os.path.join(directory,'info3'),info3)
        savemat(os.path.join(directory,'WV'),wv)
        imbd = self.data[:,:,self.data.shape[-1]//2]
        savemat(os.path.join(directory,'image_bd'),{'image_bd':imbd})
        nimbd = imbd-np.percentile(imbd,0.01) #.01 percent saturation
        nimbd = nimbd/np.percentile(nimbd,99.99)
        nimbd = (nimbd*255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory,'image_bd.tif'))
        im.save(nimbd)
        im.close()
        with open(os.path.join(directory,'image_cube'),'wb') as f:
            f.write(self.data.astype(np.uint16).tobytes(order='F'))
            
    def compress(self,outpath):
        im = self.data #3d array of pixel data
        im = im.astype(np.int32)   #convert to signed integer to avoid overflow during processing.
        mins = []   #A list to store the minimum value offsets of each of secondary frames.
        for i in range(im.shape[-1]-1,0,-1): #The first image is unchanged. the rest are expressed as the difference between themselves and the frame before them.
            im[:,:,i] = im[:,:,i] - im[:,:,i-1]   #Subtract the image from the frame before it.
            mins.append(im[:,:,i].min())    #record the new minimum value
            im[:,:,i] -= mins[-1]   #Subtract by the minimum. this ensures that the minimum is 0. If it was negative we would have an issue saving as uint8
        mins = mins[::-1]   #reverse the list to go back to forward order
        metadata = self.metadata
        metadata["compressionMins"] = [int(i) for i in mins] #This is needed for json compatability
        with open(outpath,'wb') as f:
            w=tf.TiffWriter(f)
            w.save(np.rollaxis(im.astype(np.uint16),-1,0),metadata = metadata, compress = 1)
            w.close()
    
    @classmethod
    def decompress(cls,inpath):
        with open(inpath,'rb') as f:
            t = tf.TiffFile(f)
            im = np.rollaxis(t.asarray(),0,3)
            md = json.loads(t.pages[0].tags['ImageDescription'].value)
        mins = md["compressionMins"]
        del md["compressionMins"]
        for i in range(1,im.shape[-1]):
            im[:,:,i] = im[:,:,i] + mins[i-1] + im[:,:,i-1]
        return cls(im,md)
    
    def plotMean(self):
        fig,ax = plt.subplots()
        mean = np.mean(self.data,axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax = ax)
        return fig,ax
        
    def toHyperspy(self):
        import hyperspy.api as hs
        return hs.signals.Signal1D(self.data)
    
    def normalizeByExposure(self):
        if not self._hasBeenNormalized:
            self.data = self.data / self.metadata['exposure']
        else:
            raise Exception("The ImCube has already been normalized by exposure.")
        self._hasBeenNormalized = True
    
    def subtractDarkCounts(self,count, binning:int = None):
        #Subtracts the darkcounts from the data. count is darkcounts per pixel. binning should be specified if it wasn't saved in the micromanager metadata.
        if binning is None:
            try:
                binning = self.metadata['MicroManagerMetadata']['Binning']
                if isinstance(binning, dict): #This is due to a property map change from beta to gamma
                    binning = binning['scalar']
            except:
                print('Micromanager binning data not found. Assuming no binning.')
                binning = 1
        count = count * binning**2    #Account for the fact that binning multiplies the darkcount.
        self.data = self.data - count

    def getMeanSpectra(self,mask = None):
        if mask is None:
            mask = np.ones(self.data.shape[:-1], dtype=np.bool)
        mean = self.data[mask].mean(axis=0)
        std = self.data[mask].std(axis=0)
        return mean,std
    
    def selectROI(self,xSlice = None,ySlice = None):
        #X and Y slice allow manual selection of the range.
        mask = np.zeros((self.data.shape[0],self.data.shape[1]),dtype=np.bool)
        if (xSlice is not None) and (ySlice is not None):
            if not hasattr(xSlice,'__iter__'):
                xSlice = (xSlice,)
            if not hasattr(ySlice,'__iter__'):
                ySlice = (ySlice,) 
            xSlice = slice(*xSlice)
            ySlice = slice(*ySlice)
            mask[ySlice,xSlice] = True
        else:
#            try:
#                assert typ =='rect' or typ == 'lasso'
#            except:
#                raise TypeError("A valid ROI type was not indicated. please use 'rect' or 'lasso'.")
            fig,ax = self.plotMean()
            fig.suptitle("1 for lasso, 2 for rectangle.\nClose to accept ROI")
            x,y = np.meshgrid(np.arange(self.data.shape[0]),np.arange(self.data.shape[1]))
            coords = np.vstack((y.flatten(),x.flatten())).T
            mask = np.zeros((self.data.shape[0],self.data.shape[1]),dtype=np.bool)
            

            def onSelect(verts):
                p = path.Path(verts)
                ind = p.contains_points(coords,radius=0)
                mask[coords[ind,1],coords[ind,0]] = True
            def rectSelect(mins,maxes):
                y = [int(mins.ydata),int(maxes.ydata)]
                x = [int(mins.xdata),int(maxes.xdata)]
                mask[min(y):max(y),min(x):max(x)] = True
                
            l = widgets.LassoSelector(ax,onSelect)
            r = widgets.RectangleSelector(ax,rectSelect)
            r.set_active(False)
            def onPress(event):
                k = event.key.lower()
                if k == '1': #Activate the lasso
                    r.set_active(False)
                    l.set_active(True)
                    
                elif k == '2': #activate the rectancle
                    l.set_active(False)
                    r.set_active(True)

            fig.canvas.mpl_connect('key_press_event',onPress)
            while plt.fignum_exists(fig.number):
                fig.canvas.flush_events()
        return mask
             
    def correctCameraNonlinearity(self,polynomials:typing.List[float]):
        #Apply a polynomial to the data where x is the original data and y is the data after correction.
        cfactor = np.polynomial.polynomial.polyval(self.data, polynomials) #The polynomials tell us a correction factor
        self.data = self.data / cfactor#Dividing the original data by the correction factor gives us linearized data.
        
    def __getitem__(self,slic):
        return self.data[slic]
    
    def _wavelengthsMatch(self, other:ImCube) -> bool:
        return self.wavelengths == other.wavelengths
    
    def __add__(self, other:ImCube) -> ImCube:
        if not self._wavelengthsMatch(other):
            raise ValueError("Imcube wavelengths are not compatible")
        return ImCube(self.data + other.data, self.metadata)

    def __sub__(self, other:ImCube) -> ImCube:
        if not self._wavelengthsMatch(other):
            raise ValueError("Imcube wavelengths are not compatible")
        return ImCube(self.data - other.data, self.metadata)
    
    def __mul__(self, other:ImCube) -> ImCube:
        if not self._wavelengthsMatch(other):
            raise ValueError("Imcube wavelengths are not compatible")
        return ImCube(self.data * other.data, self.metadata)
    
    def __truediv__(self, other:ImCube) -> ImCube:
        if not self._wavelengthsMatch(other):
            raise ValueError("Imcube wavelengths are not compatible")
        return ImCube(self.data / other.data, self.metadata)


    def wvIndex(self, start, stop):
        wv = np.array(self.wavelengths)
        iStart = np.argmin(np.abs(wv - start))
        iStop = np.argmin(np.abs(wv - stop))
        iStop += 1 #include the end point
        if iStop >= len(wv): #Include everything
            iStop = None
        print(iStop)
        md = self.metadata
        md['wavelengths'] = wv[iStart:iStop]
        return ImCube(self[:,:,iStart:iStop], md)
    
    
class KCube(ImCube):
    '''A class representing an ImCube after being transformed from being described in terms of wavelength in to wavenumber (k-space).'''
    def __init__(self, cube:ImCube):
        super().__init__(cube.data, cube.metadata)
        #Convert to wavenumber and reverse the order so we are ascending in order.
        wavenumbers = list((2*np.pi)/(np.array(self.wavelengths)*(1e-3)))[::-1]
        self.data = self.data[:,:,::-1]
        del self.wavelengths
        #Generate evenly spaced wavenumbers
#        dk = (self.wavenumbers[-1] - self.wavenumbers[0])/(len(self.wavenumbers)-1);
        evenWavenumbers = np.linspace(wavenumbers[0], wavenumbers[-1], num = len(wavenumbers))
        #Interpolate to the evenly spaced wavenumbers
        interpFunc = spi.interp1d(wavenumbers, self.data, kind='linear', axis=2)
        self.data = interpFunc(evenWavenumbers)
        self.wavenumbers = evenWavenumbers
    def getOpd(self, isHannWindow, indexOpdStop):
        fftSize = 2**(np.ceil(np.log2((2*len(self.wavenumbers))-1))) #%This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.

        if isHannWindow: #if hann window checkbox is selected, create hann window
            w = np.hanning(len(self.wavenumbers)) # Hann window for one vector
        else:
            w = np.ones((len(self.wavenumbers))) # Create unity window

        # Calculate the Fourier Transform of the signal multiplied by Hann window
        dataOpdPolysub = np.fft.fft(self.data * w[np.newaxis, np.newaxis, :], n=fftSize*2, axis=2)
    
        # Normalize the OPD by the quantity of wavelengths.
        dataOpdPolysub = dataOpdPolysub / len(self.wavenumbers)
        
        # by multiplying by Hann window we reduce the total power of signal. To account for that,
        dataOpdPolysub = np.abs(dataOpdPolysub / np.sqrt(np.mean(w**2)))
    
        # Isolate the desired values in the OPD.
        opd = dataOpdPolysub[:,:,:indexOpdStop]
    
        # Generate the xval for the current OPD.
        maxOpd = 2 * np.pi / (self.wavenumbers[1] - self.wavenumbers[0])
        dOpd = maxOpd / len(self.wavenumbers)
        xvalOpdPolysub = len(self.wavenumbers) / 2 * list(range(fftSize+2)) * dOpd / (fftSize+1);
        xvalOpdPolysub = xvalOpdPolysub[:indexOpdStop]
        return opd, xvalOpdPolysub
    
    def getAutoCorrelation(self,isAutocorrMinSub:bool, stopIndex:int):
        # The autocorrelation of a signal is the covariance of a signal with a
        # lagged version of itself, normalized so that the covariance at
        # zero-lag is equal to 1.0 (c[0] = 1.0).  The same process without
        # normalization is the autocovariance.
        #
        # A fast method for determining the autocovariance of a signal with
        # itself is to utilize fast-fourier transforms.  In this method, the
        # signal is converted to the frequency domain using fft.  The
        # frequency-domain signal is then convolved with itself.  The inverse
        # fft is performed on this self-convolution, yielding the
        # autocorrelation.
        #
        # In this instance, the autocorrelation is determined for a series of
        # lags, Z. Z is equal to [-P+1:P-1], where P is the quantity of
        # measurements in each signal (the quantity of wavenumbers).  Thus, the
        # quantity of lags is equal to (2*P)-1.  The fft process is fastest
        # when performed on signals with a length equal to a power of 2.  To
        # take advantage of this property, a Z-point fft is performed on the
        # signal, where Z is a number greater than (2*P)-1 that is also a power
        # of 2.
        fftSize = 2**(np.ceil(np.log2((2*len(self.wavenumbers))-1))) #This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.
        
        # Determine the fft for each signal.  The length of each signal's fft
        # will be fftSize.
        cubeFft = np.fft.fft(self.data, n=fftSize, axis=2)
        
        # Determine the ifft of the cubeFft.  The resulting ifft of each signal
        # will be of length fftSize.
        # NOTE: See the autocorrelation calculation in the Matlab function
        # "xcorr".
        cubeAutocorr = np.fft.ifft(np.abs(cubeFft)**2, axis=2) # This is the autocovariance.
        # Obtain only the lags desired.
        # Then, normalize each autocovariance so the value at zero-lags is 1.
        cubeAutocorr = cubeAutocorr[:,:,:len(self.wavenumbers)]
        cubeAutocorr /= cubeAutocorr[:,0]
        
        # In some instance, minimum subtraction is desired.  In this case,
        # determine the minimum of each signal and subtract that value from
        # each value in the signal.
        if isAutocorrMinSub:
            cubeAutocorr -= cubeAutocorr.min()
        
        # Convert the lags from units of indices to wavenumbers.
        lags = np.array(self.wavenumbers) - min(self.wavenumbers)
        
        # Square the lags. This is how it is in the paper. I'm not sure why though.
        lagsSquared = lags**2;
        
        # Before taking the log of the autocorrelation, zero values must be
        # modified to prevent outputs of "inf" or "-inf".
        cubeAutocorr[cubeAutocorr==0] = 1e-323
        
        # Obtain the log of the autocorrelation.
        cubeAutocorrLog = np.log(cubeAutocorr);

        # A first-order polynomial fit is determined between lagsSquared and
        # and cubeAutocorrLog.  This fit is to be performed only on the first
        # linear-portion of the lagsSquared vs. cubeAutocorrLog relationship.
        # The index of the last point to be used is indicated by stopIndex.
        lagsSquared = lagsSquared[:stopIndex]
        cubeAutocorrLog = cubeAutocorrLog[:,:,:stopIndex]
        
        # Determine the first-order polynomial fit for each cubeAutocorrLag.
        V = np.concatenate([np.ones(lagsSquared.shape), lagsSquared])
        M = np.matmul(V, np.linalg.pinv(V))
        cubeLinear = np.matmul(M, cubeAutocorrLog)
        cubeSlope  = (cubeLinear[1,:] - cubeLinear[0,:]) / (lagsSquared[1] - lagsSquared[0])
            
        ## -- Coefficient of Determination
        # Obtain the mean of the observed data
        meanObserved = cubeAutocorrLog.mean()
        # Obtain the regression sum of squares.
        ssReg = ((cubeLinear - meanObserved)**2).sum()
        # Obtain the residual sum of squares.
        ssErr = ((cubeAutocorrLog - cubeLinear)**2).sum()
        # Obtain the total sume of squares.
        ssTot = ssReg + ssErr
        # Obtain rSquared.
        rSquared = ssReg/ssTot
        
        return cubeSlope, rSquared
    
    @classmethod
    def loadAny(*args):
        raise NotImplementedError
    @classmethod
    def fromOldPWS(*args):
        raise NotImplementedError
    @classmethod
    def fromTiff(*args):
        raise NotImplementedError     
    def toOldPWS(*args):
        raise NotImplementedError       
    def compress(*args):
        raise NotImplementedError
    @classmethod
    def decompress(*args):
        raise NotImplementedError
    def wvIndex(*args):
        raise NotImplementedError
        