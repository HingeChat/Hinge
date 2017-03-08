from src.hinge.crypto import CryptoUtils
import struct

from src.hinge.utils import *


def packList(*items):
    buffer = b''

    # For each item in the list, convert it to a byte string and add its length as a prefix
    for item in items:
        new_bytes = longToBytes(item)
        buffer += struct.pack('!I', len(new_bytes)) + new_bytes

    return buffer


def unpackList(buffer):
    items = []

    index = 0
    while index < len(buffer):
        # Get the length of the long (4 byte int before the actual long)
        length = struct.unpack('!I', buffer[index:index+4])[0]
        index += 4

        # Convert the data back to a long and add it to the list
        item = bytesToLong(buffer[index:index+length])
        items.append(item)
        index += length

    return items


def bytesToLong(new_bytes):
    length = len(new_bytes)
    string = 0
    for i in range(length):
        string += byteToLong(new_bytes[i:i+1]) << 8*(length-i-1)
    return string


def longToBytes(long):
    new_bytes = b''
    while long != 0:
        new_bytes = longToByte(long & 0xff) + new_bytes
        long >>= 8
    return new_bytes


def byteToLong(byte):
    return struct.unpack('B', byte)[0]


def longToByte(long):
    return struct.pack('B', long)


def mulm(x, y, mod):
    return x * y % mod


def subm(x, y, mod):
    return (x - y) % mod


def createRandomExponent():
    new_bytes = CryptoUtils.CryptoUtils().getRandomBytes(192)
    return CryptoUtils.binToDec(new_bytes)


class SMP(object):

    def __init__(self, secret=None):
        self.mod = int('0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C662'
                       '8B80DC1CD129024E088A67CC74020BBEA63B139B'
                       '22514A08798E3404DDEF9519B3CD3A431B302B0A'
                       '6DF25F14374FE1356D6D51C245E485B576625E7E'
                       'C6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386B'
                       'FB5A899FA5AE9F24117C4B1FE649286651ECE45B'
                       '3DC2007CB8A163BF0598DA48361C55D39A69163F'
                       'A8FD24CF5F83655D23DCA3AD961C62F356208552'
                       'BB9ED529077096966D670C354E4ABC9804F1746C'
                       '08CA18217C32905E462E36CE3BE39E772C180E86'
                       '039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCB'
                       'F6955817183995497CEA956AE515D2261898FA05'
                       '1015728E5A8AACAA68FFFFFFFFFFFFFFFF', 0)
        self.mod_order = (self.mod - 1) // 2
        self.gen = 2
        self.match = False
        self.crypto = CryptoUtils.CryptoUtils()
        self.secret = self.crypto.mapStringToInt(secret)

    def step1(self):
        self.x2 = createRandomExponent()
        self.x3 = createRandomExponent()

        self.g2 = pow(self.gen, self.x2, self.mod)
        self.g3 = pow(self.gen, self.x3, self.mod)

        (c1, d1) = self.createLogProof('1', self.x2)
        (c2, d2) = self.createLogProof('2', self.x3)

        # Send g2a, g3a, c1, d1, c2, d2
        return packList(self.g2, self.g3, c1, d1, c2, d2)

    def step2(self, buffer):
        (g2a, g3a, c1, d1, c2, d2) = unpackList(buffer)

        if not self.isValidArgument(g2a) or not self.isValidArgument(g3a):
            raise CryptoError("Invalid g2a/g3a values", ERR_SMP_CHECK_FAILED)

        if not self.checkLogProof('1', g2a, c1, d1):
            raise CryptoError("Proof 1 check failed", ERR_SMP_CHECK_FAILED)

        if not self.checkLogProof('2', g3a, c2, d2):
            raise CryptoError("Proof 2 check failed", ERR_SMP_CHECK_FAILED)

        self.g2a = g2a
        self.g3a = g3a

        self.x2 = createRandomExponent()
        self.x3 = createRandomExponent()

        r = createRandomExponent()

        self.g2 = pow(self.gen, self.x2, self.mod)
        self.g3 = pow(self.gen, self.x3, self.mod)

        (c3, d3) = self.createLogProof('3', self.x2)
        (c4, d4) = self.createLogProof('4', self.x3)

        self.gb2 = pow(self.g2a, self.x2, self.mod)
        self.gb3 = pow(self.g3a, self.x3, self.mod)

        self.pb = pow(self.gb3, r, self.mod)
        self.qb = mulm(pow(self.gen, r, self.mod), pow(self.gb2, self.secret, self.mod), self.mod)

        (c5, d5, d6) = self.createCoordsProof('5', self.gb2, self.gb3, r)

        # Sends g2b, g3b, pb, qb, all the c's and d's
        return packList(self.g2, self.g3, self.pb, self.qb, c3, d3, c4, d4, c5, d5, d6)

    def step3(self, buffer):
        (g2b, g3b, pb, qb, c3, d3, c4, d4, c5, d5, d6) = unpackList(buffer)

        if not self.isValidArgument(g2b) or not self.isValidArgument(g3b) or \
           not self.isValidArgument(pb) or not self.isValidArgument(qb):
            raise CryptoError("Invalid g2b/g3b/pb/qb values", ERR_SMP_CHECK_FAILED)

        if not self.checkLogProof('3', g2b, c3, d3):
            raise CryptoError("Proof 3 check failed", ERR_SMP_CHECK_FAILED)

        if not self.checkLogProof('4', g3b, c4, d4):
            raise CryptoError("Proof 4 check failed", ERR_SMP_CHECK_FAILED)

        self.g2b = g2b
        self.g3b = g3b

        self.ga2 = pow(self.g2b, self.x2, self.mod)
        self.ga3 = pow(self.g3b, self.x3, self.mod)

        if not self.checkCoordsProof('5', c5, d5, d6, self.ga2, self.ga3, pb, qb):
            raise CryptoError("Proof 5 check failed", ERR_SMP_CHECK_FAILED)

        s = createRandomExponent()

        self.qb = qb
        self.pb = pb
        self.pa = pow(self.ga3, s, self.mod)
        self.qa = mulm(pow(self.gen, s, self.mod), pow(self.ga2, self.secret, self.mod), self.mod)

        (c6, d7, d8) = self.createCoordsProof('6', self.ga2, self.ga3, s)

        inv = self.invm(qb)
        self.ra = pow(mulm(self.qa, inv, self.mod), self.x3, self.mod)

        (c7, d9) = self.createEqualLogsProof('7', self.qa, inv, self.x3)

        # Sends pa, qa, ra, c6, d7, d8, c7, d9
        return packList(self.pa, self.qa, self.ra, c6, d7, d8, c7, d9)

    def step4(self, buffer):
        (pa, qa, ra, c6, d7, d8, c7, d9) = unpackList(buffer)

        if not self.isValidArgument(pa) or not self.isValidArgument(qa) or not self.isValidArgument(ra):
            raise CryptoError("Invalid pa/qa/ra values", ERR_SMP_CHECK_FAILED)

        if not self.checkCoordsProof('6', c6, d7, d8, self.gb2, self.gb3, pa, qa):
            raise CryptoError("Proof 6 check failed", ERR_SMP_CHECK_FAILED)

        if not self.checkEqualLogs('7', c7, d9, self.g3a, mulm(qa, self.invm(self.qb), self.mod), ra):
            raise CryptoError("Proof 7 check failed", ERR_SMP_CHECK_FAILED)

        inv = self.invm(self.qb)
        rb = pow(mulm(qa, inv, self.mod), self.x3, self.mod)

        (c8, d10) = self.createEqualLogsProof('8', qa, inv, self.x3)

        rab = pow(ra, self.x3, self.mod)

        inv = self.invm(self.pb)
        if rab == mulm(pa, inv, self.mod):
            self.match = True

        # Send rb, c8, d10
        return packList(rb, c8, d10)

    def step5(self, buffer):
        (rb, c8, d10) = unpackList(buffer)

        if not self.isValidArgument(rb):
            raise CryptoError("Invalid rb values", ERR_SMP_CHECK_FAILED)

        if not self.checkEqualLogs('8', c8, d10, self.g3b, mulm(self.qa, self.invm(self.qb), self.mod), rb):
            raise CryptoError("Proof 8 check failed", ERR_SMP_CHECK_FAILED)

        rab = pow(rb, self.x3, self.mod)

        inv = self.invm(self.pb)
        if rab == mulm(self.pa, inv, self.mod):
            self.match = True

    def createLogProof(self, version, x):
        rand_exponent = createRandomExponent()
        c = self.generateHash(version + str(pow(self.gen, rand_exponent, self.mod)))
        d = subm(rand_exponent, mulm(x, c, self.mod_order), self.mod_order)
        return (c, d)

    def checkLogProof(self, version, g, c, d):
        gd = pow(self.gen, d, self.mod)
        gc = pow(g, c, self.mod)
        gdgc = gd * gc % self.mod
        return (self.generateHash(version + str(gdgc)) == c)

    def createCoordsProof(self, version, g2, g3, r):
        r1 = createRandomExponent()
        r2 = createRandomExponent()

        tmp1 = pow(g3, r1, self.mod)
        tmp2 = mulm(pow(self.gen, r1, self.mod), pow(g2, r2, self.mod), self.mod)

        c = self.generateHash(version + str(tmp1) + str(tmp2))

        d1 = subm(r1, mulm(r, c, self.mod_order), self.mod_order)
        d2 = subm(r2, mulm(self.secret, c, self.mod_order), self.mod_order)

        return (c, d1, d2)

    def checkCoordsProof(self, version, c, d1, d2, g2, g3, p, q):
        tmp1 = mulm(pow(g3, d1, self.mod), pow(p, c, self.mod), self.mod)
        tmp2 = mulm(mulm(pow(self.gen, d1, self.mod), pow(g2, d2, self.mod), self.mod), pow(q, c, self.mod), self.mod)

        cprime = self.generateHash(version + str(tmp1) + str(tmp2))

        return (c == cprime)

    def createEqualLogsProof(self, version, qa, qb, x):
        r = createRandomExponent()
        tmp1 = pow(self.gen, r, self.mod)
        qab = mulm(qa, qb, self.mod)
        tmp2 = pow(qab, r, self.mod)

        c = self.generateHash(version + str(tmp1) + str(tmp2))
        tmp1 = mulm(x, c, self.mod_order)
        d = subm(r, tmp1, self.mod_order)

        return (c, d)

    def checkEqualLogs(self, version, c, d, g3, qab, r):
        tmp1 = mulm(pow(self.gen, d, self.mod), pow(g3, c, self.mod), self.mod)
        tmp2 = mulm(pow(qab, d, self.mod), pow(r, c, self.mod), self.mod)

        cprime = self.generateHash(version + str(tmp1) + str(tmp2))

        return (c == cprime)

    def invm(self, x):
        return pow(x, self.mod-2, self.mod)

    def isValidArgument(self, val):
        return (val >= 2 and val <= self.mod-2)

    def generateHash(self, message):
        return int(self.crypto.stringHash(message), 16)
