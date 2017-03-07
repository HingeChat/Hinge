import base64
import json


class Message(object):

    def __init__(self,
                 command, route=(0, 0), data='',
                 hmac='', error='', num=''):
        
        self.command = str(command)
        self.route = tuple(route)
        self.data = str(data)
        self.hmac = str(hmac)
        self.error = str(error)
        self.num = str(num)

    def __str__(self):
        return self.json()

    def json(self):
        return json.dumps({
            'command': self.command,
            'route': self.route,
            'data': self.data,
            'hmac': self.hmac,
            'error': self.error,
            'num': self.num,
        })

    def getEncryptedDataAsBinaryString(self):
        return base64.b64decode(self.data)

    def setEncryptedData(self, data):
        self.payload = base64.b64encode(data).decode()

    def getHmacAsBinaryString(self):
        return base64.b64decode(self.hmac)

    def setBinaryHmac(self, hmac):
        self.hmac = base64.b64encode(hmac).decode()

    def getMessageNumAsBinaryString(self):
        return base64.b64decode(self.num)

    def setBinaryMessageNum(self, num):
        self.num = base64.b64encode(num).decode()

    @staticmethod
    def createFromJson(jsonStr):
        jsonStr = json.loads(jsonStr)
        return Message(
            jsonStr['command'],
            jsonStr['route'],
            jsonStr['data'],
            jsonStr['hmac'],
            jsonStr['error'],
            jsonStr['num'],
        )
