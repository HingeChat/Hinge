import queue
import socket
import sys
import time
import threading

from src.hinge.network import HingeObject
from src.hinge.server.Console import Console
from src.hinge.network.Message import Message
from src.hinge.network.sock import Socket
from src.hinge.utils import *


nick_map = {}
ip_map = {}
quiet = False


def log(message):
    if log_file is not None:
        log_file.write('%s\n' % message)
        log_file.flush()


def printAndLog(message):
    if quiet:
        sys.stdout.write("\b\b\b%s\n>> " % message)
        sys.stdout.flush()
    log(message)


class TURNServer(object):

    def __init__(self, listen_port, show_console=True):
        self.listen_port = listen_port

        global quiet
        quiet = show_console

    def start(self):
        self.openLog()
        self.server_sock = self.startServer()

        while True:
            # Wait for client to connect
            (client_sock, client_addr) = self.server_sock.accept()
            # Wrap the socket in our socket object
            client_sock = Socket(client_addr, client_sock)
            # Store client's IP and port
            printAndLog("Got connection: %s" % str(client_sock))
            ip_map[str(client_sock)] = Client(client_sock)

    def startServer(self):
        printAndLog("Starting server...")
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('0.0.0.0', self.listen_port))
            server_sock.listen(10)
            return server_sock
        except NetworkError as ne:
            printAndLog("Failed to start server")
            sys.exit(1)

    def stop(self):
        printAndLog("Requested to stop server")
        for nick, client in nick_map.items():
            client.send(Message(**{
                'command': COMMAND_END,
                'route': (0, nick),
                'error': ERR_SERVER_SHUTDOWN,
            }))

        time.sleep(0.25)

        if log_file is not None:
            log_file.close()

    def openLog(self):
        global log_file
        try:
            log_file = open('hingechat.log', 'a')
        except:
            log_file = None
            print("Error opening logfile")


class Client(HingeObject.HingeObject):

    def __init__(self, sock):
        HingeObject.HingeObject.__init__(self)

        self.sock = sock
        self.nick = None

        self.send_thread = SendThread(sock)
        self.recv_thread = RecvThread(self, sock)

        self.send_thread.start()
        self.recv_thread.start()

    def send(self, message):
        self.send_thread.queue.put(message)

    def registerNick(self, nick):
        self.__nickRegistered(nick)

    def __nickRegistered(self, nick):
        printAndLog("%s -> %s" % (str(self.sock), nick))
        self.nick = nick
        nick_map[nick] = self
        try:
            del ip_map[str(self.sock)]
        except KeyError:
            pass

    def disconnect(self):
        self.sock.disconnect()
        del nick_map[self.nick]

    def kick(self):
        self.send(Message(**{
            'command': COMMAND_ERR,
            'route': (0, self.id),
            'error': ERR_KICKED,
        }))
        time.sleep(0.25)
        self.disconnect()


class SendThread(threading.Thread):

    def __init__(self, sock):
        threading.Thread.__init__(self, daemon=True)
        self.sock = sock
        self.queue = queue.Queue()

    def run(self):
        while True:
            message = self.queue.get()
            try:
                self.sock.send(str(message))
            except Exception as e:
                nick = message.route
                printAndLog("%s: error sending data to: %s" % (nick, str(e)))
                nick_map[nick].disconnect()
                return
            finally:
                self.queue.task_done()


class RecvThread(threading.Thread):

    def __init__(self, client, sock):
        threading.Thread.__init__(self, daemon=True)
        self.sock = sock
        self.client = client
        self.nick_registered_callback = client.registerNick

    def run(self):
        # The client should send the protocol version its using first
        try:
            message = Message.createFromJSON(self.sock.recv())
        except KeyError:
            printAndLog("%s: sent a command with missing JSON fields" % self.sock)
            self.__handleError(ERR_INVALID_COMMAND)
            return

        # Check that the client sent the version command
        if message.command != COMMAND_VERSION:
            printAndLog("%s: did not send version command" % self.sock)
            self.__handleError(ERR_INVALID_COMMAND)
            return

        # Check the protocol versions match
        if message.data != PROTOCOL_VERSION:
            printAndLog("%s: is using a mismatched protocol version" % self.sock)
            self.__handleError(ERR_PROTOCOL_VERSION_MISMATCH)
            return

        # The client should then register a nick
        try:
            message = Message.createFromJSON(self.sock.recv())
        except KeyError:
            printAndLog("%s: send a command with missing JSON fields" % self.sock)
            self.__handleError(ERR_INVALID_COMMAND)
            return

        # Check that the client sent the register command
        if message.command != COMMAND_REGISTER:
            printAndLog("%s: did not register a nick" % self.sock)
            self.__handleError(ERR_INVALID_COMMAND)
            return

        # Check that the nick is valid
        self.client.updateId(message.route[0])
        self.client.nick = message.data
        if isValidNick(self.client.nick) != VALID_NICK:
            printAndLog("%s: tried to register an invalid nick" % self.sock)
            self.__handleError(errors.ERR_INVALID_NICK)
            return

        # Check that the nick is not already in use
        self.client.nick = self.client.nick.lower()
        if self.client.nick in nick_map:
            printAndLog("%s: tried to register an in-use nick" % self.sock)
            self.__handleError(ERR_NICK_IN_USE)
            return

        self.nick_registered_callback(self.client.nick)

        while True:
            try:
                try:
                    message = Message.createFromJSON(self.sock.recv())
                except KeyError:
                    printAndLog("%s: send a command with missing JSON fields" % self.sock)
                    self.__handleError(ERR_INVALID_COMMAND)
                    return

                if message.command == COMMAND_END:
                    printAndLog("%s: requested to end connection" % self.client.nick)
                    nick_map[self.client.nick].disconnect()
                    self.client.id_map.remove(self.client)
                    return
                elif message.command == COMMAND_GET_ID:
                    nick = message.data
                    id = nick_map[nick].id

                    message.data = id
                    message.command = COMMAND_SEND_ID
                    message.route = (0, self.client.nick)
                    self.client.send(message)
                    return
                elif message.command != COMMAND_RELAY:
                    printAndLog("%s: sent invalid command" % self.client.nick)
                    self.__handleError(ERR_INVALID_COMMAND)
                    return

                try:
                    nick = self.client.id_map.get(message.route[1]).nick
                    if isValidNick(nick) != VALID_NICK:
                        printAndLog("%s: requested to send message to invalid nick" % self.client.nick)
                        self.__handleError(ERR_INVALID_NICK)

                    client = nick_map[nick.lower()]
                    message.route = (nick, self.nick)
                    client.send(message)
                except KeyError:
                    pass
            except Exception as e:
                if hasattr(e, 'errno') and e.errno != ERR_CLOSED_CONNECTION:
                    printAndLog("%s: error receiving from: %s" % (self.client.nick, str(e)))
                if self.client.nick in nick_map:
                    nick_map[self.client.nick].disconnect()
                return

    def __handleError(self, error_code):
        self.sock.send(str(Message(**{
            'command': COMMAND_ERR,
            'error': error_code,
        })))
        self.sock.disconnect()

        try:
            del ip_map[str(self.sock)]
            return
        except:
            pass

        try:
            del nick_map[self.client.nick]
        except:
            pass
