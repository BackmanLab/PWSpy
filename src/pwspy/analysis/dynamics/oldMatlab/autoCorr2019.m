%
% Scott Gladstein 4/7/2015
% Updated: 3-14-2019
% calc autocorrelation for timeseries image cube
%

%%


%Set parameters for code
clear all; clc;

root = 'I:\Greta Stem Cell\Vasundhara\hmcs\iPSC_Cardio_1_5_19 (DONE)\';
patList = {'Cardiomyocytes', 'iPSCs'};
cellNum = [1001:1015]; % Cell numbers to analyze
mirrorNum = 937; % Flat Normalization cube
background=1997; % Temporal Background for noise subtraction
cellNum=[cellNum,background];

memorySave=8; % Parameter for memory save when calculating fft

bwName='nuc'; % ROI suffix
cSize=512; % Camera pixels (assumes square)
darkCount = 1957; % Camera Dark Counts

if mod(cSize,memorySave)~=0
    error('memorySave must be divisible by cSize');
end

for f=1:length(patList)
    folder=[root,patList{f},'\'];
    if exist(folder,'dir')
        
        % Load Normalization Data
        cd([folder,'Cell',num2str(mirrorNum)]);
        if exist([folder,'Cell',num2str(mirrorNum),'\image_cube.mat'],'file')
            %load mirror if data saved as mat file
            load('image_cube.mat');
        else
            %load mirror if data is saved as binary
            load('WV.mat');
            numWVs = length(WV);
            fid = fopen('image_cube','r');
            image_cube = fread(fid,[cSize, cSize*numWVs], '*uint16');
            fclose(fid);
            image_cube = reshape(image_cube,cSize,cSize,numWVs);
        end
        load([folder,'Cell',num2str(mirrorNum),'\info3']);
        mirror_cube = (double(image_cube)-darkCount)./info3(2);
        clear image_cube
        
        %Loop through all cell folders +1 for background
        for i=1:(length(cellNum))
            
            % Load Cell Data
            if exist([folder,'Cell',num2str(cellNum(i))],'dir')
                cd([folder,'Cell',num2str(cellNum(i))]);
                if exist([folder,'Cell',num2str(cellNum(i)),'\image_cube.mat'],'file')
                    %load cell if data saved as mat file
                    load('image_cube.mat');
                else
                    %load cell if data is saved as binary
                    load('WV.mat');
                    numWVs = length(WV);
                    fid = fopen('image_cube','r');
                    image_cube = fread(fid,[cSize, cSize*numWVs], '*uint16');
                    fclose(fid);
                    image_cube = reshape(image_cube,cSize,cSize,numWVs);
                end
                
                %load reference and image cube and normalize
                load([folder,'Cell',num2str(cellNum(i)),'\info3']);
                image_cube = (double(image_cube)-darkCount)./info3(2);
                
                %Normalize Data
                image_cube = image_cube./mirror_cube;
                
                %Mean Subtactions
                image_cube = image_cube - repmat(mean(image_cube,3),1,1,size(image_cube,3));
                
                %Look for ROIs
                bwDir=dir;
                indBW=regexp({bwDir.name},['BW.{1,2}_',bwName,'.mat']);
                bwList={bwDir(~cellfun('isempty',indBW)).name};
                
                % If Temporal Background for noise subtraction
                if i==length(cellNum)
                    %Randomly sample points of background to save space
                    sampleSize=30000;
                    BW=zeros(cSize,cSize);
                    randPositions=ceil(rand(2,sampleSize)*512);
                    for b=1:sampleSize
                        BW(randPositions(1,b),randPositions(2,b))=1;
                    end
                    save('BW1_fullFOV.mat','BW');
                    bwList={'BW1_fullFOV.mat'};
                end
                
                %Loop Through ROIs
                if ~isempty(bwList)          
                    for d = 1:length(bwList)
                     
                        % Select Spectra from ROI region
                        load (char(bwList(d)));
                        [x,y]=find(BW);
                        spectraList=zeros(length(x),size(image_cube,3));
                        for a=1:length(x)
                            spectraList(a,:)=image_cube(x(a),y(a),:);
                        end
                        
                        % Split up data into small chunks for FFT to save memory
                        while mod(length(x),memorySave)~=0
                            memorySave=memorySave-1;
                        end
                        memLength=(length(x)/memorySave);
                        for a=1:memorySave
                            F=fft(spectraList((a-1)*memLength+1:a*memLength,:),[],2);
                            spectraList((a-1)*memLength+1:a*memLength,:) = ifft(F.*conj(F),[],2)/size(F,2);
                        end
                        clear F;
                        
                        %truncate and normalize autocorr
                        truncLength=100;
                        spectraList = spectraList(:,1:truncLength);
                        sName=strsplit(char(bwList(d)),'.');
                        save([sName{1},'_Autocorr.mat'],'spectraList');
                    end
                end
            end         
        end   
    end
end
