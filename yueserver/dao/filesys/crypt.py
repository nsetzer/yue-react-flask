
from Crypto.Cipher import Salsa20, AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import HMAC, SHA256

from binascii import hexlify as to_hex, unhexlify as from_hex
from datetime import datetime, timezone
import base64
import bcrypt
import hashlib
import struct
import time
import uuid

def generate_secure_password():
    return base64.b64encode(get_random_bytes(32)).decode("utf-8")

def sha512(msg):
    """ return the sha256 digest of a byte-string """
    m = hashlib.sha512()
    m.update(msg)
    return m.digest()

def sha256(msg):
    """ return the sha256 digest of a byte-string """
    m = hashlib.sha256()
    m.update(msg)
    return m.digest()

def _crypt_cipher(salt, password, nonce=None):
    """ derive a encryption key using a password, using bcrypt
    return an object implementing encrypt(x) and decrypt(x)
    """
    # bcrypt has a maximum input length of 50-72 bytes
    # use the sha256 digest (32 bytes) then base 64 encode (44 bytes)
    # to prevent null bytes in the string
    digest = base64.b64encode(sha256(password.encode("utf-8")))
    hashed = bcrypt.hashpw(digest, salt)
    # hash the bcrypt output, which is only 248 bits.
    #   known values including the salt are 29 bytes
    #   while the hashed value is 31 bytes
    # use sha512, so that two 256 bit keys can be derived.
    key = sha512(hashed)
    # the first 32 bytes are used as the hmac key
    # the digest is SHA256 to minimize the final output byte size
    key1 = key[:32]
    hmac = HMAC.new(key1, digestmod=SHA256)
    # the last 32 bytes are used for the cipher key
    key2 = key[32:]
    cipher = Salsa20.new(key2, nonce)
    return hmac, cipher

KEY_LENGTH = 135
KEY_LENGTH_PARTS = (2, 29, 12, 44, 44)

def cryptkey(password, text=None, nonce=None, salt=None, workfactor=12):
    """
    password: utf-8 string
    text: bytes, length==32, optional
    salt: optional, a bcrypt salt
    workfactor: bcrypt work factor

    returns a new encryption key, a utf-8 string, which is encrypted
    using the given password. use decryptkey to decrypt the output of
    this method

    A MAC is included to validate whether the correct password was provided
    HMAC with SHA256 is used in "Encrypt then MAC" mode and ensures
    that the salt, nonce, and text have not been tampered with.
    the HMAC key is derived from the given password

    if text is None then return a new, securely generated encryption key
    otherwise encrypt the given encryption key

    this allows for the true encryption key to be stored securely on disk,
    and to be re-encrypted with a new password

    if a salt is given, the workfactor is not used. if the salt is not
    a valid bcrypt salt, a ValueError is raised. If the salt is not
    given the workfactor is used to generate a new random salt
    """
    btag = b"01"  # version tag
    if salt is None:
        salt = bcrypt.gensalt(workfactor)
    hmac, cipher = _crypt_cipher(salt, password, nonce)
    if text is None:
        text = get_random_bytes(32)
    if len(text) != 32:
        raise Exception("invalid key (len: %d expected: 32" % len(text))
    b64nonce = base64.b64encode(cipher.nonce)
    b64text = base64.b64encode(cipher.encrypt(text))

    hmac.update(struct.pack("<I", len(btag)))
    hmac.update(btag)
    hmac.update(struct.pack("<I", len(salt)))
    hmac.update(salt)
    hmac.update(struct.pack("<I", len(b64nonce)))
    hmac.update(b64nonce)
    hmac.update(struct.pack("<I", len(b64text)))
    hmac.update(b64text)

    b64mac = base64.b64encode(hmac.digest())

    # combine the bcrypt salt, the salsa nonce, and the encrypted text, and mac

    return (b':'.join([btag, salt, b64nonce, b64text, b64mac])).decode("utf-8")

def decryptkey(password, key):
    """
    decrypts an encryption key using the given password

    returns 32 bytes which can be used as an encryption key

    a ValueError Exception is raised if an invalid password is given
    """

    # unfortunately, the way _crypt_cipher is implemented prevents me
    # from validating the hmac before working with the string.
    btag, salt, b64nonce, b64text, b64mac = key.encode("utf-8").split(b':', 4)
    nonce = base64.b64decode(b64nonce)
    hmac, cipher = _crypt_cipher(salt, password, nonce)
    # verify the mac before decrypting the text
    # this ensures the correct password is given
    # and that the key has not been tampered with

    hmac.update(struct.pack("<I", len(btag)))
    hmac.update(btag)
    hmac.update(struct.pack("<I", len(salt)))
    hmac.update(salt)
    hmac.update(struct.pack("<I", len(b64nonce)))
    hmac.update(b64nonce)
    hmac.update(struct.pack("<I", len(b64text)))
    hmac.update(b64text)
    hmac.verify(base64.b64decode(b64mac))

    text = cipher.decrypt(base64.b64decode(b64text))

    return text

def recryptkey(password, new_password, key, workfactor=12):
    """decrypt a key using password, then re-encrypt using a new password"""

    enckey = decryptkey(password, key)

    return cryptkey(new_password, enckey, workfactor=workfactor)

def validatekey(key):
    """
    check that the given key is fell formed.
    It should be a string with a well known length,
    And should be composed of multiple parts.
    Each part also has a well known length.

    raise an exception if the key is not well formed
    return the key unmodifed if valid

    this does not attempt to decrypt the key to check
    if the contents are valid
    """

    if len(key) != KEY_LENGTH:
        raise ValueError("Invalid key length")

    alphabet = ".:=/+$0123456789" \
        "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \

    for c in key:
        if c not in alphabet:
            raise ValueError("Invalid character")

    parts = key.split(':')

    if len(parts) != len(KEY_LENGTH_PARTS):
        raise ValueError("Invalid key length")

    if not parts[1].startswith('$2b$'):
        raise ValueError("Invalid key length")

    for part, length in zip(parts, KEY_LENGTH_PARTS):
        if len(part) != length:
            raise ValueError("Invalid key length")

    return key

class _Closeable(object):

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

def sha512_kdf(key1, key2):
    """ return the sha256 digest of a byte-string """
    m = hashlib.sha512()
    m.update(key1)
    m.update(key2)
    digest = m.digest()
    return digest[:32], digest[32:]

HEADER_SIZE = 80

def new_stream_cipher(key1, nonce=None, key2=None):
    """
    returns a new cipher for encryption and returns a
    string of bytes containing the nonce and an HMAC checksum.

    the HMAC is solely to validate that the correct password
    is given before attempting to decrypt the content, and will
    not protect against modification of the cipher text.

    the cipher returned is a streaming cipher (Salsa20) meant to be used
    to encrypt or decrypt data in a streaming context

    key1 is intended to be the output from decryptkey, 32 bytes, and
    no password hardening is provided at this level

    key2 is a cryptographic randomly generate 32 bytes used to mix in
    with the given key. this ensures that a different key is used for the
    cipher and the mac, and that keys are not reused with different files.

    security / usefulness trade-off:
        files encrypted in this way are not encrypted in the best possible way
    a third party could tamper with the contents.
    """

    if len(key1) != 32:
        raise ValueError("key1 should be 32 bytes")

    if key2 is None:
        key2 = get_random_bytes(32)

    if len(key2) != 32:
        raise ValueError("key2 should be 32 bytes")

    skey1, skey2 = sha512_kdf(key1, key2)
    cipher = Salsa20.new(skey1, nonce)
    hmac = HMAC.new(skey2, digestmod=SHA256)

    tag = b"EYUE" + struct.pack("<I", 1)
    hmac.update(tag)
    hmac.update(cipher.nonce)
    hmac.update(key2)

    # generate a 32 byte digest which will be used to validate that
    # the correct password was given at decryption time
    digest = hmac.digest()

    header = tag + cipher.nonce + key2 + digest
    return cipher, header

def get_stream_cipher(key1, header):
    """
    given a key and an 80 byte header, return a new cipher for decryption

    The Header contains a 32 byte HMAC which will be validated to ensures
    the correct decryption key is used
    """

    if len(key1) != 32:
        raise ValueError("key1 should be 32 bytes")

    if len(header) < HEADER_SIZE:
        raise ValueError("Invalid header size: %d" % len(header))
    tag = header[:8]

    # if needed, version could change how the cipher is generated.
    version = struct.unpack("<I", header[4:8])[0]

    nonce = header[8:16]
    key2 = header[16:48]
    digest = header[48:HEADER_SIZE]

    skey1, skey2 = sha512_kdf(key1, key2)
    hmac = HMAC.new(skey2, digestmod=SHA256)

    hmac.update(tag)
    hmac.update(nonce)
    hmac.update(key2)
    hmac.verify(digest)

    cipher = Salsa20.new(skey1, nonce)
    return cipher

class FileEncryptorWriter(_Closeable):
    """ wrap a writable file-like object and encrypt the contents as it is written
    an 8 byte header is added to the file
    """
    HEADER_SIZE = HEADER_SIZE

    def __init__(self, wf, key, nonce=None, key2=None):
        super(FileEncryptorWriter, self).__init__()
        self.wf = wf

        self.cipher, header = new_stream_cipher(key, nonce, key2=key2)
        # version 2 could add an HMAC
        # https://pycryptodome.readthedocs.io/en/latest/src/hash/hmac.html
        self.wf.write(header)

    def write(self, b):
        n = len(b)
        self.wf.write(self.cipher.encrypt(b))
        return n

    def close(self):
        self.wf.close()

class FileEncryptorReader(_Closeable):
    """ wrap a readable file-like object and encrypt the contents as it is read
    an 80 byte header is added to the file
    """
    HEADER_SIZE = HEADER_SIZE

    def __init__(self, rf, key, nonce=None, key2=None):
        super(FileEncryptorReader, self).__init__()
        self.rf = rf

        self.cipher, self.header = new_stream_cipher(key, nonce, key2=key2)

    def read(self, n=-1):

        if n < 0:
            # read the contents of the entire file
            if self.header:
                b = self.header + self.cipher.encrypt(self.rf.read())
                return b
            return self.cipher.encrypt(self.rf.read())

        elif n < len(self.header):
            # return part of the header
            b = self.header[:n]
            self.header = self.header[n:]
            return b

        # return the requested number of bytes, encrypted
        if self.header:
            # return the header along and enough bytes to fill up to n
            n = n - len(self.header)
            b = self.header
            self.header = b""
            if n > 0:
                b += self.cipher.encrypt(self.rf.read(n))
            return b
        return self.cipher.encrypt(self.rf.read(n))

    def close(self):
        self.rf.close()

class FileDecryptorReader(_Closeable):
    """ wrap a readable file-like object and decrypt the contents as it is read
    """
    def __init__(self, rf, key):
        super(FileDecryptorReader, self).__init__()
        self.rf = rf

        header = self.rf.read(80)
        self.cipher = get_stream_cipher(key, header)

    def read(self, *args):
        return self.cipher.decrypt(self.rf.read(*args))

    def close(self):
        self.rf.close()

class FileDecryptorWriter(_Closeable):
    """ wrap a writable file-like object and decrypt the contents as it is written
    """
    def __init__(self, wf, key):
        super(FileDecryptorWriter, self).__init__()
        self.wf = wf

        self.key = key
        self.header = b''
        self.cipher = None
        self.nonce = b''
        self.nonce_length = -1
        self.version = -1

    def write(self, b):
        """ write a file and decrypt the contents on the fly

        the first 16 bytes written will be decoded as the header.
        the following 8 bytes will contain a nonce for decryption.
        the remaining bytes written are then decrypted and written to the
        underlying output file
        """
        n = len(b)

        if len(self.header) < HEADER_SIZE:
            s = HEADER_SIZE - len(self.header)
            self.header += b[:s]
            b = b[s:]

        if len(self.header) == HEADER_SIZE and self.cipher is None:
            self.cipher = get_stream_cipher(self.key, self.header)

        if b:
            if self.cipher is None:
                raise Exception("Error initializing cipher")
            self.wf.write(self.cipher.decrypt(b))

        return n

    def close(self):
        self.wf.close()

_epoch = int(datetime(2010, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp())
_two_weeks = 2 * 7 * 24 * 60 * 60

def tpack(timestamp):
    return (int(timestamp) - _epoch) >> 8

def tpackb(timestamp):
    """ pack a timestamp into 3 bytes """
    return tpack(timestamp).to_bytes(3, 'big')

def tunpack(timestamp):
    return (int(timestamp)  << 8) + _epoch

def tunpackb(data):
    """ unpack a 3 byte timestamp """
    return tunpack(int.from_bytes(data, 'big'))

def tfmt(timestamp):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(timestamp)))

def uuid_token_generate(key, uuidstr, expiry=_two_weeks, now=None):
    """ generate a token containing a uuid


    key:     a 16byte key used for AES-GCM encryption
    uuidstr: a uuid4 string to encrypt

    the token expires 'expires' seconds from the current time
    the token is made of two parts, an unencrypted nonce containing
    version, timestamp, and random data. and the encrypted uuid
    AES-GCM is used with the nonce as the AAD ensuring data integrity
    if any part of the token is modified.

    the resulting token is exactly 50 ascii characters and case sensitive

    Note: AES-GCM uses a 12 byte nonce
    """
    user = from_hex(uuid.UUID(uuidstr).hex)

    version = b'\x01'
    t = now if now is not None else time.time()
    timestamp = tpackb(t + expiry)
    randbytes = get_random_bytes(1)

    nonce = version + timestamp + randbytes + b"\x00" * 7
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(nonce)
    text, tag = cipher.encrypt_and_digest(user)

    data = version + timestamp + randbytes + text + tag
    token = base64.b64encode(data, b'-+').decode("ascii")
    return token.rstrip('=')

def uuid_token_verify(key, token, now=None):
    """ verify a uuid token and return the uuid string

    key:     a 16byte key used for AES-GCM encryption
    token:   an encrypted uuid4 string

    """

    if len(token) != 50:
        raise ValueError("token not formatted correctly: %d" % (len(token)))

    data = base64.b64decode(token.encode("ascii") + b'==', b'-+')

    version = data[:1]

    if version != b'\x01':
        raise ValueError("Invalid token version")

    timestamp = data[1:4]
    randbytes = data[4:5]
    text = data[5:21]
    tag = data[21:]

    expires = tunpackb(timestamp)
    t = now if now is not None else time.time()
    if expires < t:
        raise ValueError('token has expired: %s' % tfmt(expires))

    nonce = version + timestamp + randbytes + b"\x00" * 7
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(nonce)
    user = cipher.decrypt_and_verify(text, tag)
    return str(uuid.UUID(to_hex(user).decode('ascii')))


