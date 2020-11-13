from pwspy.apps.CalibrationSuite.analyzer import ITOAnalyzer
import os

if __name__ == '__main__':
    directory = r'\\BackmanLabNAS\home\Year3\ITOPositionStability\AppTest'
    app = ITOAnalyzer(directory, os.path.join(directory, '10_20_2020'))
    a = 1