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

# find a clean spot (100x100 pix) in the empty resin data and
# enter the ROI coordinates in lines 119 (small NA empty resin) and 121
#(large NA empty resin)
    
# identify the depth in um to which the OPD spectra need to be integrated
OPDintegral_end = 2.0; ##  in um
HannWindow = true; #Should Hann windowing be applied to eliminate edge artifacts?

# should all pixels be analyze or only the center portion (choose the
# latter only if you have memory limitations on your PC)
fullFOV = true;

resin_OPD_subtraction = true;
wvStart = 510;     #start wavelength for poly subtraction
wvEnd = 690;     # end wavelength for poly subtraction
poly_order = 0;
wv_step = 2;
RIsample = 1.545;
SavePixelwiseRMS_OPDint = true;
darkCount = 101;




# Crop wavelength range
cube = cube.wvIndex(wvStart, wvEnd)
num_WVs_cut = len(cube.wavelengths)
cube = KCube(cube)

###  filter parameters
[b,a] = butter(6,.1*wv_step);#
filter_order = wv_step;

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

    resin_spectrum = squeeze(mean(mean(resin_cube(300:400,450:550,indx_wv_start:indx_wv_stop),1),2));
     
    OPD_resin = resin.getOPD(True, 100)
    #Need to add the ability to get a single opd from a mask.
    OPD_resin = fft(w.*(resin_spectrum - mean(resin_spectrum)), lengthft,1)/(num_WVs_cut); #wavelength/k, pixel
    OPD_resin = abs(OPD_resin(1:integral_stop_ind))./sqrt(mean(w.^2)); # relative power of OPD components at values zn (cut the range of considered OPDs); take into account power loss after windowing
end
   
#   access cell data
for cellName = cellNames               
    cube = ImCube.loadAny(os.path.join(path,cubeName))
    cube.subtractDarkCounts(darkCount)
    cube.normalizeByExposure()
    cube /= ref

    if fullFOV
        BW = ones(size(norm_cube,1),size(norm_cube,2));
    else
        BW = zeros(size(norm_cube,1),size(norm_cube,2));
        BW(100:550,200:660) = 1;
    end
    size_BW = size(BW);
    BW_indx = find(BW);
    num_pos = length(BW_indx);
    [x, y] = ind2sub(size_BW, BW_indx);
    cell_data = zeros(num_pos,length(WVnum));

    for i = 1:length(x)
        cell_data(i,:) = norm_cube(x(i),y(i),indx_wv_start:indx_wv_stop);  # AOTF data cubes (y,x,lambda)
    end

    filtered_data = filtfilt(b,a,cell_data(:,:)');

    # Interpolate the data to obtain measures at the wavenumbers in the
    # evenly spaced k-space array.                
    filtered_data_k  = (interp1q(WVnum',filtered_data(:,end:-1:1)',WVnum_even))';
#                 check conversion: 

   filtered_data    = filtered_data_k;
## Poly subtracted data
    # Create Vandermonde matrix, V
    V = bsxfun(@power,(1:length(WVnum))',0:poly_order);
    # Calculate the multiplier-matrix, M, by matrix-multiplication of V with
    # the pseudo-inverse of V.
    M = V*pinv(V);
    # Obtain the polynomial fit by multiplying the reshaped cubeCell by M.
    Poly_fit = M*filtered_data';
    # Calculate the poly subtracted signal
    poly_data_k = filtered_data - Poly_fit';                                   

    # Find the fft for each signal in the desired wavelength range
         
    OPD_data = fft(repmat(w,1,size(poly_data_k,2)).*poly_data_k, lengthft,1)/(num_WVs_cut); #wavelength/k, pixel
    OPD_data = abs(OPD_data(1:integral_stop_ind,:))./sqrt(mean(w.^2)); # relative power of OPD components at values zn (cut the range of considered OPDs); take into account power loss after windowing
    
    OPD_data = OPD_data  - repmat(abs(OPD_resin),1,size(OPD_data,2));

    RMS_data = sqrt(mean(poly_data_k.^2,1));  
    RMS_OPDint_data   =   sqrt(abs(1./2./pi.*sum  (OPD_data(1:integral_stop_ind,:).^2,1)) )./2;

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
        


