from threading import Thread

class Console(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True

        self.commands = {}