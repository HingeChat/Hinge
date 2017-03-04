import socket
import struct

from src.hinge.utils import *


class Socket(object):
    
    def __init__(self, addr, sock=None):
        self.addr = addr
        self.sock = sock
        # Create a new socket if not provided
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connected = False
        else:
            self.sock = sock
            self.connected = True

    def __str__(self):
        return self.addr[0] + ':' + str(self.addr[1])

    def connect(self):
        try:
            self.sock.connect(self.addr)
            self.connected = True
        except socket.error as se:
            raise GenericError(str(se))

    def disconnect(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except Exception as e:
            pass
        finally:
            self.connected = False

    def send(self, data):
        if not isinstance(data, str):
            raise TypeError()
        else:
            data = data.encode('utf-8')
            size = len(data)
            # Send the length of the message
            self._send(struct.pack("I", socket.htonl(size)), 4)
            # Send the actual data
            self._send(data, size)

    def _send(self, data, length):
        sent_size = 0
        while sent_size < length:
            try:
                amount_sent = self.sock.send(data[sent_size:])
            except Exception:
                self.connected = False
                raise NetworkError(UNEXPECTED_CLOSE_CONNECTION)

            if amount_sent == 0:
                self.connected = False
                raise NetworkError(UNEXPECTED_CLOSE_CONNECTION)

            sent_size += amount_sent

    def recv(self):
        # Receive length of the incoming message
        size = socket.ntohl(struct.unpack("I", self._recv(4))[0])
        # Receive data
        return self._recv(size).decode('utf-8')

    def _recv(self, length):
        try:
            data = b''
            recv_size = 0
            while recv_size < length:
                new_data = self.sock.recv(length - recv_size)
                if not new_data:
                    self.connected = False
                    raise NetworkError(CLOSE_CONNECTION)
                else:
                    data += new_data
                    recv_size += len(new_data)
            return data
        except socket.error as se:
            raise NetworkError(str(se))

    def getHostname(self):
        return self.addr[0]
