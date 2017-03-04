import os
import signal
import threading


class Console(threading.Thread):

    def __init__(self, nick_map, ip_map):
        threading.Thread.__init__(self, daemon=True)
        
        self.nick_map = nick_map
        self.ip_map = ip_map
        self.commands = {}
