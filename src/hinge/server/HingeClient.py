import queue
import threading
import time

from src.hinge.network.Message import Message
from src.hinge.utils import *


class Connection(object):

    def __init__(self, manager, ip):
        self.manager = manager
        self.ip = ip
        self.id = hash(self)
        self.nick = None


class HingeClient(Connection):

    class SendThread(threading.Thread):

        def __init__(self, client):
            threading.Thread.__init__(self, daemon=True)
            self.client = client
            self.queue = queue.Queue()

        def run(self):
            while True:
                message = self.queue.get()
                try:
                    self.client.sock.send(str(message))
                except Exception as e:
                    self.server.notify("{0}: error sending data to {1}".format(*message.route))
                    self.client.disconnect()
                    return
                finally:
                    self.queue.task_done()

    class RecvThread(threading.Thread):

        def __init__(self, client):
            threading.Thread.__init__(self, daemon=True)
            self.client = client

        def __verifyClientConnection(self):
            # The client should send the protocol version
            try:
                message = Message.createFromJson(self.client.sock.recv())
            except KeyError:
                msg = "{0}: sent a command with missing JSON fields".format(self.client.id)
                self.exit(ERR_MALFORMED_MESSAGE, msg)
                return
            # Check that the client sent the version command
            if message.command != COMMAND_VERSION:
                msg = "{0}: did not send version command".format(self.client.id)
                self.exit(ERR_INVALID_COMMAND, msg)
                return
            # Check that the protocol version match
            if message.data != PROTOCOL_VERSION:
                msg = "{0}: is using a mismatched protocol version".format(self.client.id)
                self.exit(ERR_PROTOCOL_VERSION_MISMATCH, msg)
                return
            # The client should register a nick
            try:
                message = Message.createFromJson(self.client.sock.recv())
            except KeyError:
                msg = "{0}: sent a command with missing fields".format(self.client.id)
                self.exit(ERR_INVALID_COMMAND, msg)
                return
            # Check that the client sent the register command
            if message.command != COMMAND_REGISTER:
                msg = "{0}: did not register a nick".format(self.client.id)
                self.exit(ERR_INVALID_COMMAND, msg)
                return
            # Validate the nick
            if self.client.manager.isNickValid(message.data) != VALID_NICK:
                msg = "{0}: tried to register an invalid nick".format(self.client.id)
                self.exit(ERR_INVALID_NICK, msg)
                return
            elif self.client.manager.isNickRegistered(message.data):
                msg = "{0}: tried to register an existing nick".format(self.client.id)
                self.exit(ERR_NICK_IN_USE, msg)
                return
            else:
                self.client.registerNick(message.data)

        def __handleError(self, error_code, msg=None):
            msg = Message(COMMAND_ERR, error=error_code)
            self.client.sock.send(msg.json())
            self.client.disconnect()
            if msg:
                self.server.notify(msg)
            else:
                pass

        def run(self):
            self.__verifyClientConnection()
            while True:
                try:
                    # Check for malformed messages
                    try:
                        message = Message.createFromJson(self.client.sock.recv())
                    except KeyError:
                        msg = "{0}: sent a command with missing fields".format(self.client.id)
                        self.exit(ERR_MALFORMED_MESSAGE, msg)
                        return
                    # Handle request to end connection
                    if message.command == COMMAND_END:
                        self.client.server.notify("{0}: requested to end conection".format(self.client.id))
                        self.client.manager.remove(self.client)
                        self.client.disconnect()
                    # Handle requests to retrieve a client's id
                    elif message.command == COMMAND_REQ_ID:
                        try:
                            message.data = self.client.manager.getClientId(message.data)
                        except KeyError:
                            message.data = ''
                        finally:
                            message.command = COMMAND_SEND_ID
                            message.route = (0, message.route[0])
                            self.client.send(message)
                            return
                    # Handle invalid requests
                    elif message.command != COMMAND_RELAY:
                        msg = "{0}: sent invalid command".format(self.client.id)
                        self.exit(ERR_INVALID_COMMAND, msg)
                        return
                    # Handle relay requests
                    else:
                        if self.client.manager.isIdRegistered(message.route[1]):
                            message.route = (self.client.id, message.route[1])
                        else:
                            msg = "{0}: requested to send message to invalid id".format(self.client.id)
                            self.exit(ERR_INVALID_ID, msg)
                # Handle errors
                except Exception as e:
                    if hasattr(e, 'errno') and (e.errno != ERR_CLOSED_CONNECTION):
                        msg = "{0}: error receiving".format(self.client.id)
                        self.exit(e.errno, msg)
                    else:
                        pass
                    self.client.disconnect()
                    return

    def __init__(self, server, sock):
        Connection.__init__(self, server.client_manager, str(sock))
        self.server = server
        self.sock = sock
        self.manager = self.server.client_manager
        self.send_thread = HingeClient.SendThread(self)
        self.send_thread.start()
        self.recv_thread = HingeClient.RecvThread(self)
        self.recv_thread.start()

    def __nickRegistered(self, nick):
        # Write to log
        self.server.notify("{0} -> {1}".format(str(self.sock), nick))
        # Add to CIDM
        self.nick = nick
        self.manager.register(self)

    def send(self, message):
        self.send_thread.queue.put(message)

    def registerNick(self, nick):
        self.nick = nick
        self.__nickRegistered(nick)

    def disconnect(self):
        self.sock.disconnect()
        self.manager.remove(self)

    def kick(self):
        message = Message(COMMAND_ERR, (0, self.id), ERR_KICKED)
        self.send(message)
        time.sleep(0.25)
        self.disconnect()
