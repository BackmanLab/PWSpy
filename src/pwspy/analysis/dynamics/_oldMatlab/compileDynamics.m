%
% Scott Gladstein Updated: 3-14-2019
%
% load saved autocorrelation files and analyze
%
% Data save into variable dataTempD
%  Exp Folder
%  Cell #
%  Diffusion
%  Sigma_t^2 (with background subtraction
%  Sigma_s
%  Ref

clear all; clc;

%Set parameters for code
root = 'I:\Greta Stem Cell\Vasundhara\hmcs\iPSC_Cardio_1_5_19 (DONE)\';
patList = {'Cardiomyocytes', 'iPSCs'};
cellNum = [1001:1015]; % Cell numbers to analyze
mirrorNum = 937; % Flat Normalization cube
background=1997; % Temporal Background for noise subtraction
bwName='nuc'; % ROI suffix
wavelength=0.550; %Wavelength used to aquire timedata
n_medium = 1.37; %RI of the media (avg RI of chromatin)
k = (n_medium*2*pi)/wavelength;

% Include Sigma (spectral) measurements set to 1
sigma=1;
if sigma
    sigmaCells = [1:15];
    sigmaName='p0';
end

% preallocate some variables
d_list_slp = zeros(length(patList), length(cellNum));
fileName=[bwName,'_Autocorr'];
dataAutocorr={};
dataDiff=cell(1,length(cellNum));

for f=1:length(patList)
    folder=[root,patList{f},'\'];
    dataTempD={'Cell #';'D';'Sigma_t^2 (b sub)';'Sigma_s';'Reflectance'};
    % Load the background autocorr for background subtraction
    if exist([folder,'Cell',num2str(background)],'dir')
        load([folder,'Cell',num2str(background),'\BW1_fullFOV_Autocorr.mat']);
        load([folder,'Cell',num2str(background),'\info3.mat']);
        xVals=[0:info3(2)*.001:99*info3(2)*.001];
        backgroundList=spectraList;
        meanBackground=mean(backgroundList);
        bLim=meanBackground(1);
    else
        error('No Background File');
    end
    
    % loop through cells
    d_slp_cell_list = zeros(1, 99);
    for i=1:(length(cellNum))
        if exist([folder,'Cell',num2str(cellNum(i))],'dir')
            cd([folder,'Cell',num2str(cellNum(i))]);
            
            %Look for ROIs
            bwDir=dir;
            indACF=regexp({bwDir.name},['BW.{1,2}_',fileName,'.mat']);
            indBW=regexp({bwDir.name},['BW.{1,2}_',bwName,'.mat']);
            ACFList={bwDir(~cellfun('isempty',indACF)).name};
            bwList={bwDir(~cellfun('isempty',indBW)).name};
            
            %Loop Through ROIs
            if ~isempty(ACFList)
                
                % Load sigma (spectral)
                if sigma
                    clear cubeRms;
                    load([folder,'Cell',num2str(sigmaCells(i)),'\',sigmaName,'_Rms.mat']);
                    load([folder,'Cell',num2str(sigmaCells(i)),'\',sigmaName,'_Reflectance.mat']);
                end
                
                % Loop through acf files to calculation D
                for d = 1:length(ACFList)
                    
                    % load autocorr for this roi
                    load (char(ACFList(d)));
                    
                    % background subtracted sigma_t^2
                    rmsT_sq=mean(spectraList(:,1))-meanBackground(1);
                    
                    % Remove pixels with low SNR
                    % Default threshold removes values where 1st point of acf is less than sqrt(2) of background acf
                    spectraList = spectraList(find(spectraList(:,1)>sqrt(2)*bLim), :);

                    % Background Subtraction
                    normBsCorr = spectraList-meanBackground;

                    % Normalization
                    normBsCorr = normBsCorr./squeeze(repmat(abs(normBsCorr(:,1)),1,1,size(normBsCorr, 2)));
                    
                    % Removed negative values for calculating natural log
                    list4 = normBsCorr;
                    list4(list4<0) = NaN;

                    % Calculate diffusion coefficients from first point of
                    % slope of ln(acf)
                    dt = (xVals(2)-xVals(1));
                    d_slope = -diff(nanmean(log(list4)))/(dt*4*k^2);
                    d_slope = d_slope(1);
                    
                    % Compile data
                    if sigma
                        load(char(bwList(d)));
                        dataTempD = cat(2,dataTempD,[{['Cell',num2str(cellNum(i)),'_',char(ACFList(d))]};num2cell(d_slope);num2cell(rmsT_sq);mean(cubeRms(BW));mean(cubeReflectance(BW))]); 
                    else
                        dataTempD = cat(2,dataTempD,[{['Cell',num2str(cellNum(i)),'_',char(ACFList(d))]};num2cell(d_slope);num2cell(rmsT_sq)]);
                    end
                end
            end
        end
    end
    
    dataDiff(size(dataDiff, 1) + 1, 1) = patList(f);
    dataDiff(size(dataDiff, 1) + 1:size(dataDiff, 1) + size(dataTempD, 1), 1 : size(dataTempD, 2)) = dataTempD;
end


% Can be used to arrange multiple rois in timeseries
%
% temp_data = dataDiff(2:8,:);
% temp_data = dataDiff(9:15,:);
% temp_data = dataDiff(16:22,:);
% temp_data = dataDiff(23:29,:);
% %
% num_bw = 6;
% num_parameters = size(temp_data,1);
% num_steps = 27;
% temp_data = temp_data(:,1:num_steps*num_bw);
% matrix=cell(num_bw*num_parameters, num_steps);
%
% for i = 1:num_bw
%     matrix(1+num_parameters*(i-1):num_parameters*i, :) = temp_data(:, i:num_bw:end);
% end

