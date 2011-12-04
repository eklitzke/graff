import cStringIO as StringIO
import datetime
import hashlib
import httplib
import os
import re
import traceback
import PIL.Image
from PIL.ExifTags import GPSTAGS, TAGS
import tornado.template
import tornado.web
from tornado.web import RequestHandler
try:
    import simplejson as json
except ImportError:
    import json

from graff import db
from graff import config

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
            return '<div class="%s">%s</div>' % (tornado.escape.xhtml_escape(css_class), tornado.escape.xhtml_escape(message))
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

class RequestHandler(tornado.web.RequestHandler):

    def initialize(self):
        super(RequestHandler, self).initialize()
        flash_cookie = self.get_cookie('flash')
        if flash_cookie:
            self.flash = Flash.load(tornado.escape.url_unescape(flash_cookie))
        else:
            self.flash = Flash()
        self._force_rollback = False
        self._session = None

        user_id = self.get_secure_cookie('s')
        if user_id:
            self.user = db.User.from_encid(self.session, user_id)
        else:
            self.user = None

        self.env = {
            'config': config,
            'debug': self.settings['debug'],
            'flash': self.flash,
            'gmaps_api_key': config.get('gmaps_api_key', 'AIzaSyCTd_7j6ZeXATLOfTvpAqaqCkxM0zFP5Oc'),
            'is_error': False,
            'user': self.user,
            'today': datetime.date.today()
            }

    @property
    def session(self):
        if self._session is None:
            self._session = db.Session()
        return self._session

    def finish(self, chunk=None):
        if self._session is not None:
            if self._force_rollback or self.request.method != 'POST':
                self.session.rollback()
            else:
                self.session.commit()
        if not self.flash.empty:
            self.set_cookie('flash', tornado.escape.url_escape(self.flash.dump()))
        elif 'flash' in self.request.cookies:
            self.clear_cookie('flash')
        return super(RequestHandler, self).finish(chunk)

    def write_error(self, status_code, **kwargs):
        self._force_rollback = True
        self.set_header('Content-Type', 'text/html')
        e = {'env': self.env,
             'debug': self.settings['debug'],
             'flash': self.flash,
             'is_error': False,
             'user': self.env['user'],
             'title': httplib.responses[status_code],
             }
        if 500 <= status_code <= 599:
            e['is_error'] = True
            tb = []
            for line in traceback.format_exception(*kwargs['exc_info']):
                tb.append(line)
            e['traceback'] = '\n'.join(tb)
        self.write(self.render_string("error.html", **e))
        return self.finish()

    def render(self, name):
        return super(RequestHandler, self).render(name, **self.env)

class NotFoundHandler(RequestHandler):
    """Generates an error response with status_code for all requests."""

    def prepare(self):
        raise tornado.web.HTTPError(httplib.NOT_FOUND)

class HomeHandler(RequestHandler):

    path = '/'

    def get(self):
        recent = []
        self.env['recent_photos'] = list(db.Photo.most_recent(self.session, 10))
        v = lambda x: x is not None
        self.env['latlng'] = [{'lat': p.latitude, 'lng': p.longitude} for p in self.env['recent_photos'] if v(p.latitude) and v(p.longitude)]
        if self.env['latlng']:
            minlat = min(x['lat'] for x in self.env['latlng'])
            maxlat = max(x['lat'] for x in self.env['latlng'])
            minlng = min(x['lng'] for x in self.env['latlng'])
            maxlng = max(x['lng'] for x in self.env['latlng'])
            self.env['center'] = {'lat': 0.5 * (minlat + maxlat), 'lng': 0.5 * (minlng + maxlng)}
            self.env['sw_point'] = {'lat': minlat, 'lng': minlng}
            self.env['ne_point'] = {'lat': maxlat, 'lng': maxlng}
        else:
            self.env['center'] = None
        self.render('home.html')

NAME_RE = re.compile(r'[-_~a-zA-Z0-9@!\$]*$')
class SignupHandler(RequestHandler):

    path = '/signup'

    def get(self):
        self.render('signup.html')

    def post(self):
        name = self.get_argument('name')
        if not NAME_RE.match(name):
            self.flash.error.append('Username contains characters that are not allowed')
            self.redirect('/signup')
            return
        if name.lower() == 'anonymous':
            self.flash.error.append('That username is reserved.')
            self.redirect('/signup')
            return
        if len(name) > 32:
            self.flash.error.append('Username is too long; restrict to at most 32 characters.')
            self.redirect('/signup')
            return

        password = self.get_argument('password')
        email = self.get_argument('email', None)
        location = self.get_argument('location', None)

        user = db.User.create(
            self.session,
            name = name,
            password = password,
            email = email,
            location = location
            )
        if isinstance(user, basestring):
            self.flash.error.append(user)
            self.redirect('/signup')
        else:
            self.session.commit()
            self.set_secure_cookie('s', user.encid)
            self.redirect('/user/' + name)

class LoginHandler(RequestHandler):

    path = '/login'

    def post(self):
        name = self.get_argument('name')
        password = self.get_argument('password')
        user = db.User.authenticate(self.session, name, password)
        if user:
            self.set_secure_cookie('s', user.encid)
            self.redirect('/')
        else:
            self.flash.error.append('Failed to login with that username/password')
            self.redirect('/signup')

class LogoutHandler(RequestHandler):

    path = '/logout'

    def get(self):
        self.clear_cookie('s')
        self.flash.info.append('Come back soon!')
        self.redirect('/')

    post = get

def construct_path(fsid, content_type, makedirs=False):
    p = os.path.join(os.environ.get('TEMPDIR', '/tmp'), 'graff', fsid[:2], fsid[2:4])
    if makedirs and not os.path.exists(p):
        os.makedirs(p)
    return os.path.join(p, fsid[4:])

class UploadHandler(RequestHandler):

    path = '/upload'

    def decode_gps(self, gps_field):
        gpsinfo = dict((GPSTAGS.get(k, k), v) for k, v in gps_field.iteritems())
        for field in ('GPSLatitudeRef', 'GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude'):
            assert field in gpsinfo
        assert all(x == 1 for _, x in gpsinfo['GPSLatitude'])
        assert all(x == 1 for _, x in gpsinfo['GPSLongitude'])
        assert gpsinfo['GPSLatitudeRef'] in 'NS'
        assert gpsinfo['GPSLongitudeRef'] in 'EW'
        lat = gpsinfo['GPSLatitude']
        lat = lat[0][0] + lat[1][0] / 60.0 + lat[2][0] / 3600.0
        if gpsinfo['GPSLatitudeRef'] == 'S':
            lat *= -1
        lng = gpsinfo['GPSLongitude']
        lng = lng[0][0] + lng[1][0] / 60.0 + lng[2][0] / 3600.0
        if gpsinfo['GPSLongitudeRef'] == 'W':
            lng *= -1
        return lat, lng


    def save_versions(self, img, imgtype, outpath):

        def save_img(i, extension):
            with open(outpath + '.' + extension, 'wb') as f:
                i.save(f, imgtype)

        # save the original size
        save_img(img, 'o') 
        img_width, img_height = img.size

        if img_width == img_height:
            square_img = img.copy()
        elif img_width > img_height:
            lhs = int(0.5 * (img_width - img_height))
            rhs = lhs + img_height
            square_img = img.crop((lhs, 0, rhs, img_height))
        else:
            t = int(0.5 * (img_height - img_width))
            b = t + img_width
            square_img = img.crop((0, t, img_width, b))

        assert square_img.size[0] == square_img.size[1]

        #save_img(square_img, 'os')

        def fit_preserve_aspect(im, max_width, max_height):
            """Resize the image to (max_width, max_height) without cropping or
            altering the aspect ratio. Returns a new PIL.Image object.
            """
            i = im.copy()
            i.thumbnail((max_width, max_height), PIL.Image.BICUBIC)
            return i

        save_img(fit_preserve_aspect(img, 900, 600), 'l')
        save_img(fit_preserve_aspect(square_img, 900, 600), 'ls')
        save_img(fit_preserve_aspect(img, 150, 100), 'm')
        save_img(fit_preserve_aspect(square_img, 150, 100), 'ms')
        save_img(fit_preserve_aspect(img, 32, 32), 't')
        save_img(fit_preserve_aspect(square_img, 32, 32), 'ts')
        save_img(fit_preserve_aspect(img, 20, 20), 's')
        save_img(fit_preserve_aspect(square_img, 20, 20), 'ss')

    def post(self):
        try:
            img_fields = self.request.files['img']
        except KeyError:
            self.send_error(httplib.BAD_REQUEST)
            return
        assert len(img_fields) == 1
        img_fields = img_fields[0] # XXX: why?
        body_hash = hashlib.sha1(img_fields['body']).hexdigest()
        img_file = StringIO.StringIO(img_fields['body'])
        content_type = img_fields['content_type'].lower()
        img = PIL.Image.open(img_file)
        raw_info = img._getexif()
        raw_exif = img.info['exif']
        info = dict((TAGS.get(k, k), v) for k, v in raw_info.iteritems())
        if 'Orientation' in info:
            orientation = info['Orientation']
            if orientation == 1:
                pass
            elif orientation == 2:
                img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                img = img.transpose(PIL.Image.ROTATE_180)
            elif orientation == 4:
                img = img.transpose(PIL.Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:
                img = img.transpose(PIL.Image.ROTATE_90)
                img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            elif orientation == 6:
                img = img.transpose(PIL.Image.ROTATE_270)
            elif orientation == 7:
                img = img.transpose(PIL.Image.ROTATE_270)
                img = img.transpose(PIL.Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:
                img = img.transpose(PIL.Image.ROTATE_90)
        if 'GPSInfo' in info:
            lat, lng = self.decode_gps(info['GPSInfo'])
            sensor = True
        else:
            lat, lng = None, None
            sensor = None
        dt = info.get('DateTime')
        if dt is not None:
            dt = datetime.datetime.strptime(dt, '%Y:%m:%d %H:%M:%S')
        make = info.get('Make')
        model = info.get('Model')
        
        fsid = os.urandom(16).encode('hex')
        fspath = construct_path(fsid, content_type, makedirs=True)

        if content_type == 'image/jpeg':
            pil_type = 'JPEG'
        else:
            pil_type = None

        with open(fspath + '.exif', 'wb') as f:
            f.write(raw_exif)
        self.save_versions(img, pil_type, fspath)

        row = db.Photo.create(
            self.session,
            body_hash = body_hash,
            content_type = content_type,
            fsid = fsid,
            latitude = lat,
            longitude = lng,
            make = make,
            model = model,
            photo_time = dt,
            photo_width = img.size[0],
            photo_height = img.size[1],
            sensor = sensor,
            user_id = self.user.id if self.user else None
            )
        self.session.commit()
        self.redirect('/photo/' + row.encid)

class PhotoViewHandler(RequestHandler):

    path = '/photo/(.*)'

    def get(self, photo_id):
        self.env['photo_id'] = photo_id
        photo = db.Photo.from_encid(self.session, photo_id)
        self.env['photo'] = photo
        if self.user and photo.user.id == self.user.id:
            self.env['own_photo'] = True
        else:
            self.env['own_photo'] = False
        self.env['upload_time'] = photo.time_created.strftime('%Y-%m-%d %l:%M %p')
        self.env['photo_time'] = photo.photo_time.strftime('%Y-%m-%d %l:%M %p') if photo.photo_time else 'unknown'
        if photo.latitude is not None and photo.longitude is not None:
            self.env['has_coordinates'] = True
            self.env['sensor'] = 'true' if photo.sensor else 'false'
            self.env['coordinates'] = '%1.4f, %1.4f' % (photo.latitude, photo.longitude)
        else:
            self.env['has_coordinates'] = False
            self.env['coordinates'] = 'unknown'
        self.render('photo.html')

class PhotoHandler(RequestHandler):

    path = '/p/(.*)'

    def get(self, photo_id):
        if '.' in photo_id:
            encid, size = photo_id.split('.')
        else:
            self.redirect('/p/' + photo_id + '.o')
            return

        photo = db.Photo.from_encid(self.session, encid)
        self.set_header('Content-Type', photo.content_type)
        #self.set_header('Last-Modified', photo.photo_time or p
        fspath = construct_path(photo.fsid, photo.content_type) + '.' + size
        st = os.stat(fspath)
        self.set_header('Content-Length', st.st_size)
        with open(fspath, 'rb') as f:
            self.write(f.read())

class UserHandler(RequestHandler):

    path = '/user/(.*)'

    def get(self, user_name):
        target_user = db.User.by_name(self.session, user_name)
        if target_user is None:
            raise HTTPError(httplib.NOT_FOUND)
        self.env['target_user'] = target_user
        self.render('user.html')


handlers = []
for v in globals().values():
    try:
        if issubclass(v, RequestHandler) and getattr(v, 'path', None):
            handlers.append((v.path, v))
    except TypeError:
        pass

# if no other rules match, use the 404 handler
handlers.append(('.*', NotFoundHandler))
