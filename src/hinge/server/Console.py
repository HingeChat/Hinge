import os
import signal
import threading


class Console(threading.Thread):

    def __init__(self, client_manager):
        threading.Thread.__init__(self, daemon=True)
        self.client_manager = client_manager
        self.commands = {}
