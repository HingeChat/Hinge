import base64
import queue
import threading

from src.hinge.crypto.CryptoUtils import CryptoUtils
from src.hinge.network import HingeObject
from src.hinge.network import Message
from src.hinge.utils import *


class Session(threading.Thread, HingeObject.HingeObject):

    def __init__(self, client, remote_id):
        threading.Thread.__init__(self, daemon=True)
        HingeObject.HingeObject.__init__(self)

        self.client = client
        self.remote_id = remote_id

        self.message_queue = queue.Queue()
        self.incoming_message_num = 0
        self.outgoing_message_num = 0

        self.crypto = CryptoUtils()
        self.crypto.generateDHKey()
        self.encrypted = False

    def __verifyHmac(self, hmac, data):
        generated_hmac = self.crypto.generateHmac(data)
        return secureStrcmp(generated_hmac, base64.b64decode(hmac))

    def __getDecryptedData(self, message):
        if self.encrypted:
            data = message.getEncryptedDataAsBinaryString()
            enc_num = message.getMessageNumAsBinaryString()
            # Check HMAC
            if not self.__verifyHmac(message.hmac, data):
                self.client.callbacks['err'](message.route, ERR_BAD_HMAC)
                raise CryptoError(errno=errors.BAD_HMAC)
            else:
                try:
                    # Check message number
                    num = int(self.crypto.aesDecrypt(enc_num))
                    if self.incoming_message_num > num:
                        raise ProtocolError(errno=ERR_MESSAGE_REPLAY)
                    elif self.incoming_message_num < num:
                        raise ProtocolError(errno=ERR_MESSAGE_DELETION)
                    self.incoming_message_num += 1
                    # Decrypt data
                    data = self.crypto.aesDecrypt(data)
                    return data
                except CryptoError as ce:
                    self.client.callbacks['err'](message.route, ERR_BAD_DECRYPT)
                    raise ce
        else:
            return message.data

    def connect(self):
        # Override in subclass
        pass

    def disconnect(self):
        try:
            self.sendMessage(COMMAND_END)
        except Exception:
            pass

    def run(self):
        # Override in subclass
        pass

    def sendMessage(self, command, data=None):
        message = Message.Message(command, (self.client.id, self.remote_id))

        if (data is not None) and self.encrypted:
            # Encrypt data and message number & generate HMAC
            enc_data = self.crypto.aesEncrypt(data.encode())
            num = self.crypto.aesEncrypt(str(self.outgoing_message_num).encode())
            hmac = self.crypto.generateHmac(enc_data)
            # Update message
            message.setEncryptedData(enc_data)
            message.setBinaryHmac(hmac)
            message.setBinaryMessageNum(num)
            self.outgoing_message_num += 1
        else:
            pass

        self.client.sendMessage(message)

    def sendChatMessage(self, text):
        self.sendMessage(COMMAND_MSG, data=text)

    def sendTypingMessage(self, status):
        self.sendMessage(COMMAND_TYPING, data=str(status))

    def postMessage(self, message):
        self.message_queue.put(message)
