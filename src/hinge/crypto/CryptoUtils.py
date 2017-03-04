import os

from . import dh

from Crypto import Random
from Crypto.Hash import *
from Crypto.Cipher import AES

from src.hinge.utils import *


class CryptoUtils(object):

    dhGenerator = 2
    dhPrime = int('0x00a53d56c30fe79d43e3c9a0b678e87c0fcd2e78b15c676838'
                  'd2a2bd6c299b1e7fdb286d991f62e8f366b0067ae71d3d91dac4'
                  '738fd744ee180b16c97a54215236d4d393a4c85d8b390783566c'
                  '1b0d55421a89fca20b85e0faecded7983d038821778b6504105f'
                  '455d8655953d0b62841e9cc1248fa21834bc9f3e3cc1c080cfcb'
                  '0b230fd9a2059f5f637395dfa701981fad0dbeb545e2e29cd20f'
                  '7b6baee9314039e16ef19f604746fe596d50bb3967da51b94818'
                  '4d8d4511f2c0b8e4b4e3abc44144ce1f5968aadd053600a40430'
                  'ba97ad9e0ad26fe4c444be3f48434a68aa132b1677d8442454fe'
                  '4c6ae9d3b7164e6603f1c8a8f5b5235ba0b9f5b5f86278e4f69e'
                  'b4d5388838ef15678535589516a1d85d127da8f46f150613c8a4'
                  '9258be2ed53c3e161d0049cabb40d15f9042a00c494746753b97'
                  '94a9f66a93b67498c7c59b8253a910457c10353fa8e2edcafdf6'
                  'c9354a3dc58b5a825c353302d686596c11e4855e86f3c6810f9a'
                  '4abf917f69a6083330492aedb5621ebc3fd59778a40e0a7fa845'
                  '0c8b2c6fe3923775419b2ea35cd19abe62c50020df991d9fc772'
                  'd16dd5208468dc7a9b51c6723495fe0e72e818ee2b2a8581fab2'
                  'caf6bd914e4876573b023862286ec88a698be2dd34c03925ab5c'
                  'a0f50f0b2a246ab852e3779f0cf9d3e36f9ab9a50602d5e9216c'
                  '3a29994e81e151accd88ea346d1be6588068e873', 0)

    def __init__(self):
        self.aesKey = None
        self.aesIv = None
        self.aesSalt = None
        self.dh = None
        self.aesMode = AES.MODE_CBC

    def getRandomBytes(self, n_bytes=128):
        return Random.get_random_bytes(192)

    def generateDHKey(self):
        self.dh = dh.DiffieHellman(self.dhPrime, self.dhGenerator)
        self.dh.generateKeys()

    def computeDHSecret(self, publicKey):
        self.dhSecret = self.dh.computeKey(publicKey)
        new_hash = self.generateHash(str(self.dhSecret).encode())
        self.aesKey = new_hash[0:32]
        self.aesIv = new_hash[16:32]

    def aesEncrypt(self, message):
        raw = self._pad(message, AES.block_size)
        cipher = self.__aesGetCipher()
        encMessage = cipher.encrypt(raw)
        return encMessage

    def aesDecrypt(self, message):
        cipher = self.__aesGetCipher()
        decMessage = self._unpad(cipher.decrypt(message))
        return decMessage

    def __aesGetCipher(self):
        return AES.new(self.aesKey, self.aesMode, self.aesIv)

    def generateHmac(self, message):
        hmac = HMAC.HMAC(self.aesKey, message).digest()
        return hmac

    def generateHash(self, message):
        new_hash = SHA256.new(message).digest()
        return new_hash

    def stringHash(self, message):
        digest = self.generateHash(message)
        hex_val = hex(self.__octx_to_num(digest))[2:-1].upper()
        return hex_val

    def mapStringToInt(self, string):
        num = shift = 0
        for char in reversed(string):
            num |= ord(char) << shift
            shift += 8
        return num

    def __octx_to_num(self, data):
        converted = 0
        length = len(data)
        for i in range(length):
            converted = converted + data[i] * (256 ** (length - i - 1))
        return converted

    def getDHPubKey(self):
        return self.dh.pub_key

    def _pad(self, msg, bs):
        return msg + (bs - len(msg) % bs) * bytes([bs - len(msg) % bs])

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


def binToDec(binval):
    import binascii
    return int(binascii.hexlify(binval), 16)
