class HingeObject(object):

    def __init__(self):
        self.id = str(hash(self))

    def updateId(self, new_id):
        self.id = str(new_id)
