testData = linspace(0.001, 0.1);
stime = tic;
[estimate, exact] = SigmaToD(testData, 1, 0.55, 0.009);
ftime = toc(stime) % Execution time of the function.
