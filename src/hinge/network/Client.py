import queue
import socket
import sys
import traceback
import threading

from src.hinge.network import HingeObject
from src.hinge.network import PrivateSession
from src.hinge.network import Message
from src.hinge.network.sock import Socket
from src.hinge.utils import *


class Client(HingeObject.HingeObject):

    class SendThread(threading.Thread):

        def __init__(self, client):
            threading.Thread.__init__(self, daemon=True)
            self.client = client
            self.message_queue = queue.Queue()

        def run(self):
            while True:
                message = self.message_queue.get()
                try:
                    self.client.sock.send(message.json())
                    if (message.command == COMMAND_END) and \
                       (message.route[1] == SERVER_ROUTE):
                        self.client.sock.disconnect()
                    else:
                        pass
                except NetworkError as ne:
                    self.client.callbacks['err'](SERVER_ROUTE, ERR_NETWORK_ERROR)
                    return
                finally:
                    self.message_queue.task_done()

    class RecvThread(threading.Thread):

        def __init__(self, client):
            threading.Thread.__init__(self, daemon=True)
            self.client = client

        def run(self):
            while True:
                try:
                    message = Message.Message.createFromJson(self.client.sock.recv())
                    # Check for error
                    if hasattr(message, 'error') and (message.error != ''):
                        error = int(message.error)
                    else:
                        error = 0
                    # Handle errors/shutdown from the server
                    if message.command == COMMAND_ERR:
                        # Client not found
                        if error == ERR_NICK_NOT_FOUND:
                            try:
                                del self.client.sessions[route[1]]
                            except Exception:
                                pass
                        else:
                            pass
                        self.client.callbacks['err'](message.route[1], error)
                    elif message.command == COMMAND_END:
                        if message.route[0] == SERVER_ROUTE:
                            self.client.callbacks['err'](SERVER_ROUTE, error)
                        else:
                            self.client.callbacks['err'](message.route[0], ERR_CONN_ENDED)
                    elif message.command in SYNC_COMMANDS:
                        self.client.sync_resp = message.data
                    else:
                        # Send data to intended session
                        session = self.client.sessions.get(message.route[0])
                        if session:
                            session.postMessage(message)
                        else:
                            # Create a new client
                            if message.command == COMMAND_HELO:
                                self.client.callbacks['new'](message.route[0])
                            else:
                                message = Message.Message(COMMAND_ERR,
                                                          (self.client.id, SERVER_ROUTE),
                                                          error=INVALID_COMMAND)
                                self.client.sendMessage(message)
                except NetworkError as ne:
                    if hasattr(ne, 'errno') and (ne.errno != ERR_CLOSED_CONNECTION):
                        self.client.callbacks['err'](SERVER_ROUTE, ERR_NETWORK_ERROR)
                    else:
                        pass
                    return

    def __init__(self, nick, server_addr, callbacks):
        HingeObject.HingeObject.__init__(self)
        self.nick = nick
        self.sock = Socket(server_addr)
        self.callbacks = callbacks
        self.message_queue = queue.Queue()
        self.send_thread = Client.SendThread(self)
        self.recv_thread = Client.RecvThread(self)
        self.sync_resp = None
        self.sessions = {}

    def __sendProtocolVersion(self):
        self.__sendServerCommand(COMMAND_VERSION, PROTOCOL_VERSION)

    def __sendServerCommand(self, command, data=''):
        message = Message.Message(command, (self.id, SERVER_ROUTE), data)
        self.send_thread.message_queue.put(message)

    def __registerNick(self):
        self.__sendServerCommand(COMMAND_REGISTER, self.nick)

    def __createSession(self, remote_id, imediate_handshake=False):
        if remote_id == self.id:
            self.callbacks['err'](remote_id, ERR_SELF_CONNECT)
        elif remote_id in self.sessions:
            self.callbacks['err'](remote_id, ERR_ALREADY_CONNECTED)
        else:
            new_session = PrivateSession.PrivateSession(self, remote_id, imediate_handshake)
            self.sessions[remote_id] = new_session
            new_session.start()

    def _waitForResp(self):
        while self.sync_resp is None:
            pass
        resp = str(self.sync_resp)
        self.sync_resp = None
        return resp

    def connectToServer(self):
        self.sock.connect()
        self.send_thread.start()
        self.recv_thread.start()
        self.__sendProtocolVersion()
        self.__registerNick()

    def disconnectFromServer(self):
        if self.sock.connected:
            try:
                # END all sessions
                for _, session in self.sessions.items():
                    session.disconnect()
                # Send END command to server
                self.__sendServerCommand(COMMAND_END)
            except Exception:
                pass

    def getClientId(self, nick):
        self.__sendServerCommand(COMMAND_REQ_ID, nick)
        return self._waitForResp()

    def getClientNick(self, client_id):
        self.__sendServerCommand(COMMAND_REQ_NICK, client_id)
        return self._waitForResp()

    def getSession(self, session_id):
        return self.sessions.get(session_id)

    def openSession(self, nick):
        remote_id = self.getClientId(nick)
        self.__createSession(remote_id, imediate_handshake=True)

    def closeSession(self, nick):
        remote_id = self.getClientId(nick)
        if remote_id:
            # Send END command
            message = Message.Message(COMMAND_END, (self.id, remote_id))
            self.sendMessage(message)
            # Remove session from sessions list
            self.destroySession(remote_id)
        else:
            pass

    def destroySession(self, session_id):
        del self.sessions[session_id]

    def sendMessage(self, message):
        self.send_thread.message_queue.put(message)

    def newClientAccepted(self, remote_id):
        self.__createSession(remote_id)

    def newClientRejected(self, remote_id):
        # If rejected, send the rejected command to the client
        message = Message.Message(COMMAND_REJECT, (self.id, remote_id))
        self.sendMessage(message)

    def respondSmp(self, session_id, answer):
        self.sessions[session_id].respondSmp(answer)
