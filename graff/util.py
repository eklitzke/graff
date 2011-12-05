import socket
import struct
from tornado.escape import xhtml_escape
import simplejson as json

class Flash(object):

    def __init__(self, info=None, error=None):
        self.info = info or []
        self.error = error or []

    @classmethod
    def load(cls, val):
        v = json.loads(val)
        return cls(v['info'], v['error'])

    def dump(self):
        return json.dumps({'info': self.info, 'error': self.error})

    @property
    def empty(self):
        return not bool(self.info or self.error)

    def render_html(self):
        def render_bit(css_class, message):
            return '<div class="%s">%s</div>' % (xhtml_escape(css_class), xhtml_escape(message))
        divs = []
        for i in self.info:
            divs.append(render_bit('flash_info', i))
        for e in self.error:
            divs.append(render_bit('flash_error', e))
        html = ''.join(divs)
        self.clear()
        return html

    def clear(self):
        del self.info[:]
        del self.error[:]


def inet_aton(ip_address):
    return struct.unpack('>L', socket.inet_aton(ip_address))[0]

def inet_ntoa(ip_address):
    return socket.inet_ntoa(struct.pack('>L', ip_address))

def detect_mobile(user_agent):
    if ' Android ' in user_agent:
        return True
    elif user_agent.startswith('Mozilla/5.0 (iPhone'):
        return True
    return False
