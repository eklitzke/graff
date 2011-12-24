import os
import sys
from graff import config

settings = {}
if os.isatty(sys.stdin.fileno()):
    import optparse
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config', help='Path to the config file')
    parser.add_option('-d', '--debug', action='store_true', default=False)
    parser.add_option('-p', '--port', type='int', default=9000)
    parser.add_option('-n', '--num-procs', type='int', default=0)
    parser.add_option('--memory', default=False, action='store_true', help='use a sqlite:///:memory: table for the database')
    opts, args = parser.parse_args()
    config.load_config(opts.config, memory=opts.memory)
    config.setdefault('cookie_secret', os.urandom(16) if opts.memory else '----------------')
    settings['debug'] = opts.debug
else:
    config.load_config(None, memory=False)
    assert config.get('cookie_secret') is not None

settings['cookie_secret'] = config.get('cookie_secret')

import tornado.httpserver
import tornado.ioloop
import tornado.web
from graff.handlers import handlers
from graff.ui import modules

def p(name):
    return os.path.realpath(os.path.join(os.path.dirname(__file__), '..', name))
settings['static_path'] = p('static')
settings['template_path'] = p('templates')
settings['ui_modules'] = modules
del p

if __name__ == '__main__':
    app = tornado.web.Application(handlers, **settings)
    server = tornado.httpserver.HTTPServer(app, xheaders=True)
    server.bind(opts.port)
    num_procs = 1 if opts.debug or opts.memory else opts.num_procs
    server.start(num_procs)
    tornado.ioloop.IOLoop.instance().start()
else:
    app = tornado.web.Application(handlers, **settings)
