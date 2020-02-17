function out = acfd(d, lmin, lmax)

delta = 0.1;

out = 3 + (log(acf_1(d, lmin, lmax, (lmax+lmin)./100 + delta)) - ...
    log(acf_1(d, lmin, lmax, (lmax+lmin)./100)))./ ...
    (log((lmax+lmin)./100 + delta) - log((lmax+lmin)./100));
end
