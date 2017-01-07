import base64
import json

class Message(object):
    def __init__(self, serverCommand=None, clientCommand=None, sourceNick=None, destNicks=[],
                 payload=None, hmac=None, error=None, num=None, isGroup=False):
        self.serverCommand = str(serverCommand)
        self.clientCommand = str(clientCommand)
        self.sourceNick    = str(sourceNick)
        self.destNicks    = list(destNicks)
        self.payload       = str(payload)
        self.hmac          = str(hmac)
        self.error         = str(error)
        self.num           = str(num)
        self.isGroup       = bool(isGroup)

    def __str__(self):
        return json.dumps({'serverCommand': self.serverCommand, 'clientCommand': self.clientCommand,
                           'sourceNick': self.sourceNick, 'destNicks': self.destNicks,
                           'payload': self.payload, 'hmac': self.hmac, 'error': self.error, 'num': self.num,
                           'isGroup': self.isGroup})

    def getEncryptedPayloadAsBinaryString(self):
        return base64.b64decode(self.payload)

    def setEncryptedPayload(self, payload):
        self.payload = str(base64.b64encode(payload))

    def getHmacAsBinaryString(self):
        return base64.b64decode(self.hmac)

    def setBinaryHmac(self, hmac):
        self.hmac = str(base64.b64encode(hmac))

    def getMessageNumAsBinaryString(self):
        return base64.b64decode(self.num)

    def setBinaryMessageNum(self, num):
        self.num = str(base64.b64encode(num))

    @staticmethod
    def createFromJSON(jsonStr):
        jsonStr = json.loads(jsonStr)
        return Message(jsonStr['serverCommand'], jsonStr['clientCommand'], jsonStr['sourceNick'], jsonStr['destNicks'],
                       jsonStr['payload'], jsonStr['hmac'], jsonStr['error'], jsonStr['num'], jsonStr['isGroup'])