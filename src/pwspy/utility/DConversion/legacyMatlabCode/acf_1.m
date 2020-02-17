function out = acf_1(d, lmin, lmax, x)

out = ((3-d) .* ((((lmin.^4) .* ((lmin./lmax).^(-1.*d)) .* vpa(expint(-2+d, sym(x./lmax))))./(lmax.^3))...
    - lmin .* vpa(expint(-2+d, sym(x./lmin))))) ./ (lmin.*(1 - (lmin./lmax).^(3-d)));

% r = x;
% out = (3-d).* r.^(d-3) ./ (lmin.^(d-3) - lmax.^(d-3)) .*  (gamma_incomplete(r./lmax,3-d) - gamma_incomplete(r./lmin, 3-d));

end