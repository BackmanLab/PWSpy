function fun=gamma_incomplete(x,a)
% GAMMA_INCOMPLETE evaluates the upper incomplete gamma function 
% (incomplete gamma function of the second kind) $\Gamma(a,x)$ 
% at non-negative values of the argument. This function extends the 
% MATLAB function gammainc to negative values of the parameter a.
% 
%  SYNOPSIS:  fun=gamma_incomplete(x,a)
%            
% 
%  INPUT  x       : function argument
%         a       : parameter
% 
%  OUTPUT fun     : a vector of the same length as x; it contains NaN values 
%  at places where elements of x are negative.
% %  
% %  REMARK This function extends the MATLAB function gammainc 
% %  to negative values of the parameter a.
% %  
% %  EXAMPLES
% %
% %     x=0.01:0.01:8;
% %     f=gamma_incomplete(x,1);
% %     plot(x,f);
% %  
% % 
% %     x=0.001:0.001:.1;
% %     f=gamma_incomplete(x,-2.3);
% %     plot(x,f);
% % 
% % 
% %     x=0.001:0.001:.2;
% %     f=gamma_incomplete(x,-1);
% %     plot(x,f);
%     
% p=find(x>=0);
% q=find(x<0);
% f = gamma_inc(a,x(p));
% fun(p)=f;
% fun(q)=NaN;
% function res=gamma_inc(a,x)
% if a==0
%     res= expint(x);    
% end
fun = zeros(size(a)) .*NaN;
% if a>0
    
    fun(a>0)=gamma(a(a>0)).*gammainc(x(a>0),a(a>0),'upper');
% end
   
% if a<0
    
%     gamma(a+1).*gammainc(x,a+1,'upper')
    
    fun(a<0)=(gamma(a(a<0)+1).*gammainc(x(a<0),a(a<0)+1,'upper')-x(a<0).^a(a<0).*exp(-x(a<0)))./a(a<0);
    
% end