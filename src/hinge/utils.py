import os
import sys
import time


# Constants

DEFAULT_TURN_SERVER = '127.0.0.1'
DEFAULT_PORT = 9000
PROTOCOL_VERSION = '1'
NICK_MAX_LEN = 32
DEFAULT_AES_MODE = 'aes_256_cbc'
DEFAULT_RSA_BITS = 4096
DEFAULT_HASH_TYPE = 'sha512'
TYPING_TIMEOUT = 1500

# Server commands

COMMAND_REGISTER = "REG"
COMMAND_RELAY = "REL"
COMMAND_ADD = "ADD"
COMMAND_VERSION = "VERSION"
COMMAND_GET_REMOTE = "REMOTE"
COMMAND_GET_ID = "GETID"
COMMAND_SEND_ID = "SENDID"

# Handshake commands

COMMAND_HELO = "HELO"
COMMAND_REDY = "REDY"
COMMAND_REJECT = "REJ"
COMMAND_PUB_KEY = "PUB_KEY"

# Loop commands

COMMAND_MSG = "MSG"
COMMAND_TYPING = "TYPING"
COMMAND_END = "END"
COMMAND_ERR = "ERR"
COMMAND_SMP_0 = "SMP0"
COMMAND_SMP_1 = "SMP1"
COMMAND_SMP_2 = "SMP2"
COMMAND_SMP_3 = "SMP3"
COMMAND_SMP_4 = "SMP4"
SMP_COMMANDS = [
    COMMAND_SMP_0,
    COMMAND_SMP_1,
    COMMAND_SMP_2,
    COMMAND_SMP_3,
    COMMAND_SMP_4,
]
LOOP_COMMANDS = [
    COMMAND_MSG,
    COMMAND_TYPING,
    COMMAND_END,
    COMMAND_ERR,
    COMMAND_SMP_0,
    COMMAND_SMP_1,
    COMMAND_SMP_2,
    COMMAND_SMP_3,
    COMMAND_SMP_4,
]

# Message sources

MSG_SENDER = 0
MSG_RECEIVER = 1
MSG_SERVICE = 2

# Typing statuses

TYPING_START = 0
TYPING_STOP_WITHOUT_TEXT = 1
TYPING_STOP_WITH_TEXT = 2

# QT UI Button codes

BUTTON_OKAY = 0
BUTTON_CANCEL = 1
BUTTON_FORGOT = 2

# Ncurses accept/mode dialog codes

ACCEPT = 0
REJECT = 1

# Other

CONNECT = 0
WAIT = 1

SMP_CALLBACK_REQUEST = 0
SMP_CALLBACK_COMPLETE = 1
SMP_CALLBACK_ERROR = 2

URL_REGEX = r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?]))"

# Exceptions

class GenericError(Exception):

    def __init__(self, err=0, msg=None):
        Exception.__init__(self)
        self.err = err
        self.msg = msg


class NetworkError(GenericError):
    pass


class ProtocolError(GenericError):
    pass


class ProtocolEnd(GenericError):
    pass


class CryptoError(GenericError):
    pass

# Nick validation statuses

VALID_NICK = 0
INVALID_NICK_CONTENT = 1
INVALID_NICK_LENGTH = 2
INVALID_EMPTY_NICK = 3

# UI error messages

TITLE_CONNECTION_ENDED          = "Connection Ended"
TITLE_NETWORK_ERROR             = "Network Error"
TITLE_CRYPTO_ERROR              = "Crypto Error"
TITLE_END_CONNECTION            = "Connection Ended"
TITLE_INVALID_NICK              = "Invalid Nickname"
TITLE_NICK_NOT_FOUND            = "Nickname Not Found"
TITLE_CONNECTION_REJECTED       = "Connection Rejected"
TITLE_PROTOCOL_ERROR            = "Invalid Response"
TITLE_CLIENT_EXISTS             = "Client Exists"
TITLE_SELF_CONNECT              = "Self Connection"
TITLE_SERVER_SHUTDOWN           = "Server Shutdown"
TITLE_INVALID_COMMAND           = "Invalid Command"
TITLE_ALREADY_CONNECTED         = "Already Chatting"
TITLE_UNKNOWN_ERROR             = "Unknown Error"
TITLE_EMPTY_NICK                = "No Nickname Provided"
TITLE_NETWORK_ERROR             = "Network Error"
TITLE_BAD_HMAC                  = "Tampering Detected"
TITLE_BAD_DECRYPT               = "Decryption Error"
TITLE_NICK_IN_USE               = "Nickname Not Available"
TITLE_KICKED                    = "Kicked"
TITLE_SMP_MATCH_FAILED          = "Eavesdropping Detected"
TITLE_MESSAGE_REPLAY            = "Tampering Detected"
TITLE_MESSAGE_DELETION          = "Tampering Detected"
TITLE_PROTOCOL_VERSION_MISMATCH = "Incompatible Versions"

UNEXPECTED_CLOSE_CONNECTION = "Server unexpectedly closed connection"
CLOSE_CONNECTION            = "The server closed the connection"
UNEXPECTED_DATA             = "Remote sent unexpected data"
UNEXPECTED_COMMAND          = "Receieved unexpected command"
NO_COMMAND_SEPARATOR        = "Command separator not found in message"
UNKNOWN_ENCRYPTION_TYPE     = "Unknown encryption type"
VERIFY_PASSPHRASE_FAILED    = "Passphrases do not match"
BAD_PASSPHRASE              = "Wrong passphrase"
BAD_PASSPHRASE_VERBOSE      = "An incorrect passphrase was entered"
FAILED_TO_START_SERVER      = "Error starting server"
FAILED_TO_ACCEPT_CLIENT     = "Error accepting client connection"
FAILED_TO_CONNECT           = "Error connecting to server"
CLIENT_ENDED_CONNECTION     = "The client requested to end the connection"
INVALID_NICK_CONTENT        = "Sorry, nicknames can only contain numbers and letters"
INVALID_NICK_LENGTH         = "Sorry, nicknames must be less than %d characters" % NICK_MAX_LEN
NICK_NOT_FOUND              = "%s is not connected to the server"
CONNECTION_REJECTED         = "%s rejected your connection"
PROTOCOL_ERROR              = "%s sent unexpected data"
CLIENT_EXISTS               = "%s is open in another tab already"
CONNECTION_ENDED            = "%s has disconnected"
SELF_CONNECT                = "You cannot connect to yourself"
SERVER_SHUTDOWN             = "The server is shutting down"
INVALID_COMMAND             = "An invalid command was recieved from %s"
ALREADY_CONNECTED           = "A chat with %s is already open"
UNKNOWN_ERROR               = "An unknown error occured with %s"
EMPTY_NICK                  = "Please enter a nickname"
NETWORK_ERROR               = "A network error occured while communicating with the server. Try connecting to the server again."
BAD_HMAC                    = "Warning: Automatic data integrity check failed. Someone may be tampering with your conversation."
BAD_DECRYPT                 = "Unable to decrypt incoming message. This usually happens when the client sends malformed data."
NICK_IN_USE                 = "Sorry, someone else is already using that nickname"
KICKED                      = "You have been kicked off the server"
SMP_MATCH_FAILED            = "Chat authentication failed. Either your buddy provided the wrong answer to the question or someone may be attempting to eavesdrop on your conversation. Note that answers are case sensitive."
SMP_MATCH_FAILED_SHORT      = "Chat authentication failed. Note that answers are case sensitive."
MESSAGE_REPLAY              = "Warning: Old message recieved multiple times. Someone may be tampering with your conversation."
MESSAGE_DELETION            = "Warning: Message deletion detected. Someone may be tampering with your conversation."
PROTOCOL_VERSION_MISMATCH = "The server is reporting that you are using an outdated version of the program. Are you running the most recent version?"

# Error codes

ERR_CONN_ENDED = 0
ERR_NICK_NOT_FOUND = 1
ERR_CONN_REJECTED = 2
ERR_BAD_HANDSHAKE = 3
ERR_CLIENT_EXISTS = 4
ERR_SELF_CONNECT = 5
ERR_SERVER_SHUTDOWN = 6
ERR_INVALID_COMMAND = 7
ERR_ALREADY_CONNECTED = 8
ERR_NETWORK_ERROR = 9
ERR_BAD_HMAC = 10
ERR_BAD_DECRYPT = 11
ERR_INVALID_NICK = 12
ERR_NICK_IN_USE = 13
ERR_CLOSED_CONN = 14
ERR_KICKED = 15
ERR_SMP_CHECK_FAILED = 16
ERR_SMP_MATCH_FAILED = 17
ERR_MESSAGE_REPLAY = 18
ERR_MESSAGE_DELETION = 19
ERR_PROTOCOL_VERSION_MISMATCH = 20

# Functions

def isValidNick(nick):
    if nick == "":
        return INVALID_EMPTY_NICK
    if not nick.isalnum():
        return INVALID_NICK_CONTENT
    if len(nick) > NICK_MAX_LEN:
        return INVALID_NICK_LENGTH
    return VALID_NICK

def getTimestamp():
    return time.strftime('%H:%M:%S', time.localtime())

def getAbsoluteResourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        try:
            base_path = os.path.dirname(sys.modules[''].__file__)
        except Exception:
            base_path = ''

        if not os.path.exists(os.path.join(base_path, relative_path)):
            base_path = ''
    path = os.path.join(base_path, relative_path)
    if not os.path.exists(path):
        return None
    else:
        return path

def secureStrcmp(left, right):
    equal = True
    if len(left) != len(right):
        equal = False
    for i in range(0, min(len(left), len(right))):
        if left[i] != right[i]:
            equal = False
    return equal
