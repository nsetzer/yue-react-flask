


from Crypto.Cipher import Salsa20
from Crypto.Random import get_random_bytes
from Crypto.Hash import HMAC, SHA256

import hashlib

def sha512_kdf(key1):
    """ return the sha256 digest of a byte-string """
    m = hashlib.sha512()
    m.update(key1)
    digest = m.digest()
    return digest[:32], digest[32:]

class ApplicationToken(object):
    """
    A token which is at most 256 bytes

    The token is signed using a key which is used to verify
    that the token is legitmate and not tampered with.

    the token can contain a small amount of data
    """

    @staticmethod
    def new(secret, payload, nonce=None):
        key1, key2 = sha512_kdf(secret)
        hmac = HMAC.new(key1, digestmod=SHA256)
        cipher = Salsa20.new(key2, nonce)

        enctext = cipher.encrypt(payload)

        b16nonce = cipher.nonce.hex()
        b16text = enctext.hex()

        hmac.update(cipher.nonce)
        hmac.update(enctext)

        b16mac = hmac.hexdigest()

        length = 176  # 256 - 80

        if len(b16text) > 176:
            raise ValueError("payload too long")

        token = b16mac + b16nonce + b16text

        return token

    def validate(secret, token):

        b16mac = token[:64]
        b16nonce = token[64: 80]
        b16text = token[80:]

        mac = bytes.fromhex(b16mac)
        nonce = bytes.fromhex(b16nonce)
        enctext = bytes.fromhex(b16text)

        key1, key2 = sha512_kdf(secret)
        hmac = HMAC.new(key1, digestmod=SHA256)
        cipher = Salsa20.new(key2, nonce)

        hmac.update(nonce)
        hmac.update(enctext)
        hmac.verify(mac)

        text = cipher.decrypt(enctext)

        return text

if __name__ == '__main__':
    token = ApplicationToken.new(b"test", b"userid")
    print(token)
    print(ApplicationToken.validate(b"test", token))

