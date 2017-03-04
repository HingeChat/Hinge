import queue
import socket
import sys
import traceback
import threading

from src.hinge.network import HingeObject
from src.hinge.network import PrivateSession
from src.hinge.network.Message import Message
from src.hinge.network.sock import Socket
from src.hinge.utils import *


class Client(HingeObject.HingeObject):
    
    def __init__(self, nick, server_addr, callbacks):
        HingeObject.HingeObject.__init__(self)

        self.sessions = {}
        self.nick = nick
        self.sock = Socket(server_addr)

        self.callbacks = callbacks

        self.message_queue = queue.Queue()
        self.send_thread = SendThread(self.sock, self.callbacks['err'])
        self.recv_thread = RecvThread(self.sock, self.recvMessage, self.callbacks['err'])

    def __sendProtocolVersion(self):
        self.__sendServerCommand(COMMAND_VERSION, PROTOCOL_VERSION)

    def __sendServerCommand(self, command, data=''):
        self.send_thread.message_queue.put(Message(**{
            'command': command,
            'route': (self.id, 0),
            'data': data,
        }))

    def __registerNick(self):
        self.__sendServerCommand(COMMAND_REGISTER, self.nick)

    def __createSession(self, client, imediate_handshake=False):
        if client.id == self.id:
            self.callbacks['err'](client.id, ERR_SELF_CONNECT)
        # NEED TO FIX AFTER IDENTIFICATION IS IMPLEMENTED
        elif client.id in self.sessions:
            self.callbacks['err'](client.id, ERR_ALREADY_CONNECTED)
        else:
            new_session = PrivateSession(client, self.callbacks, imediate_handshake)
            self.sessions[new_session.id] = new_session
            new_session.start()

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

    def getClientById(self, client_id):
        self.__sendServerCommand(COMMAND_GET_REMOTE, str(client_id))

    def getSession(self, session_id):
        try:
            return self.sessions[session_id]
        except KeyError:
            return None

    def openSession(self, client):
        self.__createSession(client, imediate_handshake=True)

    def closeSession(self, session_id):
        if self.getClient(session_id):
            # Send END command
            self.sendMessage(Message(**{
                'command': COMMAND_END,
                'route': (self.id, 0),
            }))
            # Remove session from sessions list
            self.destroySession(session_id)

    def destroySession(self, session_id):
        del self.sessions[session_id]

    def sendMessage(self, message):
        self.send_thread.message_queue.put(message)

    def recvMessage(self, message):
        command = message.command
        route = message.command
        # Handle errors/shutdown from the server
        if message.command == COMMAND_ERR:
            # Client not found
            if int(message.error) == ERR_NICK_NOT_FOUND:
                try:
                    # NEED TO FIX AFTER IDENTIFICATION IS IMPLEMENTED
                    del self.sessions[route[1]]
                except Exception:
                    pass
            self.callbacks['err'](route[1], int(message.error))
        elif message.command == COMMAND_END:
            self.callbacks['err']('', int(message.error))
        else:
            if command == COMMAND_ADD:
                # NEED TO FIX AFTER IDENTIFICATION IS IMPLEMENTED
                pass
            else:
                # Send data to intended session
                try:
                    self.sessions[route[1]].postMessage(message)
                except KeyError as ke:
                    # Create a new client
                    if command == COMMAND_HELO:
                        self.newClientCallback(route[1])
                    else:
                        self.sendMessage(Message(**{
                            'command': COMMAND_ERR,
                            'route': (self.id, 0),
                            'error': INVALID_COMMAND,
                        }))

    def newClientAccepted(self, client):
        self.__createSession(nick)

    def newClientRejected(self, client):
        # If rejected, send the rejected command to the client
        self.sendMessage(Message(**{
            'command': COMMAND_REJECT,
            'route': (self.id, client.id),
        }))

    def respondSmp(self, session_id, answer):
        self.sessions[session_id].respondSMP(answer)


class RecvThread(threading.Thread):
    
    def __init__(self, sock, recv_callback, err_callback):
        threading.Thread.__init__(self, daemon=True)
        self.sock = sock
        self.recv_callback = recv_callback
        self.err_callback = err_callback

    def run(self):
        while True:
            try:
                message = Message.createFromJSON(self.sock.recv())
                self.recv_callback(message)
            except NetworkError as ne:
                if hasattr(ne, 'errno') and (ne.errno != ERR_CLOSED_CONNECTION):
                    self.err_callback('', ERR_NETWORK_ERROR)
                return


class SendThread(threading.Thread):
    
    def __init__(self, sock, err_callback):
        threading.Thread.__init__(self, daemon=True)
        self.sock = sock
        self.err_callback = err_callback
        self.message_queue = queue.Queue()

    def run(self):
        while True:
            message = self.message_queue.get()
            try:
                self.sock.send(str(message))
                if message.command == COMMAND_END:
                    self.sock.disconnect()
            except NetworkError as ne:
                self.err_callback('', ERR_NETWORK_ERROR)
                return
            finally:
                self.message_queue.task_done()
