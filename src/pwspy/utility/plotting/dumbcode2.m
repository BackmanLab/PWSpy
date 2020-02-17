%% out = dumbcode(cell_folder_path, analysis_prefix, roi_suffix, roi_numbers, limits, scale_bg, nuc_power_scale, scale_bar_nmperpixel,  save_option)
function out = dumbcode2(cell_folder_path, analysis_prefix, roi_suffix, roi_numbers, limits, scale_bg, nuc_power_scale, scale_bar_nmperpixel,  save_option)
if nargin<7
    nuc_power_scale = 1;
end

if nargin<8
    scale_bar_nmperpixel = 0;
end

if nargin<9
    save_option = 0;
end

%load analysis
cubeRms = h5read([cell_folder_path '\PWS\analyses\analysisResults_' analysis_prefix '.h5'],'/rms');
    
% load rois
for ii = 1:length(roi_numbers)
    hinfo = hdf5info([cell_folder_path '\ROI_' roi_suffix '.h5']);
    BW = hdf5read(hinfo.GroupHierarchy.Groups(ii).Datasets(1));
    maps(:,:,ii) = BW;
end

map = sum(maps,3)>0; % make a 2d map

% scale and process rms cube (this is probably not the best way to do it)
cubeRms = cubeRms-limits(1);
cubeRms(cubeRms<0) = 0;
cubeRms(cubeRms>(limits(2)-limits(1))) = limits(2)-limits(1);
cubeRms = cubeRms.^nuc_power_scale;
cubeRms = cubeRms * 1/((limits(2)-limits(1)).^nuc_power_scale); % normalize image so maximum value is 1

% make the nucs red and everything else gray scale
out = zeros(size(cubeRms,1), size(cubeRms,2), 3);
out(:,:,:) = repmat(cubeRms, [1 1 3])*scale_bg;
out(:,:,:) = out(:,:,:) .* repmat(~map, [1 1 3]);
out(:,:,1) = out(:,:,1) + (map .* cubeRms);

if (scale_bar_nmperpixel > 0)
    out(round(length(out)*.965):round(length(out)*.975), round(length(out)*.03):round(length(out)*.03+scale_bar_nmperpixel), :) = 1;
end

if (save_option == 1) || strcmp(save_option, 'save') || strcmp(save_option, 'yes')
    imwrite(out,['PWSimage_' num2str(sum(clock .* [12*30.4375*24*60*60 30.4375*24*60*60 24*60*60 60*60 60 1])) '.jpg'],'jpg')
end

figure;
set(gcf,'color','w');
imshow(out)
hold on
