
import os
import sys
import base64

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP

class CryptoManager(object):

    """ RSA / AES scheme for storing secrets

    Generate a public and private key used for encrypting and
    decrypting secrets.

    The public key is used to encrypt and is intended to be
    distributed to any entity which needs to be able to encrypt
    secrets for configuration purposes

    The private key is used to decrypt and is intended to
    be used by the server at runtime to decrypt configuration values

    """
    def __init__(self):
        super(CryptoManager, self).__init__()

    def new_key(self, size=2048):

        key = RSA.generate(size)
        private_key = key.export_key()
        public_key = key.publickey().export_key()

        return private_key, public_key

    def generate_key(self, outdir, name, size=2048):

        pub_name = os.path.join(outdir, name + ".pub")
        pem_name = os.path.join(outdir, name + ".pem")

        private_key, public_key = self.new_key(size)

        with open(pem_name, "wb") as wb:
            wb.write(private_key)

        with open(pub_name, "wb") as wb:
            wb.write(public_key)

        return private_key, public_key

    def load_key(self, outdir, name):
        private_key = RSA.import_key(open("private.pem").read())
        public_key = RSA.import_key(open("public.pem").read())
        return private_key, public_key

    def encrypt(self, public_key, data):

        key = RSA.import_key(public_key)

        session_key = get_random_bytes(16)
        # Encrypt the session key with the public RSA key
        cipher_rsa = PKCS1_OAEP.new(key)
        enc_session_key = cipher_rsa.encrypt(session_key)
        # Encrypt the data with the AES session key
        cipher_aes = AES.new(session_key, AES.MODE_EAX)
        ciphertext, tag = cipher_aes.encrypt_and_digest(data)

        return enc_session_key + cipher_aes.nonce + tag + ciphertext

    def decrypt(self, private_key, data):

        key = RSA.import_key(private_key)

        n1 = key.size_in_bytes()
        n2 = n1 + 16
        n3 = n2 + 16

        enc_session_key = data[:n1]
        nonce = data[n1:n2]
        tag = data[n2:n3]
        ciphertext = data[n3:]

        # Decrypt the session key with the private RSA key
        cipher_rsa = PKCS1_OAEP.new(key)
        session_key = cipher_rsa.decrypt(enc_session_key)

        # Decrypt the data with the AES session key
        cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
        data = cipher_aes.decrypt_and_verify(ciphertext, tag)

        return data

    def encrypt64(self, public_key, data):
        """ data must be bytes and not string """
        return base64.b64encode(self.encrypt(public_key, data)).decode("utf-8")

    def decrypt64(self, private_key, string):
        return self.decrypt(private_key, base64.b64decode(string))

class CipherConfigDecryptor(object):
    """

    Note: this decryptor is meant as a stepping stone towards
    better implementations, such as a parameter store decryptor
    It should only be used if better options are not available

    """

    prefix = "ENC:"

    def __init__(self):
        super(CipherConfigDecryptor, self).__init__()
        self.cm = CryptoManager()
        self.pem = None

    def init(self):
        """ initialize the secret decryptor
        this module expects the secret key to be passed in via stdin
        """
        if not sys.stdin.isatty():
            self.pem = sys.stdin.read()

    def decrypt(self, data):
        """ decrypts a base64 encoded string prefixed with prefix
        """
        if self.pem is None:
            raise Exception("CipherConfigDecryptor not initialized")
        data = data[len(ParameterStoreConfigDecryptor.prefix):]
        return self.cm.decrypt64(self.pem, data)

class ParameterStoreConfigDecryptor(object):
    prefix = "SSM:"

    def __init__(self):
        super(ParameterStoreConfigDecryptor, self).__init__()

    def init(self):
        pass

    def decrypt(self, data):
        """ retrieve a value from a parameter store given a key
        """
        data = data[len(ParameterStoreConfigDecryptor.prefix):]
        raise NotImplementedError("ssm decryption not implemented")
