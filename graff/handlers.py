import cStringIO as StringIO
import datetime
import hashlib
import httplib
import os
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

class RequestHandler(tornado.web.RequestHandler):

    def initialize(self):
        super(RequestHandler, self).initialize()
        self.env = {
            'debug': self.settings['debug'],
            'user': None,
            'today': datetime.date.today()
            }
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = db.Session()
        return self._session

    def finish(self, chunk=None):
        if self._session is not None:
            if self.request.method == 'POST':
                self.session.commit()
            else:
                self.session.rollback()
        return super(RequestHandler, self).finish(chunk)

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'text/html')
        e = {'env': self.env,
             'debug': self.settings['debug'],
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
        raise tornado.web.HTTPError(404)

class MainHandler(RequestHandler):

    path = '/'

    def get(self):
        recent = []
        for p in db.Photo.most_recent(self.session, 10):
            recent.append({'uploaded': p.time_created.strftime('%Y-%m-%d %H:%M'), 'photo_id': p.encid})
        self.env['recent_photos'] = recent
        self.render('main.html')

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
        else:
            lat, lng = None, None
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

        row = db.Photo.insert(
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
            photo_height = img.size[1]
            )
        self.session.commit()
        self.redirect('/photo/' + row.encid)

class PhotoViewHandler(RequestHandler):

    path = '/photo/(.*)'

    def get(self, photo_id):
        self.env['photo_id'] = photo_id
        photo = db.Photo.from_encid(self.session, photo_id)
        self.env['upload_time'] = photo.time_created.strftime('%Y-%m-%d %l:%M %p')
        self.env['photo_time'] = photo.photo_time.strftime('%Y-%m-%d %l:%M %p') if photo.photo_time else 'unknown'
        if photo.latitude is not None and photo.longitude is not None:
            self.env['coordinates'] = '%1.4f, %1.4f' % (photo.latitude, photo.longitude)
        else:
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

handlers = []
for v in globals().values():
    try:
        if issubclass(v, RequestHandler) and getattr(v, 'path', None):
            handlers.append((v.path, v))
    except TypeError:
        pass
handlers.append(('.*', NotFoundHandler))
