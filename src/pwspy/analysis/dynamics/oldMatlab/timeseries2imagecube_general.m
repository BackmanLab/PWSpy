   %
% Scott Gladstein 4-6-2015
% Last Updated on 11-20-2015
%
% Create reference image cubes for time series data
%

folder = 'I:\Greta Stem Cell\Vasundhara\hmcs\iPSC_Cardio_1_5_19 (DONE)\Cardiomyocytes\'; % path to folder (include '\' at end)
mirrorNum = 1997; % reference cube to use as base for single wv reference
mirrorSaveNum = 937;% number to save new reference, 931 is default
cSize=512;%size of image cube

cd([folder,'Cell',num2str(mirrorNum)]);
if exist('image_cube.mat','file')
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

%Time average reference cube
mirrorFrame = squeeze(mean(image_cube(1:cSize,1:cSize,:),3));

%preallocate matrix for cube
image_cube=zeros(cSize,cSize,numWVs);

%fill image image cube
for j=1:201
    image_cube(1:cSize,1:cSize,j)= mirrorFrame;
end

%create folder and save data
cd(folder);
mkdir(['Cell',num2str(mirrorSaveNum)]);
cd([folder,'Cell',num2str(mirrorSaveNum)]);
image_cube=uint16(image_cube);
save('image_cube.mat','image_cube');
copyfile([folder,'Cell',num2str(mirrorNum),'\info3.mat'],[folder,'Cell',num2str(mirrorSaveNum),'\info3.mat']);
copyfile([folder,'Cell',num2str(mirrorNum),'\WV.mat'],[folder,'Cell',num2str(mirrorSaveNum),'\WV.mat']);
