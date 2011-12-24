import base64
import binascii
import hashlib
import os
import struct
from Crypto.Cipher import DES3

from graff import config

crypto_secret = config.get('crypto_secret', None)
if crypto_secret is not None:
    crypto_secret = crypto_secret.decode('hex')
elif config.get('memory', False):
    default_secret = os.urandom(16)
else:
    crypto_secret = '?' * 16

##
# from "tempest"
##

PADDING_CHAR = '\0'
BLOCK_SIZE = DES3.block_size
HASH_SIZE = 8
HALF_HASH_SIZE = 4 # hash size to use for 'half-aligned' buffers
IV_SIZE = 8

BASE64_BLOCK_SIZE = 8
BASE64_PADDING_CHAR = '='

BLOB_LEN_SIZE = 4

class InvalidEncryptedId(ValueError):
    pass

def encrypt_blob(plaintext, key):
    lenbuf = struct.pack('!I', len(plaintext))
    assert len(lenbuf) == BLOB_LEN_SIZE
    padding = PADDING_CHAR * ((BLOCK_SIZE - (BLOB_LEN_SIZE + len(plaintext) + HASH_SIZE)) % BLOCK_SIZE)
    return encrypt_buffer(lenbuf + plaintext + padding, key)

def decrypt_blob(ciphertext, key):
    plainbuf = decrypt_buffer(ciphertext, key)
    (bloblen,) = struct.unpack('!I', plainbuf[:BLOB_LEN_SIZE])
    return plainbuf[BLOB_LEN_SIZE:][:bloblen]

def encrypt_string(plaintext, key=None):
    key = key or crypto_secret
    # plaintext must be a string
    assert isinstance(plaintext, str)

    padding = PADDING_CHAR * (BLOCK_SIZE - ((len(plaintext) + HASH_SIZE) % BLOCK_SIZE))
    padded_buffer = plaintext + padding
    return encrypt_buffer(padded_buffer, key)

def decrypt_string(ciphertext, key):
    key = key or crypto_secret
    plaintext = decrypt_buffer(ciphertext, key)
    return plaintext.rstrip(PADDING_CHAR)

# buffer must be padded to crypter.block_size
def encrypt_buffer(buffer, key, half_aligned=False):
    # buffer must be a string
    assert isinstance(buffer, str)
    # create crypter with key and initialization vector (generated as a hash of buffer and key)
    crypter = DES3.new(key, DES3.MODE_CBC, hashlib.sha1(buffer+key).digest()[:IV_SIZE])

    # compute hash of padded buffer
    bufferHash = hashlib.sha1(buffer).digest()
    if half_aligned:
        bufferHash = bufferHash[:HALF_HASH_SIZE]
    else:
        bufferHash = bufferHash[:HASH_SIZE]

    # encrypt the buffer, prepend the IV, and return everything base64'd (minus the trailing newline)
    return trim_base64(base64.encodestring(crypter.IV + crypter.encrypt(buffer + bufferHash)))

# decrypt our base64 (non-standard) encrypted buffer
def decrypt_buffer(buffer, key, half_aligned=False):
    # buffer must be a string
    if type(buffer) is unicode:
        buffer = str(buffer) # if this fails it's OK, the buffer was invalid anyway
    assert isinstance(buffer, str)

    # decode from base64
    tmp = base64.decodestring(fatten_base64(buffer))

    # create crypter with given key, and IV extracted from buffer
    crypter = DES3.new(key, DES3.MODE_CBC, tmp[:IV_SIZE])

    # decrypt the buffer after the IV
    plaintext = crypter.decrypt(tmp[IV_SIZE:])

    # verify that the hash of the fields matches the hash included in the buffer
    if half_aligned:
        hs = HALF_HASH_SIZE
    else:
        hs = HASH_SIZE
    if hashlib.sha1(plaintext[:-hs]).digest()[:hs] != plaintext[-hs:]:
        raise InvalidEncryptedId('encrypted hash does not match')

    return plaintext[:-hs]

# remove the dreaded = signs, they are a huge pain, remap non-url-safe tokens
def trim_base64(b64):
    b64 = b64.replace('\n', '')
    b64 = b64.replace('=', '')
    b64 = b64.replace('+', '_')
    b64 = b64.replace('/', '-')
    return b64

# add back the '=' padding and fix remap url-safe tokens
def fatten_base64(buffer):
    buffer = buffer.replace('_', '+')
    buffer = buffer.replace('-', '/')

    padding = BASE64_PADDING_CHAR * (BASE64_BLOCK_SIZE - (len(buffer) % BASE64_BLOCK_SIZE))
    return buffer + padding


_encid_formats = ('!I', '!Q')

# size in bytes that all tokens should be
_encid_sizes = (22, 32)

def encid_core(id, sixtyfour, key):
    if not isinstance(id, (int, long)):
        raise TypeError("Can only encrypt integers but got: %s (%s)" % (id, type(id)))

    # pack id into a binary buffer
    try:
        buf = struct.pack(_encid_formats[int(bool(sixtyfour))], id)
    except DeprecationWarning:
        raise ValueError('Got integer %d, invalid for struct format %r' % (id, _encid_formats[int(bool(sixtyfour))]))
    return encrypt_buffer(buf, key, not sixtyfour)

def decid_core(id, sixtyfour, key):
    # check to make sure the token is of correct length
    if id is None:
        raise InvalidEncryptedId("None is not a valid id")

    if not isinstance(id, basestring):
        raise InvalidEncryptedId("Can't decrypt values of type %s: %s" % (type(id), repr(id)[:100]))

    # convert id to a string (not a unicode)
    try:
        id = str(id)
    except UnicodeEncodeError, e:
        raise InvalidEncryptedId("Error: '%r'" % (e))

    if len(id) != _encid_sizes[int(bool(sixtyfour))]:
        raise InvalidEncryptedId("encrypted id is wrong size: '%s' (%u)" % (id, _encid_sizes[int(bool(sixtyfour))]))

    try:
        buf = decrypt_buffer(id, key, not sixtyfour)
    except binascii.Error:
        raise InvalidEncryptedId("Error: Incorrect padding: '%s'" % (id))
    except ValueError, e:
        raise InvalidEncryptedId(str(e))
    # unpack and return the id
    return struct.unpack(_encid_formats[int(bool(sixtyfour))], buf)[0]

def encid(num, key=None):
    return encid_core(num, False, key or crypto_secret)

def decid(num, key=None):
    return decid_core(num, False, key or crypto_secret)
