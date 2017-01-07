import os
from . import dh
from Crypto import Random
from Crypto.Hash import *
from Crypto.Cipher import AES

from src.hinge.utils import constants
from src.hinge.utils import exceptions

class CryptoUtils(object):
    dhPrime = 0x00a53d56c30fe79d43e3c9a0b678e87c0fcd2e78b15c676838d2a2bd6c299b1e7fdb286d991f62e8f366b0067ae71d3d91dac4738fd744ee180b16c97a54215236d4d393a4c85d8b390783566c1b0d55421a89fca20b85e0faecded7983d038821778b6504105f455d8655953d0b62841e9cc1248fa21834bc9f3e3cc1c080cfcb0b230fd9a2059f5f637395dfa701981fad0dbeb545e2e29cd20f7b6baee9314039e16ef19f604746fe596d50bb3967da51b948184d8d4511f2c0b8e4b4e3abc44144ce1f5968aadd053600a40430ba97ad9e0ad26fe4c444be3f48434a68aa132b1677d8442454fe4c6ae9d3b7164e6603f1c8a8f5b5235ba0b9f5b5f86278e4f69eb4d5388838ef15678535589516a1d85d127da8f46f150613c8a49258be2ed53c3e161d0049cabb40d15f9042a00c494746753b9794a9f66a93b67498c7c59b8253a910457c10353fa8e2edcafdf6c9354a3dc58b5a825c353302d686596c11e4855e86f3c6810f9a4abf917f69a6083330492aedb5621ebc3fd59778a40e0a7fa8450c8b2c6fe3923775419b2ea35cd19abe62c50020df991d9fc772d16dd5208468dc7a9b51c6723495fe0e72e818ee2b2a8581fab2caf6bd914e4876573b023862286ec88a698be2dd34c03925ab5ca0f50f0b2a246ab852e3779f0cf9d3e36f9ab9a50602d5e9216c3a29994e81e151accd88ea346d1be6588068e873
    dhGenerator = 2

    def __init__(self):
        self.localKeypair   = None
        self.remoteKeypair  = None
        self.aesKey         = None
        self.aesIv          = None
        self.aesSalt        = None
        self.dh             = None
        self.aesMode        = AES.MODE_CBC

    def getRandomBytes(self, bytes=128):
        return Random.get_random_bytes(192)

    def generateDHKey(self):
        self.dh = dh.DiffieHellman(self.dhPrime, self.dhGenerator)
        self.dh.generateKeys()

    def computeDHSecret(self, publicKey):
        self.dhSecret = self.dh.computeKey(publicKey)
        hash = self.hash(str(self.dhSecret))
        self.aesKey = hash[0:32]
        self.aesIv = hash[16:32]

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

    def hash(self, message):
        hash = SHA256.new(message).digest()
        return hash

    def stringHash(self, message):
        digest = self.hash(message)
        return hex(self.__octx_to_num(digest))[2:-1].upper()

    def mapStringToInt(self, string):
        num = 0
        shift = 0

        for char in reversed(string):
          num |= ord(char) << shift
          shift += 8

        return num

    def getKeypairAsString(self, passphrase):
        self._keypairPassphrase = passphrase
        return self.localKeypair.as_pem(self.aesMode, self.__passphraseCallback)

    def __generateFingerprint(self, key):
        digest = self.stringHash(key)

        # Add colons between every 2 characters of the fingerprint
        fingerprint = ''
        digestLength = len(digest)
        for i in range(0, digestLength):
            fingerprint += digest[i]
            if i&1 and i != 0 and i != digestLength-1:
                fingerprint += ':'
        return fingerprint

    def __octx_to_num(self, data):
        converted = 0
        length = len(data)
        for i in range(length):
            converted = converted + ord(data[i]) * (256 ** (length - i - 1))
        return converted

    def getDHPubKey(self):
        return self.dh.pub_key

    def __checkLocalKeypair(self):
        if self.localKeypair is None:
            raise exceptions.CryptoError("Local keypair not set.")

    def __checkRemoteKeypair(self):
        if self.remoteKeypair is None:
            raise exceptions.CryptoError("Remote public key not set.")

    def __passphraseCallback(self, ignore, prompt1=None, prompt2=None):
        return self._keypairPassphrase

    def _pad(self, s, bs):
        return s + (bs - len(s) % bs) * chr(bs - len(s) % bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

def binToDec(binval):
    multi = 1
    dec = 0
    for item in binval[::-1]:
        if item=='1':
            dec=dec+multi
        multi=multi*2
    import binascii
    hex = binascii.hexlify(str(dec))
    return int(hex, 16)