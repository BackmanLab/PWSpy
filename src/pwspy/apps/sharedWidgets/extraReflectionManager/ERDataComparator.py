from pwspy.apps.sharedWidgets.extraReflectionManager import ERDataDirectory, EROnlineDirectory


class ERDataComparator:
    def __init__(self, local: ERDataDirectory, online: EROnlineDirectory):
        self.local = local
        self.online = online