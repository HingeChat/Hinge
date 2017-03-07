import base64

from src.hinge.network import Session
from src.hinge.crypto.smp import SMP
from src.hinge.utils import *


class PrivateSession(Session.Session):

    def __init__(self, client, remote_id, imediate_handshake=False):
        Session.Session.__init__(self, client, remote_id)
        
        self.imediate_handshake = imediate_handshake
        self.handshake_done = False
        
        self.smp = None
        self.smp_step_1 = None

    def __getHandshakeMessageData(self, expected):
        message = self.message_queue.get()
        if message.command != expected:
            # Client ended
            if message.command == COMMAND_END:
                raise ProtocolEnd()
            # Client rejected connection
            elif message.command == COMMAND_REJECT:
                raise ProtocolError(errno=ERR_CONNECTION_REJECTED)
            # Handshake failed
            else:
                raise ProtocolError(errno=ERR_BAD_HANDSHAKE)
        else:
            # Decrypt message
            data = self._Session__getDecryptedData(message)
            # Mark as done
            self.message_queue.task_done()
            return data

    def __handleHandshakeError(self, exception):
        self.callbacks['err'](self.id, exception.errno)
        # Rejected connection
        if exception.errno == ERR_CONNECTION_REJECTED:
            self.client.destroySession(self.id)
        # Error
        else:
            self.sendMessage(COMMAND_ERR)

    def __initiateHandshake(self):
        try:
            # Send HELO command
            self.sendMessage(COMMAND_HELO)
            # Receive REDY command
            self.__getHandshakeMessageData(COMMAND_REDY)
            # Send public key
            pub_key = base64.b64encode(str(self.crypto.getDHPubKey()).encode())
            self.sendMessage(COMMAND_PUB_KEY, pub_key)
            # Receive client's public key
            client_pub_key = self.__getHandshakeMessageData(COMMAND_PUB_KEY)
            self.crypto.computeDHSecret(int(base64.b64decode(client_pub_key)))
            # Switch to AES encryption
            self.encrypted = True
            # Mark as done
            self.handshake_done = True
            self.callbacks['handshake'](self.id, False)
        except ProtocolEnd:
            self.disconnect()
            self.client.destroySession(self.id)
        except (ProtocolError, CryptoError) as e:
            self.__handleHandshakeError(e)

    def __doHandshake(self):
        try:
            # Send REDY command
            self.sendMessage(COMMAND_REDY)
            # Receive client's public key
            client_pub_key = self.__getHandshakeMessageData(COMMAND_PUB_KEY).encode()
            self.crypto.computeDHSecret(int(base64.b64decode(client_pub_key)))
            # Send our public key
            pub_key = base64.b64encode(str(self.crypto.getHPubKey()).encode('ascii'))
            self.sendMessage(COMMAND_PUB_KEY, pub_key)
            # Switch to AES encryption
            self.encrypted = True
            # Mark as done
            self.handshake_done = True
            self.callbacks['handshake'](self.id, False)
        except ProtocolEnd:
            self.disconnect()
            self.client.destroySession(self.id)
        except (ProtocolError, CryptoError) as e:
            self.__handleHandshakeError(e)

    def __checkSmp(self):
        if not self.smp.match:
            raise CryptoError(errno=ERR_SMP_MATCH_FAILED)
        else:
            return True

    def __handleSmpCommand(self, command, data):
        try:
            if command == COMMAND_SMP_0:
                # SMP callback with the given question
                data = data.decode()
                self.callbacks['smp'](SMP_CALLBACK_REQUEST, self.id, data)
            elif command == COMMAND_SMP_1:
                # If there's already an smp object, go ahead to step 1.
                # Otherwise, save the data until we have an answer from the user to respond with
                if self.smp:
                    self.__doSmpStep1(data)
                else:
                    self.smp_step_1 = data
            elif command == COMMAND_SMP_2:
                self.__doSmpStep2(data)
            elif command == COMMAND_SMP_3:
                self.__doSmpStep3(data)
            elif command == COMMAND_SMP_4:
                self.__doSmpStep4(data)
            else:
                raise CryptoError(errno=ERR_SMP_CHECK_FAILED)
        except CryptoError as ce:
            self.smpRequestCallback(SMP_CALLBACK_ERROR, self.client.id, '', ce.errno)

    def __doSmpStep1(self, data):
        buffer = self.smp.step2(data)
        self.sendMessage(COMMAND_SMP_2, buffer)

    def __doSmpStep2(self, data):
        buffer = self.smp.step3(data)
        self.sendMessage(COMMAND_SMP_3, buffer)

    def __doSmpStep3(self, data):
        buffer = self.smp.step4(data)
        self.sendMessage(COMMAND_SMP_4, buffer)

    def __doSmpStep4(self, data):
        self.smp.step5(data)
        if self.__checkSmp():
            self.callbacks(SMP_CALLBACK_COMPLETE, self.id)
        self.smp = None

    def connect(self):
        self.__initiateHandshake()

    def run(self):
        # Handshake
        if self.imediate_handshake:
            self.__initiateHandshake()
        else:
            self.__doHandshake()
        # Confirm handshake
        if not self.handshake_done:
            return
        # Main loop
        while True:
            message = self.message_queue.get()
            # Check if client requested to end
            if message.command == COMMAND_END:
                self.client.destroySession(self.id)
                self.callbacks['err'](self.id, ERR_CONNECTION_ENDED)
            # Verify command
            elif self.handshake_done and (message.command not in LOOP_COMMANDS):
                self.client.destroySession(self.id)
                self.callbacks['err'](self.id, ERR_INVALID_COMMAND)
            # Handle commands
            else:
                # Decrypt data
                data = self.__getDecryptedData(message.data)
                # Mark as done
                self.message_queue.task_done()
                # Handle SMP commands
                if command in SMP_COMMANDS:
                    self.__handleSmpCommand(message.command, message.data)
                else:
                    self.callbacks['recv'](message.command,
                                           message.route,
                                           message.data.decode())

    def initiateSmp(self, question, answer):
        self.sendMessage(COMMAND_SMP0, question)
        self.smp = SMP(answer)
        buffer = self.smp.step1()
        self.sendMessage(COMMAND_SMP1, buffer)

    def respondSmp(self, answer):
        self.smp = SMP(answer)
        self.__doSmpStep1(self.smp_step_1)
