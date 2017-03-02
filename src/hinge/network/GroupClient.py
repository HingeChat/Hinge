import base64
import queue

from src.hinge.crypto.CryptoUtils import CryptoUtils
from src.hinge.crypto.smp import SMP

from src.hinge.network.Message import Message

from threading import Thread

from src.hinge.utils import constants
from src.hinge.utils import errors
from src.hinge.utils import exceptions
from src.hinge.utils import utils

class Session(object):
    def __init__(self, nicks):
        self.nicks = []
        for n in nicks:
            self.nicks.append(n)

    def removeClient(self, nick):
        self.nicks.remove(nick)

    def recvMessage(self, src, msg):
        if src.name in self.nicks:
            print(("Received message : {0}: {1}".format(src.name, msg)))

class GroupClient(Thread):
    def __init__(self, connectionManager, admin, nicks, sendMessageCallback, recvMessageCallback, handshakeDoneCallback, smpRequestCallback, errorCallback):
        Thread.__init__(self)
        self.daemon = True

        self.connectionManager = connectionManager
        self.admin = admin
        self.nicks = nicks
        self.sendMessageCallback = sendMessageCallback
        self.recvMessageCallback = recvMessageCallback
        self.handshakeDoneCallback = handshakeDoneCallback
        self.smpRequestCallback = smpRequestCallback
        self.errorCallback = errorCallback

        self.sessions = []

        self.incomingMessageNum = 0
        self.outgoingMessageNum = 0
        self.isEncrypted = False
        self.messageQueue = queue.Queue()

        self.crypto = CryptoUtils()
        self.crypto.generateDHKey()
        self.smp = None

    def sendChatMessage(self, text):
        self.sendMessage(constants.COMMAND_MSG, text)

    def sendTypingMessage(self, status):
        self.sendMessage(constants.COMMAND_TYPING, str(status))

    def sendMessage(self, command, payload=None):
        message = Message(clientCommand=command, isGroup=True, destNicks=self.nicks)

        # Encrypt all outgoing data
        if payload is not None and self.isEncrypted:
            payload = self.crypto.aesEncrypt(payload)
            message.setEncryptedPayload(payload)

            # Generate and set the HMAC for the message
            message.setBinaryHmac(self.crypto.generateHmac(payload))

            # Encrypt the message number of the message
            message.setBinaryMessageNum(self.crypto.aesEncrypt(str(self.outgoingMessageNum)))
            self.outgoingMessageNum += 1
        else:
            message.payload = payload

        self.sendMessageCallback(message)

    def postMessage(self, message):
        self.messageQueue.put(message)

    def initiateSMP(self, question, answer):
        self.sendMessage(constants.COMMAND_SMP_0, question)

        self.smp = SMP(answer)
        buffer = self.smp.step1()
        self.sendMessage(constants.COMMAND_SMP_1, buffer)

    def respondSMP(self, answer):
        self.smp = SMP(answer)
        self.__doSMPStep1(self.smpStep1)

    def run(self):
        self.group = self.__createSession(self.nicks)

        while True:
            message = self.messageQueue.get()

            command = message.clientCommand
            payload = message.payload
            sourceNick = message.sourceNick

            # Check if the client requested to end the connection
            if command == constants.COMMAND_END:
                self.connectionManager.destroyClient(self.admin)
                self.errorCallback(self.admin, errors.ERR_CONNECTION_ENDED)
                return
            # Ensure we got a valid command
            elif self.wasHandshakeDone and command not in constants.LOOP_COMMANDS:
                self.connectionManager.destroyClient(self.admin)
                self.errorCallback(self.admin, errors.ERR_INVALID_COMMAND)
                return

            # Decrypt the incoming data
            payload = self.__getDecryptedPayload(message)

            self.messageQueue.task_done()

            # Handle SMP commands specially
            if command in constants.SMP_COMMANDS:
               self.__handleSMPCommand(command, payload)
            else:
                payload = payload.decode()
                if command == constants.COMMAND_MSG:
                    if hasattr(self, 'group'):
                        self.sendMessagee(self.group, payload)
                self.recvMessageCallback(command, sourceNick, payload, True)

    def sendMessagee(self, dest, data):
        dest.recvMessage(self, data)

    def disconnect(self):
        try:
            self.sendMessage(constants.COMMAND_END)
        except:
            pass

    def __getSession(self, session):
        return self.sessions.get(session)

    def __createSession(self, nicks):
        new = Session(nicks)
        self.sessions.append(new)
        return new

    def __getDecryptedPayload(self, message):
        if self.isEncrypted:
            payload = message.getEncryptedPayloadAsBinaryString()
            encryptedMessageNumber = message.getMessageNumAsBinaryString()

            # Check the HMAC
            if not self.__verifyHmac(message.hmac, payload):
                self.errorCallback(message.sourceNick, errors.ERR_BAD_HMAC)
                raise exceptions.CryptoError(errno=errors.BAD_HMAC)

            try:
                # Check the message number
                messageNumber = int(self.crypto.aesDecrypt(encryptedMessageNumber))

                # If the message number is less than what we're expecting, the message is being replayed
                if self.incomingMessageNum > messageNumber:
                    raise exceptions.ProtocolError(errno=errors.ERR_MESSAGE_REPLAY)
                # If the message number is greater than what we're expecting, messages are being deleted
                elif self.incomingMessageNum < messageNumber:
                    raise exceptions.ProtocolError(errno=errors.ERR_MESSAGE_DELETION)
                self.incomingMessageNum += 1

                # Decrypt the payload
                payload = self.crypto.aesDecrypt(payload)
            except exceptions.CryptoError as ce:
                self.errorCallback(message.sourceNick, errors.ERR_BAD_DECRYPT)
                raise ce
        else:
            payload = message.payload

        return payload

    def __verifyHmac(self, givenHmac, payload):
        generatedHmac = self.crypto.generateHmac(payload)
        return utils.secureStrcmp(generatedHmac, base64.b64decode(givenHmac))

    def __handleSMPCommand(self, command, payload):
        try:
            if command == constants.COMMAND_SMP_0:
                # Fire the SMP request callback with the given question
                payload = payload.decode()
                self.smpRequestCallback(constants.SMP_CALLBACK_REQUEST, self.admin, payload)
            elif command == constants.COMMAND_SMP_1:
                # If there's already an smp object, go ahead to step 1.
                # Otherwise, save the payload until we have an answer from the user to respond with
                if self.smp:
                    self.__doSMPStep1(payload)
                else:
                    self.smpStep1 = payload
            elif command == constants.COMMAND_SMP_2:
                self.__doSMPStep2(payload)
            elif command == constants.COMMAND_SMP_3:
                self.__doSMPStep3(payload)
            elif command == constants.COMMAND_SMP_4:
                self.__doSMPStep4(payload)
            else:
                # This shouldn't happen
                raise exceptions.CryptoError(errno=errors.ERR_SMP_CHECK_FAILED)
        except exceptions.CryptoError as ce:
            self.smpRequestCallback(constants.SMP_CALLBACK_ERROR, self.admin, '', ce.errno)

    def __doSMPStep1(self, payload):
        buffer = self.smp.step2(payload)
        self.sendMessage(constants.COMMAND_SMP_2, buffer)

    def __doSMPStep2(self, payload):
        buffer = self.smp.step3(payload)
        self.sendMessage(constants.COMMAND_SMP_3, buffer)

    def __doSMPStep3(self, payload):
        buffer = self.smp.step4(payload)
        self.sendMessage(constants.COMMAND_SMP_4, buffer)

        # Destroy the SMP object now that we're done
        self.smp = None

    def __doSMPStep4(self, payload):
        self.smp.step5(payload)

        if self.__checkSMP():
            self.smpRequestCallback(constants.SMP_CALLBACK_COMPLETE, self.admin)

        # Destroy the SMP object now that we're done
        self.smp = None

    def __checkSMP(self):
        if not self.smp.match:
            raise exceptions.CryptoError(errno=errors.ERR_SMP_MATCH_FAILED)
        return True