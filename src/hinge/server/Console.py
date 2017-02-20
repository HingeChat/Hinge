import os
import signal

from threading import Thread

class Console(Thread):
    def __init__(self, nickMap, ipMap):
        Thread.__init__(self)

        self.nickMap = nickMap
        self.ipMap = ipMap

        self.daemon = True

        self.commands = {}