import socket
import sys

from src.hinge.server.Console import Console
from src.hinge.server.ClientManager import ClientManager
from src.hinge.server.HingeClient import HingeClient
from src.hinge.network.Message import Message
from src.hinge.network.sock import Socket


class TURNServer(object):

    def __init__(self, listen_port, show_console=True):
        self.listen_port = listen_port
        self.show_console = show_console
        self.client_manager = ClientManager()

    def openLog(self):
        try:
            self.log_file = open('hingechat.log', 'a')
        except:
            self.log_file = None
            self.notify("Error opening logfile")

    def log(self, message):
        if self.log_file is not None:
            self.log_file.write('%s\n' % message)
            self.log_file.flush()
        else:
            pass

    def notify(self, message):
        if self.show_console:
            sys.stdout.write("\b\b\b%s\n>> " % message)
            sys.stdout.flush()
        else:
            pass
        self.log(message)

    def start(self):
        self.openLog()
        self.server_sock = self.startServer()
        while True:
            # Wait for client to connect
            (client_sock, client_addr) = self.server_sock.accept()
            # Wrap the socket in our socket object
            client_sock = Socket(client_addr, client_sock)
            # Store client's IP and port
            self.notify("Got connection: %s" % str(client_sock))
            self.client_manager.add(HingeClient(self, client_sock))

    def startServer(self):
        self.notify("Starting server...")
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('0.0.0.0', self.listen_port))
            server_sock.listen(10)
            return server_sock
        except NetworkError as ne:
            self.notify("Failed to start server")
            sys.exit(1)

    def stop(self):
        self.notify("Requested to stop server")
        # Pulse shutdown
        message = Message(COMMAND_END, error=ERR_SERVER_SHUTDOWN)
        for client in self.client_manager.clients:
            message.route = (0, client.id)
            client.send(message)
        # Pause to ensure message has been received
        time.sleep(0.25)
        # Close log
        if log_file is not None:
            log_file.close()
        else:
            pass
