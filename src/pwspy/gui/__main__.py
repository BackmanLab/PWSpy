
def isIpython():
    try:
        return __IPYTHON__
    except:
        return False



if __name__ == '__main__':
    from pwspy.gui.analysis import App
    from PyQt5.QtWidgets import QApplication
    import sys

    if isIpython():
        app = App()
    else:
        print("Not Ipython")
        app = QApplication(sys.argv)
        ex = App()
        sys.exit(app.exec_())
