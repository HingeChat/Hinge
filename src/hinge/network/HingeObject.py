class ClientMap(dict):

    def add(self, client):
        self.__setitem__(client.id, client)

    def remove(self, client):
        if self.get(client.id):
            del self[client.id]
        else:
            raise KeyError()


class HingeObject(object):

    id_map = ClientMap()

    def __init__(self):
        self.id = id(self)
        self.id_map.add(self)

    def updateId(self, new_id):
        self.id_map.remove(self)
        self.id = new_id
        self.id_map.add(self)
