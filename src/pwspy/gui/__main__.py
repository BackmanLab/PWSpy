
def isIpython():
    try:
        return __IPYTHON__
    except:
        return False



if __name__ == '__main__':
    from pwspy.gui.analysis import PWSApp
    from PyQt5.QtWidgets import QApplication
    import sys

    if isIpython():
        app = PWSApp(sys.argv)
    else:
        print("Not Ipython")
        # app = QApplication(sys.argv)
        # ex = App()
        app = PWSApp(sys.argv)
        sys.exit(app.exec_())
