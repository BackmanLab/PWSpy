%% [d_estimate, d_exact] = SigmaToD(raw_rms, system_correction, NAi, noise, option)
%
% DESCRIPTION
%   This function will convert RMS values to D using one or two different
%   methods. This function requires acfd.m, acf_1.m and SigmaToD_coefs.mat
%   to function properly.
%
% INPUT ARGUMENTS
%   raw_rms: 
%       The rms values you with to convert (e.g., cubeRms).
%   system_correction: 
%       Optional input for the correction factor required to convert RMS to 
%       Sigma due to extra reflections in the microscope. The default is [2.43].
%   NAi:
%       Optional input for the illumination numerical aperture (NA) of the 
%       objective. The default is [0.55].
%   noise:
%       Optional input for the background noise in the system (i.e., RMS of
%       the glass). The default [0.009].
%   option:
%       Optional input to tell the function to only run the approximation 
%       method. Alternatively, the user can define this by limiting the 
%       output arguments. The default is [] and the alternative option is 
%       ['approximation only'] or ['approx'].
%
% OUTPUT ARGUMENTS
%   d_estimate:
%       This is an estimation of D calculated from Sigma. It's based on a
%       15th order polynomial fit of d_exact. No value of D yields error >0.1%.
%   d_exact:
%       Optional output for calculating more exact solution of D from Sigma. 
%       This calculation is based on derivations by Vadim Backman.
%
% EXAMPLES
%   [d_estimate, d_exact] = SigmaToD(0.1, [], [], 0.005 , 'approximation only')
%   [d_estimate, d_exact] = SigmaToD(cubeRms, 2, 0.45);
%   d_estimate = SigmaToD(cubeRms);
%
% REFERENCES
%   L. Cherkezyan, D. Zhang, H. Subramanian, I. Capoglu, A. Taflove, 
%   V. Backman, "Review of interferometric spectroscopy of scattered light 
%   for the quantification of subdiffractional structure of biomaterials."
%   J. of Biomedical Optics, 22(3), 030901 (2017).
%
%   
% Author: Adam Eshein (aeshein@u.northwestern.edu) 3.14.2019
%   Based on Mathematica code written by Vadim Backman (v-backman@northwestern.edu)
function [d_estimate, d_exact] = SigmaToD(raw_rms, system_correction, NAi, noise, option)
%% Adjust system params
if (nargin < 2) || isempty(system_correction)
    system_correction = 2.43; % This is the correction factor measured for LCPWS1. It's the default if input isn't supplied.
end

if (nargin < 3) || isempty(NAi)
    NAi = 0.55; % This is NAi measured for LCPWS1. It's the default if input isn't supplied.
end
if (nargin < 4) || isempty(noise)
    noise = 0.009; % This is the noise (RMS) of the glass measured on LCPWS1. It's the default if input isn't supplied.
end

% checking to see if we should calculate the slower exact solution.
if (nargout < 2) || ((nargin > 4) && (strcmp(option, 'approximation only') || strcmp(option, 'approx')))
    exact_option = 0;
% 		fprintf('\n\n Skipping exact D calculation \n\n');
else
    exact_option = 1;
end

%% Calculate D_size (linear)
sigma = real(sqrt(double(raw_rms).^2 - noise^2)) .* system_correction; % subtract noise and multiply by correction factor to get Sigma
d_size = sigma .* (13.8738 * NAi) + 1.473; % Convert Sigma to D_size 

%% Exact method (acf D)
if exact_option == 1
    mf = 1000000;
    
    d_size(d_size == 3) = 3.00001; % adjust D because of discontinuity 
    
    lmaxlminapprox = 100;
    correction = ((3-d_size) .* (1 - (lmaxlminapprox.^(-1.*d_size)))) ./ (d_size .* (1 - (lmaxlminapprox .^ (d_size-3)))); %correction to mass(D) because of using D_size
    mass = mf ./ correction ;
    
    d_exact = acfd(d_size, 1, mass.^(1./d_size)); % Calculate acf D
    d_exact = double(d_exact); % convert to double
    
else
    d_exact = [];
end

%% Estimation of D acf that's much quicker
coefs_struct = load('SigmaToD_coefs'); % load polynomial coefficients for estimation method.
d_estimate = polyval(coefs_struct.coefs, d_size);
if max(d_size(:)) >= 10
% 	fprintf('\n\n Warning: d_size exceeds recommended range for approximation model. Coercing values to 2.99 \n Ensure that normalization was processed correctly and correct system parameters are used. \n\n');
	d_estimate(d_size>10) = 2.99; % The fitting doesn't work well at very high values of D_size.
elseif max(d_size(:)) >= 6 % The fit still works at these high values of d_size, however it should be rare to have these very high values in chromatin.
% 	fprintf('\n\n Warning: Input RMS matrix includes high values with d_size >6. \n Ensure that normalization was processed correctly and correct system parameters are used. \n\n');
end

%% Test the approximation on a few values (5) just to make sure
if exact_option == 0 % only need to calculate this if we haven't already calculated it
    mf = 1000000;
    d_size(d_size == 3) = 3.00001;
    lmaxlminapprox = 100;
    correction = ((3-d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end])) .* (1 - (lmaxlminapprox.^(-1.*d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]))))) ./ (d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]) .* (1 - (lmaxlminapprox .^ (d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end])-3))));
    mass = mf ./ correction ;
    test_exact = acfd(d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]), 1, mass.^(1./d_size([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]))); % Calculate acf D
    test_exact = double(test_exact);
else
    test_exact = d_exact; %If we did already calculate d_exact values, then assign them to our test vector.
end

test_err = abs(test_exact([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end])-d_estimate([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]))./test_exact([1 ceil(end/4) ceil(end/2) ceil(end*3/4) end]); % calculate error
if sum(test_err > .01) > 0
    fprintf('\n\n Warning! Approximation method is >1%% different from the exact calculation method. Check the polynomial coeficients. \n\n')
end

end
