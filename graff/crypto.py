import base64
from hashlib import sha1
import os
import struct
from Crypto.Cipher import DES3

from graff import config

_default_secret = '?' * 16
encid_secret = config.get('crypto_secret', _default_secret)
if encid_secret != _default_secret:
    encid_secret = encid_secret.decode('hex')

HASH_SIZE = IV_SIZE = BASE64_BLOCK_SIZE = 8
HALF_HASH_SIZE = 4

def norm_b64(s):
    s = s.rstrip('=\n')
    s = s.replace('+', '_')
    s = s.replace('/', '-')
    return s

def unnorm_b64(s):
    s = s.replace('_', '+')
    s = s.replace('-', '/')
    padding = '=' * (BASE64_BLOCK_SIZE - (len(s) % BASE64_BLOCK_SIZE))
    return s + padding

def encid(num, key=encid_secret):
    buf = struct.pack('=I', num)
    crypter = DES3.new(key, DES3.MODE_CBC, sha1(buf + key).digest()[:IV_SIZE])
    buffer_hash = sha1(buf).digest()[:HALF_HASH_SIZE]
    return norm_b64(base64.encodestring(crypter.IV + crypter.encrypt(buf + buffer_hash)))

def decid(buf, key=encid_secret):
    buf = base64.decodestring(unnorm_b64(buf))
    crypter = DES3.new(key, DES3.MODE_CBC, buf[:IV_SIZE])
    plaintext = crypter.decrypt(buf[IV_SIZE:])
    if sha1(plaintext[:-HALF_HASH_SIZE]).digest()[:HALF_HASH_SIZE] != plaintext[-HALF_HASH_SIZE:]:
        raise ValueError('ecnrypted hash does not match')
    return struct.unpack('=I', plaintext[:HALF_HASH_SIZE])[0]
