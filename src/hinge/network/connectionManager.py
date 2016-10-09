import Queue
import socket
import sys
import traceback

from threading import Thread

from Client import Client
from Message import Message
from sock import Socket

from src.hinge.utils import constants
from src.hinge.utils import exceptions
from src.hinge.utils import errors
from src.hinge.utils import utils

class ConnectionManager(object):
    def __init__(self, nick, serverAddr, recvMessageCallback, newClientCallback, handshakeDoneCallback, smpRequestCallback, errorCallback):
        self.clients = {}
        self.groupClients = {}

        self.nick = nick
        self.sock = Socket(serverAddr)
        self.recvMessageCallback = recvMessageCallback
        self.newClientCallback = newClientCallback
        self.handshakeDoneCallback = handshakeDoneCallback
        self.smpRequestCallback = smpRequestCallback
        self.errorCallback = errorCallback
        self.sendThread = SendThread(self.sock, self.errorCallback)
        self.recvThread = RecvThread(self.sock, self.recvMessage, self.errorCallback)
        self.messageQueue = Queue.Queue()

    def connectToServer(self):
        self.sock.connect()
        self.sendThread.start()
        self.recvThread.start()
        self.__sendProtocolVersion()
        self.__registerNick()

    def disconnectFromServer(self):
        if self.sock.isConnected:
            try:
                # Send the end command to all clients
                for nick, client in self.clients.iteritems():
                    client.disconnect()

                # Send the end command to the server
                self.__sendServerCommand(constants.COMMAND_END)
            except Exception:
                pass

    def openChat(self, destNick, otherNicks='', isGroup=False):
        self.__createClient(destNick.lower(), otherNicks, isGroup, initiateHandshakeOnStart=True)

    def __createClient(self, nick, otherNicks, isGroup, initiateHandshakeOnStart=False):
        if type(nick) is not str:
            raise TypeError
        # Check that we're not connecting to ourself
        elif nick == self.nick:
            self.errorCallback(nick, errors.ERR_SELF_CONNECT)
            return
        # Check if a connection to the nick already exists
        elif nick in self.clients and isGroup is False:
            self.errorCallback(nick, errors.ERR_ALREADY_CONNECTED)
            return

        if otherNicks is not '':
            newClient = Client(self, nick, self.sendMessage, self.recvMessageCallback, self.handshakeDoneCallback, self.smpRequestCallback, self.errorCallback, initiateHandshakeOnStart, isGroup=isGroup, otherNicks=otherNicks)
            otherClient = Client(self, otherNicks, self.sendMessage, self.recvMessageCallback, self.handshakeDoneCallback, self.smpRequestCallback, self.errorCallback, initiateHandshakeOnStart, isGroup=isGroup)
        else:
            newClient = Client(self, nick, self.sendMessage, self.recvMessageCallback, self.handshakeDoneCallback, self.smpRequestCallback, self.errorCallback, initiateHandshakeOnStart, isGroup=isGroup)
        if isGroup is False:
            self.clients[nick] = newClient
        else:
            self.clients[nick] = newClient
        if otherNicks is not '':
            if otherNicks not in self.clients:
                self.clients[otherNicks] = otherClient
        newClient.start()

    def closeChat(self, nick):
        client = self.getClient(nick)
        if client is None:
            return

        # Send the end command to the client
        self.sendMessage(Message(clientCommand=constants.COMMAND_END, destNick=nick))

        # Remove the client from the clients list
        self.destroyClient(nick)

    def destroyClient(self, nick):
        del self.clients[nick]

    def getGroupClients(self):
        try:
            return self.clients
        except KeyError:
            return None

    def getClient(self, nick):
        try:
            return self.clients[nick]
        except KeyError:
            return None

    def __sendProtocolVersion(self):
        self.__sendServerCommand(constants.COMMAND_VERSION, constants.PROTOCOL_VERSION)

    def __registerNick(self):
        self.__sendServerCommand(constants.COMMAND_REGISTER)

    def __sendServerCommand(self, command, payload=None):
        # Send a commend intended for the server, not another client (such as registering a nick)
        self.sendThread.messageQueue.put(Message(serverCommand=command, sourceNick=self.nick, payload=payload))

    def sendMessage(self, message):
        message.serverCommand = constants.COMMAND_RELAY
        message.sourceNick = self.nick
        self.sendThread.messageQueue.put(message)

    def recvMessage(self, message):
        command  = message.clientCommand
        sourceNick = message.sourceNick
        isGroup = message.isGroup
        otherNicks = message.otherNicks

        # Handle errors/shutdown from the server
        if message.serverCommand == constants.COMMAND_ERR:
            # If the error was that the nick wasn't found, kill the client trying to connect to that nick
            if int(message.error) == errors.ERR_NICK_NOT_FOUND:
                try:
                    del self.clients[str(message.destNick)]
                except:
                    pass

            self.errorCallback(message.destNick, int(message.error))
            return
        elif message.serverCommand == constants.COMMAND_END:
            self.errorCallback('', int(message.error))
            return

        # Send the payload to its intended client
        try:
            self.clients[sourceNick].postMessage(message)
        except KeyError as ke:
            # Create a new client if we haven't seen this client before
            if command == constants.COMMAND_HELO:
                if isGroup:
                    if otherNicks is not '':
                        self.newClientCallback(sourceNick, isGroup=True, otherNicks=otherNicks)
                    else:
                        self.newClientCallback(sourceNick, isGroup=True)
                else:
                    self.newClientCallback(sourceNick)
            else:
                self.sendMessage(Message(clientCommand=constants.COMMAND_ERR, error=errors.INVALID_COMMAND))

    def newClientAccepted(self, nick, isGroup=False, otherNicks=''):
        self.__createClient(nick, otherNicks, isGroup=isGroup)

    def newClientRejected(self, nick):
        # If rejected, send the rejected command to the client
        self.sendMessage(Message(clientCommand=constants.COMMAND_REJECT, destNick=nick))

    def respondSMP(self, nick, answer):
        self.clients[nick].respondSMP(answer)

class RecvThread(Thread):
    def __init__(self, sock, recvCallback, errorCallback):
        Thread.__init__(self)
        self.daemon = True

        self.sock = sock
        self.errorCallback = errorCallback
        self.recvCallback = recvCallback

    def run(self):
        while True:
            try:
                message = Message.createFromJSON(self.sock.recv())

                # Send the message to the given callback
                self.recvCallback(message)
            except exceptions.NetworkError as ne:
                # Don't show an error if the connection closing was expected/normal
                if hasattr(ne, 'errno') and ne.errno != errors.ERR_CLOSED_CONNECTION:
                    self.errorCallback('', errors.ERR_NETWORK_ERROR)
                return

class SendThread(Thread):
    def __init__(self, sock, errorCallback):
        Thread.__init__(self)
        self.daemon = True

        self.sock = sock
        self.errorCallback = errorCallback
        self.messageQueue = Queue.Queue()

    def run(self):
        while True:
            # Get (or wait) for a message in the message queue
            message = self.messageQueue.get()

            try:
                self.sock.send(str(message))

                # If the server command is END, shut the socket now that the message ws sent
                if message.serverCommand == constants.COMMAND_END:
                    self.sock.disconnect()
            except exceptions.NetworkError as ne:
                self.errorCallback('', errors.ERR_NETWORK_ERROR)
                return
            finally:
                # Mark the operation as done
                self.messageQueue.task_done()