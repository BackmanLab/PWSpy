These are matlab scripts used by Scott Gladstein to analyze dynamics data. The python dynamics analysis is based on these scripts.
My understanding is that they should be run in the following order:
    timeseries2imagecube_general: Average the reference image over time so the cube is static over time.
    RMS_T_General: Uses the output of `timeserie....` script to generate RMS_T saved in the cell folder as "Cellx_T_Poly0_ps.mat"
    autoCorr2019: Uses the output of `timeserie...` script to generate the autocorrelation and save as `xxxxx_Autocorr.mat`
    compileDynamics.m: Compiles the output of the other the `timeserie...` and `autoCorr2019` scripts. Note that RMS_t is calculated from the autocorrelation rather than using the output of the `RMS_t_general` script.
  
