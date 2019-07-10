
import unittest
import io
import uuid
import time
import base64

from .crypt import \
    FileEncryptorWriter, FileEncryptorReader, \
    FileDecryptorWriter, FileDecryptorReader, \
    cryptkey, decryptkey, recryptkey, validatekey, \
    new_stream_cipher, get_stream_cipher, \
    KEY_LENGTH, KEY_LENGTH_PARTS, \
    uuid_token_generate, uuid_token_verify

class CryptTestCase(unittest.TestCase):

    def test_new_cipher_get_cipher(self):

        sampletext = b"hello world"
        key1 = b"0" * 32
        key2 = b"1" * 32
        cipher, header = new_stream_cipher(b"0" * 32)

        ciphertext = cipher.encrypt(sampletext)
        # when the correct password is used, a new cipher is used
        cipher = get_stream_cipher(key1, header)

        # show that new_cipher / get_cipher can be used to round-trip data
        plaintext = cipher.decrypt(ciphertext)
        self.assertEqual(plaintext, sampletext)

        # when an incorrect password is used, a value error is raised
        with self.assertRaises(ValueError):
            get_stream_cipher(key2, header)

    def test_crypt_1(self):

        key1 = b'0' * 32
        nonce = b"1" * 8
        key2 = b'0' * 32
        text = b'The secret message to encrypt client side.'

        # ---------------------------------------------------------------------
        # test 1:
        # show that encrypting while writing works regardless of the write size

        bf = io.BytesIO()
        enc = FileEncryptorWriter(bf, key1, nonce, key2)
        enc.write(text)
        ciphertext = bf.getvalue()

        for i in range(1, len(text)):
            bw = io.BytesIO()
            enc = FileEncryptorWriter(bw, key2, nonce, key2)
            for j in range(0, len(text), i):
                enc.write(text[j:j + i])
            ciphertext_out = bw.getvalue()
            self.assertEqual(ciphertext, ciphertext_out)

    def test_crypt_2(self):

        key = b'0' * 32
        text = b'The secret message to encrypt client side.'

        # ---------------------------------------------------------------------
        # test 2:
        # show that decrypting while reading works regardless of the read size

        bf = io.BytesIO()
        enc = FileEncryptorWriter(bf, key)
        enc.write(text)

        for i in range(1, len(text)):
            bf.seek(0)
            dec = FileDecryptorReader(bf, key)
            text_out = b"".join(iter(lambda: dec.read(i), b""))
            self.assertEqual(text_out, text)

        bf.seek(0)
        dec = FileDecryptorReader(bf, key)
        text_out = dec.read()

    def test_crypt_3(self):

        key1 = b'0' * 32
        key2 = b'0' * 32
        nonce = b'1' * 8
        text = b'The secret message to encrypt client side.'

        # ---------------------------------------------------------------------
        # test 3:
        # show that encrypting while reading works regardless of the write size

        bf = io.BytesIO(text)
        dec = FileEncryptorReader(bf, key1, nonce, key2)
        ciphertext = dec.read()

        for i in range(1, len(text)):
            bf = io.BytesIO(text)
            dec = FileEncryptorReader(bf, key1, nonce, key2)
            ciphertext_out = b"".join(iter(lambda: dec.read(i), b""))
            self.assertEqual(ciphertext, ciphertext_out)

    def test_crypt_4(self):

        key = b'0' * 32
        text = b'The secret message to encrypt client side.'

        # ---------------------------------------------------------------------
        # test 4:
        # show that decrypting while writing works regardless of the write size

        bf = io.BytesIO(text)
        enc = FileEncryptorReader(bf, key)
        ciphertext = enc.read()

        for i in range(1, len(ciphertext)):
            bw = io.BytesIO()
            dec = FileDecryptorWriter(bw, key)
            for j in range(0, len(ciphertext), i):
                dec.write(ciphertext[j:j + i])
            self.assertEqual(bw.getvalue(), text)

    def test_crypt_5(self):

        key = b'0' * 32
        text = b'The secret message to encrypt client side.'

        # ---------------------------------------------------------------------
        # test 5:
        # show that enc/dec is auto-closeable in a context manager

        bf = io.BytesIO(text)
        with FileEncryptorWriter(bf, key) as enc:
            enc.write(text)
            self.assertEqual(bf.getvalue()[:4], b'EYUE')
        self.assertTrue(bf.closed)

    def test_keygen_1(self):
        # these tests use the minimum workfactor to speed up testing

        salt = b'$2b$04$0GNJpMOV5WWVtdVjOP/PMe'
        expected_enckey = b'0' * 32
        # the key is made up of a bcrypt salt, salsa 20 nonce,
        # the encrypted key, and finally an HMAC for the previous 3 components
        expected_key = '01:$2b$04$0GNJpMOV5WWVtdVjOP/PMe:MTExMTExMTE=:' \
            'Oyf9QOxkAcpw3e7L1StFEAymudz76FZ+RD2CKC8bH4M=:' \
            'NRzAs5Vb8DaOpo3KiNrMQKS75Ln7MEJDoL6B9h6CUCc='
        key = cryptkey("password", b"0" * 32, b"1" * 8, salt)
        self.assertEqual(expected_key, key)

        enckey = decryptkey("password", key)
        self.assertEqual(expected_enckey, enckey)

    def test_keygen_2(self):
        """ test the typical use case """
        expected_enckey = b'1' * 32
        key = cryptkey("password", expected_enckey, workfactor=4)
        enckey = decryptkey("password", key)
        self.assertEqual(expected_enckey, enckey)

    def test_keygen_3(self):
        """ show that an invalid password fails to decrypt the key """
        expected_enckey = b'1' * 32
        key = cryptkey("password", expected_enckey, workfactor=4)
        with self.assertRaises(ValueError):
            decryptkey("invalid", key)
        enckey = decryptkey("password", key)
        self.assertEqual(expected_enckey, enckey)

    def test_keygen_4(self):
        # a ValueError is raised if the salt is not a valid bcrypt salt

        salt = b'invalid'
        with self.assertRaises(ValueError):
            key = cryptkey("password", b"0" * 32, b"1" * 8, salt)

    def test_keygen_5(self):
        """ show that a key can be re-encrypted """
        expected_enckey = b'1' * 32
        key = cryptkey("password", expected_enckey, workfactor=4)
        new_key = recryptkey("password", "secret", key)
        enckey = decryptkey("secret", new_key)
        self.assertEqual(expected_enckey, enckey)
        self.assertNotEqual(key, new_key)

    def test_keygen_6(self):
        expected_enckey = b'1' * 32
        key = cryptkey("password", expected_enckey, workfactor=4)
        with self.assertRaises(ValueError):
            recryptkey("invalid", "secret", key)

    def test_keygen_7(self):

        key = cryptkey("password")
        print(key)
        self.assertTrue(validatekey(key))

        # reject a key with an invalid length
        with self.assertRaises(ValueError):
            validatekey("0" * 100)

        # reject valid length keys with invalid characters
        with self.assertRaises(ValueError):
            validatekey("@" * KEY_LENGTH)

        # a key with an incorrect number of colon
        # delimited parts will raise an error
        with self.assertRaises(ValueError):
            validatekey("0" * KEY_LENGTH)

        # reject keys where the salt is incorrect
        with self.assertRaises(ValueError):
            key = ':'.join(["0" * n for n in KEY_LENGTH_PARTS])
            validatekey(key)

        # reject keys where the salt is incorrect
        with self.assertRaises(ValueError):
            key = ["0" * n for n in KEY_LENGTH_PARTS]
            key[1] = '$2b$' + key[1][4:]
            key = ':'.join(key)
            validatekey(key + '0')

    def test_uuidtok_1(self):

        key = b"\x00" * 16
        now = int(time.time())
        uuid_str = str(uuid.uuid4())
        token = uuid_token_generate(key, uuid_str, now=now)
        uuid_out = uuid_token_verify(key, token)

        self.assertEqual(uuid_str, uuid_out)

    def test_uuidtok_2_expires(self):

        # a token generated 4 weeks ago with  a 2 week expiry should
        # fail to validate
        key = b"\x00" * 16
        now = int(time.time()) - 4 * 7 * 24 * 60 * 60
        uuid_str = str(uuid.uuid4())
        token = uuid_token_generate(key, uuid_str, now=now)

        with self.assertRaises(ValueError):
            uuid_out = uuid_token_verify(key, token)

    def test_uuidtok_3_version(self):

        # a token generated 4 weeks ago with  a 2 week expiry should
        # fail to validate
        key = b"\x00" * 16
        now = int(time.time())
        uuid_str = str(uuid.uuid4())
        token = uuid_token_generate(key, uuid_str, now=now)

        with self.assertRaises(ValueError) as e:
            # modify the encrypted data
            data = base64.b64decode(token.encode("ascii") + b'==', b'-+')
            data = b'2' + data[1:]
            token = base64.b64encode(data, b'-+').decode("ascii").rstrip('==')
            uuid_out = uuid_token_verify(key, token)

        self.assertEqual(str(e.exception), 'Invalid token version')

    def test_uuidtok_4_mac(self):

        # a token generated 4 weeks ago with  a 2 week expiry should
        # fail to validate
        key = b"\x00" * 16
        now = int(time.time())
        uuid_str = str(uuid.uuid4())
        token = uuid_token_generate(key, uuid_str, now=now)

        with self.assertRaises(ValueError) as e:
            # modify the encrypted data
            data = base64.b64decode(token.encode("ascii") + b'==', b'-+')
            data = data[:5] + data[5:].upper()
            token = base64.b64encode(data, b'-+').decode("ascii").rstrip('==')
            uuid_out = uuid_token_verify(key, token)

        self.assertEqual(str(e.exception), 'MAC check failed')



def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CryptTestCase)
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
