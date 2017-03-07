from src.hinge.network.Message import Message
from src.hinge.utils import *


class ClientManager(object):

    def __init__(self):
        self._ip_to_connections = {}
        self._id_to_client = {}
        self._nick_to_client = {}

    @property
    def clients(self):
        return self._id_to_client.values()

    @property
    def ids(self):
        return self._id_to_client.keys()

    @property
    def nicks(self):
        return self._nick_to_client.keys()

    def __clientRegistered(self, client):
        if self._nick_to_client.get(client.nick):
            raise Exception("client with nick {0} already exists".format(client.id))
        else:
            self._nick_to_client[client.nick] = client

    def __clientUnregistered(self, nick):
        if self._nick_to_client.get(nick):
            del self._nick_to_client[nick]
        else:
            raise KeyError("client with nick {0} does not exist".format(nick))

    def add(self, client):
        # Add to IP map
        if self._ip_to_connections.get(client.ip):
            self._ip_to_connections[client.ip].append(client)
        else:
            self._ip_to_connections[client.ip] = [client]
        # Add to ID map
        if not self._id_to_client.get(client.id):
            self._id_to_client[client.id] = client
        else:
            # Should not happen
            raise Exception("client with id {0} already exists".format(client.id))

    def remove(self, client):
        # Remove from nick map
        if (client.nick is not None) and self._nick_to_client.get(client.nick):
            del self._nick_to_client[client.nick]
        elif self._nick_to_client.get(client.nick):
            self.unregister(client)
            del self._nick_to_client[client.nick]
        else:
            pass
        # Remove from ID map
        if self._id_to_client.get(client.id):
            del self._id_to_client[client.id]
        else:
            raise KeyError("client with id {0} does not exist".format(client.id))
        # Remove from IP map
        if self._ip_to_connections.get(client.ip):
            self._ip_to_connections.get(client.ip).remove(client)
        else:
            raise KeyError("ip {0} is not connected".format(client.ip))

    def register(self, client):
        if not self._id_to_client.get(client.id):
            raise Exception("client with id {0} does not exist".format(client.id))
        elif client.nick is None:
            raise Exception("client has no nick")
        else:
            self.__clientRegistered(client)

    def unregister(self, client):
        nick = client.nick
        client.nick = None
        self.__clientUnregistered(nick)

    @staticmethod
    def isNickValid(nick):
        if nick == '':
            return INVALID_EMPTY_NICK
        elif not nick.isalnum():
            return INVALID_NICK_CONTENT
        elif len(nick) > NICK_MAX_LEN:
            return INVALID_NICK_LENGTH
        else:
            return VALID_NICK

    def isNickRegistered(self, nick):
        if self._nick_to_client.get(nick):
            return True
        else:
            return False

    def isIdRegistered(self, client_id):
        if self._id_to_client.get(client_id):
            return True
        else:
            return False

    def getClientById(self, client_id):
        if self.isIdRegistered(client_id):
            return self._id_to_client.get(client_id)
        else:
            raise KeyError("client with id {0} does not exist".format(client_id))

    def getClientByNick(self, nick):
        if self.isNickRegistered(nick):
            return self._nick_to_client.get(nick)
        else:
            raise KeyError("client with nick {0} does not exist".format(nick))

    def getClientId(self, nick):
        client = self.getClientByNick(nick)
        return client.id

    def getClientNick(self, client_id):
        client = self.getClientById(client_id)
        return client.nick

    def updateClientId(self, client_id, new_client_id):
        client = self.getClientById(client_id)
        client.id = new_client_id
        # Change in ID map
        del self._id_to_client[client_id]
        self._id_to_client[client.id] = client

    def updateClientNick(self, nick, new_nick):
        client = self.getClientByNick(nick)
        client.nick = new_nick
        # Change in nick map
        del self._nick_to_client[nick]
        self._nick_to_client[client.nick] = client
