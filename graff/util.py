import socket
import struct

def inet_aton(ip_address):
    return struct.unpack('>L', socket.inet_aton(ip_address))[0]

def inet_ntoa(ip_address):
    return socket.inet_ntoa(struct.pack('>L', ip_address))
