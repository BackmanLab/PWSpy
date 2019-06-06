%
% Scott Gladstein 4/11/2015
% Last updated on 11/20/2015
% Calculate RMS T map, no poly subtract, filtration, ect.
%


%Set parameters for code
clear all; clc;
% root='J:\Temporal Dynamics\Lamin\7-20-2016\Run 3\';
% root = 'F:\Temporal Dynamics\Fixation\';
% patList = {'8-14-2015'};
% folder = 'L:\K+ Fluorescence\2-16-2018\PWS\5uM control 1\';
% folder = 'J:\Temporal Dynamics\UV Exposure\Just UV and Controls\6-1-2016\UVC4\';
% folder = 'K:\Norma UV\11-14-2018\20 hours later\';
% patList={'UV1','UV3','UV4'};
% folder = 'J:\Temporal Dynamics\Fixation\8-14-2015\';
root = 'I:\Greta Stem Cell\Vasundhara\hmcs\iPSC_Cardio_1_5_19 (DONE)\';
patList = {'Cardiomyocytes', 'iPSCs'};
% 'UV1', 'UV2', 'UV3', 'UV4', 'UV5', 'UV6'};

% root = 'H:\IMR90_Prolif_Senescent_11_16_18 (Scott Code)\';
% patList = {'Prolif_CONTROL1_plated_11_15',...
%     'Prolif_CONTROL2_plated_11_15',...
%     'Prolif_CONTROL3_plated_11_15'...
%     'Senescent_IR1_plated_11_07',...
%     'Senescent_IR2_plated_11_07',...
%     'Senescent_IR3_plated_11_07'...
%     };

% mirrorfolder=folder;
cellNum = [1001:1015];%Cell numbers to analyze
% cellNum=[501];
mirrorNum=937;%mirror number to analyze

%old camera
% cSize=1024;
% darkCount=50;

%new camera
cSize=512;%size of image cube
darkCount = 1957;%set proper dark count subtraction

suffix='ps';%analysis suffix for saving

saveFold='Sigma Maps';
% displayRange=[0.011,0.027];
displayRange = [0.013,0.03];
% displayRange=[0.02,0.028];
frameAVG=0;%1 yes frame avg, 0 no frame avg
sizeAVG=3;

for f=1:length(patList)
    folder=[root,patList{f},'\'];
    %Loop through all cell folders
    for i=1:length(cellNum)
        %     i
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
            cellCube = (double(image_cube)-darkCount)./info3(2);
            clear image_cube;
            
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
            
            %Normalize Data
            load([folder,'Cell',num2str(mirrorNum),'\info3']);
            image_cube = (double(image_cube)-darkCount)./info3(2);
            image_cube = cellCube./image_cube;
            clear cellCube;
            
            if frameAVG
                %Frame Averaging
                new_cube=image_cube;
                for n=1:size(image_cube,3)
                    if n-sizeAVG<1
                        new_cube(:,:,n)=mean(image_cube(:,:,1:n+sizeAVG),3);
                    elseif n+sizeAVG>size(image_cube,3)
                        new_cube(:,:,n)=mean(image_cube(:,:,n-sizeAVG:end),3);
                    else
                        new_cube(:,:,n)=mean(image_cube(:,:,n-sizeAVG:n+sizeAVG),3);
                    end
                end
                image_cube=new_cube;
                clear new_cube;
            end
            
            %Mean Subtactions
            image_cube = image_cube - repmat(mean(image_cube,3),1,1,size(image_cube,3));
            
            
            %         % SUBSAMPLING
%                     rmsWidth=20;
%                     for z=1:size(image_cube,3)/rmsWidth
%             % %         figure;
%                     rmsMap=medfilt2(rms(image_cube(:,:,(z-1)*rmsWidth+1:(z-1)*rmsWidth+rmsWidth),3));
%             % %          rmsMap=rms(image_cube(:,:,(z-1)*rmsWidth+1:(z-1)*rmsWidth+rmsWidth),3);
%                     img = mat2gray(rmsMap,[.01,.015]);
%                         [img, ~] = gray2ind(img);
%             RGB = ind2rgb(img, jet);
%             %         colormap(jet);
%                     imwrite(RGB, [folder,'SubSampleFrames\',num2str(cellNum(i)),'_',num2str(z),'.tiff'], 'tiff');
%                     end
            %          % SUBSAMPLING
            
            
            %         test=rms(image_cube(:,:,(z-1)*rmsWidth+1:(z-1)*rmsWidth+rmsWidth),3);
            %         imagesc(medfilt2(test),[0.010,0.015]);
            %
            %         imagesc(rms(image_cube,3),[0.01,0.015]);
            
            
            %calculate RMS T
            rmsMap=rms(image_cube,3);
            % rmsMap=rms(image_cube(:,:,2:end),3);
            
            %Save Data
            cd([folder,'Cell',num2str(cellNum(i))]);
            save([folder,'Cell',num2str(cellNum(i)),'\RMS_T_Poly0_',suffix,'.mat'],'rmsMap');
            
            %Display map
            %         map=figure;
            %         imagesc(rmsMap,displayRange);
            %         colormap(jet);
            %         cd ..;
            %            print(map, '-dtiff', ['Cell',num2str(cellNum(i)),'_rmsMap.tif']);
            %         cellNum(i)
            
            mkdir([folder,saveFold,'\']);
            img = mat2gray(rmsMap,displayRange);
            [img, ~] = gray2ind(img);
            RGB = ind2rgb(img, jet);
            %         colormap(jet);
            imwrite(RGB,[folder,saveFold,'\',num2str(cellNum(i)),'.tiff'], 'tiff');
        end
    end
end

