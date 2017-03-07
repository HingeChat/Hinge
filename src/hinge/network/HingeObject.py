class HingeObject(object):

    def __init__(self):
        self.id = hash(self)

    def updateId(self, new_id):
        self.id = new_id
