
import os
import hmac
import base64
import struct
import json
import time

class WebTokenException(Exception):
    pass

class WebTokenExpired(WebTokenException):
    pass

class WebTokenInvalidSignature(WebTokenException):
    pass

class WebToken(object):
    """
    Create and Verify JWT-like authentication tokens

    Like JWT, this uses a 3 dotted sections of base-64 encoded data.
    The first section is a binary header.
    The second section is user provided data,.
    The last section is a sha-256 HMAC signature, using the provided key

    The header contains a magic number, version, timestamp for
    when the token was issued, and when it expires, and a 4 byte salt.
    This construction ensures that for any given user data a unique
    signature will be produced.

    The user data can be any sequence of bytes. for JWT compatability, the
    user data should be utf-8 encoded json.



    """
    ONE_HOUR =  60 * 60
    ONE_DAY = 24 * ONE_HOUR
    TWO_WEEKS = 14 * ONE_DAY

    EPOCH_BASE = 1577836800 # 2020/01/01T00:00

    def __init__(self, key, expires_in=TWO_WEEKS):
        super(WebToken, self).__init__()
        self.version = 1
        if isinstance(key, str):
            self.key = key.encode("utf-8")
        else:
            self.key = key
        self.expires_in = expires_in

    def create(self, payload):
        issued_at = self.now()
        expires_at = issued_at + self.expires_in
        salt = os.urandom(4)

        hdr = struct.pack(">2sBLL4s", b'WT',
            self.version, issued_at, expires_at, salt)

        bdy = b".".join([base64.urlsafe_b64encode(hdr),
                 base64.urlsafe_b64encode(payload), b''])

        h = hmac.new(self.key, bdy, "sha256")
        tag = base64.urlsafe_b64encode(h.digest())

        return (bdy + tag).decode("utf-8")

    def verify(self, token):

        if isinstance(token, str):
            token = token.encode("utf-8")

        index = token.rfind(b".")
        bdy = token[:index + 1]
        tag = token[index + 1:]

        h = hmac.new(self.key, bdy, "sha256")
        actual_tag = base64.urlsafe_b64encode(h.digest())

        if not hmac.compare_digest(actual_tag, tag):
            raise WebTokenInvalidSignature("signature validation failed")

        parts = bdy.split(b".")
        if len(parts) != 3: # one empty part
            raise WebTokenException("malformed token")

        hdr = base64.urlsafe_b64decode(parts[0])

        magic, version, issued_at, expires_at, salt = struct.unpack(
            ">2sBLL4s", hdr)

        if magic != b"WT":
            raise WebTokenException("invalid magic: %d" % magic)

        if version != 1:
            raise WebTokenException("invalid version: %d" % version)

        now = self.now()

        if expires_at < now:
            raise WebTokenExpired("expired token")

        payload = base64.urlsafe_b64decode(parts[1])

        return payload


    def now(self):
        return int(time.time()) - WebToken.EPOCH_BASE

