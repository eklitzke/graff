import optparse
import os
import tornado.ioloop
import tornado.web
from graff.handlers import handlers

def p(name):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), '..', name))
settings = {
    'static_path': p('static'),
    'template_path': p('templates'),
    'cookie_secret': os.environ.get('COOKIE_SECRET', 'rVopzswv48s+GnJWjOfkjL/W35Y=')
    }
del p

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug', action='store_true', default=False)
    parser.add_option('-p', '--port', type='int', default=8000)
    opts, args = parser.parse_args()
    settings['debug'] = opts.debug
    app = tornado.web.Application(handlers, **settings)
    app.listen(opts.port)
    tornado.ioloop.IOLoop.instance().start()
else:
    app = tornado.web.Application(handlers, **settings)
