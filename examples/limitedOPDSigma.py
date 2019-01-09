# -*- coding: utf-8 -*-
"""
Created on Tue Jan  8 10:07:20 2019

@author: backman05
"""

from pwspython import ImCube, KCube

path = r''
refName = 
resinName = 
cellNames = []
    
# identify the depth in um to which the OPD spectra need to be integrated
OPDintegral_end = 2.0 ##  in um
HannWindow = True #Should Hann windowing be applied to eliminate edge artifacts?

resin_OPD_subtraction = True
wvStart = 510     #start wavelength for poly subtraction
wvEnd = 690     # end wavelength for poly subtraction
poly_order = 0
wv_step = 2
RIsample = 1.545
SavePixelwiseRMS_OPDint = True
darkCount = 101
wv_step = 2

# Crop wavelength range
cube = cube.wvIndex(wvStart, wvEnd)
num_WVs_cut = len(cube.wavelengths)
cube = KCube(cube)

b,a = sps.butter(6, 0.1*wv_step) #The cutoff totally ignores what the `sample rate` is. so a 2nm interval image cube will be filtered differently than a 1nm interval cube. This is how it is in matlab.


zn = floor(num_WVs_cut/2)*linspace(0,1, lengthft/2+1)*2*pi/(khigh-klow); # OPD values, um
[~, integral_stop_ind] = min(abs(zn./2./RIsample-OPDintegral_end));

 ### load and save mirror or glass image cube
ref = ImCube.loadAny(os.path.join(path,refName))
ref.subtractDarkCounts(darkCount)
ref.normalizeByExposure()
    
if resin_OPD_subtraction
    ### load and save reference empty resin image cube
    resin = ImCube.loadAny(os.path.join(path,resinName))
    resin.subtractDarkCounts(darkCount)
    resin.normalizeByExposure()
    resin /= ref
     
    OPD_resin = resin.getOPD(isHannWindow, 100, mask)
   
#   access cell data
for cellName = cellNames               
    cube = ImCube.loadAny(os.path.join(path,cubeName))
    cube.subtractDarkCounts(darkCount)
    cube.normalizeByExposure()
    cube /= ref

    cube.data = sps.filtfilt(b,a,cube.data,axis=2)

    cube = KCube(cube)

    ## -- Polynomial Fit
    print("Subtracting Polynomial")
    polydata = cube.data.reshape((cube.data.shape[0]*cube.data.shape[1], cube.data.shape[2]))
    polydata = np.rollaxis(polydata,1) #Flatten the array to 2d and put the wavenumber axis first.
    cubePoly = np.zeros(polydata.shape)#make an empty array to hold the fit values.
    polydata = np.polyfit(cube.wavenumbers,polydata,orderPolyFit) #At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
    for i in range(orderPolyFit + 1):
        cubePoly += (np.array(cube.wavenumbers)[:,np.newaxis]**i) * polydata[i,:] #Populate cubePoly with the fit values.
    cubePoly = np.moveaxis(cubePoly, 0, 1)
    cubePoly = cubePoly.reshape(cube.data.shape) #reshape back to a cube.
    # Remove the polynomial fit from filtered cubeCell.
    cube.data = cube.data - cubePoly                                  

    # Find the fft for each signal in the desired wavelength range
    opdData = cube.getOpd(isHannWindow, 100, mask)
    
    opdData = opdData  - abs(OPD_resin) #why is this abs?

    RMS_data = np.sqrt(np.mean(cube.data**2, axis=2)) 
    RMS_OPDint_data   =   np.sqrt(np.abs(1/(2*np.pi)*np.sum(opdData[:,:,:integral_stop_ind],axis=2)**2))/2

    ### create a map of RMS_OPDint
    if (SavePixelwiseRMS_OPDint)
        cubeRMS = zeros(size(BW));
        cubeRmsResinOpdSub = zeros(size(BW));
        for i = 1:length(x)
            cubeRmsResinOpdSub(x(i), y(i)) = RMS_OPDint_data(i);
            cubeRMS(x(i), y(i)) = RMS_data(i);
        end
    end      
    
    if (SavePixelwiseRMS_OPDint)
        figure(cell),
        subplot(121),imagesc(cubeRMS(100:550,200:660),[0 0.08]),colorbar, axis image off, title('RMS');
        subplot(122),imagesc(abs(cubeRmsResinOpdSub(100:550,200:660)),[0 0.03]),colorbar,axis image off,title(['RMS from OPD below ',num2str(OPDintegral_end),'\mum, after resin OPD subtraction'])      
        colormap jet
        set(gcf, 'position',[100 100 1000 250])
        name = 'um_hann.mat';
        savefig(gcf,['Cell',num2str(cell),'_RMS_vs_RmsOpdInt_resinOPDsubtraction_',num2str(OPDintegral_end),'um_with_background_nohann.fig'])
    end # save RMS_OPDint maps in each cell directory?
end# cell num
        


